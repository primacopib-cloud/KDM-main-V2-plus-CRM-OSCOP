"""Iter 61 backend tests: Territoires (CRUD admin) + bug commandes acheteur."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"},
               timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def buyer_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"},
               timeout=30)
    assert r.status_code == 200, f"buyer login failed: {r.status_code} {r.text}"
    return s


# --- Territoires ---
def test_list_territories_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/territories", timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    codes = {i["code"]: i for i in items}
    assert len(items) >= 7, f"expected >=7 zones, got {len(items)}: {list(codes.keys())}"
    assert "GUADELOUPE" in codes, "GUADELOUPE zone missing"
    assert codes["GUADELOUPE"].get("is_active") is True, "GUADELOUPE must be active"
    assert codes["GUADELOUPE"]["orders_count"] >= 1, \
        f"GUADELOUPE orders_count should be >=1, got {codes['GUADELOUPE']['orders_count']}"


def test_list_territories_buyer_forbidden(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/admin/territories", timeout=30)
    assert r.status_code == 403, f"expected 403 got {r.status_code}"


def test_territory_full_crud_and_public_visibility(admin_session):
    code = "TEST_ZONE_IT61"
    # cleanup residues if any
    admin_session.delete(f"{BASE_URL}/api/admin/territories/{code}", timeout=30)

    # ADD (with lowercase input to test upper-case conversion)
    r = admin_session.post(f"{BASE_URL}/api/admin/territories",
                           json={"code": code.lower(), "name": "Zone Test 61"}, timeout=30)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["code"] == code
    assert doc["is_active"] is True

    # duplicate -> 409
    r = admin_session.post(f"{BASE_URL}/api/admin/territories",
                           json={"code": code, "name": "dup"}, timeout=30)
    assert r.status_code == 409

    def _pub_codes():
        j = requests.get(f"{BASE_URL}/api/v2/zones", timeout=30).json()
        arr = j if isinstance(j, list) else j.get("items", [])
        return {z["code"] for z in arr}

    # Visible in public zones
    codes_pub = _pub_codes()
    assert code in codes_pub, f"new zone not in public /api/v2/zones: {codes_pub}"

    # HIDE
    r = admin_session.patch(f"{BASE_URL}/api/admin/territories/{code}",
                            json={"is_active": False}, timeout=30)
    assert r.status_code == 200

    codes_pub = _pub_codes()
    assert code not in codes_pub, "hidden zone still appears in public listing"

    # REACTIVATE
    r = admin_session.patch(f"{BASE_URL}/api/admin/territories/{code}",
                            json={"is_active": True}, timeout=30)
    assert r.status_code == 200
    codes_pub = _pub_codes()
    assert code in codes_pub

    # DELETE
    r = admin_session.delete(f"{BASE_URL}/api/admin/territories/{code}", timeout=30)
    assert r.status_code == 200

    # After delete gone
    r = admin_session.get(f"{BASE_URL}/api/admin/territories", timeout=30)
    codes_all = {i["code"] for i in r.json()["items"]}
    assert code not in codes_all


def test_delete_territory_with_orders_forbidden(admin_session):
    r = admin_session.delete(f"{BASE_URL}/api/admin/territories/GUADELOUPE", timeout=30)
    assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text}"
    assert "masquez" in r.text.lower() or "commande" in r.text.lower()
    # Ensure still present + active
    r = admin_session.get(f"{BASE_URL}/api/admin/territories", timeout=30)
    codes = {i["code"]: i for i in r.json()["items"]}
    assert "GUADELOUPE" in codes and codes["GUADELOUPE"]["is_active"] is True


# --- Bug commandes acheteur ---
def test_buyer_orders_list_ok(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/v2/orders", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) >= 1, f"expected >=1 order for acheteur-pro, got {len(items)}"
