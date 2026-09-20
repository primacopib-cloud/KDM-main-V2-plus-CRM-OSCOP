"""Tests iter106: aperçu emails i18n superadmin + WhatsApp/i18n home smoke."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"},
               timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def test_i18n_email_previews_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/email-previews/i18n", timeout=15)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_i18n_email_previews_ok(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/email-previews/i18n", timeout=15)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    data = r.json()
    assert "templates" in data and "langs" in data
    assert data["langs"] == ["fr", "en", "es", "gcf", "ar"]
    assert len(data["templates"]) == 5, f"Expected 5 templates, got {len(data['templates'])}"

    ids = [t["id"] for t in data["templates"]]
    for expected in ["quote-ack", "quote-followup", "partner-ack", "partner-accepted", "partner-rejected"]:
        assert expected in ids, f"Missing template {expected}"

    # Chaque template a 5 langues avec subject + html
    for tpl in data["templates"]:
        for lg in ["fr", "en", "es", "gcf", "ar"]:
            assert lg in tpl["langs"], f"{tpl['id']} missing lang {lg}"
            entry = tpl["langs"][lg]
            assert entry.get("subject") and entry.get("html")

    # Arabic RTL check
    for tpl in data["templates"]:
        ar_html = tpl["langs"]["ar"]["html"]
        if tpl["id"] in ("quote-ack", "partner-ack", "partner-accepted", "partner-rejected"):
            assert "dir='rtl'" in ar_html or 'dir="rtl"' in ar_html, f"{tpl['id']} ar not RTL"


def test_i18n_arabic_subjects(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/email-previews/i18n", timeout=15)
    data = r.json()
    tpl_ack = next(t for t in data["templates"] if t["id"] == "quote-ack")
    subj_ar = tpl_ack["langs"]["ar"]["subject"]
    # Should contain Arabic characters
    assert any("\u0600" <= c <= "\u06FF" for c in subj_ar), f"Not Arabic: {subj_ar}"

    tpl_pa = next(t for t in data["templates"] if t["id"] == "partner-accepted")
    subj_gcf = tpl_pa["langs"]["gcf"]["subject"]
    assert subj_gcf, "GCF partner-accepted subject empty"
