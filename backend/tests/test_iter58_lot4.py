"""Iter 58 — Lot 4 features:
 - Vendor notification prefs GET/PUT
 - Vendor recap settings GET/PUT
 - Admin consultation duplicate
 - Admin campaign dashboard
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PWD = "Demo2026!"

EXISTING_CAMP_ID = "08e38381-5c08-420f-9730-0ad52a23900b"


def _login(session, email, pwd, portal=None):
    body = {"email": email, "password": pwd}
    if portal:
        body["portal"] = portal
    r = session.post(f"{BASE_URL}/api/auth/login", json=body)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PWD, portal="admin")
    return s


@pytest.fixture(scope="module")
def vendor_sess():
    s = requests.Session()
    _login(s, VENDOR_EMAIL, VENDOR_PWD)
    return s


# ---------- PREFS NOTIFICATIONS ----------
def test_get_notification_prefs_defaults(vendor_sess):
    r = vendor_sess.get(f"{BASE_URL}/api/prefs/notifications")
    assert r.status_code == 200
    d = r.json()
    assert set(d["events"]) == {"referral_bonus", "referral_welcome", "closure_reminder", "report_available"}
    for e in d["events"]:
        assert d["prefs"][e] in ("both", "email", "inapp", "none")


def test_put_notification_prefs_valid_and_persist(vendor_sess):
    payload = {"prefs": {"referral_bonus": "email", "referral_welcome": "inapp",
                          "closure_reminder": "none", "report_available": "both"}}
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/notifications", json=payload)
    assert r.status_code == 200 and r.json().get("ok") is True
    # GET back
    d = vendor_sess.get(f"{BASE_URL}/api/prefs/notifications").json()
    for k, v in payload["prefs"].items():
        assert d["prefs"][k] == v
    # restore defaults
    vendor_sess.put(f"{BASE_URL}/api/prefs/notifications",
                    json={"prefs": {e: "both" for e in payload["prefs"]}})


def test_put_notification_prefs_invalid(vendor_sess):
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/notifications",
                        json={"prefs": {"referral_bonus": "xxx"}})
    assert r.status_code == 400
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/notifications",
                        json={"prefs": {"unknown_event": "both"}})
    assert r.status_code == 400


# ---------- PREFS RECAP ----------
def test_get_recap_defaults(vendor_sess):
    r = vendor_sess.get(f"{BASE_URL}/api/prefs/recap")
    assert r.status_code == 200
    d = r.json()
    assert 0 <= d["day"] <= 6
    assert d["frequency"] in ("weekly", "biweekly", "monthly")
    assert isinstance(d["enabled"], bool)


def test_put_recap_valid_and_persist(vendor_sess):
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/recap",
                        json={"enabled": True, "day": 3, "frequency": "biweekly"})
    assert r.status_code == 200
    d = vendor_sess.get(f"{BASE_URL}/api/prefs/recap").json()
    assert d["day"] == 3 and d["frequency"] == "biweekly" and d["enabled"] is True
    # restore
    vendor_sess.put(f"{BASE_URL}/api/prefs/recap",
                    json={"enabled": True, "day": 0, "frequency": "weekly"})


def test_put_recap_invalid_day(vendor_sess):
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/recap",
                        json={"enabled": True, "day": 9, "frequency": "weekly"})
    assert r.status_code == 400


def test_put_recap_invalid_frequency(vendor_sess):
    r = vendor_sess.put(f"{BASE_URL}/api/prefs/recap",
                        json={"enabled": True, "day": 0, "frequency": "daily"})
    assert r.status_code == 400


# ---------- CAMPAIGN DASHBOARD ----------
def test_campaign_dashboard(admin_sess):
    r = admin_sess.get(f"{BASE_URL}/api/admin/campaigns/{EXISTING_CAMP_ID}/dashboard")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["campaign"]["id"] == EXISTING_CAMP_ID
    assert "lots" in d and isinstance(d["lots"], list)
    assert "totals" in d
    for k in ("lots", "inscriptions", "offres_valides", "attribues"):
        assert k in d["totals"]
    assert d["totals"]["lots"] == len(d["lots"])
    # each lot has expected fields
    for lot in d["lots"]:
        assert "entries" in lot and "valid_bids" in lot and "awarded" in lot


def test_campaign_dashboard_404(admin_sess):
    r = admin_sess.get(f"{BASE_URL}/api/admin/campaigns/nope-xyz/dashboard")
    assert r.status_code == 404


# ---------- CONSULTATION DUPLICATE ----------
def _create_transport_consultation(admin_sess):
    payload = {
        "title": "TEST_iter58_dup_src", "type": "STANDARD", "procedure": "SCELLEE",
        "category": "transport", "products": [], "territories": ["GUADELOUPE"],
        "specs": "test", "max_rounds": 3,
        "opens_at": "2026-08-01T00:00:00+00:00",
        "closes_at": "2026-08-08T00:00:00+00:00",
    }
    r = admin_sess.post(f"{BASE_URL}/api/admin/consultations", json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_duplicate_creates_brouillon_copy(admin_sess):
    src = _create_transport_consultation(admin_sess)
    src_id = src["id"]
    src_ref = src["ref"]
    try:
        r = admin_sess.post(f"{BASE_URL}/api/admin/consultations/{src_id}/duplicate")
        assert r.status_code == 200, r.text
        dup = r.json()
        assert dup["status"] == "BROUILLON"
        assert dup["duplicated_from"] == src_id
        assert dup["ref"] != src_ref
        assert dup["title"] == src["title"]
        assert dup["category"] == "transport"
        # legal_status re-resolved (transport = VERT)
        assert dup["legal_status"] == "VERT"
        # dates recalées à maintenant + durée d'origine (7 jours)
        from datetime import datetime as _dt
        dup_open = _dt.fromisoformat(dup["opens_at"])
        dup_close = _dt.fromisoformat(dup["closes_at"])
        duration_days = (dup_close - dup_open).days
        assert duration_days == 7
        # cleanup dup
        admin_sess.delete(f"{BASE_URL}/api/admin/consultations/{dup['id']}")
    finally:
        admin_sess.delete(f"{BASE_URL}/api/admin/consultations/{src_id}")


# ---------- AUTH GUARD ----------
def test_prefs_requires_auth():
    r = requests.get(f"{BASE_URL}/api/prefs/notifications")
    assert r.status_code in (401, 403)


def test_dashboard_requires_admin(vendor_sess):
    r = vendor_sess.get(f"{BASE_URL}/api/admin/campaigns/{EXISTING_CAMP_ID}/dashboard")
    assert r.status_code in (401, 403)
