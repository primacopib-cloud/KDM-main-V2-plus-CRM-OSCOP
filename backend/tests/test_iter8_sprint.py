"""Iter 8 Sprint: Premium charter + Stripe mode admin + relay modal preselect.

Tests:
- GET /api/lolodrive/admin/stripe/mode (admin → mode/active_key_prefix/live_key_configured/warning)
- GET /api/lolodrive/admin/stripe/mode (no auth → 401/403; non-admin → 403)
- POST /api/lolodrive/checkout/pass-session (marie → Stripe TEST session, sk_test_*, checkout.stripe.com)
- POST /api/lolodrive/admin/notifications/auto-renew-batch (still functional → {sent, skipped})
- GET /api/lolodrive/lolo-points (regression → 10 points lat/lng/territory)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!"}
MARIE = {"email": "marie@example.com", "password": "Demo2026!"}
GERANT = {"email": "gerant@lolopoint.fr", "password": "Demo2026!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def marie_token():
    return _login(MARIE)


@pytest.fixture(scope="module")
def gerant_token():
    return _login(GERANT)


# -- Stripe mode admin endpoint ----------------------------------------

class TestStripeModeEndpoint:
    def test_admin_stripe_mode_ok(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/lolodrive/admin/stripe/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mode"] == "test", f"STRIPE_MODE must be 'test' (got {data['mode']})"
        assert data["live_key_configured"] is True
        assert data["active_key_prefix"] is not None
        assert data["active_key_prefix"].startswith("sk_test"), data["active_key_prefix"]
        assert "test" in data["warning"].lower() or "sandbox" in data["warning"].lower()

    def test_admin_stripe_mode_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/stripe/mode", timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_admin_stripe_mode_non_admin(self, marie_token):
        r = requests.get(
            f"{BASE_URL}/api/lolodrive/admin/stripe/mode",
            headers={"Authorization": f"Bearer {marie_token}"},
            timeout=15,
        )
        assert r.status_code == 403, f"marie (titulaire) must be 403, got {r.status_code}"

    def test_admin_stripe_mode_gerant_blocked(self, gerant_token):
        r = requests.get(
            f"{BASE_URL}/api/lolodrive/admin/stripe/mode",
            headers={"Authorization": f"Bearer {gerant_token}"},
            timeout=15,
        )
        assert r.status_code == 403, f"gerant must be 403, got {r.status_code}"


# -- Stripe checkout still TEST mode -----------------------------------

class TestCheckoutStripeTestMode:
    def test_pass_session_uses_test_key(self, marie_token):
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/checkout/pass-session",
            headers={"Authorization": f"Bearer {marie_token}"},
            json={"origin_url": "https://coop-dashboard-8.preview.emergentagent.com"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # URL must point at Stripe Checkout (real or Emergent sandbox)
        assert "url" in data, data
        url = data["url"]
        assert ("checkout.stripe.com" in url) or ("checkout.stripe.test" in url), url
        # Session id format → cs_test_* in test mode
        if "session_id" in data:
            assert data["session_id"].startswith("cs_test_"), data["session_id"]


# -- Auto-renew batch regression ---------------------------------------

class TestAutoRenewBatchStillWorks:
    def test_auto_renew_returns_dict(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/lolodrive/admin/notifications/auto-renew-batch",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "sent" in data and "skipped" in data
        assert isinstance(data["sent"], int)
        assert isinstance(data["skipped"], int)


# -- Lolo points regression --------------------------------------------

class TestLoloPointsRegression:
    def test_ten_points_with_geo(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/lolo-points", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # API may return list or {items: [...]}
        items = data if isinstance(data, list) else data.get("items") or data.get("points") or []
        assert len(items) >= 10, f"Expected >=10 lolo points, got {len(items)}"
        for p in items[:10]:
            assert p.get("lat") is not None, p
            assert p.get("lng") is not None, p
            assert p.get("territory"), p
