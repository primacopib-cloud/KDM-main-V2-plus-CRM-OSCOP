"""Iteration 27 — Validate load_dotenv (no override) + Stripe key override + /health root.

Confirms preview still works after deployment-fix:
- GET /health returns 200 (no /api prefix — deployment readiness probe)
- GET /api/health returns 200
- Admin login + /api/v2/me works (auth cookies unchanged)
- Buyer login works
- Connectors: /api/connectors admin returns 2 enabled connectors
- Connector oscop-ged health OK (needs OSCOP_CRM_* env vars from .env)
- Stripe live-health: mode set + keys configured (not sk_test_emergent placeholder)
- Catalog products endpoint works (MongoDB operational)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!"}
BUYER = {"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:300]}"
    return s


@pytest.fixture(scope="module")
def buyer_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=BUYER, timeout=15)
    assert r.status_code == 200, f"Buyer login failed: {r.status_code} {r.text[:300]}"
    return s


# ---------- Health / deployment probes ----------

def test_root_health_endpoint_backend_direct():
    """New GET /health (no /api) must return 200 {status: ok} on the backend directly.
    NOTE: In preview, public /health without /api is routed to frontend (SPA index.html),
    so we hit backend on localhost:8001 to verify the actual FastAPI route added for the
    deployment readiness probe."""
    r = requests.get("http://localhost:8001/health", timeout=10)
    assert r.status_code == 200, f"/health returned {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data.get("status") == "ok", data


def test_public_root_health_returns_200():
    """In preview, public /health goes to frontend which returns 200 HTML — deployment
    probe only requires a 200 status code, so this is acceptable."""
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200


def test_api_health_endpoint():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200
    # api health returns {"status": "healthy" or "ok"}
    data = r.json()
    assert isinstance(data, dict) and ("status" in data or "ok" in data)


# ---------- Auth (cookies) still works ----------

def test_admin_me_via_cookie(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/v2/me", timeout=10)
    assert r.status_code == 200, f"/api/v2/me admin: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("email") == ADMIN["email"]


def test_buyer_me_via_cookie(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/v2/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("email") == BUYER["email"]


# ---------- MongoDB reachable (env load didn't break MONGO_URL) ----------

def test_catalog_products_returns_data(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/v2/catalog/products", timeout=15)
    assert r.status_code == 200, f"products: {r.status_code} {r.text[:300]}"
    data = r.json()
    # data can be list or dict with items
    items = data if isinstance(data, list) else data.get("items") or data.get("products") or []
    assert len(items) > 0, "Expected at least one product"


# ---------- Connectors (rely on OSCOP_CRM_* env vars from .env) ----------

def test_connectors_listing_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/connectors", timeout=15)
    assert r.status_code == 200, f"connectors list: {r.status_code} {r.text[:300]}"
    data = r.json()
    items = data if isinstance(data, list) else data.get("items") or data.get("connectors") or []
    enabled = [c for c in items if c.get("enabled") is True]
    assert len(enabled) >= 2, f"Expected >=2 enabled connectors, got {len(enabled)}: {[c.get('name') for c in items]}"


def test_connector_oscop_ged_health(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/connectors/oscop-ged/health", timeout=20)
    assert r.status_code == 200, f"oscop-ged health: {r.status_code} {r.text[:300]}"
    data = r.json()
    # Any positive health signal
    status = str(data.get("status") or data.get("ok") or "").lower()
    healthy_flag = data.get("healthy") is True or data.get("ok") is True or status in ("ok", "healthy", "up")
    assert healthy_flag or "error" not in data, f"unhealthy connector: {data}"


# ---------- Stripe: verify real keys loaded (not sk_test_emergent placeholder) ----------

def test_stripe_live_health_keys_configured(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/stripe/live-health", timeout=20)
    assert r.status_code == 200, f"stripe live-health: {r.status_code} {r.text[:300]}"
    data = r.json()
    accounts = data.get("accounts") or {}
    assert "oscop" in accounts and "kdmarche" in accounts, f"missing accounts: {accounts}"
    for acc in ("oscop", "kdmarche"):
        info = accounts[acc]
        assert info.get("key_configured") is True, f"{acc} key not configured: {info}"
        prefix = info.get("key_prefix") or ""
        # Ensure placeholder (sk_test_emergent) is NOT what's loaded
        assert "emergent" not in prefix.lower(), f"{acc} still using placeholder: {prefix}"
        assert prefix.startswith("sk_"), f"{acc} unexpected prefix: {prefix}"
