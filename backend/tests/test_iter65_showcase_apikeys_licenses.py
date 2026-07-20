"""Iteration 65: showcase partners, admin API keys, public API v1, licenses (marque blanche)."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"
    })
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# ---- Showcase partners ----

class TestShowcasePartners:
    def test_admin_crud_and_public_filter(self, admin_session):
        name = f"TEST_Partner_{uuid.uuid4().hex[:6]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/showcase/partners",
                               json={"name": name, "link": "https://x.test"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["is_active"] is True
        assert r.json()["name"] == name

        # List admin (all)
        r = admin_session.get(f"{BASE_URL}/api/admin/showcase/partners")
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json()["items"])

        # Patch (rename + hide)
        new_name = name + "_ren"
        r = admin_session.patch(f"{BASE_URL}/api/admin/showcase/partners/{pid}",
                                json={"name": new_name, "is_active": False})
        assert r.status_code == 200

        # Public should NOT show inactive
        pub = requests.get(f"{BASE_URL}/api/showcase/partners")
        assert pub.status_code == 200
        assert all(p["id"] != pid for p in pub.json()["items"])

        # Re-activate
        r = admin_session.patch(f"{BASE_URL}/api/admin/showcase/partners/{pid}",
                                json={"is_active": True})
        assert r.status_code == 200
        pub = requests.get(f"{BASE_URL}/api/showcase/partners")
        assert any(p["id"] == pid and p["name"] == new_name for p in pub.json()["items"])
        # Sort order ascending
        orders = [p["sort_order"] for p in pub.json()["items"]]
        assert orders == sorted(orders)

        # Move up
        r = admin_session.post(f"{BASE_URL}/api/admin/showcase/partners/{pid}/move?direction=up")
        assert r.status_code == 200

        # Delete
        r = admin_session.delete(f"{BASE_URL}/api/admin/showcase/partners/{pid}")
        assert r.status_code == 200
        r = admin_session.delete(f"{BASE_URL}/api/admin/showcase/partners/{pid}")
        assert r.status_code == 404


# ---- API keys ----

@pytest.fixture(scope="module")
def created_api_key(admin_session):
    name = f"TEST_KEY_{uuid.uuid4().hex[:6]}"
    r = admin_session.post(f"{BASE_URL}/api/admin/api-keys", json={
        "name": name, "scopes": ["catalog:read", "orders:read", "territories:read", "stock:write"]
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["api_key"].startswith("kdm_live_")
    assert "key_hash" not in data
    yield {"id": data["id"], "key": data["api_key"], "name": name}
    admin_session.delete(f"{BASE_URL}/api/admin/api-keys/{data['id']}")


class TestApiKeysAdmin:
    def test_list_hides_hash(self, admin_session, created_api_key):
        r = admin_session.get(f"{BASE_URL}/api/admin/api-keys")
        assert r.status_code == 200
        body = r.json()
        assert "valid_scopes" in body
        for it in body["items"]:
            assert "key_hash" not in it
        assert any(it["id"] == created_api_key["id"] for it in body["items"])

    def test_create_requires_scope(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/api-keys",
                               json={"name": "TEST_NoScopes", "scopes": []})
        assert r.status_code == 400

    def test_toggle_and_recover(self, admin_session, created_api_key):
        r = admin_session.patch(f"{BASE_URL}/api/admin/api-keys/{created_api_key['id']}")
        assert r.status_code == 200 and r.json()["is_active"] is False
        # public API must return 403 when disabled
        pr = requests.get(f"{BASE_URL}/api/public/v1/ping",
                          headers={"X-API-Key": created_api_key["key"]})
        assert pr.status_code == 403
        # Re-enable
        r = admin_session.patch(f"{BASE_URL}/api/admin/api-keys/{created_api_key['id']}")
        assert r.status_code == 200 and r.json()["is_active"] is True


# ---- Public API v1 ----

class TestPublicApiV1:
    def test_ping_ok(self, created_api_key):
        r = requests.get(f"{BASE_URL}/api/public/v1/ping",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_ping_missing_header(self):
        r = requests.get(f"{BASE_URL}/api/public/v1/ping")
        assert r.status_code == 401

    def test_ping_invalid_key(self):
        r = requests.get(f"{BASE_URL}/api/public/v1/ping",
                         headers={"X-API-Key": "kdm_live_invalid_xxx"})
        assert r.status_code == 401

    def test_scope_missing(self, admin_session):
        # Create key with only catalog:read
        name = f"TEST_KEY_CATALOG_{uuid.uuid4().hex[:6]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/api-keys", json={
            "name": name, "scopes": ["catalog:read"]
        })
        assert r.status_code == 200
        kid = r.json()["id"]
        key = r.json()["api_key"]
        try:
            # orders:read missing → 403
            r = requests.get(f"{BASE_URL}/api/public/v1/orders",
                             headers={"X-API-Key": key})
            assert r.status_code == 403
            # catalog OK
            r = requests.get(f"{BASE_URL}/api/public/v1/products",
                             headers={"X-API-Key": key})
            assert r.status_code == 200
        finally:
            admin_session.delete(f"{BASE_URL}/api/admin/api-keys/{kid}")

    def test_products_pagination(self, created_api_key):
        r = requests.get(f"{BASE_URL}/api/public/v1/products?limit=5&offset=0",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 200
        d = r.json()
        assert d["limit"] == 5 and d["offset"] == 0
        assert "total" in d and "items" in d
        assert len(d["items"]) <= 5

    def test_product_get_and_stock(self, admin_session, created_api_key):
        r = requests.get(f"{BASE_URL}/api/public/v1/products?limit=1",
                         headers={"X-API-Key": created_api_key["key"]})
        items = r.json().get("items", [])
        if not items:
            pytest.skip("No products available")
        pid = items[0]["id"]

        r = requests.get(f"{BASE_URL}/api/public/v1/products/{pid}",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 200
        assert r.json()["id"] == pid

        # PATCH stock
        r = requests.patch(f"{BASE_URL}/api/public/v1/products/{pid}/stock",
                          headers={"X-API-Key": created_api_key["key"]},
                          json={"stock_qty": 42})
        assert r.status_code == 200
        assert r.json()["stock_qty"] == 42

        # 404 unknown product
        r = requests.get(f"{BASE_URL}/api/public/v1/products/does-not-exist",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 404

    def test_orders_and_territories(self, created_api_key):
        r = requests.get(f"{BASE_URL}/api/public/v1/orders?limit=3",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 200
        assert "items" in r.json()

        r = requests.get(f"{BASE_URL}/api/public/v1/territories",
                         headers={"X-API-Key": created_api_key["key"]})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        codes = [t["code"] for t in items]
        assert "GUADELOUPE" in codes or "MARTINIQUE" in codes


# ---- Licenses ----

class TestLicenses:
    def test_full_flow(self, admin_session):
        name = f"TEST_LIC Café Martinique {uuid.uuid4().hex[:4]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/licenses", json={
            "name": name, "territory_code": "MARTINIQUE",
            "tagline": "Le goût du Nord", "primary_color": "#123456"
        })
        assert r.status_code == 200, r.text
        lic = r.json()
        lid = lic["id"]
        slug = lic["slug"]
        assert "café" not in slug  # translittéré
        assert slug.startswith("test-lic-cafe-martinique")

        try:
            # Duplicate slug → 409
            r = admin_session.post(f"{BASE_URL}/api/admin/licenses", json={
                "name": name, "slug": slug, "territory_code": "MARTINIQUE"
            })
            assert r.status_code == 409

            # Unknown territory → 404
            r = admin_session.post(f"{BASE_URL}/api/admin/licenses", json={
                "name": "TEST_bad", "territory_code": "ZZ_UNKNOWN"
            })
            assert r.status_code == 404

            # Public GET works
            r = requests.get(f"{BASE_URL}/api/licenses/{slug}")
            assert r.status_code == 200
            body = r.json()
            assert body["name"] == name
            assert body["primary_color"] == "#123456"
            assert "stats" in body
            assert set(["products", "orders", "vendors"]).issubset(body["stats"].keys())

            # PATCH deactivate → public 404
            r = admin_session.patch(f"{BASE_URL}/api/admin/licenses/{lid}",
                                    json={"is_active": False})
            assert r.status_code == 200
            r = requests.get(f"{BASE_URL}/api/licenses/{slug}")
            assert r.status_code == 404

            # Reactivate
            r = admin_session.patch(f"{BASE_URL}/api/admin/licenses/{lid}",
                                    json={"is_active": True})
            assert r.status_code == 200

            # Update bad territory
            r = admin_session.patch(f"{BASE_URL}/api/admin/licenses/{lid}",
                                    json={"territory_code": "ZZ_NOPE"})
            assert r.status_code == 404
        finally:
            admin_session.delete(f"{BASE_URL}/api/admin/licenses/{lid}")

    def test_public_slug_not_found(self):
        r = requests.get(f"{BASE_URL}/api/licenses/does-not-exist-slug-xyz")
        assert r.status_code == 404
