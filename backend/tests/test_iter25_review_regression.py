"""Iteration 25 — Non-regression tests for 2nd code-review pass.
Focus: explicit imports (schema_catalog re-exports, routes_logiscop TRANSPORT_RATES_PER_M3,
routes_payment payment_models), plus cart/order v2 flow that depends on schema_catalog re-exports.
"""
import os
import pytest
import requests

def _read_frontend_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_url()).rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PASSWORD = "Demo2026!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def buyer_session():
    return _login(BUYER_EMAIL, BUYER_PASSWORD)


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


# ============ schema_catalog re-exports (routes_catalog / routes_cart_v2 / routes_orders_v2) ============

class TestSchemaCatalogReexports:
    def test_v2_catalog_products(self, buyer_session):
        r = buyer_session.get(f"{BASE_URL}/api/v2/catalog/products", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else data.get("products") or data.get("items") or []
        assert len(items) > 0, "No products returned"

    def test_v2_catalog_categories(self, buyer_session):
        r = buyer_session.get(f"{BASE_URL}/api/v2/catalog/categories", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        cats = data if isinstance(data, list) else data.get("categories") or data.get("items") or []
        assert isinstance(cats, list)

    def test_v2_cart_and_orders_list(self, buyer_session):
        # GET current cart (v2) — must not raise NameError from re-exports
        r = buyer_session.get(f"{BASE_URL}/api/v2/cart", timeout=15)
        assert r.status_code in (200, 404), r.text
        # List orders (v2)
        r2 = buyer_session.get(f"{BASE_URL}/api/v2/orders", timeout=15)
        assert r2.status_code == 200, r2.text

    def test_v2_add_to_cart_then_get_cart(self, buyer_session):
        # find a product
        rp = buyer_session.get(f"{BASE_URL}/api/v2/catalog/products", timeout=15)
        items = rp.json() if isinstance(rp.json(), list) else rp.json().get("products") or rp.json().get("items") or []
        if not items:
            pytest.skip("No products available")
        pid = items[0].get("id") or items[0].get("product_id")
        assert pid
        # add to cart (best-effort: multiple endpoint shapes exist)
        add = buyer_session.post(
            f"{BASE_URL}/api/v2/cart/items",
            json={"product_id": pid, "quantity": 1},
            timeout=15,
        )
        # accept success or business errors, but NOT 500 NameError
        assert add.status_code != 500, f"500 on add-to-cart: {add.text}"
        assert add.status_code in (200, 201, 400, 404, 409, 422), add.text
        # get cart still functional
        rc = buyer_session.get(f"{BASE_URL}/api/v2/cart", timeout=15)
        assert rc.status_code in (200, 404)


# ============ routes_logiscop explicit imports (TRANSPORT_RATES_PER_M3) ============

class TestLogiscopImports:
    def test_pickup_locations(self):
        r = requests.get(f"{BASE_URL}/api/logiscop/pickup-locations", timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_rates_includes_per_m3(self):
        r = requests.get(f"{BASE_URL}/api/logiscop/rates", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "rates_per_kg" in data
        assert "rates_per_m3" in data, "TRANSPORT_RATES_PER_M3 missing from response"
        assert data["rates_per_m3"], "rates_per_m3 must be non-empty"

    def test_delivery_quote_uses_per_m3(self):
        # ensure TRANSPORT_RATES_PER_M3 is referenced without NameError
        payload = {
            "zone_code": "GUADELOUPE",
            "weight_kg": 12.0,
            "volume_m3": 0.15,
            "items_count": 3,
            "slot": "standard",
            "delivery_type": "standard",
        }
        r = requests.post(f"{BASE_URL}/api/logiscop/quote", json=payload, timeout=15)
        assert r.status_code != 500, f"500 on delivery quote (possible NameError): {r.text}"
        assert r.status_code in (200, 400, 422), r.text
        if r.status_code == 200:
            data = r.json()
            assert "total_ttc_cents" in data
            assert data["total_ttc_cents"] > 0


# ============ routes_payment explicit imports (CREDIT_PACKAGES / payment_models) ============

class TestPaymentImports:
    def test_packages(self):
        r = requests.get(f"{BASE_URL}/api/payments/packages", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "packages" in data, data
        assert isinstance(data["packages"], list)
        assert len(data["packages"]) > 0
        assert data.get("currency") == "EUR"

    def test_bank_details(self):
        r = requests.get(f"{BASE_URL}/api/payments/bank-details", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "bank_details" in data


# ============ Quick admin auth regression ============

class TestAdminAuth:
    def test_admin_me(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("email") == ADMIN_EMAIL
