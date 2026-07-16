"""LOT 4 refactor regression: vendor split (vendor_models, routes_vendor_admin) + superadmin split (activity, stats)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
VENDOR_ID = "vendor-demo-pro"


@pytest.fixture(scope="session")
def http():
    return requests.Session()


def _login(http, creds):
    r = http.post(f"{API}/auth/login", json={"email": creds[0], "password": creds[1]}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(http):
    return _login(http, ADMIN)


@pytest.fixture(scope="session")
def buyer_token(http):
    return _login(http, BUYER)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ----- Vendor public endpoints (routes_vendor.py residual + vendor_models split) -----
class TestVendorPublic:
    def test_countries(self, http):
        r = http.get(f"{API}/vendor/countries", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        countries = data["countries"] if isinstance(data, dict) else data
        assert isinstance(countries, list) and len(countries) > 0

    def test_vendor_dashboard(self, http):
        r = http.get(f"{API}/vendor/dashboard/{VENDOR_ID}", timeout=15)
        assert r.status_code == 200, r.text

    def test_vendor_products(self, http):
        r = http.get(f"{API}/vendor/products/{VENDOR_ID}", timeout=15)
        assert r.status_code == 200, r.text


# ----- Vendor Admin (routes_vendor_admin.py — moved) -----
class TestVendorAdmin:
    def test_admin_list(self, http, admin_token):
        r = http.get(f"{API}/vendor/admin/list", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_admin_products_pending(self, http, admin_token):
        r = http.get(f"{API}/vendor/admin/products/pending", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_alias_admin_products_pending(self, http, admin_token):
        # Alias in routes_core_admin should still forward properly
        r = http.get(f"{API}/admin/products/pending", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text


# ----- Superadmin split (activity + stats moved) -----
class TestSuperadmin:
    def test_kpis(self, http, admin_token):
        r = http.get(f"{API}/superadmin/kpis", params={"period": "month"}, headers=_h(admin_token), timeout=20)
        assert r.status_code == 200, r.text

    def test_alerts(self, http, admin_token):
        r = http.get(f"{API}/superadmin/alerts", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_recent_activity(self, http, admin_token):
        r = http.get(f"{API}/superadmin/recent-activity", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_advanced_stats(self, http, admin_token):
        r = http.get(f"{API}/superadmin/advanced-stats", params={"period": "month"}, headers=_h(admin_token), timeout=20)
        assert r.status_code == 200, r.text

    def test_vendors_kept(self, http, admin_token):
        r = http.get(f"{API}/superadmin/vendors", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text


# ----- Lots 2-3 regression smoke -----
class TestLots23Smoke:
    def test_health(self, http):
        r = http.get(f"{API}/health", timeout=10)
        assert r.status_code == 200

    def test_buyer_login(self, http, buyer_token):
        assert buyer_token

    def test_v2_catalog_products(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200

    def test_zones(self, http):
        r = http.get(f"{API}/zones", timeout=15)
        assert r.status_code == 200
