"""
Backend tests for KDMARCHÉ / LOLODRIVE by O'SCOP platform.
Covers: auth, LOLODRIVE (PASS, wallet, catalog, orders, POS, lolo-points, events, KPI)
and CRM (contacts, organizations, opportunities, dossiers, tasks, impact, sync).
NOTE: Most API responses wrap lists with a named key (e.g. {"products": [...]})
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

# Credentials are loaded from environment (see /app/backend/.env.test for local
# defaults). Never commit real production passwords to the test files.
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")
MARIE_EMAIL = os.environ.get("TEST_MARIE_EMAIL", "marie@example.com")
MARIE_PASSWORD = os.environ.get("TEST_MARIE_PASSWORD", "Demo2026!")
POS_EMAIL = os.environ.get("TEST_POS_EMAIL", "pos@lolodrive.fr")
POS_PASSWORD = os.environ.get("TEST_POS_PASSWORD", "Demo2026!")


def _extract_list(data, *candidate_keys):
    """Many endpoints return {"<key>": [...]}; some return raw lists."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in candidate_keys:
            if k in data and isinstance(data[k], list):
                return data[k]
        # fallback: first list-valued field
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def marie_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": MARIE_EMAIL, "password": MARIE_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def pos_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": POS_EMAIL, "password": POS_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"pos login failed: {r.text}")
    return r.json()["access_token"]


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============= AUTH =============
class TestAuth:
    def test_admin_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"].get("is_admin") is True

    def test_marie_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": MARIE_EMAIL, "password": MARIE_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == MARIE_EMAIL


# ============= LOLODRIVE health =============
class TestLolodriveHealth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


# ============= PASS / WALLET =============
class TestPassWallet:
    def test_marie_pass_active(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pass/me", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        wallet = data.get("wallet") or {}
        balance = wallet.get("balance_uc") or wallet.get("balance")
        assert balance is not None and balance > 0, f"expected positive UC balance (seed=450), got {balance}, payload={data}"
        p = data.get("pass") or {}
        status_v = p.get("status") or p.get("is_active") or p.get("active") or data.get("pass_active")
        assert status_v in [True, "ACTIVE", "active"], f"expected PASS active, got: pass={p}"

    def test_marie_wallet_ledger(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/wallet/me", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        ledger = _extract_list(data, "ledger", "entries")
        assert len(ledger) > 0, f"expected ledger entries >0, payload={data}"


# ============= CATALOG =============
class TestCatalog:
    def test_products_list(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token))
        assert r.status_code == 200, r.text
        products = _extract_list(r.json(), "products", "items")
        assert len(products) >= 12, f"expected >=12 products, got {len(products)}"
        essentials = [p for p in products if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL"]
        normals = [p for p in products if (p.get("catalog_type") or p.get("type")) == "NORMAL"]
        assert len(essentials) >= 8, f"expected >=8 ESSENTIAL got {len(essentials)}"
        assert len(normals) >= 4, f"expected >=4 NORMAL got {len(normals)}"
        sample = products[0]
        assert "display_price_cents" in sample, f"missing display_price_cents: {sample}"

    def test_catalog_quote(self, marie_token):
        prods = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token)).json(), "products")
        essential = next(p for p in prods if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL")
        payload = {"items": [{"sku": essential["sku"], "qty": 2}]}
        r = requests.post(f"{BASE_URL}/api/lolodrive/catalog/quote", json=payload, headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert ("subtotal_cents" in data) or ("subtotal" in data), f"no subtotal: {data}"
        lines = data.get("lines") or []
        assert len(lines) == 1
        assert "unit_uc" in lines[0], f"no unit_uc in line: {lines[0]}"


# ============= ORDERS =============
class TestOrders:
    def test_my_orders_marie(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/orders/me", headers=H(marie_token))
        assert r.status_code == 200, r.text
        orders = _extract_list(r.json(), "orders")
        assert len(orders) >= 3, f"expected >=3 seed orders for Marie, got {len(orders)}"

    def test_create_order_drive(self, marie_token):
        prods = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token)).json(), "products")
        essential = next(p for p in prods if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL")
        payload = {"items": [{"sku": essential["sku"], "qty": 1}], "fulfillment_type": "DRIVE"}
        r = requests.post(f"{BASE_URL}/api/lolodrive/orders", json=payload, headers=H(marie_token))
        assert r.status_code in [200, 201], r.text
        data = r.json()
        # Allow wrap
        order = data.get("order") if isinstance(data, dict) and "order" in data else data
        assert order.get("status") in ["DRAFT", "PENDING", "PAID"], f"unexpected status: {order}"
        assert "id" in order

    def test_pay_uc_decrements_wallet(self, marie_token):
        prods = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token)).json(), "products")
        essential = next(p for p in prods if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL")
        oc = requests.post(f"{BASE_URL}/api/lolodrive/orders",
                           json={"items": [{"sku": essential["sku"], "qty": 1}], "fulfillment_type": "DRIVE"},
                           headers=H(marie_token))
        assert oc.status_code in [200, 201], oc.text
        oc_data = oc.json()
        order = oc_data.get("order") if isinstance(oc_data, dict) and "order" in oc_data else oc_data
        order_id = order["id"]

        w_before_data = requests.get(f"{BASE_URL}/api/lolodrive/wallet/me", headers=H(marie_token)).json()
        bal_before = (w_before_data.get("wallet") or {}).get("balance_uc") or 0

        r = requests.post(f"{BASE_URL}/api/lolodrive/orders/{order_id}/pay-uc", headers=H(marie_token))
        assert r.status_code == 200, r.text
        rdata = r.json()
        # pay-uc returns {ok, order_id, paid_with, total_uc} - verify via GET orders/me
        assert rdata.get("ok") is True, f"pay-uc not ok: {rdata}"
        assert rdata.get("paid_with") == "UC"

        w_after_data = requests.get(f"{BASE_URL}/api/lolodrive/wallet/me", headers=H(marie_token)).json()
        bal_after = (w_after_data.get("wallet") or {}).get("balance_uc") or 0
        assert bal_after < bal_before, f"wallet not decremented: before={bal_before} after={bal_after}"


# ============= POS =============
class TestPOS:
    def test_pos_orders_list(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pos/orders", headers=H(admin_token))
        assert r.status_code == 200, r.text
        orders = _extract_list(r.json(), "orders")
        assert isinstance(orders, list)

    def test_pos_filter_status(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pos/orders?status=PAID", headers=H(admin_token))
        assert r.status_code == 200, r.text

    def test_pos_status_transition_to_fulfilled(self, admin_token, marie_token):
        prods = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token)).json(), "products")
        essential = next(p for p in prods if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL")
        oc = requests.post(f"{BASE_URL}/api/lolodrive/orders",
                           json={"items": [{"sku": essential["sku"], "qty": 1}], "fulfillment_type": "DRIVE"},
                           headers=H(marie_token))
        assert oc.status_code in [200, 201], oc.text
        oc_data = oc.json()
        order = oc_data.get("order") if isinstance(oc_data, dict) and "order" in oc_data else oc_data
        order_id = order["id"]
        pay = requests.post(f"{BASE_URL}/api/lolodrive/orders/{order_id}/pay-uc", headers=H(marie_token))
        if pay.status_code != 200:
            pytest.skip(f"pay-uc failed: {pay.text}")

        # PAID -> PREPARING
        r1 = requests.post(f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/status",
                           json={"status": "PREPARING"}, headers=H(admin_token))
        assert r1.status_code == 200, r1.text
        # -> READY
        r2 = requests.post(f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/status",
                           json={"status": "READY"}, headers=H(admin_token))
        assert r2.status_code == 200, r2.text
        # -> FULFILLED via scan
        r3 = requests.post(f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/scan", headers=H(admin_token))
        assert r3.status_code == 200, r3.text
        rj = r3.json()
        final = rj.get("order") if isinstance(rj, dict) and "order" in rj else rj
        assert final.get("status") == "FULFILLED", f"final status: {final}"


# ============= LOLO POINTS =============
class TestLoloPoints:
    def test_list_points(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/lolo-points")
        assert r.status_code == 200
        pts = _extract_list(r.json(), "points", "lolo_points")
        assert len(pts) >= 4, f"expected >=4 lolo-points, got {len(pts)}"

    def test_payout_preview(self, admin_token):
        pts = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/lolo-points").json(), "points")
        pid = pts[0]["id"]
        r = requests.post(f"{BASE_URL}/api/lolodrive/admin/lolo-points/{pid}/payout-preview",
                          json={"from_date": "2026-01-01T00:00:00", "to_date": "2026-01-31T23:59:59"},
                          headers=H(admin_token))
        assert r.status_code == 200, r.text


# ============= EVENTS =============
class TestEvents:
    def test_active_events(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/events/active")
        assert r.status_code == 200
        events = _extract_list(r.json(), "events")
        assert len(events) >= 4, f"expected >=4 active events, got {len(events)}"


# ============= KPI =============
class TestAdminKPI:
    def test_kpi_overview(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/overview", headers=H(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["pass_active", "orders", "lolo_points_active"]:
            assert k in data, f"missing key {k} in KPI overview: {data}"


# ============= CRM =============
class TestCRM:
    def test_impact_summary(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/impact/summary", headers=H(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "impact_positioning" in data, f"missing impact_positioning: {data}"

    def test_contacts_seed(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/contacts", headers=H(admin_token))
        assert r.status_code == 200
        lst = _extract_list(r.json(), "contacts")
        assert len(lst) >= 4, f"expected >=4 contacts, got {len(lst)}"

    def test_organizations_seed(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/organizations", headers=H(admin_token))
        assert r.status_code == 200
        lst = _extract_list(r.json(), "organizations")
        assert len(lst) >= 5, f"got {len(lst)}"

    def test_opportunities_seed(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/opportunities", headers=H(admin_token))
        assert r.status_code == 200
        lst = _extract_list(r.json(), "opportunities")
        assert len(lst) >= 4

    def test_dossiers_seed(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/dossiers", headers=H(admin_token))
        assert r.status_code == 200
        lst = _extract_list(r.json(), "dossiers")
        assert len(lst) >= 3

    def test_tasks_seed(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/tasks", headers=H(admin_token))
        assert r.status_code == 200
        lst = _extract_list(r.json(), "tasks")
        assert len(lst) >= 3

    def test_rebuild_from_lolodrive(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/crm/sync/rebuild-from-lolodrive", headers=H(admin_token))
        assert r.status_code == 200, r.text


# ============= ITERATION 2 NEW ENDPOINTS =============
class TestDemoEndpoints:
    """New demo simulators + savings endpoint added in iteration 2."""

    def test_simulate_pass_activation(self, marie_token):
        r = requests.post(f"{BASE_URL}/api/lolodrive/demo/simulate-pass-activation", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("uc_granted") == 600
        assert "ends_at" in data
        # Verify PASS is now active
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/pass/me", headers=H(marie_token))
        assert r2.status_code == 200
        p = (r2.json().get("pass") or {})
        assert p.get("status") in ["ACTIVE", "active"], f"PASS not active after activation: {p}"

    def test_my_savings(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/me/savings", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "savings_cents" in data
        assert "essential_items" in data
        assert "orders_count" in data
        assert isinstance(data["savings_cents"], int)
        assert isinstance(data["essential_items"], int)
        assert isinstance(data["orders_count"], int)
        assert data["orders_count"] >= 0

    def test_simulate_order_payment(self, marie_token):
        # Create a DRAFT order first
        prods = _extract_list(requests.get(f"{BASE_URL}/api/lolodrive/catalog/products", headers=H(marie_token)).json(), "products")
        essential = next(p for p in prods if (p.get("catalog_type") or p.get("type")) == "ESSENTIAL")
        oc = requests.post(f"{BASE_URL}/api/lolodrive/orders",
                           json={"items": [{"sku": essential["sku"], "qty": 1}], "fulfillment_type": "DRIVE"},
                           headers=H(marie_token))
        assert oc.status_code in [200, 201], oc.text
        oc_data = oc.json()
        order = oc_data.get("order") if isinstance(oc_data, dict) and "order" in oc_data else oc_data
        order_id = order["id"]
        # Only test if order is in DRAFT/PENDING_PAYMENT state
        if order.get("status") not in ["DRAFT", "PENDING_PAYMENT"]:
            pytest.skip(f"order created in status {order.get('status')}, cannot test simulate-order-payment")
        r = requests.post(f"{BASE_URL}/api/lolodrive/demo/simulate-order-payment/{order_id}", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("status") == "PAID"


class TestKPIPeriods:
    """KPI overview with different periods."""

    def test_kpi_7d(self, admin_token):
        from datetime import datetime, timedelta
        f = (datetime.utcnow() - timedelta(days=7)).isoformat()
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/overview?from_date={f}", headers=H(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "orders" in data
        assert "count" in data["orders"]
        assert "revenue_cents" in data["orders"]
        assert "drive" in data["orders"]
        assert "delivery" in data["orders"]
        assert "lolo_point" in data["orders"]
        assert "paid_uc" in data["orders"]
        assert "wallet" in data
        assert "debited_uc" in data["wallet"]

    def test_kpi_30d(self, admin_token):
        from datetime import datetime, timedelta
        f = (datetime.utcnow() - timedelta(days=30)).isoformat()
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/overview?from_date={f}", headers=H(admin_token))
        assert r.status_code == 200, r.text

    def test_kpi_90d(self, admin_token):
        from datetime import datetime, timedelta
        f = (datetime.utcnow() - timedelta(days=90)).isoformat()
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/overview?from_date={f}", headers=H(admin_token))
        assert r.status_code == 200, r.text
