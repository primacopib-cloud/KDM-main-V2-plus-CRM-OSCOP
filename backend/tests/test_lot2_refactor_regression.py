"""
Backend regression test suite after LOT 2 refactoring (server.py split into
routes_core_*.py modules + shared core_deps.py helpers).

Focus: verify that all routes previously inlined in server.py still work
identically after the extraction into routes_core_auth/users/admin/notifications/orgs.
Plus smoke-checks on included routers (superadmin, v2, lolodrive, payments).
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PASSWORD = "Demo2026!"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(http, email, password):
    r = http.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data or "token" in data, f"no token in response: {data}"
    return data.get("access_token") or data.get("token"), data


@pytest.fixture(scope="session")
def buyer_token(http):
    tok, _ = _login(http, BUYER_EMAIL, BUYER_PASSWORD)
    return tok


@pytest.fixture(scope="session")
def admin_token(http):
    tok, data = _login(http, ADMIN_EMAIL, ADMIN_PASSWORD)
    user = data.get("user") or {}
    assert user.get("is_admin") is True, f"admin login did not return is_admin=true: {user}"
    return tok


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Core routes_core_auth.py ----------
class TestCoreAuthRoutes:
    def test_root(self, http):
        r = http.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_health(self, http):
        r = http.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy", data

    def test_login_buyer(self, http):
        tok, data = _login(http, BUYER_EMAIL, BUYER_PASSWORD)
        assert tok
        assert data.get("user", {}).get("email") == BUYER_EMAIL

    def test_login_admin_is_admin(self, http):
        _, data = _login(http, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert data["user"]["is_admin"] is True

    def test_auth_me_buyer(self, http, buyer_token):
        r = http.get(f"{API}/auth/me", headers=_auth(buyer_token), timeout=15)
        assert r.status_code == 200
        me = r.json()
        assert me.get("email") == BUYER_EMAIL

    def test_register_and_login(self, http):
        unique = uuid.uuid4().hex[:10]
        email = f"TEST_lot2_{unique}@example.com"
        payload = {
            "email": email,
            "password": "TestPass2026!",
            "contact_name": "Test Lot2",
            "phone": "+590123456789",
            "company_name": "TEST Company",
            "siret": str(uuid.uuid4().int)[:14],
        }
        r = http.post(f"{API}/auth/register", json=payload, timeout=20)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
        # Login with created account
        r2 = http.post(f"{API}/auth/login", json={"email": email, "password": "TestPass2026!"}, timeout=20)
        assert r2.status_code == 200, r2.text


# ---------- routes_core_users.py ----------
class TestCoreUsersRoutes:
    def test_users_stats_buyer(self, http, buyer_token):
        r = http.get(f"{API}/users/stats", headers=_auth(buyer_token), timeout=15)
        assert r.status_code == 200

    def test_credits_buyer(self, http, buyer_token):
        r = http.get(f"{API}/credits", headers=_auth(buyer_token), timeout=15)
        assert r.status_code == 200

    def test_subscriptions_public(self, http):
        r = http.get(f"{API}/subscriptions", timeout=15)
        assert r.status_code == 200
        data = r.json()
        plans = data.get("plans") if isinstance(data, dict) else data
        assert isinstance(plans, list) and len(plans) > 0

    def test_documents_public(self, http):
        r = http.get(f"{API}/documents", timeout=15)
        assert r.status_code == 200

    def test_create_quote_public(self, http):
        payload = {
            "company": "TEST Regression Co",
            "contact_name": "Reg Tester",
            "email": f"TEST_quote_{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+590601020304",
            "plan": "essentiel",
            "message": "Regression smoke test after LOT 2 refactor",
        }
        r = http.post(f"{API}/quotes", json=payload, timeout=20)
        assert r.status_code in (200, 201), f"quote create failed: {r.status_code} {r.text}"


# ---------- routes_core_admin.py ----------
class TestCoreAdminRoutes:
    def test_admin_stats(self, http, admin_token):
        r = http.get(f"{API}/admin/stats", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200

    def test_admin_users(self, http, admin_token):
        r = http.get(f"{API}/admin/users", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200

    def test_admin_quotes(self, http, admin_token):
        r = http.get(f"{API}/admin/quotes", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200

    def test_admin_organizations(self, http, admin_token):
        r = http.get(f"{API}/admin/organizations", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200


# ---------- routes_core_notifications.py ----------
class TestCoreNotifications:
    def test_notifications_list(self, http, admin_token):
        r = http.get(f"{API}/notifications", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "unread_count" in data, f"missing unread_count: {data}"

    def test_notifications_read_all(self, http, admin_token):
        r = http.post(f"{API}/notifications/read-all", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200


# ---------- routes_core_orgs.py ----------
class TestCoreOrgsRoutes:
    def test_zones_public(self, http):
        r = http.get(f"{API}/zones", timeout=15)
        assert r.status_code == 200
        zones = r.json()
        assert isinstance(zones, list) and len(zones) > 0
        names = " ".join(z.get("name", "") for z in zones)
        assert "Guadeloupe" in names or "Martinique" in names, f"expected DOM zones, got: {names}"


# ---------- Included routers still working ----------
class TestIncludedRouters:
    def test_superadmin_kpis(self, http, admin_token):
        r = http.get(f"{API}/superadmin/kpis", headers=_auth(admin_token), params={"period": "month"}, timeout=20)
        assert r.status_code == 200, r.text

    def test_v2_plans(self, http):
        r = http.get(f"{API}/v2/plans", timeout=15)
        assert r.status_code == 200

    def test_lolodrive_territories(self, http):
        r = http.get(f"{API}/lolodrive/territories", timeout=15)
        assert r.status_code == 200

    def test_payments_packages_buyer(self, http, buyer_token):
        r = http.get(f"{API}/payments/packages", headers=_auth(buyer_token), timeout=15)
        assert r.status_code == 200
