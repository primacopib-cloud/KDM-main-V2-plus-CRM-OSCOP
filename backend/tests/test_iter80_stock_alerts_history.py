"""Iter80 : Seuil stock alerte + historique stock — routes_stock_admin.py"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
PRODUCT_ID = "61c31a9c-d072-4988-9a39-76ca46520bba"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"})
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_stock_endpoints_require_auth():
    r1 = requests.put(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
                      json={"zone_code": "MARTINIQUE", "quantity_available": 40})
    r2 = requests.get(f"{BASE_URL}/api/catalog/admin/stock-history?product_id={PRODUCT_ID}")
    assert r1.status_code in (401, 403), f"PUT unauth expected 401/403 got {r1.status_code}"
    assert r2.status_code in (401, 403), f"GET unauth expected 401/403 got {r2.status_code}"


def test_low_stock_alert_triggered_and_reset(auth_headers):
    # First ensure MARTINIQUE=40 (baseline above threshold)
    r0 = requests.put(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
                     headers=auth_headers,
                     json={"zone_code": "MARTINIQUE", "quantity_available": 40})
    assert r0.status_code == 200, r0.text

    # Drop below threshold (10)
    r1 = requests.put(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
                     headers=auth_headers,
                     json={"zone_code": "MARTINIQUE", "quantity_available": 8})
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1.get("low_stock_alert_triggered") is True, body1

    # Restore to 40 -> alert should NOT trigger
    r2 = requests.put(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
                     headers=auth_headers,
                     json={"zone_code": "MARTINIQUE", "quantity_available": 40})
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2.get("low_stock_alert_triggered") is False, body2
    assert body2.get("quantity_available") == 40


def test_stock_history_entries(auth_headers):
    r = requests.get(f"{BASE_URL}/api/catalog/admin/stock-history?product_id={PRODUCT_ID}",
                     headers=auth_headers)
    assert r.status_code == 200, r.text
    entries = r.json().get("entries", [])
    assert isinstance(entries, list)
    assert len(entries) >= 2, f"Expected history entries after prior updates, got {len(entries)}"
    e = entries[0]
    for key in ("old_quantity", "new_quantity", "author_email", "created_at", "zone_code"):
        assert key in e, f"Missing key {key} in {e}"


def test_final_martinique_is_40(auth_headers):
    r = requests.get(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}", headers=auth_headers)
    assert r.status_code == 200
    stocks = {s["zone_code"]: s for s in r.json().get("stocks", [])}
    assert stocks.get("MARTINIQUE", {}).get("quantity_available") == 40
