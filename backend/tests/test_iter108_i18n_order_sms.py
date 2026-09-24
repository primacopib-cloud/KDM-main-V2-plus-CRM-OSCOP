"""Iter108 — i18n regressions for order SMS/emails + translation-health + investor language selector.

Covers:
1. order_email_i18n.ORDER_T has 5 languages with r_sms/r_sms_slot keys and formats without KeyError.
2. GET /api/catalog/admin/translation-health returns missing=0, missing_drafts=0, total=17, ok=true.
3. POST /api/catalog/admin/translate-all returns translated=0 and message containing 'déjà'.
4. Investor language selector: POST /api/profile/language + GET verify round-trip (fr/ar/fr).
5. investor_statement_digest module has ST_T with 5 languages and expected keys.
"""
import os
import sys
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
sys.path.insert(0, "/app/backend")


# ---------- Module-level: order_email_i18n ORDER_T ----------
class TestOrderEmailI18n:
    def test_order_t_five_languages_r_sms_no_keyerror(self):
        from order_email_i18n import ORDER_T
        expected_langs = {"fr", "en", "es", "gcf", "ar"}
        assert set(ORDER_T.keys()) == expected_langs, f"Missing langs: {expected_langs - set(ORDER_T.keys())}"
        # r_sms format
        for lang in expected_langs:
            t = ORDER_T[lang]
            assert "r_sms" in t, f"[{lang}] missing r_sms"
            assert "r_sms_slot" in t, f"[{lang}] missing r_sms_slot"
            # Format both — must not KeyError
            slot_str = t["r_sms_slot"].format(slot="10h-11h")
            sms = t["r_sms"].format(num="ORD-1", point="LP-CAP", slot=slot_str)
            assert "ORD-1" in sms
            assert "LP-CAP" in sms
            # Verify no raw French leaked in non-FR langs
            if lang == "ar":
                assert "طلب" in sms or "#ORD-1" in sms
            if lang == "en":
                assert "ready" in sms.lower()
            if lang == "es":
                assert "listo" in sms.lower() or "recoger" in sms.lower()

    def test_order_lang_fallback(self):
        from order_email_i18n import order_lang
        assert order_lang({"preferred_language": "ar"}) == "ar"
        assert order_lang({"preferred_language": "zz"}) == "fr"
        assert order_lang({}) == "fr"
        assert order_lang(None) == "fr"


# ---------- Module-level: investor_statement_digest ----------
class TestInvestorStatementDigest:
    def test_module_has_st_t_five_langs(self):
        import investor_statement_digest as isd
        assert hasattr(isd, "ST_T"), "investor_statement_digest.ST_T missing"
        assert hasattr(isd, "send_investor_statements"), "send_investor_statements missing"
        assert set(isd.ST_T.keys()) >= {"fr", "en", "es", "gcf", "ar"}, f"Only got: {set(isd.ST_T.keys())}"


# ---------- API: translation health & translate-all ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"},
                      timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("access_token") or r.json().get("token")


class TestTranslationHealth:
    def test_health_ok_full(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/catalog/admin/translation-health",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "missing" in data and "total" in data and "ok" in data
        assert data["missing"] == 0, f"missing={data['missing']}"
        assert data.get("missing_drafts", 0) == 0, f"missing_drafts={data.get('missing_drafts')}"
        assert data["total"] == 17, f"total={data['total']} (expected 17)"
        assert data["ok"] is True

    def test_translate_all_noop(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/catalog/admin/translate-all",
                          headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("translated", -1) == 0
        assert data.get("remaining", -1) == 0
        assert data.get("remaining_drafts", 0) == 0
        msg = (data.get("message") or "").lower()
        assert "déjà" in msg or "deja" in msg or "already" in msg, f"unexpected message: {data.get('message')}"


# ---------- Investor profile language round-trip ----------
@pytest.fixture(scope="module")
def investor_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "invest.test.i@test.fr", "password": "InvestTest2026!"},
                      timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Investor login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("access_token") or r.json().get("token")


class TestInvestorLanguage:
    def test_set_and_get_language(self, investor_token):
        h = {"Authorization": f"Bearer {investor_token}"}
        # set to ar
        r = requests.post(f"{BASE_URL}/api/profile/language", json={"language": "ar"}, headers=h, timeout=15)
        assert r.status_code in (200, 204), r.text
        # get
        g = requests.get(f"{BASE_URL}/api/profile/language", headers=h, timeout=15)
        assert g.status_code == 200, g.text
        assert g.json().get("language") == "ar"
        # restore fr
        r2 = requests.post(f"{BASE_URL}/api/profile/language", json={"language": "fr"}, headers=h, timeout=15)
        assert r2.status_code in (200, 204)
        g2 = requests.get(f"{BASE_URL}/api/profile/language", headers=h, timeout=15)
        assert g2.json().get("language") == "fr"
