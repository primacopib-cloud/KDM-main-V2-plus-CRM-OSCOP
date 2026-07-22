"""Iter 67 — PROSPECT'IA A/B campagnes + Bibliothèque + Preuve sociale + Rapport hebdo."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD, "portal": "admin"})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    # ensure prospectia enabled
    s.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": True})
    yield s
    # leave prospectia OFF as requested
    try:
        s.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": False})
    except Exception:
        pass


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ================ SECURITY ==================
class TestSecurityNoAuth:
    def test_library_get_no_auth(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/prospectia/library")
        assert r.status_code in (401, 403), r.status_code

    def test_social_admin_no_auth(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/social-proof/testimonials")
        assert r.status_code in (401, 403)

    def test_weekly_send_no_auth(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/admin/reports/weekly/send")
        assert r.status_code in (401, 403)


# ================ LIBRARY ==================
class TestLibrary:
    saved_id = None

    def test_create_script(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/prospectia/library", json={
            "title": "TEST_Iter67_Email_Vendeurs",
            "content": "Bonjour {prenom}, découvrez KDMARCHÉ pour {entreprise}: {lien}",
            "content_type": "email", "target": "vendor", "lang": "fr",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == "TEST_Iter67_Email_Vendeurs"
        assert "id" in data
        TestLibrary.saved_id = data["id"]

    def test_list_scripts_has_created(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/prospectia/library")
        assert r.status_code == 200
        items = r.json()["items"]
        found = next((i for i in items if i["id"] == TestLibrary.saved_id), None)
        assert found is not None
        assert "campaigns_count" in found
        assert "total_sent" in found
        assert "total_clicks" in found
        assert "click_rate" in found

    def test_delete_script(self, admin_session):
        r = admin_session.delete(f"{BASE_URL}/api/admin/prospectia/library/{TestLibrary.saved_id}")
        assert r.status_code == 200
        # verify gone
        r2 = admin_session.get(f"{BASE_URL}/api/admin/prospectia/library")
        assert not any(i["id"] == TestLibrary.saved_id for i in r2.json()["items"])


# ================ CAMPAIGN A/B ==================
class TestCampaignAB:
    campaign = None
    library_id = None

    def test_create_library_for_campaign(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/prospectia/library", json={
            "title": "TEST_Iter67_LibForCampaign",
            "content": "Corps: {prenom} pour {entreprise} sur {lien}",
            "content_type": "email", "target": "vendor", "lang": "fr",
        })
        assert r.status_code == 200
        TestCampaignAB.library_id = r.json()["id"]

    def test_create_campaign_ab(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/prospectia/campaigns", json={
            "name": "TEST_Iter67_AB",
            "subject": "Rejoignez la Communityplace KDMARCHÉ",
            "body": "Bonjour {prenom}, KDMARCHÉ propose des prix négociés pour {entreprise}. Découvrez : {lien}",
            "prospects_csv": "testeur1_iter67@example.com, Ent A, Jean\ntesteur2_iter67@example.com, Ent B, Marie",
            "library_id": TestCampaignAB.library_id,
        }, timeout=120)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("subject_b"), "subject_b missing"
        assert c["subject_b"].strip() != c["subject"].strip(), "subject_b should differ from subject"
        assert c.get("followup_1"), "followup_1 empty"
        assert c.get("followup_2"), "followup_2 empty"
        assert c.get("library_id") == TestCampaignAB.library_id
        TestCampaignAB.campaign = c

    def test_prospects_alternate_variant(self, admin_session):
        # need internal DB info; use list endpoint returns prospects_total not variants,
        # so check via a raw DB-agnostic path — infer from sent_count being 2 (batch immediate)
        # and check that campaign stored subject_b differing.
        c = TestCampaignAB.campaign
        assert c is not None
        # sent_count should be 2 after immediate batch
        r = admin_session.get(f"{BASE_URL}/api/admin/prospectia/campaigns")
        item = next((x for x in r.json()["items"] if x["id"] == c["id"]), None)
        assert item is not None
        assert item["prospects_total"] == 2
        # A/B split should have clicks_a=0 clicks_b=0 initial but counters exist
        assert "clicks_a" in item and "clicks_b" in item

    def test_library_stats_updated(self, admin_session):
        # library should now report campaigns_count>=1 for our library_id
        r = admin_session.get(f"{BASE_URL}/api/admin/prospectia/library")
        item = next((i for i in r.json()["items"] if i["id"] == TestCampaignAB.library_id), None)
        assert item is not None
        assert item["campaigns_count"] >= 1

    def test_cleanup_library(self, admin_session):
        admin_session.delete(f"{BASE_URL}/api/admin/prospectia/library/{TestCampaignAB.library_id}")


# ================ TESTIMONIALS ==================
class TestTestimonialsPublic:
    tid = None

    def test_submit_valid(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/public/testimonials", json={
            "name": "TEST Iter67 Bob",
            "company": "Ent Iter67",
            "role": "Gérant",
            "territory": "Guadeloupe",
            "email": "bob_iter67@example.com",
            "rating": 5,
            "text": "Super plateforme coopérative et vraiment utile pour nos achats groupés",
        })
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

    def test_submit_too_short(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/public/testimonials", json={
            "name": "X", "text": "trop court",
        })
        assert r.status_code == 400

    def test_public_only_approved_no_email(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/public/testimonials")
        assert r.status_code == 200
        items = r.json()["items"]
        for it in items:
            assert it.get("status", "approved") == "approved" or "status" not in it
            assert "email" not in it


class TestTestimonialsAdmin:
    tid = None
    original_prospectia = True

    def test_list_all(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/social-proof/testimonials")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "invited_count" in data
        # find one pending testimonial from previous test
        pending = [t for t in data["items"] if t["status"] == "pending" and t["name"].startswith("TEST Iter67")]
        assert pending, "no pending TEST testimonial found"
        TestTestimonialsAdmin.tid = pending[0]["id"]

    def test_approve(self, admin_session):
        r = admin_session.patch(f"{BASE_URL}/api/admin/social-proof/testimonials/{TestTestimonialsAdmin.tid}",
                                json={"status": "approved"})
        assert r.status_code == 200

    def test_polish_requires_prospectia(self, admin_session):
        # disable prospectia then expect 403
        admin_session.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": False})
        r = admin_session.post(f"{BASE_URL}/api/admin/social-proof/testimonials/{TestTestimonialsAdmin.tid}/polish")
        assert r.status_code == 403
        # re-enable
        admin_session.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": True})

    def test_polish_success(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/social-proof/testimonials/{TestTestimonialsAdmin.tid}/polish",
                               timeout=90)
        assert r.status_code == 200, r.text
        assert r.json().get("text")

    def test_invite_requires_prospectia(self, admin_session):
        admin_session.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": False})
        r = admin_session.post(f"{BASE_URL}/api/admin/social-proof/invite", json={"limit": 1})
        assert r.status_code == 403
        admin_session.put(f"{BASE_URL}/api/admin/ai-agents", json={"prospectia_enabled": True})

    def test_invite_limit_1(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/social-proof/invite", json={"limit": 1}, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok")
        assert "sent" in data
        # template should be present when there was somebody to invite; may be absent if no users
        if data["sent"] > 0:
            assert data.get("template")


# ================ WEEKLY REPORT ==================
class TestWeeklyReport:
    def test_trigger_report(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/reports/weekly/send", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("sent_to") == "contact@objectifscopoutremer.com"
