"""LOT 6 refactor regression: verbatim splits of 15 backend files (non-payment).

Covers new modules/routers included in server.py:
  - shopping_lists_items_router (+ shopping_lists_router)
  - user_prefs_favorites_router (+ user_prefs_router)
  - pod_sign_router (+ pod_router)
  - logiscop_router (models split)
  - ess_router (models split)
  - abac_engine / abac_policy façade -> v2 endpoints
  - schema_catalog {enums, cart} façade -> v2 endpoints
  - schema_preparation defaults / admin_zones_common + admin_zones_public_router
  - ws_manager -> ws_status, notifications endpoints reachable
  - pdf_generators -> /api/v2/pdf/orders/{fake} non-500
  - contracts_models -> /api/contracts/transport/disclaimer
  - export_common -> /api/admin/export/{summary,organizations}

Reachability + non-500 tolerance. Stripe LIVE keys → no real charges.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")


@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(http, creds):
    r = http.post(f"{API}/auth/login", json={"email": creds[0], "password": creds[1]}, timeout=30)
    assert r.status_code == 200, f"login {creds[0]} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(http):
    return _login(http, ADMIN)


@pytest.fixture(scope="session")
def buyer_token(http):
    return _login(http, BUYER)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ============ Server import health ============
class TestServerHealth:
    def test_health(self, http):
        r = http.get(f"{API}/health", timeout=10)
        assert r.status_code == 200


# ============ Split #1 — Shopping Lists (common + main + items) ============
class TestShoppingLists:
    def test_frequencies_options(self, http, buyer_token):
        r = http.get(f"{API}/shopping-lists/options/frequencies", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_list_empty_or_populated(self, http, buyer_token):
        r = http.get(f"{API}/shopping-lists", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_full_crud_flow(self, http, buyer_token):
        # Create
        payload = {"name": "TEST_LOT6_REG_LIST", "description": "regression lot6", "frequency": "weekly", "color": "#00AA55"}
        r = http.post(f"{API}/shopping-lists", headers=_h(buyer_token), json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        created = r.json()
        list_id = created.get("id") or created.get("_id")
        assert list_id, created

        try:
            # Get
            r = http.get(f"{API}/shopping-lists/{list_id}", headers=_h(buyer_token), timeout=15)
            assert r.status_code == 200, r.text
            assert r.json()["name"] == "TEST_LOT6_REG_LIST"

            # Patch
            r = http.patch(f"{API}/shopping-lists/{list_id}", headers=_h(buyer_token), json={"description": "updated"}, timeout=15)
            assert r.status_code == 200, r.text
            assert r.json()["description"] == "updated"

            # Items endpoint reachable (validation-triggered non-500)
            r = http.post(f"{API}/shopping-lists/{list_id}/items", headers=_h(buyer_token), json={}, timeout=15)
            assert r.status_code in (200, 400, 404, 422), r.text

            # Duplicate reachable
            r = http.post(f"{API}/shopping-lists/{list_id}/duplicate", headers=_h(buyer_token), timeout=15)
            assert r.status_code in (200, 400, 422), r.text
            if r.status_code == 200:
                dup_id = r.json().get("id")
                if dup_id:
                    http.delete(f"{API}/shopping-lists/{dup_id}", headers=_h(buyer_token), timeout=10)

            # Use reachable
            r = http.post(f"{API}/shopping-lists/{list_id}/use", headers=_h(buyer_token), timeout=15)
            assert r.status_code in (200, 400, 404, 422), r.text
        finally:
            # Delete cleanup
            r = http.delete(f"{API}/shopping-lists/{list_id}", headers=_h(buyer_token), timeout=15)
            assert r.status_code in (200, 204), r.text


# ============ Split #2 — User Prefs (common + shortcuts + favorites) ============
class TestUserPrefs:
    def test_shortcuts_get(self, http, buyer_token):
        r = http.get(f"{API}/user-prefs/shortcuts", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_shortcuts_suggestions(self, http, buyer_token):
        r = http.get(f"{API}/user-prefs/shortcuts/suggestions", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_favorites_get(self, http, buyer_token):
        r = http.get(f"{API}/user-prefs/favorites", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_favorites_ids(self, http, buyer_token):
        r = http.get(f"{API}/user-prefs/favorites/ids", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_favorite_toggle_flow(self, http, buyer_token):
        pid = "TEST_LOT6_PROD_NONEXISTENT_XYZ"
        # Toggle should not 500 even for unknown product id
        r = http.post(f"{API}/user-prefs/favorites/{pid}/toggle", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (200, 400, 404, 422), r.text
        # Clean up if added
        http.delete(f"{API}/user-prefs/favorites/{pid}", headers=_h(buyer_token), timeout=10)


# ============ Split #3 — POD (models + main + sign) ============
class TestPOD:
    def test_pod_generate_empty_422(self, http, admin_token):
        r = http.post(f"{API}/delivery/pod/generate", headers=_h(admin_token), json={}, timeout=15)
        assert r.status_code in (400, 401, 403, 422), r.text

    def test_pod_get_fake_404(self, http, admin_token):
        r = http.get(f"{API}/delivery/pod/nonexistent-abc-123", headers=_h(admin_token), timeout=15)
        assert r.status_code in (401, 403, 404), r.text

    def test_pod_verify_reachable(self, http):
        r = http.get(f"{API}/delivery/pod/verify/FAKECODE123", timeout=15)
        assert r.status_code in (200, 400, 404), r.text

    def test_pod_by_order_reachable(self, http, admin_token):
        r = http.get(f"{API}/delivery/pod/by-order/fake-order-id", headers=_h(admin_token), timeout=15)
        assert r.status_code in (200, 401, 403, 404), r.text


# ============ Split #4 — Logiscop (models + main) ============
class TestLogiscop:
    def test_pickup_locations(self, http):
        r = http.get(f"{API}/logiscop/pickup-locations", timeout=15)
        assert r.status_code == 200, r.text

    def test_delivery_slots(self, http):
        r = http.get(f"{API}/logiscop/delivery-slots", timeout=15)
        assert r.status_code == 200, r.text

    def test_rates(self, http):
        r = http.get(f"{API}/logiscop/rates", timeout=15)
        assert r.status_code == 200, r.text

    def test_quote_reachable(self, http, buyer_token):
        payload = {
            "pickup_location_id": "PU-BAIE-MAHAULT",
            "delivery_zone": "GP-BT",
            "items": [{"sku": "RHUM-DAMOISEAU-VSOP-70CL", "quantity": 2}],
        }
        r = http.post(f"{API}/logiscop/quote", headers=_h(buyer_token), json=payload, timeout=20)
        assert r.status_code in (200, 400, 404, 422), r.text


# ============ Split #5 — ESS (models + main) ============
class TestESS:
    def test_disclaimer(self, http):
        # ess_router prefix "/api/ess"; endpoint "/disclaimer" -> /api/ess/disclaimer
        r = http.get(f"{API}/ess/disclaimer", timeout=15)
        assert r.status_code == 200, r.text

    def test_tours(self, http):
        r = http.get(f"{API}/ess/tours?zone_code=GUADELOUPE", timeout=15)
        assert r.status_code == 200, r.text

    def test_policy_zone(self, http):
        r = http.get(f"{API}/ess/policy/GUADELOUPE", timeout=15)
        assert r.status_code in (200, 404), r.text

    def test_quote_reachable(self, http, buyer_token):
        r = http.post(f"{API}/ess/quote", headers=_h(buyer_token), json={}, timeout=15)
        assert r.status_code in (200, 400, 401, 422), r.text


# ============ Split #6 — ABAC engine/policy façade -> v2 endpoints ============
class TestABAC:
    def test_v2_catalog_products_buyer(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_v2_cart_reachable(self, http, buyer_token):
        r = http.get(f"{API}/v2/cart", headers=_h(buyer_token), timeout=15)
        # buyer may lack org -> 400; must not be 500
        assert r.status_code in (200, 400, 401, 403, 404), r.text

    def test_v2_orders_reachable(self, http, buyer_token):
        r = http.get(f"{API}/v2/orders", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (200, 400, 401, 403, 404), r.text


# ============ Split #7 — schema_catalog + schema_preparation + admin_zones_public ============
class TestSchemaAndZones:
    def test_admin_v1_zones(self, http, admin_token):
        r = http.get(f"{API}/admin/v1/zones", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_public_zone_prep_options(self, http):
        # admin_zones_public_router prefix /api/admin/v1, endpoint /public/zones/{code}/prep-options
        r = http.get(f"{API}/admin/v1/public/zones/GUADELOUPE/prep-options", timeout=15)
        assert r.status_code in (200, 404), r.text

    def test_apply_cart_prep_options_reachable(self, http, buyer_token):
        r = http.post(f"{API}/admin/v1/b2b/cart/prep-options/apply", headers=_h(buyer_token), json={}, timeout=15)
        assert r.status_code in (200, 400, 401, 403, 404, 422), r.text


# ============ Split #8 — websockets (ws_manager) ============
class TestWebsockets:
    def test_ws_status(self, http):
        r = http.get(f"{API}/ws/status", timeout=15)
        assert r.status_code in (200, 401), r.text

    def test_notifications_route(self, http, buyer_token):
        # any notifications endpoint reachable — not 500
        r = http.get(f"{API}/notifications", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (200, 401, 404), r.text


# ============ Split #9 — pdf_generators / contracts_models / export_common ============
class TestPDFAndContractsAndExport:
    def test_pdf_orders_fake(self, http):
        # No auth -> should be 401 or 404, must NOT be 500
        r = http.get(f"{API}/v2/pdf/orders/nonexistent-abc", timeout=15)
        assert r.status_code in (401, 403, 404), r.text

    def test_contracts_transport_disclaimer(self, http):
        r = http.get(f"{API}/contracts/transport/disclaimer", timeout=15)
        assert r.status_code == 200, r.text

    def test_export_summary_admin(self, http, admin_token):
        r = http.get(f"{API}/admin/export/summary", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200, r.text

    def test_export_organizations_csv(self, http, admin_token):
        r = http.get(f"{API}/admin/export/organizations", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        # CSV or JSON — either OK, just not empty
        assert len(r.content) > 0


# ============ Split #10 — schema_product_card_parts (vendor endpoint smoke) ============
class TestProductCard:
    def test_v2_catalog_reachable(self, http, buyer_token):
        # product card parts used within catalog schema — v2 catalog must render
        r = http.get(f"{API}/v2/catalog/products?limit=1", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text
