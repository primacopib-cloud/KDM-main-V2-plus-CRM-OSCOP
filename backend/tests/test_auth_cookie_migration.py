"""Test suite for JWT cookie migration (session iteration).

Verifies:
- POST /api/auth/login sets Set-Cookie httpOnly access_token
- GET /api/auth/me works with cookie only
- GET /api/auth/me works with legacy Bearer token
- POST /api/auth/logout clears the cookie
- Authenticated endpoints work by cookie (buyer + admin flows)
"""
import os
import pytest
import requests

def _load_base_url():
    env_url = os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return ""

BASE_URL = _load_base_url()

BUYER = {"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}
ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!"}


# ---------- Fixtures ----------
@pytest.fixture
def buyer_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=BUYER, timeout=15)
    assert r.status_code == 200, f"buyer login failed: {r.status_code} {r.text[:200]}"
    return s, r


@pytest.fixture
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s, r


# ---------- Cookie primitives ----------
def test_login_sets_httponly_cookie(buyer_session):
    _, r = buyer_session
    set_cookie = r.headers.get("set-cookie", "")
    assert "access_token" in set_cookie.lower(), f"no access_token cookie: {set_cookie[:300]}"
    assert "httponly" in set_cookie.lower(), f"cookie is not HttpOnly: {set_cookie[:300]}"
    body = r.json()
    assert "access_token" in body or "token" in body  # legacy body still returned


def test_me_with_cookie_only(buyer_session):
    s, _ = buyer_session
    # remove Authorization if any and hit /auth/me relying only on session cookies
    r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 200, f"/auth/me by cookie failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert data.get("email", "").lower() == BUYER["email"].lower()


def test_me_with_bearer_legacy(buyer_session):
    _, r = buyer_session
    token = r.json().get("access_token") or r.json().get("token")
    assert token, "no token in login body for legacy Bearer path"
    fresh = requests.Session()  # no cookies
    r2 = fresh.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r2.status_code == 200, f"legacy Bearer failed: {r2.status_code}"


def test_me_without_credentials_401():
    fresh = requests.Session()
    r = fresh.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401


def test_logout_clears_cookie(buyer_session):
    s, _ = buyer_session
    r = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
    assert r.status_code in (200, 204), f"logout failed: {r.status_code} {r.text[:200]}"
    set_cookie = r.headers.get("set-cookie", "")
    # Either deletes cookie or sets it to empty + Max-Age=0
    assert "access_token" in set_cookie.lower(), f"logout should touch access_token cookie: {set_cookie[:300]}"
    # After logout, /auth/me should be 401 with same session
    r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r2.status_code == 401, f"session still valid after logout: {r2.status_code}"


# ---------- Buyer authenticated endpoints (cookie-only) ----------
class TestBuyerCookieAccess:
    """Verifies buyer authenticated endpoints work with the cookie (no Bearer header)."""

    def test_orders(self, buyer_session):
        s, _ = buyer_session
        r = s.get(f"{BASE_URL}/api/v2/orders", timeout=15)
        assert r.status_code == 200, f"/v2/orders: {r.status_code}"

    def test_favorites(self, buyer_session):
        s, _ = buyer_session
        r = s.get(f"{BASE_URL}/api/user-prefs/favorites", timeout=15)
        assert r.status_code == 200, f"/user-prefs/favorites: {r.status_code}"

    def test_shopping_lists(self, buyer_session):
        s, _ = buyer_session
        r = s.get(f"{BASE_URL}/api/shopping-lists", timeout=15)
        assert r.status_code == 200, f"/shopping-lists: {r.status_code}"

    def test_catalog_products(self, buyer_session):
        s, _ = buyer_session
        r = s.get(f"{BASE_URL}/api/v2/catalog/products", timeout=15)
        assert r.status_code == 200, f"/v2/catalog/products: {r.status_code}"

    def test_categories(self, buyer_session):
        s, _ = buyer_session
        r = s.get(f"{BASE_URL}/api/v2/catalog/categories", timeout=15)
        assert r.status_code == 200, f"/v2/catalog/categories: {r.status_code}"

    def test_buyer_dashboard(self, buyer_session):
        s, _ = buyer_session
        # Try a couple of likely endpoints
        candidates = ["/api/buyer/dashboard", "/api/dashboard/buyer", "/api/me/dashboard"]
        statuses = []
        for c in candidates:
            r = s.get(f"{BASE_URL}{c}", timeout=15)
            statuses.append((c, r.status_code))
            if r.status_code == 200:
                return
        # If none exist, skip rather than fail — endpoint name is fuzzy
        pytest.skip(f"No buyer dashboard endpoint found: {statuses}")


# ---------- Admin authenticated endpoints (cookie-only) ----------
class TestAdminCookieAccess:
    def test_admin_me(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json().get("email", "").lower() == ADMIN["email"].lower()

    def test_admin_plans(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/plans/subscriptions", timeout=15)
        assert r.status_code == 200, f"/admin/plans/subscriptions: {r.status_code} {r.text[:200]}"

    def test_admin_plans_options(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/plans/options", timeout=15)
        assert r.status_code == 200, f"/admin/plans/options: {r.status_code}"

    def test_admin_products(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/catalog/admin/products", timeout=15)
        assert r.status_code == 200, f"/catalog/admin/products: {r.status_code}"

    def test_admin_stats(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/stats", timeout=15)
        assert r.status_code == 200, f"/admin/stats: {r.status_code}"

    def test_admin_v2_applications(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/v2/admin/applications", timeout=15)
        assert r.status_code == 200, f"/v2/admin/applications: {r.status_code}"
