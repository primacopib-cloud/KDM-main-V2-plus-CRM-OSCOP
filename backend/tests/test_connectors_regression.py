"""
Regression tests after backend/.env password quoting fix.
Focus: connectors health, auth for 3 users, quick regression endpoints.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

CREDS = {
    "admin": ("admin@kdmarche-oscop.fr", "AdminKDM2025!"),
    "vendor": ("vendor-pro@kdmarche.fr", "Demo2026!"),
    "buyer": ("acheteur-pro@kdmarche.fr", "Demo2026!"),
}


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin_token():
    r = _login(*CREDS["admin"])
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Auth regression ---
@pytest.mark.parametrize("role", ["admin", "vendor", "buyer"])
def test_login_all_roles(role):
    email, pw = CREDS[role]
    r = _login(email, pw)
    assert r.status_code == 200, f"{role} login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token and isinstance(token, str) and len(token) > 10
    # password must NOT contain surrounding quotes (would fail if literal quotes stored)
    # login success itself proves that


# --- Connectors ---
def test_connectors_list(admin_headers):
    r = requests.get(f"{BASE_URL}/api/connectors", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Should have 6 connectors
    connectors = data if isinstance(data, list) else data.get("connectors", data.get("items", []))
    assert len(connectors) >= 6, f"Expected >=6 connectors, got {len(connectors)}: {connectors}"
    ids = [c.get("id") or c.get("name") or c.get("key") for c in connectors]
    print(f"Connector IDs: {ids}")


def test_connectors_health_status(admin_headers):
    r = requests.get(f"{BASE_URL}/api/connectors/health-status", headers=admin_headers, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    print(f"Health status response: {data}")
    # Expected 6 connectors
    items = data if isinstance(data, list) else data.get("statuses", data.get("connectors", data.get("results", data.get("items", []))))
    assert items, f"No connectors returned: {data}"
    expected = {"oscop-ged", "oscop-finance", "oscop-ia-bois", "oscop-ge", "coppam", "crm-ess"}
    seen = set()
    failures = []
    for item in items:
        cid = item.get("id") or item.get("connector_id") or item.get("name") or item.get("key")
        status = item.get("status") or item.get("health")
        err = item.get("error")
        seen.add(cid)
        print(f"  - {cid}: status={status}, error={err}")
        if str(status).lower() not in ("ok", "healthy", "up", "online", "success"):
            failures.append((cid, status, err))
    missing = expected - seen
    assert not missing, f"Missing connectors: {missing}"
    assert not failures, f"Unhealthy connectors: {failures}"


def test_connectors_sync_events(admin_headers):
    r = requests.get(f"{BASE_URL}/api/connectors/sync-events", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Just verify it responds correctly
    assert isinstance(data, (list, dict))


# --- Quick regression ---
def test_public_plans():
    r = requests.get(f"{BASE_URL}/api/public/plans", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    plans = data if isinstance(data, list) else data.get("plans", [])
    assert len(plans) == 3, f"Expected 3 plans, got {len(plans)}"


def test_public_kdmarche_videos():
    r = requests.get(f"{BASE_URL}/api/public/kdmarche-videos", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    videos = data if isinstance(data, list) else data.get("videos", [])
    assert len(videos) == 2, f"Expected 2 videos, got {len(videos)}"


def test_vendor_credits():
    # login as vendor
    r = _login(*CREDS["vendor"])
    assert r.status_code == 200
    token = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/vendor/credits/vendor-demo-pro", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Expect balance numeric + transactions
    balance = data.get("balance") if isinstance(data, dict) else None
    if balance is None:
        balance = data.get("credits")
    assert balance is not None, f"No balance/credits field: {data}"
    assert isinstance(balance, (int, float)), f"Balance not numeric: {balance}"
    assert "transactions" in data, f"No transactions field: {data}"
