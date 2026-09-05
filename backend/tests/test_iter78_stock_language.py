"""Iter 78 — Stock zone admin GET/PUT + Profile language memory."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
PRODUCT_ID = "61c31a9c-d072-4988-9a39-76ca46520bba"
INITIAL_STOCKS = {"MARTINIQUE": 40, "GUADELOUPE": 30, "GUYANE": 50, "REUNION": 100}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@kdmarche-oscop.fr",
        "password": "AdminKDM2025!",
        "portal": "admin",
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---- Stock admin ----

def test_stock_get_requires_auth():
    r = requests.get(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}")
    assert r.status_code in (401, 403)


def test_stock_get_returns_zones(admin_headers):
    r = requests.get(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}", headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["product_id"] == PRODUCT_ID
    assert isinstance(data["stocks"], list)
    zone_codes = {s["zone_code"] for s in data["stocks"]}
    # Should include the 4 zones
    for z in INITIAL_STOCKS:
        assert z in zone_codes, f"Zone {z} missing: got {zone_codes}"


def test_stock_put_updates_and_persists(admin_headers):
    # Update MARTINIQUE to 999
    r = requests.put(
        f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
        headers=admin_headers,
        json={"zone_code": "MARTINIQUE", "quantity_available": 999},
    )
    assert r.status_code == 200, r.text
    assert r.json()["quantity_available"] == 999

    # Verify persistence via GET
    g = requests.get(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}", headers=admin_headers)
    stocks = {s["zone_code"]: s["quantity_available"] for s in g.json()["stocks"]}
    assert stocks["MARTINIQUE"] == 999


def test_zzz_restore_stocks(admin_headers):
    """Restore initial stocks — must run last (zzz prefix)."""
    for zone, qty in INITIAL_STOCKS.items():
        r = requests.put(
            f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}",
            headers=admin_headers,
            json={"zone_code": zone, "quantity_available": qty},
        )
        assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/catalog/admin/stock/{PRODUCT_ID}", headers=admin_headers)
    stocks = {s["zone_code"]: s["quantity_available"] for s in g.json()["stocks"]}
    for z, q in INITIAL_STOCKS.items():
        assert stocks[z] == q


# ---- Profile language ----

def test_language_get(admin_headers):
    r = requests.get(f"{BASE_URL}/api/profile/language", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert "language" in r.json()


def test_language_set_gcf_then_fr(admin_headers):
    r = requests.post(f"{BASE_URL}/api/profile/language", headers=admin_headers, json={"language": "gcf"})
    assert r.status_code == 200
    assert r.json()["language"] == "gcf"

    g = requests.get(f"{BASE_URL}/api/profile/language", headers=admin_headers)
    assert g.json()["language"] == "gcf"

    # Restore to FR
    r2 = requests.post(f"{BASE_URL}/api/profile/language", headers=admin_headers, json={"language": "fr"})
    assert r2.status_code == 200
    assert r2.json()["language"] == "fr"


def test_language_invalid(admin_headers):
    r = requests.post(f"{BASE_URL}/api/profile/language", headers=admin_headers, json={"language": "xx"})
    assert r.status_code == 422


def test_zzz_final_language_fr(admin_headers):
    """Ensure ends in FR."""
    requests.post(f"{BASE_URL}/api/profile/language", headers=admin_headers, json={"language": "fr"})
    g = requests.get(f"{BASE_URL}/api/profile/language", headers=admin_headers)
    assert g.json()["language"] == "fr"
