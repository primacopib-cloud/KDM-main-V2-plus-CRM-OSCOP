"""Tests for the Demande de devis footer + O'SCOP push + Super Admin Demandes tab (iter 46)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://coop-dashboard-8.preview.emergentagent.com').rstrip('/')

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No token: {data}"
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestRemoteTarifs:
    def test_remote_tarifs_structure(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/demandes/remote-tarifs", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tarif_achat" in data
        assert "tarifs" in data
        assert data["tarif_achat"].get("prix_ttc") == 25.02
        tarifs = data["tarifs"].get("tarifs_generaux") or []
        assert isinstance(tarifs, list) and len(tarifs) >= 1
        # Expect 6 as stated in review
        assert len(tarifs) >= 6, f"expected >=6 tarifs, got {len(tarifs)}"


class TestQuotePushFlow:
    submitted_company = "TEST QA Footer"

    def test_public_submit_quote(self):
        payload = {
            "company": self.submitted_company,
            "contact_name": "Marie Test",
            "email": "qa.footer@example.com",
            "phone": "0690123456",
            "plan": "undecided",
            "message": "Test QA automatique iter46 - demande de devis via footer",
        }
        r = requests.post(f"{BASE_URL}/api/quotes", json=payload)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data.get("id") or data.get("quote_id") or data.get("success"), data

    def test_push_appears_in_admin_pushes(self, admin_headers):
        # push is async; wait a bit
        found = None
        for _ in range(10):
            time.sleep(2)
            r = requests.get(f"{BASE_URL}/api/admin/demandes/pushes", headers=admin_headers)
            assert r.status_code == 200, r.text
            quotes = (r.json() or {}).get("quotes", [])
            latest = None
            for q in quotes:
                if q.get("company") == self.submitted_company and q.get("email") == "qa.footer@example.com":
                    if not latest or (q.get("created_at", "") > latest.get("created_at", "")):
                        latest = q
            if latest:
                found = latest
                if found.get("oscop_status") == "PUSHED":
                    break
        assert found, "Test quote not visible in /api/admin/demandes/pushes"
        assert found.get("oscop_status") == "PUSHED", f"Status={found.get('oscop_status')} err={found.get('oscop_error')}"
        assert found.get("oscop_demande_id"), f"oscop_demande_id missing: {found}"
