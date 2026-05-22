"""
Backend tests for Super Admin - Plans & Credits Management
Endpoints: /api/admin/plans/*
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://plan-builder-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    # Try common login endpoint
    for path in ("/auth/login", "/login"):
        r = requests.post(f"{API}{path}", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token") or data.get("token") or (data.get("user") or {}).get("token")
            if token:
                return token
    pytest.skip("Cannot authenticate admin user via /auth/login or /login")


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def admin_user_id(admin_headers):
    """Find admin user id via credits/users search."""
    r = requests.get(f"{API}/admin/plans/credits/users", params={"search": "admin@kdmarche"}, headers=admin_headers, timeout=30)
    if r.status_code == 200 and r.json().get("users"):
        return r.json()["users"][0]["user_id"]
    pytest.skip("Cannot resolve admin user id")


# ---------- Auth checks ----------
class TestAuthorization:
    def test_no_token_returns_403(self):
        r = requests.get(f"{API}/admin/plans/subscriptions", timeout=30)
        assert r.status_code == 403, f"Expected 403 without token, got {r.status_code}"

    def test_invalid_token_returns_403(self):
        r = requests.get(f"{API}/admin/plans/subscriptions", headers={"Authorization": "Bearer invalid.token.here"}, timeout=30)
        assert r.status_code == 403

    def test_stats_requires_admin(self):
        r = requests.get(f"{API}/admin/plans/stats", timeout=30)
        assert r.status_code == 403


# ---------- Subscription Plans ----------
class TestSubscriptionPlans:
    def test_list_seeded_plans(self, admin_headers):
        r = requests.get(f"{API}/admin/plans/subscriptions", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        plans = r.json()
        ids = [p["id"] for p in plans]
        assert "ess-acces-pro" in ids
        assert "ess-volume-pro" in ids
        assert "ess-impact-pro" in ids
        # validate structure
        sample = plans[0]
        for k in ("name", "slug", "price_cents", "period", "default_credits", "features", "active"):
            assert k in sample

    def test_list_include_inactive(self, admin_headers):
        r = requests.get(f"{API}/admin/plans/subscriptions", params={"include_inactive": "true"}, headers=admin_headers, timeout=30)
        assert r.status_code == 200

    def test_create_update_delete_plan_lifecycle(self, admin_headers):
        unique = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_PLAN_{unique}",
            "description": "Plan de test",
            "price_cents": 9900,
            "period": "mois",
            "default_credits": 50,
            "features": ["Feature A", "Feature B"],
            "popular": False
        }
        # CREATE
        r = requests.post(f"{API}/admin/plans/subscriptions", headers=admin_headers, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        created = r.json()
        plan_id = created["id"]
        assert created["name"] == payload["name"]
        assert created["price_cents"] == 9900
        assert created["default_credits"] == 50

        # GET (verify persistence)
        r = requests.get(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["name"] == payload["name"]

        # Verify it appears in public /api/subscriptions
        r = requests.get(f"{API}/subscriptions", timeout=30)
        assert r.status_code == 200
        body = r.json()
        plans_list = body["plans"] if isinstance(body, dict) and "plans" in body else body
        public_ids = [p.get("id") for p in plans_list]
        assert plan_id in public_ids, "new plan not in public /api/subscriptions"

        # PATCH
        r = requests.patch(
            f"{API}/admin/plans/subscriptions/{plan_id}",
            headers=admin_headers,
            json={"price_cents": 12900, "popular": True, "name": f"TEST_PLAN_{unique}_UPD"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        upd = r.json()
        assert upd["price_cents"] == 12900
        assert upd["popular"] is True
        assert upd["name"].endswith("_UPD")

        # Verify update persisted
        r = requests.get(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, timeout=30)
        assert r.json()["price_cents"] == 12900

        # SOFT DELETE
        r = requests.delete(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        # Should be inactive
        r = requests.get(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["active"] is False

        # FORCE DELETE
        r = requests.delete(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, params={"force": "true"}, timeout=30)
        assert r.status_code == 200
        # Should be gone
        r = requests.get(f"{API}/admin/plans/subscriptions/{plan_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 404


# ---------- Plan Options ----------
class TestPlanOptions:
    def test_options_crud(self, admin_headers):
        # List initial
        r = requests.get(f"{API}/admin/plans/options", headers=admin_headers, timeout=30)
        assert r.status_code == 200

        # Create
        payload = {
            "name": f"TEST_OPT_{uuid.uuid4().hex[:6]}",
            "description": "Option test",
            "price_cents": 1900,
            "period": "mois",
            "credits_included": 25,
            "compatible_plans": [],
        }
        r = requests.post(f"{API}/admin/plans/options", headers=admin_headers, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        opt = r.json()
        opt_id = opt["id"]
        assert opt["price_cents"] == 1900
        assert opt["credits_included"] == 25

        # Patch
        r = requests.patch(f"{API}/admin/plans/options/{opt_id}", headers=admin_headers, json={"price_cents": 2900}, timeout=30)
        assert r.status_code == 200
        assert r.json()["price_cents"] == 2900

        # Delete
        r = requests.delete(f"{API}/admin/plans/options/{opt_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 200

        # Confirm gone (delete returns 404 a second time)
        r = requests.delete(f"{API}/admin/plans/options/{opt_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 404


# ---------- Credits ----------
class TestCredits:
    def test_list_users_with_credits(self, admin_headers):
        r = requests.get(f"{API}/admin/plans/credits/users", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "users" in data and "total" in data

    def test_search_users(self, admin_headers):
        r = requests.get(f"{API}/admin/plans/credits/users", params={"search": "admin"}, headers=admin_headers, timeout=30)
        assert r.status_code == 200
        users = r.json().get("users", [])
        assert any("admin" in (u.get("email") or "").lower() for u in users)

    def test_get_user_detail(self, admin_headers, admin_user_id):
        r = requests.get(f"{API}/admin/plans/credits/users/{admin_user_id}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "credits_balance" in data
        assert "history" in data

    def test_adjust_credits_add(self, admin_headers, admin_user_id):
        # Get current balance
        r = requests.get(f"{API}/admin/plans/credits/users/{admin_user_id}", headers=admin_headers, timeout=30)
        before = r.json()["credits_balance"]

        # Add 50
        r = requests.post(
            f"{API}/admin/plans/credits/users/{admin_user_id}/adjust",
            headers=admin_headers,
            json={"amount": 50, "reason": "Test credit add"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["new_balance"] == before + 50

        # Verify history has entry
        r = requests.get(f"{API}/admin/plans/credits/users/{admin_user_id}", headers=admin_headers, timeout=30)
        assert r.json()["credits_balance"] == before + 50
        assert len(r.json()["history"]) > 0
        assert r.json()["history"][0]["reason"] == "Test credit add"

        # Deduct 50 cleanup
        requests.post(
            f"{API}/admin/plans/credits/users/{admin_user_id}/adjust",
            headers=admin_headers,
            json={"amount": -50, "reason": "Test cleanup"},
            timeout=30,
        )

    def test_adjust_credits_negative_rejected(self, admin_headers, admin_user_id):
        # Try to deduct way more than balance
        r = requests.post(
            f"{API}/admin/plans/credits/users/{admin_user_id}/adjust",
            headers=admin_headers,
            json={"amount": -999999, "reason": "Should fail"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_bulk_adjust(self, admin_headers, admin_user_id):
        r = requests.post(
            f"{API}/admin/plans/credits/bulk-adjust",
            headers=admin_headers,
            json={"adjustments": [{"user_id": admin_user_id, "amount": 10, "reason": "bulk test"}]},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["results"][0]["status"] == "success"

        # cleanup
        requests.post(
            f"{API}/admin/plans/credits/users/{admin_user_id}/adjust",
            headers=admin_headers,
            json={"amount": -10, "reason": "cleanup"},
            timeout=30,
        )

    def test_stats(self, admin_headers):
        r = requests.get(f"{API}/admin/plans/stats", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("plans", "options", "subscriptions", "credits"):
            assert k in data
        assert data["plans"]["active"] >= 3


# ---------- Public /api/subscriptions ----------
class TestPublicSubscriptions:
    def test_subscriptions_returns_db_plans(self):
        r = requests.get(f"{API}/subscriptions", timeout=30)
        assert r.status_code == 200
        body = r.json()
        plans = body["plans"] if isinstance(body, dict) and "plans" in body else body
        ids = [p.get("id") for p in plans]
        assert "ess-acces-pro" in ids
        assert "ess-volume-pro" in ids
        assert "ess-impact-pro" in ids
