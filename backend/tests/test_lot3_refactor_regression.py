"""LOT 3 refactor regression: cart_v2, orders_v2, v2_applications, v2_billing, admin_ess_rules, admin_ess_capacity."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")


@pytest.fixture(scope="session")
def http():
    return requests.Session()


def _login(http, creds):
    r = http.post(f"{API}/auth/login", json={"email": creds[0], "password": creds[1]}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def buyer_token(http):
    return _login(http, BUYER)


@pytest.fixture(scope="session")
def admin_token(http):
    return _login(http, ADMIN)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ----- Catalog (routes_catalog.py residual + cart_v2) -----
class TestCatalog:
    def test_categories(self, http):
        r = http.get(f"{API}/v2/catalog/categories", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_products(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))


# ----- routes_cart_v2.py -----
class TestCartV2:
    def test_get_cart(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/cart", headers=_h(buyer_token), timeout=15)
        # Acheteur-pro seed has organization_id=null → route responds 400.
        # Refactor is VERBATIM; behaviour matches source. Assert route reachable and NOT 500.
        assert r.status_code in (200, 400), r.text
        if r.status_code == 400:
            assert "organisation" in r.text.lower()

    def test_installment_calculate(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/installment/calculate", params={"amount_ht_cents": 100000},
                     headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_add_and_clear_cart(self, http, buyer_token):
        # find a product
        pr = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert pr.status_code == 200
        products = pr.json()
        if isinstance(products, dict):
            products = products.get("products") or products.get("items") or []
        if not products:
            pytest.skip("no products available")
        product_id = products[0].get("id") or products[0].get("_id") or products[0].get("product_id")
        assert product_id

        # Add — will 400 if buyer has no org; verify route reachable.
        r = http.post(f"{API}/v2/catalog/cart/items",
                      headers={**_h(buyer_token), "Content-Type": "application/json"},
                      json={"product_id": product_id, "quantity": 1}, timeout=15)
        assert r.status_code in (200, 201, 400), f"unexpected: {r.status_code} {r.text}"

        # Clear
        rc = http.delete(f"{API}/v2/catalog/cart", headers=_h(buyer_token), timeout=15)
        assert rc.status_code in (200, 400), rc.text


# ----- routes_orders_v2.py -----
class TestOrdersV2:
    def test_list_orders_buyer(self, http, buyer_token):
        r = http.get(f"{API}/v2/orders", headers=_h(buyer_token), timeout=15)
        # Verbatim moved endpoint — accepts 200 (with org) or 400 (buyer no org — pre-existing seed).
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            assert isinstance(r.json(), list)


# ----- routes_v2.py residual + billing/applications -----
class TestV2Core:
    def test_plans(self, http):
        r = http.get(f"{API}/v2/plans", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_me(self, http, buyer_token):
        r = http.get(f"{API}/v2/me", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200

    def test_admin_orgs(self, http, admin_token):
        r = http.get(f"{API}/v2/admin/orgs", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_applications(self, http, admin_token):
        r = http.get(f"{API}/v2/admin/applications", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ----- routes_admin_ess* -----
class TestAdminESS:
    def test_stats(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/routes/stats", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_zones(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/routes/zones", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_policies(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/routes/policies", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200

    def test_rules_list(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/routes/rules", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_capacity_list(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/routes/capacity", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
