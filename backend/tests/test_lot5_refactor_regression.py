"""LOT 5 refactor regression: 8 backend file splits reachability.

Splits covered:
  #1 lolodrive_oscoop (client+stripe) + pos + points + manager + admin
  #2 signature (public + admin)
  #3 email_service -> email_alerts (import-time, server boots)
  #4 v1 logiscop (quote) + orders (checkout/orders/delivery-policy)
  #5 opa_bundle (zones/policies/bundle/evaluate)
  #6 admin_plans (plans+options) + credits (credits+stats)
  #7 schema_v2 facade (v2 endpoints still work)
  #8 ged (models/list/render) + ged_admin

DO NOT create real Stripe charges — Stripe LIVE keys are configured.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
MANAGER = ("gerant@lolopoint.fr", "Demo2026!")


@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(http, creds):
    r = http.post(f"{API}/auth/login", json={"email": creds[0], "password": creds[1]}, timeout=30)
    assert r.status_code == 200, f"login failed for {creds[0]}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(http):
    return _login(http, ADMIN)


@pytest.fixture(scope="session")
def buyer_token(http):
    return _login(http, BUYER)


@pytest.fixture(scope="session")
def manager_token(http):
    try:
        return _login(http, MANAGER)
    except AssertionError:
        return None


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ============ Split #3 first — server import health ============
class TestServerHealth:
    def test_health(self, http):
        r = http.get(f"{API}/health", timeout=10)
        assert r.status_code == 200


# ============ Split #1 — lolodrive_oscoop / pos / points / manager / admin ============
class TestLolodrivePublic:
    def test_health(self, http):
        r = http.get(f"{API}/lolodrive/health", timeout=15)
        assert r.status_code == 200

    def test_territories(self, http):
        r = http.get(f"{API}/lolodrive/territories", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_points(self, http):
        r = http.get(f"{API}/lolodrive/lolo-points", timeout=15)
        assert r.status_code == 200

    def test_events_active(self, http):
        r = http.get(f"{API}/lolodrive/events/active", timeout=15)
        assert r.status_code == 200

    def test_logistics_config(self, http):
        r = http.get(f"{API}/lolodrive/logistics/config", timeout=15)
        assert r.status_code == 200

    def test_delivery_zones(self, http):
        r = http.get(f"{API}/lolodrive/logistics/zones", timeout=15)
        assert r.status_code == 200


class TestLolodriveBuyer:
    def test_pass_me(self, http, buyer_token):
        r = http.get(f"{API}/lolodrive/pass/me", headers=_h(buyer_token), timeout=15)
        # buyer may not have PASS → 200 or 404 acceptable, but must not be 500
        assert r.status_code in (200, 404), r.text

    def test_wallet_me(self, http, buyer_token):
        r = http.get(f"{API}/lolodrive/wallet/me", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (200, 404), r.text

    def test_catalog_products(self, http, buyer_token):
        r = http.get(f"{API}/lolodrive/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text


class TestLolodriveAdmin:
    def test_kpi_overview(self, http, admin_token):
        r = http.get(f"{API}/lolodrive/admin/kpi/overview", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200, r.text

    def test_stripe_mode(self, http, admin_token):
        r = http.get(f"{API}/lolodrive/admin/stripe/mode", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text


class TestLolodriveManager:
    def test_manager_my_point(self, http, manager_token):
        if not manager_token:
            pytest.skip("manager login unavailable")
        r = http.get(f"{API}/lolodrive/manager/my-point", headers=_h(manager_token), timeout=15)
        # 200 (has point) or 404 (unassigned) OK; must not be 500 (import error)
        assert r.status_code in (200, 404), r.text


# ============ Split #2 — signature (public + admin) ============
class TestSignature:
    def test_admin_stats(self, http, admin_token):
        r = http.get(f"{API}/signatures/admin/stats", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_admin_list(self, http, admin_token):
        r = http.get(f"{API}/signatures/admin/list", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_initiate_empty_payload_422(self, http, buyer_token):
        r = http.post(f"{API}/signatures/initiate", headers=_h(buyer_token), json={}, timeout=15)
        # 422 (validation) expected; 400/401 also acceptable non-500
        assert r.status_code in (400, 401, 422), r.text

    def test_status_fake_id_404(self, http, buyer_token):
        r = http.get(f"{API}/signatures/status/nonexistent-abc-123", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (401, 404), r.text


# ============ Split #4 — v1 logiscop (quote/orders/delivery-policy) ============
class TestLogiscopV1:
    def test_delivery_policy(self, http):
        r = http.get(f"{API}/v1/b2b/delivery-policy", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict) and len(data) > 0

    def test_logiscop_quote(self, http, buyer_token):
        payload = {
            "items": [{"sku": "RHUM-DAMOISEAU-VSOP-70CL", "quantity": 6}],
            "delivery_zone": "GP-BT",
            "incoterm": "EXW",
        }
        r = http.post(
            f"{API}/v1/b2b/logiscop/quote",
            headers=_h(buyer_token),
            json=payload,
            timeout=20,
        )
        # 200 (quote), 400/422 (payload rules), 404 (sku)  = all NON-500 acceptable
        assert r.status_code in (200, 400, 404, 422), r.text

    def test_checkout_quote_full_reachable(self, http, buyer_token):
        r = http.post(
            f"{API}/v1/b2b/checkout/quote-full",
            headers=_h(buyer_token),
            json={},
            timeout=15,
        )
        assert r.status_code in (400, 401, 404, 422), r.text


# ============ Split #5 — OPA bundle ============
class TestOPA:
    def test_zones(self, http):
        r = http.get(f"{API}/opa/zones", timeout=15)
        assert r.status_code == 200, r.text

    def test_policies(self, http):
        r = http.get(f"{API}/opa/policies", timeout=15)
        assert r.status_code == 200, r.text

    def test_bundle_data(self, http):
        r = http.get(f"{API}/opa/bundle/data.json", timeout=15)
        assert r.status_code == 200, r.text

    def test_evaluate_reachable(self, http):
        r = http.post(f"{API}/opa/evaluate", json={"input": {}}, timeout=15)
        assert r.status_code in (200, 400, 401, 422), r.text


# ============ Split #6 — admin_plans + credits ============
class TestAdminPlans:
    def test_list_plans(self, http, admin_token):
        r = http.get(f"{API}/admin/plans/subscriptions", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_options(self, http, admin_token):
        r = http.get(f"{API}/admin/plans/options", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_credits_users(self, http, admin_token):
        r = http.get(f"{API}/admin/plans/credits/users", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_stats(self, http, admin_token):
        r = http.get(f"{API}/admin/plans/stats", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200, r.text


# ============ Split #7 — schema_v2 facade ============
class TestSchemaV2:
    def test_v2_catalog_products(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_zones(self, http):
        r = http.get(f"{API}/zones", timeout=15)
        assert r.status_code == 200, r.text


# ============ Split #8 — GED ============
class TestGED:
    def test_documents_list(self, http):
        r = http.get(f"{API}/ged/documents", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_document_cg_oscop(self, http):
        r = http.get(f"{API}/ged/documents/cg-oscop", timeout=15)
        # 200 or 404 (if slug differs) — must not be 500
        assert r.status_code in (200, 404), r.text

    def test_document_render(self, http):
        # Try the same doc_type render
        r = http.get(f"{API}/ged/documents/cg-oscop/render", timeout=15)
        assert r.status_code in (200, 404), r.text
