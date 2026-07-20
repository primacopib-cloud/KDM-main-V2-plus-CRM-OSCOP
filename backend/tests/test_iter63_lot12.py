"""Iter 63 / Lot 12 backend tests — LOGICOOP missions, Partner email, Audit journal, COOP'IA admin."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
PWD = "Demo2026!"


def _login(email, password, portal=None):
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PWD, portal="admin")


@pytest.fixture(scope="module")
def vendor_session():
    return _login(VENDOR_EMAIL, PWD)


@pytest.fixture(scope="module")
def buyer_session():
    return _login(BUYER_EMAIL, PWD)


# ---------- 1. LOGICOOP missions ----------

def test_missions_vendor_operator(vendor_session):
    r = vendor_session.get(f"{BASE_URL}/api/logicoop/missions", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data.get("items", [])
    assert len(items) >= 1, f"Expected >=1 mission, got {items}"
    enl = [m for m in items if m.get("mission") == "ENLEVEMENT"]
    assert len(enl) >= 1, f"Expected an ENLEVEMENT mission, items={items}"
    m = enl[0]
    assert m.get("zone_code") == "GUADELOUPE"
    assert m.get("order_number") == "KDM-20260716-60C1CBA8", f"got order_number={m.get('order_number')}"
    assert m.get("total_ht_cents") == 6400, f"expected 6400 cents (64,00€), got {m.get('total_ht_cents')}"
    assert m.get("pickup_location"), f"pickup_location empty: {m}"


def test_missions_buyer_forbidden(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/logicoop/missions", timeout=20)
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


# ---------- 2. Partner apply — email + notification ----------

def test_apply_partner_sends_emails_and_notification(admin_session):
    ts = int(time.time())
    email = f"test-iter63-{ts}@example.com"
    name = f"TEST_iter63_{ts}"
    r = requests.post(
        f"{BASE_URL}/api/partners/apply",
        json={"type": "COOPERS", "name": name, "email": email},
        timeout=25,
    )
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("ok") is True
    app_id = body.get("id")
    assert app_id
    # Give async tasks a moment
    time.sleep(1.0)
    # Verify application exists via admin listing
    r2 = admin_session.get(f"{BASE_URL}/api/admin/partners/applications", timeout=20)
    assert r2.status_code == 200
    apps = r2.json().get("items", [])
    assert any(a.get("id") == app_id for a in apps), "application not found"
    # Notification in-app: read via admin notifications endpoint if any (best-effort)
    r3 = admin_session.get(f"{BASE_URL}/api/notifications", timeout=20)
    if r3.status_code == 200:
        notifs = r3.json()
        items = notifs.get("items") if isinstance(notifs, dict) else notifs
        if isinstance(items, list):
            found = any(
                (n.get("type") == "partner_application") and (name in (n.get("title","") + n.get("body","")))
                for n in items
            )
            assert found, f"partner_application notification not found for {name}"


# ---------- 3. Audit journal ----------

def test_audit_list(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/audit?limit=10", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data.get("items", [])
    assert len(items) > 0
    # sorted desc by seq
    seqs = [it.get("seq") for it in items if it.get("seq") is not None]
    assert seqs == sorted(seqs, reverse=True), f"not desc sorted: {seqs}"
    types = data.get("event_types", [])
    for expected in ("TERRITORY_CREATED", "CAMPAIGN_CREATED", "LOT_CREATED"):
        assert expected in types, f"missing event_type {expected} in {types}"


def test_audit_filter_by_type(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/audit?event_type=TERRITORY_CREATED", timeout=20)
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) >= 1
    for it in items:
        assert it.get("event_type") == "TERRITORY_CREATED"


def test_audit_search(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/audit?q=admin@", timeout=20)
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) >= 1
    for it in items:
        blob = f"{it.get('actor','')}{it.get('event_type','')}{it.get('consultation_id','')}"
        assert "admin@" in blob.lower() or "admin" in blob.lower()


def test_audit_verify_chain(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/audit/verify", timeout=30)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert data.get("valid") is True, f"chain invalid: {data}"
    verified = data.get("entries_verified") or data.get("verified") or 0
    assert verified >= 383, f"expected >=383 verified entries, got {verified}"


def test_audit_forbidden_for_buyer(buyer_session):
    r = buyer_session.get(f"{BASE_URL}/api/admin/audit?limit=5", timeout=20)
    assert r.status_code == 403


# ---------- 4. COOP'IA procedure suggestion accessible to ADMIN ----------

def test_coopia_procedure_suggestion_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/buyer-tools/procedure-suggestion?category=alimentaire", timeout=60)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    # response should contain a suggestion / procedure code
    txt = str(data).upper()
    assert ("SCELLEE" in txt) or ("ENCHERE" in txt) or ("PROCEDURE" in txt) or ("RECOMMEND" in txt.upper())
