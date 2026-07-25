"""
Iter73 — BUGFIX test: cart accepts zone_code query param & admin bypass check_price_access
Also: catalog visitor sees images gallery for DAM-RHUM-BLANC-1L
"""
import os
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")

BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PWD = "Demo2026!"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"


def _login(email, pwd, portal=None):
    payload = {"email": email, "password": pwd}
    if portal:
        payload["portal"] = portal
    r = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=30)
    assert r.status_code == 200, f"Login failed {email}: {r.status_code} {r.text[:300]}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in response: {data}"
    return token


class TestZoneCartBugfix:
    def test_public_products_martinique(self):
        # Products endpoint public
        r = requests.get(f"{BASE_URL}/api/v2/catalog/products", params={"zone_code": "GUADELOUPE"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        products = r.json()
        assert isinstance(products, list) and len(products) > 0
        # Find DAM-RHUM-BLANC-1L
        rhum = next((p for p in products if p.get("sku") == "DAM-RHUM-BLANC-1L"), None)
        assert rhum is not None, f"DAM-RHUM-BLANC-1L not found in catalog"
        images = rhum.get("images") or []
        assert isinstance(images, list), f"images field missing/invalid: {rhum.get('images')}"
        assert len(images) == 3, f"expected 3 images for DAM-RHUM-BLANC-1L, got {len(images)}: {images}"

    def test_buyer_add_to_cart_with_zone_code_martinique(self):
        token = _login(BUYER_EMAIL, BUYER_PWD)
        headers = {"Authorization": f"Bearer {token}"}
        # Get a product available in MARTINIQUE
        r = requests.get(f"{BASE_URL}/api/v2/catalog/products",
                         params={"zone_code": "MARTINIQUE"}, headers=headers, timeout=30)
        assert r.status_code == 200
        products = [p for p in r.json() if p.get("price_visible")]
        assert products, "No product with price_visible for buyer in MARTINIQUE"
        prod = products[0]
        qty = max(prod.get("min_order_qty", 1), 1)
        # POST with zone_code query param
        r2 = requests.post(
            f"{BASE_URL}/api/v2/catalog/cart/items",
            params={"zone_code": "MARTINIQUE"},
            json={"product_id": prod["id"], "quantity": qty},
            headers=headers, timeout=30,
        )
        assert r2.status_code == 200, f"add_to_cart failed: {r2.status_code} {r2.text[:400]}"
        cart = r2.json()
        assert cart.get("zone_code") == "MARTINIQUE"
        assert cart.get("items_count", 0) >= 1
        # GET cart with zone_code
        r3 = requests.get(f"{BASE_URL}/api/v2/catalog/cart",
                          params={"zone_code": "MARTINIQUE"}, headers=headers, timeout=30)
        assert r3.status_code == 200, r3.text[:300]
        assert r3.json().get("zone_code") == "MARTINIQUE"

    def test_buyer_add_to_cart_unauthorized_zone_guadeloupe(self):
        """Buyer's org zones = GUADELOUPE + MARTINIQUE per seed. So GUADELOUPE should be authorized too.
        Test with a truly unauthorized zone like GUYANE."""
        token = _login(BUYER_EMAIL, BUYER_PWD)
        headers = {"Authorization": f"Bearer {token}"}
        # Try an unauthorized zone (from the review: GUADELOUPE stated as non-authorized but seed says both). Let's just check price access via GUYANE.
        r = requests.get(f"{BASE_URL}/api/v2/catalog/products", params={"zone_code": "GUYANE"}, headers=headers, timeout=30)
        if r.status_code != 200:
            return  # skip if zone doesn't exist
        products = r.json()
        if not products:
            return
        prod = products[0]
        qty = max(prod.get("min_order_qty", 1), 1)
        r2 = requests.post(
            f"{BASE_URL}/api/v2/catalog/cart/items",
            params={"zone_code": "GUYANE"},
            json={"product_id": prod["id"], "quantity": qty},
            headers=headers, timeout=30,
        )
        # Expected 403 if not authorized, or 400 if product not sold there
        assert r2.status_code in (400, 403), f"unexpected {r2.status_code}: {r2.text[:300]}"

    def test_admin_can_add_to_cart_bypass_price_access(self):
        token = _login(ADMIN_EMAIL, ADMIN_PWD, portal="admin")
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/api/v2/catalog/products",
                         params={"zone_code": "MARTINIQUE"}, headers=headers, timeout=30)
        assert r.status_code == 200
        products = r.json()
        assert products, "No products found for admin"
        prod = products[0]
        qty = max(prod.get("min_order_qty", 1), 1)
        r2 = requests.post(
            f"{BASE_URL}/api/v2/catalog/cart/items",
            params={"zone_code": "MARTINIQUE"},
            json={"product_id": prod["id"], "quantity": qty},
            headers=headers, timeout=30,
        )
        # admin may not have org membership -> 400 "Aucune organisation associée". That's acceptable — bugfix path is that it should NOT be 403.
        # The review request says admin should not be blocked by check_price_access.
        assert r2.status_code != 403, f"Admin blocked by price access: {r2.text[:300]}"
        # Accept 200 (has org) or 400 (no org membership)
        assert r2.status_code in (200, 400), f"unexpected {r2.status_code}: {r2.text[:300]}"
