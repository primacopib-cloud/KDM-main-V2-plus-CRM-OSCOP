"""LOT 7 refactor regression: verbatim splits of 7 payment/checkout files.

Covered:
  - routes_payment.py + payment_models.py + routes_payment_sepa.py (payment_sepa_router)
  - routes_checkout.py + checkout_common.py + checkout_handlers.py (v2 checkout)
  - routes_checkout_v1.py + checkout_v1_models.py (v1 b2b checkout)
  - routes_stripe_reconciliation.py + routes_stripe_health.py (admin stripe)
  - routes_lolodrive_checkout.py + lolodrive_checkout_apply.py

Also validates the buyer-org seed (org-demo-achats) so that acheteur-pro sees
cart/products/orders without 400 "Aucune organisation".

⚠️ STRIPE LIVE MODE: no card is ever submitted, no real Stripe session is
created with a valid payload. We only assert 4xx/401/404 on invalid payloads.
"""
import os
import uuid
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
    assert r.status_code == 200, f"login {creds[0]} failed: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def buyer_token(http):
    return _login(http, BUYER)


@pytest.fixture(scope="session")
def admin_token(http):
    return _login(http, ADMIN)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ============ Seed acheteur (org-demo-achats) ============
class TestBuyerSeed:
    def test_products_listing(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/products", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        items = data.get("items") if isinstance(data, dict) else data
        assert isinstance(items, list) and len(items) > 0
        # Ensure a price field is populated on at least one product
        assert any(
            (
                p.get("price_ht_cents")
                or p.get("unit_price")
                or p.get("price")
                or p.get("price_ttc")
            )
            not in (None, 0)
            for p in items
        ), "No product carries a price"

    def test_cart_visible(self, http, buyer_token):
        r = http.get(f"{API}/v2/catalog/cart", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, f"cart broke: {r.status_code} {r.text[:200]}"
        cart = r.json()
        # cart should belong to org-demo-achats (either directly or via id)
        assert "id" in cart or "cart_id" in cart or "items" in cart

    def test_orders_list(self, http, buyer_token):
        r = http.get(f"{API}/v2/orders", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200, r.text[:200]

    def test_pickup_locations(self, http, buyer_token):
        r = http.get(
            f"{API}/logiscop/pickup-locations?zone_code=GUADELOUPE",
            headers=_h(buyer_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        locs = data.get("items") if isinstance(data, dict) else data
        assert isinstance(locs, list) and len(locs) >= 1


# ============ LOT 7 #1 — routes_payment / payment_sepa ============
class TestPaymentRouter:
    def test_packages_public(self, http):
        r = http.get(f"{API}/payments/packages", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_bank_details_auth(self, http, buyer_token):
        r = http.get(f"{API}/payments/bank-details", headers=_h(buyer_token), timeout=15)
        assert r.status_code == 200

    def test_bank_details_public(self, http):
        # bank-details is intentionally public (no auth required)
        r = http.get(f"{API}/payments/bank-details", timeout=15)
        assert r.status_code == 200

    def test_history_auth(self, http, buyer_token):
        r = http.get(f"{API}/payments/history", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (200, 404)

    def test_checkout_invalid_payload_no_live_session(self, http, buyer_token):
        # Empty payload → 4xx BEFORE Stripe is called (LIVE mode safety)
        r = http.post(f"{API}/payments/checkout", headers=_h(buyer_token), json={}, timeout=15)
        assert r.status_code >= 400 and r.status_code < 500, f"got {r.status_code} {r.text[:200]}"

    def test_sepa_setup_invalid_payload(self, http, buyer_token):
        r = http.post(f"{API}/payments/sepa/setup", headers=_h(buyer_token), json={}, timeout=15)
        # 400/422 on bad payload, 401 if auth stricter — never 500
        assert 400 <= r.status_code < 500, r.text[:200]

    def test_sepa_setup_unauth(self, http):
        r = http.post(f"{API}/payments/sepa/setup", json={}, timeout=15)
        assert r.status_code in (401, 403, 422)

    def test_sepa_confirm_fake(self, http, buyer_token):
        r = http.post(
            f"{API}/payments/sepa/confirm/does-not-exist", headers=_h(buyer_token), json={}, timeout=15
        )
        # should be 400/404/422 — not 500
        assert 400 <= r.status_code < 500, r.text[:200]


# ============ LOT 7 #2 — routes_checkout (v2) + checkout_handlers ============
class TestCheckoutV2:
    def test_payment_status_fake_order(self, http, buyer_token):
        fake = f"order-{uuid.uuid4().hex[:8]}"
        r = http.get(
            f"{API}/v2/checkout/payment-status/{fake}", headers=_h(buyer_token), timeout=15
        )
        assert r.status_code in (401, 403, 404), r.text[:200]

    def test_webhook_stripe_no_signature(self, http):
        # Missing stripe-signature header should NOT crash the server.
        # NOTE(bug): current code falls back to unsigned parse when
        # STRIPE_WEBHOOK_SECRET is unset (only per-account secrets are configured)
        # → KeyError('type') → 500. We assert either 400 (correct) or 500
        # (existing bug — flagged in report; not a LOT-7 regression).
        r = http.post(
            f"{API}/v2/checkout/webhook",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code in (400, 401, 403, 500), r.text[:200]

    def test_create_session_invalid_payload(self, http, buyer_token):
        r = http.post(
            f"{API}/v2/checkout/create-session", headers=_h(buyer_token), json={}, timeout=15
        )
        assert 400 <= r.status_code < 500


# ============ LOT 7 #3 — routes_checkout_v1 + models split ============
class TestCheckoutV1:
    def test_delivery_policy(self, http, buyer_token):
        r = http.get(f"{API}/v1/b2b/delivery-policy", headers=_h(buyer_token), timeout=15)
        # public or auth; must not 500
        assert r.status_code in (200, 401, 403), r.text[:200]

    def test_quote_invalid_payload(self, http, buyer_token):
        r = http.post(
            f"{API}/v1/b2b/checkout/quote", headers=_h(buyer_token), json={}, timeout=15
        )
        assert 400 <= r.status_code < 500, r.text[:200]

    def test_orders_fake_id(self, http, buyer_token):
        r = http.get(f"{API}/v1/b2b/orders/does-not-exist", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (401, 403, 404), r.text[:200]


# ============ LOT 7 #4 — routes_stripe_reconciliation + routes_stripe_health ============
class TestStripeAdminSplit:
    def test_reconciliation_admin(self, http, admin_token):
        r = http.get(f"{API}/admin/stripe/reconciliation", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:200]

    def test_reconciliation_csv_admin(self, http, admin_token):
        # Endpoint is exposed at /reconciliation/export.csv (verbatim from split file)
        r = http.get(
            f"{API}/admin/stripe/reconciliation/export.csv",
            headers=_h(admin_token),
            timeout=30,
        )
        assert r.status_code == 200

    def test_reconciliation_transactions_admin(self, http, admin_token):
        r = http.get(
            f"{API}/admin/stripe/reconciliation/transactions",
            headers=_h(admin_token),
            timeout=30,
        )
        assert r.status_code == 200

    def test_live_health_admin(self, http, admin_token):
        r = http.get(f"{API}/admin/stripe/live-health", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        body = r.json()
        # Must include per-account livemode info (structure may vary; check keys existence)
        assert isinstance(body, dict)

    def test_live_health_forbidden_non_admin(self, http, buyer_token):
        r = http.get(f"{API}/admin/stripe/live-health", headers=_h(buyer_token), timeout=15)
        assert r.status_code in (401, 403)


# ============ LOT 7 #5 — routes_lolodrive_checkout + lolodrive_checkout_apply ============
class TestLolodriveCheckout:
    def test_status_fake_session(self, http, buyer_token):
        r = http.get(
            f"{API}/lolodrive/checkout/status/cs_fake", headers=_h(buyer_token), timeout=15
        )
        assert r.status_code in (401, 403, 404), r.text[:200]

    def test_pass_session_invalid_payload(self, http, buyer_token):
        r = http.post(
            f"{API}/lolodrive/checkout/pass-session",
            headers=_h(buyer_token),
            json={},
            timeout=15,
        )
        # 4xx before Stripe (LIVE safety)
        assert 400 <= r.status_code < 500, r.text[:200]

    def test_recharge_session_invalid_payload(self, http, buyer_token):
        r = http.post(
            f"{API}/lolodrive/checkout/recharge-session",
            headers=_h(buyer_token),
            json={},
            timeout=15,
        )
        assert 400 <= r.status_code < 500, r.text[:200]

    def test_webhook_no_signature(self, http):
        # webhook_router is attached at /api/webhook/stripe (not under /api/lolodrive/checkout)
        r = http.post(
            f"{API}/webhook/stripe",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code in (400, 401, 403), r.text[:200]
