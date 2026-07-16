"""Iteration 23 — Connectors (OSCOP-GED / OSCOP-Finance) + Favorites Restock/Promo Alerts.

Safety notes:
- DO NOT call POST /api/connectors/push/order/* (creates real payment in remote prod CRM).
- Retry of existing GED ERROR event is safe (remote upload will fail again).
- Price of the tested product is restored at teardown.
"""
from __future__ import annotations

import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")
BUYER_EMAIL = os.environ.get("TEST_BUYER_EMAIL", "acheteur-pro@kdmarche.fr")
BUYER_PASSWORD = os.environ.get("TEST_BUYER_PASSWORD", "Demo2026!")

TEST_PRODUCT_ID = "61c31a9c-d072-4988-9a39-76ca46520bba"  # Riz long grain 5kg
TEST_ZONE = "MARTINIQUE"
ORIGINAL_PRICE_CENTS = 1250


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session() -> requests.Session:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def buyer_session() -> requests.Session:
    return _login(BUYER_EMAIL, BUYER_PASSWORD)


@pytest.fixture()
def clean_alerts_log():
    """Purge favorites_alerts_log for the tested product to bypass the 24h anti-spam gate."""
    client = MongoClient("mongodb://localhost:27017")
    db = client["kdmarche_lolodrive"]
    db.favorites_alerts_log.delete_many({"product_id": TEST_PRODUCT_ID})
    yield db
    client.close()


# --------------------------- Connectors ---------------------------
class TestConnectors:
    def test_list_connectors(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/connectors", timeout=20)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        names = {c["name"]: c for c in data["connectors"]}
        assert "oscop-ged" in names
        assert "oscop-finance" in names
        assert names["oscop-ged"]["enabled"] is True
        assert names["oscop-finance"]["enabled"] is True

    def test_ged_health(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/connectors/oscop-ged/health", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["status"] == "OK", f"unexpected: {data}"
        assert data.get("external", {}).get("status") == "healthy", f"external not healthy: {data}"

    def test_sync_events_list_and_counts(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/connectors/sync-events", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "events" in data and "counts" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["counts"], dict)

    def test_sync_events_filter_error(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/connectors/sync-events?status=ERROR", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for ev in data["events"]:
            assert ev["status"] == "ERROR"

    def test_retry_existing_error_event(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/connectors/sync-events?status=ERROR&connector=oscop-ged", timeout=20)
        assert r.status_code == 200
        events = r.json()["events"]
        if not events:
            pytest.skip("No ERROR event to retry")
        ev_id = events[0]["id"]
        r2 = admin_session.post(f"{BASE_URL}/api/connectors/sync-events/{ev_id}/retry", timeout=45)
        assert r2.status_code == 200, r2.text[:300]
        # Retry expected to remain ERROR (known remote CRM bug)
        result = r2.json()
        assert result.get("status") in ("ERROR", "SUCCESS"), f"unexpected retry status: {result}"


# --------------------------- Admin route protection ---------------------------
class TestAdminProtection:
    def test_buyer_forbidden_connectors(self, buyer_session):
        r = buyer_session.get(f"{BASE_URL}/api/connectors", timeout=20)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"

    def test_buyer_forbidden_stock_admin(self, buyer_session):
        r = buyer_session.put(
            f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "quantity_available": 5},
            timeout=20,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"


# --------------------------- Favorites: Restock alert ---------------------------
class TestRestockAlert:
    def _get_notif_count(self, session, ntype: str) -> int:
        r = session.get(f"{BASE_URL}/api/notifications?limit=100", timeout=20)
        if r.status_code != 200:
            return 0
        data = r.json()
        notifs = data.get("notifications", data) if isinstance(data, dict) else data
        return sum(1 for n in notifs if n.get("type") == ntype)

    def test_restock_flow_and_antispam(self, admin_session, buyer_session, clean_alerts_log):
        # Baseline notif count for buyer
        before = self._get_notif_count(buyer_session, "favorite_restock")

        # 1) Force stock to 0
        r0 = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "quantity_available": 0},
            timeout=20,
        )
        assert r0.status_code == 200, r0.text[:300]
        assert r0.json()["restock_alert_triggered"] is False

        # 2) Bring stock back > 0 -> alert should trigger
        r1 = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "quantity_available": 25},
            timeout=20,
        )
        assert r1.status_code == 200, r1.text[:300]
        assert r1.json()["restock_alert_triggered"] is True

        time.sleep(3)  # allow async task
        after_first = self._get_notif_count(buyer_session, "favorite_restock")
        assert after_first > before, f"expected new restock notification (before={before}, after={after_first})"

        # 3) Repeat 0 -> >0 : trigger flag True, but no new notif due to 24h anti-spam
        admin_session.put(
            f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "quantity_available": 0},
            timeout=20,
        )
        r3 = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "quantity_available": 40},
            timeout=20,
        )
        assert r3.json()["restock_alert_triggered"] is True

        time.sleep(3)
        after_second = self._get_notif_count(buyer_session, "favorite_restock")
        assert after_second == after_first, (
            f"anti-spam 24h broken: notifications went {after_first} -> {after_second}"
        )


# --------------------------- Favorites: Promo alert ---------------------------
class TestPromoAlert:
    def _get_notif_count(self, session, ntype: str) -> int:
        r = session.get(f"{BASE_URL}/api/notifications?limit=100", timeout=20)
        if r.status_code != 200:
            return 0
        data = r.json()
        notifs = data.get("notifications", data) if isinstance(data, dict) else data
        return sum(1 for n in notifs if n.get("type") == ntype)

    def test_price_up_no_alert_then_price_down_triggers(self, admin_session, buyer_session, clean_alerts_log):
        before = self._get_notif_count(buyer_session, "favorite_promo")

        # Ensure baseline: set price to ORIGINAL_PRICE_CENTS (may or may not trigger promo depending on current)
        # Then raise price (no promo)
        r_up = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/price/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "price_ht_cents": ORIGINAL_PRICE_CENTS + 200},
            timeout=20,
        )
        assert r_up.status_code == 200, r_up.text[:300]
        assert r_up.json()["promo_alert_triggered"] is False

        # Price down -> promo alert triggered
        r_dn = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/price/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "price_ht_cents": ORIGINAL_PRICE_CENTS - 100},
            timeout=20,
        )
        assert r_dn.status_code == 200
        assert r_dn.json()["promo_alert_triggered"] is True

        time.sleep(3)
        after = self._get_notif_count(buyer_session, "favorite_promo")
        assert after > before, f"expected new promo notification (before={before}, after={after})"

    def test_teardown_restore_price(self, admin_session):
        r = admin_session.put(
            f"{BASE_URL}/api/catalog/admin/price/{TEST_PRODUCT_ID}",
            json={"zone_code": TEST_ZONE, "price_ht_cents": ORIGINAL_PRICE_CENTS},
            timeout=20,
        )
        assert r.status_code == 200
        # Restoring to lower-than-current may trigger promo — acceptable, just ensure endpoint OK
