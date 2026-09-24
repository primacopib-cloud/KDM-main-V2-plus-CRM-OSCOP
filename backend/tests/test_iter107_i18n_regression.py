"""Iter107 — Backend regression: translate-all (AI) + superadmin lang-usage stats.
Only two backend endpoints in scope for this iteration.
"""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


def _admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"},
        timeout=30,
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return r.json().get("access_token") or r.json().get("token")


# --- Feature: AI catalog translate-all (backend/routes_product_ai.py) ---

class TestCatalogTranslateAll:
    def test_translate_all_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/catalog/admin/translate-all", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 without token, got {r.status_code}"

    def test_translate_all_with_admin_token_returns_zero_remaining(self):
        token = _admin_token()
        r = requests.post(
            f"{BASE_URL}/api/catalog/admin/translate-all",
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        assert r.status_code == 200, f"translate-all failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        # Data assertions - full catalog should already be translated
        assert "translated" in data
        assert "remaining" in data
        assert data["remaining"] == 0, f"remaining should be 0, got {data['remaining']}"
        # message should indicate already translated when translated=0
        if data.get("translated", 0) == 0:
            msg = str(data.get("message", "")).lower()
            assert "déjà" in msg or "already" in msg or "translated" in msg, f"unexpected message: {data.get('message')}"


# --- Feature: Superadmin language usage stats (routes_lang_stats.py) ---

class TestLangUsageStats:
    def test_lang_usage_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/lang-usage/stats", timeout=15)
        assert r.status_code in (401, 403)

    def test_lang_usage_returns_daily_series(self):
        token = _admin_token()
        r = requests.get(
            f"{BASE_URL}/api/admin/lang-usage/stats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert "daily" in data, f"expected 'daily' field, keys={list(data.keys())}"
        assert isinstance(data["daily"], list), "daily should be a list"
