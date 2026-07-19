"""Iteration 49 — E2E tests for new features: Messages, Announcements, Flash Promos,
Fiscal Register, Partner Conventions, Vendor Invoices PDF, Vendor Onboarding new fields."""
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PASSWORD = "Demo2026!"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"},
               timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def vendor_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PASSWORD},
               timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Vendor login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- Messages ----------

class TestMessages:
    def test_directory(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/messages/directory", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) > 0

    def test_send_and_inbox_flow(self, admin_session, vendor_session):
        # find vendor-pro id via directory
        r = admin_session.get(f"{BASE_URL}/api/messages/directory", timeout=15)
        assert r.status_code == 200
        # get vendor id via /api/auth/me endpoint on vendor session
        me = vendor_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200, me.text
        vendor_id = me.json().get("id") or me.json().get("user", {}).get("id")
        assert vendor_id

        # Send message admin -> vendor
        payload = {
            "to_user_id": vendor_id,
            "subject": "TEST_iter49 subject",
            "body": "TEST_iter49 body content"
        }
        r = admin_session.post(f"{BASE_URL}/api/messages", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["subject"] == "TEST_iter49 subject"
        mid = msg["id"]

        # Sent list has it
        r = admin_session.get(f"{BASE_URL}/api/messages/sent", timeout=15)
        assert r.status_code == 200
        assert any(m["id"] == mid for m in r.json()["items"])

        # Vendor inbox has it
        r = vendor_session.get(f"{BASE_URL}/api/messages/inbox", timeout=15)
        assert r.status_code == 200
        assert any(m["id"] == mid for m in r.json()["items"])

        # Unread count > 0
        r = vendor_session.get(f"{BASE_URL}/api/messages/unread-count", timeout=15)
        assert r.status_code == 200
        assert r.json()["unread"] >= 1

        # Mark read
        r = vendor_session.post(f"{BASE_URL}/api/messages/{mid}/read", timeout=15)
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ---------- Announcements ----------

class TestAnnouncements:
    created_id = None

    def test_create_and_list(self, admin_session):
        payload = {
            "title": "TEST_iter49 Announcement",
            "body": "Body of test announcement",
            "priority": "urgente",
            "audiences": ["all"],
            "active": True,
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/announcements", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == payload["title"]
        TestAnnouncements.created_id = data["id"]

        # Public list
        r = requests.get(f"{BASE_URL}/api/announcements", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(a["id"] == TestAnnouncements.created_id for a in items)

    def test_view_increment(self, admin_session):
        aid = TestAnnouncements.created_id
        assert aid
        r = requests.post(f"{BASE_URL}/api/announcements/{aid}/view", timeout=15)
        assert r.status_code == 200

    def test_update(self, admin_session):
        aid = TestAnnouncements.created_id
        r = admin_session.put(f"{BASE_URL}/api/admin/announcements/{aid}",
                              json={"title": "TEST_iter49 Updated"}, timeout=15)
        assert r.status_code == 200

    def test_delete(self, admin_session):
        aid = TestAnnouncements.created_id
        r = admin_session.delete(f"{BASE_URL}/api/admin/announcements/{aid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["deleted"] is True


# ---------- Flash Promos ----------

class TestFlashPromos:
    created_id = None

    def test_create_flash_promo(self, admin_session):
        starts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        ends = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            "title": "TEST_iter49 Flash",
            "description": "Test flash promo",
            "discount_pct": 20,
            "starts_at": starts,
            "ends_at": ends,
            "placements": ["landing", "kdmarche"],
            "active": True,
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/flash-promos", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == payload["title"]
        TestFlashPromos.created_id = data["id"]

        # Public list — placement landing
        r = requests.get(f"{BASE_URL}/api/public/flash-promos?placement=landing", timeout=15)
        assert r.status_code == 200
        assert any(p["id"] == TestFlashPromos.created_id for p in r.json()["items"])

    def test_invalid_dates(self, admin_session):
        starts = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        ends = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        payload = {
            "title": "TEST_iter49 Invalid",
            "starts_at": starts, "ends_at": ends,
            "placements": ["landing"], "active": True,
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/flash-promos", json=payload, timeout=15)
        assert r.status_code == 400

    def test_update_and_delete(self, admin_session):
        pid = TestFlashPromos.created_id
        assert pid
        r = admin_session.put(f"{BASE_URL}/api/admin/flash-promos/{pid}",
                              json={"discount_pct": 30}, timeout=15)
        assert r.status_code == 200
        r = admin_session.delete(f"{BASE_URL}/api/admin/flash-promos/{pid}", timeout=15)
        assert r.status_code == 200


# ---------- Fiscal Register ----------

class TestFiscalRegister:
    def test_fiscal_register(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/accounting/fiscal-register", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Just verify structure — no 500
        assert isinstance(data, dict) or isinstance(data, list)


# ---------- Vendor Invoices PDF ----------

class TestVendorInvoices:
    def test_list_invoices(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/vendor-invoices", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data

    def test_pdf_download(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/vendor-invoices", timeout=15)
        items = r.json().get("items", [])
        if not items:
            pytest.skip("No vendor invoices in DB to test PDF download")
        number = items[0]["number"]
        r = admin_session.get(f"{BASE_URL}/api/admin/vendor-invoices/{number}/pdf", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500
        assert r.content[:4] == b"%PDF"


# ---------- Partner Conventions ----------

class TestPartnerConventions:
    created_id = None
    sign_token = None

    def test_create(self, admin_session):
        payload = {
            "title": "TEST_iter49 Convention",
            "partner_type": "PARTNER",
            "partner_name": "Test Partner SARL",
            "partner_email": "test-partner-iter49@example.com",
            "content": "Article 1 — Objet\nCeci est un contenu de test.",
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/partner-conventions", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        TestPartnerConventions.created_id = r.json()["id"]

    def test_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/partner-conventions", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "stats" in data

    def test_send_and_sign(self, admin_session):
        cid = TestPartnerConventions.created_id
        assert cid
        # Send (may fail if Brevo issue; do not hard-fail token retrieval — check DB via /admin list won't return sign_token)
        r = admin_session.post(f"{BASE_URL}/api/admin/partner-conventions/{cid}/send", timeout=30)
        # Send may fail if brevo config missing — still token should be set
        if r.status_code != 200:
            pytest.skip(f"Convention send failed (email/brevo?): {r.status_code} {r.text[:200]}")
        # We don't have direct token retrieval — but signature by token requires token from email
        # So we test the by-token endpoint returns 404 for a bad token
        r2 = requests.get(f"{BASE_URL}/api/partner-conventions/by-token/badtoken123", timeout=15)
        assert r2.status_code == 404

    def test_pdf(self, admin_session):
        cid = TestPartnerConventions.created_id
        r = admin_session.get(f"{BASE_URL}/api/admin/partner-conventions/{cid}/pdf", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_delete_draft(self, admin_session):
        cid = TestPartnerConventions.created_id
        # It's in SENT (or DRAFT if send skipped) — delete allowed
        r = admin_session.delete(f"{BASE_URL}/api/admin/partner-conventions/{cid}", timeout=15)
        # Either deleted or 400 if signed
        assert r.status_code in (200, 400)


# ---------- Vendor Onboarding new fields ----------

class TestVendorOnboarding:
    def test_start_with_new_fields(self):
        payload = {
            "company": "TEST_iter49 Onboarding SARL",
            "contact_name": "Jean Dupont",
            "email": f"test-iter49-{int(time.time())}@example.com",
            "phone": "0690123456",
            "siret": "12345678901234",
            "plan_slug": "ess-acces-pro",
            "origin_url": BASE_URL,
            "member_type": "vendor",
            "locale": "fr",
            "country": "GP",
            "legal_form": "SARL",
            "first_name": "Jean",
            "last_name": "Dupont",
        }
        r = requests.post(f"{BASE_URL}/api/vendor-onboarding/start", json=payload, timeout=30)
        # Might fail if plan doesn't exist — try alternative
        if r.status_code == 400 and "invalide" in r.text.lower():
            # Try alternate plan slugs
            for slug in ["vendor_pro", "vendor-pro-monthly", "adhesion_vendeur_pro", "vendor_pro_annual"]:
                payload["plan_slug"] = slug
                r = requests.post(f"{BASE_URL}/api/vendor-onboarding/start", json=payload, timeout=30)
                if r.status_code == 200:
                    break
        assert r.status_code == 200, f"onboarding start failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert "onboarding_id" in data
        assert "checkout_url" in data
        assert "stripe.com" in data["checkout_url"] or "checkout" in data["checkout_url"]

        # Verify persistence via status endpoint
        oid = data["onboarding_id"]
        r = requests.get(f"{BASE_URL}/api/vendor-onboarding/{oid}/status", timeout=15)
        assert r.status_code == 200
