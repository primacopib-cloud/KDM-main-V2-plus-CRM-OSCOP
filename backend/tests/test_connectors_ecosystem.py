"""Backend tests for connectors ecosystem, IA Bois sync, sync-events, health.

Iteration 29 — validates:
- GET /api/connectors (admin) → registry
- GET /api/connectors/ecosystem (admin) → {apps, total, ok} live health
- GET /api/connectors/ecosystem without token → 401/403
- POST /api/connectors/oscop-ia-bois/sync (admin) → {status, total, new, event_id}
- GET /api/connectors/iabois/projects (admin) → projects list
- GET /api/connectors/sync-events (admin) → events + counts, SUCCESS for oscop-ia-bois
- GET /api/connectors/oscop-ia-bois/health (admin) → status OK
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Registry ---
def test_list_connectors(admin_headers):
    r = requests.get(f"{BASE_URL}/api/connectors", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "connectors" in body and isinstance(body["connectors"], list)
    assert len(body["connectors"]) >= 4
    names = {c["name"] for c in body["connectors"]}
    assert "oscop-ia-bois" in names


# --- Ecosystem overview ---
def test_ecosystem_requires_auth():
    r = requests.get(f"{BASE_URL}/api/connectors/ecosystem", timeout=30)
    assert r.status_code in (401, 403), f"Expected 401/403 without token, got {r.status_code}"


def test_ecosystem_overview(admin_headers):
    r = requests.get(f"{BASE_URL}/api/connectors/ecosystem", headers=admin_headers, timeout=45)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    body = r.json()
    assert "apps" in body and "total" in body and "ok" in body
    assert isinstance(body["apps"], list) and len(body["apps"]) >= 4
    for app in body["apps"]:
        for k in ("name", "label", "base_url", "enabled", "health", "sync"):
            assert k in app, f"missing key {k} in app {app.get('name')}"
        assert "status" in app["health"]


# --- IA Bois sync ---
def test_iabois_manual_sync(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/connectors/oscop-ia-bois/sync",
        headers=admin_headers,
        timeout=60,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    body = r.json()
    for k in ("status", "total", "new", "event_id"):
        assert k in body, f"missing key {k}: {body}"
    assert body["status"] in ("OK", "SUCCESS", "ok")
    assert isinstance(body["total"], int)


def test_iabois_projects_list(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/connectors/iabois/projects?limit=200",
        headers=admin_headers,
        timeout=20,
    )
    assert r.status_code == 200
    body = r.json()
    assert "projects" in body and "total" in body
    assert isinstance(body["projects"], list)
    # Expected ~44 per problem statement
    assert body["total"] > 0, "No IA Bois projects imported"


def test_iabois_health(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/connectors/oscop-ia-bois/health",
        headers=admin_headers,
        timeout=20,
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "OK", f"Expected OK, got {body}"


# --- Sync events ---
def test_sync_events(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/connectors/sync-events?connector=oscop-ia-bois&limit=50",
        headers=admin_headers,
        timeout=20,
    )
    assert r.status_code == 200
    body = r.json()
    assert "events" in body and "counts" in body
    events = body["events"]
    assert len(events) > 0, "No sync events found for oscop-ia-bois"
    statuses = {e.get("status") for e in events}
    assert "SUCCESS" in statuses, f"No SUCCESS event for oscop-ia-bois; statuses={statuses}"
