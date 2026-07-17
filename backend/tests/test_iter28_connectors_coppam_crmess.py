"""Iteration 28 — Validation flux COPPAM + CRM ESS + 4 connecteurs sur commande payée.

Contexte :
- Commande de référence poussée par le main agent : f002ce0d-8512-4274-8743-29698e21e0c4
- COPPAM distant en 500 sur endpoints métier (retry doit rester ERROR = comportement attendu)
- CRM ESS live OK
"""
import os
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


BASE_URL = _load_backend_url()
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PASSWORD = "Demo2026!"
ORDER_ID = "f002ce0d-8512-4274-8743-29698e21e0c4"

EXPECTED_CONNECTORS = {"oscop-ged", "oscop-finance", "oscop-ia-bois", "oscop-ge", "coppam", "crm-ess"}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


def test_list_connectors_6_all_enabled(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/connectors", timeout=15)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    connectors = data["connectors"]
    names = {c["name"] for c in connectors}
    assert names == EXPECTED_CONNECTORS, f"Missing/extra connectors: got {names}"
    for c in connectors:
        assert c["enabled"] is True, f"Connector {c['name']} not enabled: {c}"


def test_health_crm_ess_ok(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/connectors/crm-ess/health", timeout=30)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["status"] == "OK", f"crm-ess health not OK: {data}"


def test_health_coppam_ok(admin_session):
    """COPPAM /api/auth/session doit répondre 200 même si endpoints métier sont en 500."""
    r = admin_session.get(f"{BASE_URL}/api/connectors/coppam/health", timeout=30)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["status"] == "OK", f"coppam health not OK: {data}"


def test_sync_events_contains_4_connectors_for_order(admin_session):
    """Les 4 connecteurs (oscop-ged, oscop-finance, coppam, crm-ess) doivent avoir un event pour la commande."""
    r = admin_session.get(f"{BASE_URL}/api/connectors/sync-events?limit=200", timeout=15)
    assert r.status_code == 200, r.text[:300]
    events = r.json()["events"]
    order_events = [e for e in events if e.get("source_id") == ORDER_ID]
    by_conn = {}
    for e in order_events:
        by_conn.setdefault(e["connector"], []).append(e)

    # Vérification statuts attendus
    assert "oscop-finance" in by_conn, f"Missing oscop-finance event for order (found: {list(by_conn)})"
    assert any(e["status"] == "SUCCESS" for e in by_conn["oscop-finance"]), f"oscop-finance not SUCCESS: {by_conn['oscop-finance']}"

    assert "crm-ess" in by_conn, f"Missing crm-ess event (found: {list(by_conn)})"
    assert any(e["status"] == "SUCCESS" and e["action"] == "push_invoice" for e in by_conn["crm-ess"]), \
        f"crm-ess push_invoice not SUCCESS: {by_conn['crm-ess']}"

    assert "oscop-ged" in by_conn, f"Missing oscop-ged event"
    assert any(e["status"] == "ERROR" for e in by_conn["oscop-ged"]), f"oscop-ged expected ERROR: {by_conn['oscop-ged']}"

    assert "coppam" in by_conn, f"Missing coppam event"
    assert any(e["status"] == "ERROR" for e in by_conn["coppam"]), f"coppam expected ERROR: {by_conn['coppam']}"


def test_retry_coppam_stays_error_and_increments_attempts(admin_session):
    """Retry sur COPPAM ERROR doit rester ERROR (API distante 500) et incrémenter attempts."""
    r = admin_session.get(
        f"{BASE_URL}/api/connectors/sync-events?connector=coppam&status=ERROR&limit=50", timeout=15
    )
    assert r.status_code == 200
    events = [e for e in r.json()["events"] if e.get("source_id") == ORDER_ID]
    assert events, "No coppam ERROR event for the target order"
    ev = events[0]
    prev_attempts = ev.get("attempts", 0)
    event_id = ev["id"]

    retry_resp = admin_session.post(f"{BASE_URL}/api/connectors/sync-events/{event_id}/retry", timeout=30)
    assert retry_resp.status_code == 200, retry_resp.text[:300]
    data = retry_resp.json()
    assert data.get("status") == "ERROR", f"Expected ERROR after retry (remote 500), got: {data}"

    # Verify persistence: attempts incremented
    r2 = admin_session.get(
        f"{BASE_URL}/api/connectors/sync-events?connector=coppam&limit=50", timeout=15
    )
    refreshed = [e for e in r2.json()["events"] if e["id"] == event_id]
    assert refreshed, "Event disappeared after retry"
    new_attempts = refreshed[0].get("attempts", 0)
    assert new_attempts > prev_attempts, f"attempts not incremented: {prev_attempts} -> {new_attempts}"
    assert refreshed[0]["status"] == "ERROR"


def test_buyer_login_and_catalogue():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Buyer login failed: {r.status_code} {r.text[:200]}"
    r2 = s.get(f"{BASE_URL}/api/v2/catalog/products?limit=5", timeout=15)
    # accepte 200 avec products, ou 200 avec liste vide
    assert r2.status_code == 200, f"Catalogue KO: {r2.status_code} {r2.text[:200]}"
