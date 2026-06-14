"""
Iteration 10 — Multi-account Stripe Checkout + Native Google OAuth tests.

Scope:
- POST /api/lolodrive/checkout/pass-session       → stripe_account=oscop
- POST /api/lolodrive/checkout/order-session      → stripe_account=kdmarche
- POST /api/lolodrive/checkout/recharge-session   → stripe_account=oscop
- GET  /api/lolodrive/checkout/status/<sid>       → uses persisted tx.stripe_account
- POST /api/webhook/stripe                        → 400 on invalid signature (dual-account)
- GET  /api/auth/google/login                     → 302 redirect to accounts.google.com
"""
import os
import re
import pytest
import requests
from urllib.parse import urlparse, parse_qs

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
MARIE_EMAIL = os.environ.get("DEMO_USER_EMAIL", "marie@example.com")
# Password sourced from env; falls back to the documented demo seed for local CI.
MARIE_PASSWORD = os.environ.get("DEMO_USER_PASSWORD") or os.environ.get("DEMO_SEED_PASSWORD") or "Demo2026!"
ORIGIN = os.environ.get("REACT_APP_FRONTEND_ORIGIN", BASE_URL)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def marie_token(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": MARIE_EMAIL, "password": MARIE_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def marie_client(marie_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {marie_token}",
    })
    return s


# --------------------------------------------------------------------------- #
# Stripe Checkout — multi-account routing
# --------------------------------------------------------------------------- #
class TestStripeMultiAccountCheckout:
    """Validate that the stripe_account field is correctly returned + persisted."""

    def test_pass_session_uses_oscop_account(self, marie_client):
        r = marie_client.post(
            f"{BASE_URL}/api/lolodrive/checkout/pass-session",
            json={"origin_url": ORIGIN},
            timeout=20,
        )
        assert r.status_code == 200, f"pass-session: {r.status_code} {r.text[:400]}"
        data = r.json()
        # Emergent shared test key returns https://checkout.stripe.test/<sid>;
        # real Stripe returns https://checkout.stripe.com/c/pay/<sid>. Accept both.
        assert "url" in data and re.match(r"^https://checkout\.stripe\.(com|test)/", data["url"]), data
        assert "session_id" in data and data["session_id"].startswith("cs_test_"), data
        assert data.get("stripe_account") == "oscop", data

        # Persisted: status endpoint must echo the same account
        sid = data["session_id"]
        s = marie_client.get(
            f"{BASE_URL}/api/lolodrive/checkout/status/{sid}",
            timeout=15,
        )
        assert s.status_code == 200, f"status: {s.status_code} {s.text[:300]}"
        sdata = s.json()
        assert sdata.get("stripe_account") == "oscop", sdata
        assert sdata.get("kind") == "PASS"
        assert sdata.get("payment_status") in ("unpaid", "no_payment_required", "paid")

    def test_order_session_uses_kdmarche_account(self, marie_client):
        # Find or create a DRAFT order
        r_orders = marie_client.get(f"{BASE_URL}/api/lolodrive/orders/me", timeout=15)
        assert r_orders.status_code == 200, f"orders/me: {r_orders.status_code} {r_orders.text[:300]}"
        orders = r_orders.json()
        # Response may be a list or {orders: [...]}
        if isinstance(orders, dict):
            orders = orders.get("orders") or orders.get("items") or []
        draft = next((o for o in orders if o.get("status") in ("DRAFT", "PENDING_PAYMENT")), None)
        if not draft:
            pytest.skip("No DRAFT/PENDING_PAYMENT order for Marie — skipping order checkout test")

        r = marie_client.post(
            f"{BASE_URL}/api/lolodrive/checkout/order-session",
            json={"origin_url": ORIGIN, "order_id": draft["id"]},
            timeout=20,
        )
        assert r.status_code == 200, f"order-session: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert re.match(r"^https://checkout\.stripe\.(com|test)/", data["url"]), data
        assert data["session_id"].startswith("cs_test_"), data
        assert data.get("stripe_account") == "kdmarche", data
        assert data.get("amount_cents") == draft["total_cents"], data

        # Status endpoint must read kdmarche account
        sdata = marie_client.get(
            f"{BASE_URL}/api/lolodrive/checkout/status/{data['session_id']}",
            timeout=15,
        ).json()
        assert sdata.get("stripe_account") == "kdmarche", sdata
        assert sdata.get("kind") == "ORDER"

    def test_recharge_session_uses_oscop_account(self, marie_client):
        # Recharge requires PASS ACTIVE. Marie has PASS active in seed; if not, skip.
        pass_resp = marie_client.get(f"{BASE_URL}/api/lolodrive/pass/me", timeout=15)
        is_active = False
        if pass_resp.status_code == 200:
            body = pass_resp.json() or {}
            # pass/me returns {pass: {...}, wallet: {...}, active: bool}
            p = body.get("pass") if isinstance(body, dict) else None
            status_val = (p or body or {}).get("status")
            is_active = bool(body.get("active")) or status_val == "ACTIVE"
        if not is_active:
            pytest.skip("Marie's PASS is not ACTIVE — recharge cannot be tested")

        r = marie_client.post(
            f"{BASE_URL}/api/lolodrive/checkout/recharge-session",
            json={"origin_url": ORIGIN, "pack": "STANDARD"},
            timeout=20,
        )
        assert r.status_code == 200, f"recharge-session: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert re.match(r"^https://checkout\.stripe\.(com|test)/", data["url"]), data
        assert data.get("stripe_account") == "oscop", data
        assert data.get("pack") == "STANDARD"


# --------------------------------------------------------------------------- #
# Status endpoint — authorization
# --------------------------------------------------------------------------- #
class TestStatusAuthorization:
    def test_status_requires_auth(self, session):
        r = session.get(
            f"{BASE_URL}/api/lolodrive/checkout/status/cs_test_nonexistent",
            timeout=10,
        )
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text[:200]}"

    def test_status_unknown_session(self, marie_client):
        r = marie_client.get(
            f"{BASE_URL}/api/lolodrive/checkout/status/cs_test_definitely_unknown_xyz",
            timeout=10,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


# --------------------------------------------------------------------------- #
# Stripe webhook — invalid signature
# --------------------------------------------------------------------------- #
class TestStripeWebhook:
    def test_webhook_invalid_signature_returns_400(self, session):
        # No Stripe-Signature header -> both accounts should fail verification -> 400
        r = session.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b'{"id":"evt_test","type":"checkout.session.completed"}',
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"

    def test_webhook_bogus_signature_returns_400(self, session):
        r = session.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b'{"id":"evt_test","type":"checkout.session.completed"}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1234567890,v1=deadbeef",
            },
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"


# --------------------------------------------------------------------------- #
# Native Google OAuth — login redirect well-formed
# --------------------------------------------------------------------------- #
class TestGoogleOAuth:
    def test_google_login_redirects_to_accounts_google(self, session):
        r = session.get(
            f"{BASE_URL}/api/auth/google/login",
            allow_redirects=False,
            timeout=15,
        )
        assert r.status_code in (302, 307), f"expected 302, got {r.status_code}: {r.text[:200]}"
        location = r.headers.get("Location") or r.headers.get("location")
        assert location, "Missing Location header on redirect"
        parsed = urlparse(location)
        assert parsed.netloc == "accounts.google.com", f"Unexpected host: {parsed.netloc}"
        assert parsed.path == "/o/oauth2/v2/auth", f"Unexpected path: {parsed.path}"

        qs = parse_qs(parsed.query)
        assert qs.get("client_id", [""])[0].startswith("299456348062-"), qs
        assert qs.get("response_type") == ["code"]
        assert "openid" in qs.get("scope", [""])[0]
        assert "email" in qs.get("scope", [""])[0]
        # redirect_uri must come from env
        assert qs.get("redirect_uri", [""])[0].endswith("/api/auth/google/callback"), qs
        # state must be present and signed (format: nonce.mac)
        state = qs.get("state", [""])[0]
        assert "." in state and len(state) > 20, f"bad state: {state}"

        # state cookie should be set
        cookie_header = r.headers.get("set-cookie", "") or r.headers.get("Set-Cookie", "")
        assert "oauth_state" in cookie_header, f"missing oauth_state cookie: {cookie_header}"
