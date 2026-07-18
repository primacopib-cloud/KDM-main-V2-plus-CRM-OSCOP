"""Iter41 - Test flux BUYER_PRO adhésion + registre + non-régression stats support + FAQ."""
import os
import uuid
import asyncio
from datetime import datetime

import pytest
import requests

from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def unique_suffix():
    return uuid.uuid4().hex[:8]


def _unique_siret() -> str:
    # 14 chiffres unique
    return "9" + str(uuid.uuid4().int)[:13]


class TestBuyerProFlow:
    """Flux complet adhésion BUYER_PRO -> registre."""

    def test_full_flow(self, admin_session, unique_suffix):
        email = f"TEST-buyer-{unique_suffix}@kdm-test.fr"
        password = "TestPwd2026!"
        siret = _unique_siret()

        # 1. Register
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": password,
            "contact_name": "Buyer Test",
            "company_name": f"TEST BUYER PRO {unique_suffix}",
            "siret": siret,
            "account_type": "buyer",
            "phone": "0690000000",
        }, timeout=30)
        assert r.status_code in (200, 201), f"register: {r.status_code} {r.text[:200]}"

        # 2. Login user
        user_s = _login(email, password)

        # 3. Create org BUYER_PRO
        r = user_s.post(f"{BASE_URL}/api/v2/orgs", json={
            "legal_name": f"TEST BUYER PRO {unique_suffix}",
            "registration_country": "FR",
            "registration_id": siret,
            "territory": "GUADELOUPE",
            "member_type": "BUYER_PRO",
            "contact_email": email,
            "contact_name": "Buyer Test",
            "contact_phone": "0690000000",
        }, timeout=30)
        assert r.status_code == 201, f"create_org: {r.status_code} {r.text[:300]}"
        org_id = r.json()["id"]

        # 4. Create application
        r = user_s.post(f"{BASE_URL}/api/v2/orgs/{org_id}/applications", timeout=30)
        assert r.status_code == 200, f"create_application: {r.status_code} {r.text[:300]}"
        app_id = r.json()["id"]

        # 5. Insert docs directly in Mongo
        async def _insert_docs():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            now = datetime.utcnow()
            for doc_type in ("REGISTRATION_DOC", "ID_SIGNATORY"):
                await db.application_documents.insert_one({
                    "id": str(uuid.uuid4()),
                    "application_id": app_id,
                    "org_id": org_id,
                    "doc_type": doc_type,
                    "file_url": f"https://fake-storage/{doc_type}.pdf",
                    "file_name": f"{doc_type}.pdf",
                    "checksum_sha256": "0" * 64,
                    "status": "PENDING",
                    "uploaded_at": now,
                    "created_at": now,
                })
            client.close()
        asyncio.get_event_loop().run_until_complete(_insert_docs())

        # 6. Submit
        r = user_s.post(f"{BASE_URL}/api/v2/applications/{app_id}/submit", timeout=30)
        assert r.status_code == 200, f"submit: {r.status_code} {r.text[:300]}"
        assert r.json()["status"] == "PENDING_REVIEW"

        # 7. Admin decision APPROVED
        r = admin_session.post(f"{BASE_URL}/api/v2/applications/{app_id}/decision", json={
            "decision": "APPROVED",
        }, timeout=30)
        assert r.status_code == 200, f"decision: {r.status_code} {r.text[:300]}"
        assert r.json()["status"] == "APPROVED"

        # 8. GET registry
        r = admin_session.get(f"{BASE_URL}/api/v2/admin/member-registry?member_type=BUYER_PRO", timeout=30)
        assert r.status_code == 200
        data = r.json()
        members = data.get("members", [])
        assert any(m.get("org_id") == org_id for m in members), (
            f"New org {org_id} not found in BUYER_PRO registry. Sample: {[m.get('legal_name') for m in members[:5]]}"
        )
        # Vérifier détails
        entry = next(m for m in members if m["org_id"] == org_id)
        assert entry["member_type"] == "BUYER_PRO"
        assert entry["siret"] == siret
        assert entry["territory"] == "GUADELOUPE"
        assert entry["status"] == "ACTIVE"
        assert entry["contact_email"] == email


class TestRegistryAuth:
    def test_registry_forbidden_for_non_admin(self):
        # buyer user
        s = _login("acheteur-pro@kdmarche.fr", "Demo2026!")
        r = s.get(f"{BASE_URL}/api/v2/admin/member-registry", timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"

    def test_registry_lists_vendor_pro(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/v2/admin/member-registry?member_type=VENDOR_PRO", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "members" in data and "counts" in data
        # Le seed contient 'REGISTRE VENDEUR TEST SARL'
        names = [m.get("legal_name") for m in data["members"]]
        assert any("REGISTRE VENDEUR TEST" in (n or "").upper() for n in names), f"seed vendor missing: {names}"


class TestSupportStats:
    """Stats support admin - non-régression."""

    def test_stats_admin_only(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/support/admin/stats", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        # Champs attendus
        assert "avg_first_response_hours" in data or "avg_response_hours" in data or "avg_first_response" in data, f"missing avg field, keys={list(data.keys())}"
        assert "total_tickets" in data or "total" in data, f"missing total, keys={list(data.keys())}"

    def test_stats_forbidden_for_non_admin(self):
        s = _login("acheteur-pro@kdmarche.fr", "Demo2026!")
        r = s.get(f"{BASE_URL}/api/support/admin/stats", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


class TestSupportTicketRegression:
    def test_create_ticket_public(self):
        r = requests.post(f"{BASE_URL}/api/support/contact", json={
            "email": "TEST-support@kdm-test.fr",
            "name": "Test Support",
            "category": "GENERAL",
            "subject": "Test iter41",
            "message": "Ceci est un ticket de test iter41",
        }, timeout=30)
        # Selon impl, peut être 200/201
        assert r.status_code in (200, 201), f"create ticket: {r.status_code} {r.text[:200]}"
