"""
Contract tests for the Stripe LIVE Health endpoint (go/no-go admin dashboard).

Endpoint: GET /api/admin/stripe/live-health
Auth: super-admin only (403 otherwise).

These tests do NOT create Stripe transactions — they only assert:
  - shape of the response
  - authentication / authorization behaviour
  - masking of the Stripe key prefix (never full key in payload)
  - verdict logic reacts to configured accounts / webhooks
"""
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminKDM2025!")
BUYER_EMAIL = os.environ.get("DEMO_USER_EMAIL", "marie@example.com")
BUYER_PASSWORD = os.environ.get("DEMO_USER_PASSWORD") or os.environ.get("DEMO_SEED_PASSWORD") or "Demo2026!"


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token")
    assert token, "no access_token in login response"
    return token


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def buyer_token() -> str:
    return _login(BUYER_EMAIL, BUYER_PASSWORD)


class TestStripeLiveHealthAuth:
    def test_no_auth_returns_403(self):
        r = requests.get(f"{BASE_URL}/api/admin/stripe/live-health", timeout=15)
        assert r.status_code == 403

    def test_non_admin_returns_403(self, buyer_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {buyer_token}"},
            timeout=15,
        )
        assert r.status_code == 403


class TestStripeLiveHealthShape:
    def test_response_shape(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        # Top-level keys
        for key in ("checked_at", "window_hours", "mode", "accounts", "last_webhook_received",
                    "last_successful_payment", "stats_24h", "verdict", "reasons"):
            assert key in d, f"missing top-level key: {key}"

        assert d["window_hours"] == 24
        assert d["mode"] in ("live", "test")
        assert d["verdict"] in ("go", "warn", "no-go")
        assert isinstance(d["reasons"], list)

    def test_both_accounts_present(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        d = r.json()
        for account in ("oscop", "kdmarche"):
            assert account in d["accounts"], f"missing account {account}"
            info = d["accounts"][account]
            assert set(info.keys()) == {"key_configured", "key_prefix", "webhook_secrets_count"}
            assert isinstance(info["key_configured"], bool)
            assert isinstance(info["webhook_secrets_count"], int)
            # Stats
            assert account in d["stats_24h"]
            stats = d["stats_24h"][account]
            for k in ("paid_count", "paid_amount_cents", "paid_amount_eur",
                      "refund_full_count", "refund_partial_count", "stale_pending_count"):
                assert k in stats, f"missing stat {k} for {account}"
                assert isinstance(stats[k], (int, float))

    def test_key_prefix_is_masked(self, admin_token):
        """The full Stripe secret key must NEVER be in the response."""
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        d = r.json()
        for account in ("oscop", "kdmarche"):
            prefix = d["accounts"][account].get("key_prefix") or ""
            # A prefix ending with an ellipsis, at most ~15 usable chars visible.
            assert len(prefix) <= 20, f"key_prefix too long for {account}: {prefix}"
            assert "…" in prefix or prefix == "" or prefix.startswith("sk_")
            # No obvious full-key giveaway markers
            assert prefix.count("_") <= 3, f"key_prefix looks like a full key for {account}: {prefix}"


class TestStripeLiveHealthVerdict:
    def test_verdict_reasons_are_strings(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        d = r.json()
        assert all(isinstance(reason, str) for reason in d["reasons"])

    def test_verdict_is_no_go_only_when_key_missing(self, admin_token):
        """Verdict='no-go' is reserved for missing keys — a currently-configured setup
        should never return no-go without explicit reasons."""
        r = requests.get(
            f"{BASE_URL}/api/admin/stripe/live-health",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        d = r.json()
        if d["verdict"] == "no-go":
            # At least one 'clé Stripe non configurée' reason must be present
            assert any("clé" in r.lower() or "key" in r.lower() for r in d["reasons"]), \
                f"no-go verdict without key-related reason: {d['reasons']}"
