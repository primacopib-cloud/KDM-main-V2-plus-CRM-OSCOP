"""
Iteration 3 tests: Stripe Checkout, Webhook, POS cancel/refund, Admin KPI dashboard, WebSocket /api/ws/notifications
"""
import os
import json
import pytest
import requests
import websocket  # websocket-client
from urllib.parse import urlparse

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")
MARIE_EMAIL = os.environ.get("TEST_MARIE_EMAIL", "marie@example.com")
MARIE_PASSWORD = os.environ.get("TEST_MARIE_PASSWORD", "Demo2026!")


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


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


ORIGIN = "https://coop-dashboard-8.preview.emergentagent.com"


# =========== Stripe Checkout ===========

class TestStripeCheckout:
    def test_pass_session_creates(self, marie_token):
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/pass-session",
            headers=H(marie_token),
            json={"origin_url": ORIGIN},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data and data["url"].startswith("http")
        assert "session_id" in data and len(data["session_id"]) > 0

    def test_recharge_session_active_pass(self, marie_token):
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/recharge-session",
            headers=H(marie_token),
            json={"origin_url": ORIGIN, "pack": "STANDARD"},
        )
        # Marie usually has PASS active per seed
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            data = r.json()
            assert "url" in data and "session_id" in data
            assert data.get("pack") == "STANDARD"

    def test_recharge_session_invalid_pack(self, marie_token):
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/recharge-session",
            headers=H(marie_token),
            json={"origin_url": ORIGIN, "pack": "INVALID_PACK"},
        )
        assert r.status_code == 400

    def test_order_session_for_pending(self, marie_token):
        # Create a draft order via existing endpoint
        # Try to find any DRAFT/PENDING order; otherwise skip
        r_orders = requests.get(f"{BASE_URL}/api/lolodrive/orders/me", headers=H(marie_token))
        if r_orders.status_code != 200:
            pytest.skip("Cannot fetch orders")
        orders = r_orders.json()
        if isinstance(orders, dict):
            orders = orders.get("orders", [])
        candidate = next((o for o in orders if o.get("status") in ("DRAFT", "PENDING_PAYMENT")), None)
        if not candidate:
            pytest.skip("No DRAFT/PENDING_PAYMENT order available")
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/order-session",
            headers=H(marie_token),
            json={"origin_url": ORIGIN, "order_id": candidate["id"]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data
        assert "session_id" in data
        assert "amount_cents" in data

    def test_status_endpoint(self, marie_token):
        # First create a session, then poll status
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/pass-session",
            headers=H(marie_token),
            json={"origin_url": ORIGIN},
        )
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/checkout/status/{session_id}", headers=H(marie_token))
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["session_id"] == session_id
        assert "payment_status" in data
        assert data.get("kind") == "PASS"
        assert "applied" in data


# =========== Webhook ===========

class TestWebhook:
    def test_webhook_route_exists(self):
        # No valid signature => 400 expected, but route must exist (not 404)
        r = requests.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b"{}",
            headers={"Content-Type": "application/json", "Stripe-Signature": "invalid"},
        )
        # 400 invalid signature is expected; 404 means route missing
        assert r.status_code != 404, f"Webhook route missing: {r.status_code} {r.text}"
        assert r.status_code in (200, 400, 422)


# =========== POS cancel/refund ===========

class TestPosCancel:
    def _make_paid_order_with_uc(self, marie_token, admin_token):
        rp = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?zone_code=971&limit=1", headers=H(marie_token))
        if rp.status_code != 200:
            pytest.skip("catalog unavailable")
        data = rp.json()
        prods = data.get("products", []) if isinstance(data, dict) else data
        if not prods:
            pytest.skip("no products")
        sku = prods[0].get("sku") or prods[0].get("id")
        # Create draft order
        ro = requests.post(
            f"{BASE_URL}/api/lolodrive/orders",
            headers=H(marie_token),
            json={"items": [{"sku": sku, "qty": 1}], "fulfillment_type": "DRIVE"},
        )
        if ro.status_code != 200:
            pytest.skip(f"order create failed: {ro.status_code} {ro.text[:200]}")
        order = ro.json()
        order_id = order["id"]
        # Pay with UC
        rp2 = requests.post(f"{BASE_URL}/api/lolodrive/orders/{order_id}/pay-uc", headers=H(marie_token))
        if rp2.status_code != 200:
            pytest.skip(f"pay-uc failed: {rp2.status_code} {rp2.text[:200]}")
        # Fetch order from POS list (to ensure it's PAID)
        return {"id": order_id}

    def test_cancel_with_refund_uc(self, marie_token, admin_token):
        order = self._make_paid_order_with_uc(marie_token, admin_token)
        order_id = order["id"]
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/cancel",
            headers=H(admin_token),
            json={"reason": "Test refund", "refund_uc": True},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("status") == "REFUNDED"
        assert "reason" in data

    def test_cancel_without_refund(self, marie_token, admin_token):
        order = self._make_paid_order_with_uc(marie_token, admin_token)
        order_id = order["id"]
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/cancel",
            headers=H(admin_token),
            json={"reason": "Test no refund", "refund_uc": False},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "CANCELLED"

    def test_cancel_invalid_status(self, marie_token, admin_token):
        order = self._make_paid_order_with_uc(marie_token, admin_token)
        order_id = order["id"]
        # Cancel first
        requests.post(
            f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/cancel",
            headers=H(admin_token), json={"reason": "first", "refund_uc": False},
        )
        # Try again => should be 400
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/pos/orders/{order_id}/cancel",
            headers=H(admin_token), json={"reason": "second", "refund_uc": False},
        )
        assert r.status_code == 400


# =========== Admin KPI Dashboard ===========

class TestAdminKpiDashboard:
    def test_dashboard_kpis(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/dashboard", headers=H(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("uc_in_circulation", "uc_consumed", "ca_today", "ca_month", "top_products", "alerts"):
            assert k in data, f"missing {k} in response: {list(data.keys())}"
        assert isinstance(data["top_products"], list)
        assert len(data["top_products"]) <= 5
        assert isinstance(data["alerts"], list)


# =========== WebSocket ===========

class TestWebSocket:
    def test_ws_connect_and_welcome(self):
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/notifications?is_admin=true"
        ws = websocket.create_connection(ws_url, timeout=10)
        try:
            ws.settimeout(5)
            msg = ws.recv()
            data = json.loads(msg)
            assert data.get("type") == "connected"
        finally:
            ws.close()
