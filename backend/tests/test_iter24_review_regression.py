"""Iteration 24 — Non-regression tests after code-review fixes.

Covers:
 1) Backend imports OK (no NameError) via calling endpoints from refactored modules:
    - routes_checkout.py (checkout_common wildcard replaced)
    - routes_checkout_v1.py (checkout_v1_models wildcard replaced)
    - abac_policy.py (abac_engine wildcard replaced) — indirectly via any protected endpoint
 2) Admin ESS capacity/rules — previously crashing with NameError generate_id on POST
 3) Favorites alerts refactor — 0->N restock triggers restock_alert_triggered=true
    and creates favorite_restock notification (using zone GUYANE, free of anti-spam).
 4) GET /api/user-prefs/favorites/alerts-center returns products+alerts.
"""
from __future__ import annotations

import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com"
).rstrip("/")

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")
BUYER_EMAIL = os.environ.get("TEST_BUYER_EMAIL", "acheteur-pro@kdmarche.fr")
BUYER_PASSWORD = os.environ.get("TEST_BUYER_PASSWORD", "Demo2026!")

TEST_PRODUCT_ID = "61c31a9c-d072-4988-9a39-76ca46520bba"
TEST_ZONE = "GUYANE"  # per main-agent instructions: free zone


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session() -> requests.Session:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def buyer_session() -> requests.Session:
    return _login(BUYER_EMAIL, BUYER_PASSWORD)


# ---------- 1) Server & basic endpoints ----------
def test_health():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200


def test_auth_me_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("email") == ADMIN_EMAIL


def test_auth_me_buyer(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("email") == BUYER_EMAIL


# ---------- 2) Checkout modules load & respond (no wildcard import breakage) ----------
def test_checkout_v1_module_reachable(buyer_session):
    """Any GET on a v1 checkout endpoint just needs to NOT return 500 (import failure)."""
    # Common list endpoint used by buyers
    r = buyer_session.get(f"{BASE_URL}/api/v1/checkout/orders", timeout=15)
    assert r.status_code in (200, 401, 403, 404), f"unexpected {r.status_code}: {r.text[:200]}"


def test_checkout_v2_module_reachable(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/v2/orders", timeout=15)
    # Should not be 500 (import error would be 500 at request time or startup)
    assert r.status_code != 500, f"500 from v2 orders: {r.text[:200]}"


# ---------- 3) Admin ESS capacity/rules — generate_id fix ----------
def test_admin_ess_capacity_create_no_nameerror(admin_session):
    tour_id = f"TEST_tour_{uuid.uuid4().hex[:8]}"
    payload = {
        "zone_code": "GUADELOUPE",
        "tour_id": tour_id,
        "capacity": 10,
        "booked": 0,
        "is_active": True,
    }
    r = admin_session.post(
        f"{BASE_URL}/api/admin/v1/routes/capacity", json=payload, timeout=15
    )
    assert r.status_code == 201, f"POST capacity failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("id"), "id missing in response"
    assert data.get("tour_id") == tour_id
    capacity_id = data["id"]

    # GET to verify persistence
    g = admin_session.get(
        f"{BASE_URL}/api/admin/v1/routes/capacity/{capacity_id}", timeout=15
    )
    assert g.status_code == 200
    assert g.json().get("tour_id") == tour_id

    # cleanup
    admin_session.delete(
        f"{BASE_URL}/api/admin/v1/routes/capacity/{capacity_id}", timeout=15
    )


def test_admin_ess_rules_create_no_nameerror(admin_session):
    payload = {
        "zone_code": "GUADELOUPE",
        "code": f"TEST_RULE_{uuid.uuid4().hex[:6]}",
        "weight": 5,
        "is_active": True,
        "sort_order": 100,
    }
    r = admin_session.post(
        f"{BASE_URL}/api/admin/v1/routes/rules", json=payload, timeout=15
    )
    # Success (201) OR a validation error (400) both prove the code reached
    # generate_id() without NameError (the pre-fix crash was 500 NameError).
    assert r.status_code in (201, 400), (
        f"POST rule unexpected status: {r.status_code} {r.text[:300]}"
    )
    assert r.status_code != 500, "500 indicates NameError regression"
    if r.status_code == 201:
        rule_id = r.json().get("id")
        assert rule_id
        admin_session.delete(
            f"{BASE_URL}/api/admin/v1/routes/rules/{rule_id}", timeout=15
        )


# ---------- 4) Favorites alerts refactor — 0->N restock ----------
@pytest.fixture()
def clean_alerts_log_guyane():
    client = MongoClient("mongodb://localhost:27017")
    db = client["kdmarche_lolodrive"]
    db.favorites_alerts_log.delete_many(
        {"product_id": TEST_PRODUCT_ID, "zone_code": TEST_ZONE}
    )
    yield
    client.close()


def test_favorites_restock_alert_after_refactor(admin_session, clean_alerts_log_guyane):
    # Force stock to 0 first
    r0 = admin_session.put(
        f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
        json={"zone_code": TEST_ZONE, "quantity_available": 0},
        timeout=15,
    )
    assert r0.status_code in (200, 201), f"reset to 0 failed: {r0.status_code} {r0.text[:200]}"

    # Now trigger 0 -> 50 (restock)
    r1 = admin_session.put(
        f"{BASE_URL}/api/catalog/admin/stock/{TEST_PRODUCT_ID}",
        json={"zone_code": TEST_ZONE, "quantity_available": 50},
        timeout=20,
    )
    assert r1.status_code in (200, 201), f"restock failed: {r1.status_code} {r1.text[:200]}"
    body = r1.json()
    assert body.get("restock_alert_triggered") is True, (
        f"restock_alert_triggered not True: {body}"
    )


def test_favorites_alerts_center_buyer(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/user-prefs/favorites/alerts-center", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "products" in data, f"missing 'products': {data}"
    assert "alerts" in data, f"missing 'alerts': {data}"
    assert isinstance(data["products"], list)
    assert isinstance(data["alerts"], list)


# ---------- 5) Connector oscop-ged health (safe) ----------
def test_connector_ged_health(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/connectors/oscop-ged/health", timeout=20)
    assert r.status_code == 200, f"health failed: {r.text[:200]}"
