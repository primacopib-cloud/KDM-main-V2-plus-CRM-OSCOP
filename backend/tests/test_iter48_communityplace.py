"""Iter 48 — Communityplace: TVA, profils, comptabilité, target_profiles, PDF conventions, weekly report."""
import os
import io
import asyncio
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"

TEST_EMAILS = [
    "test-iter48-gp@example.com",
    "test-iter48-fr@example.com",
    "test-iter48-us@example.com",
]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"
    })
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ============ TVA computation (pure) ============
def test_compute_vat_module():
    import sys
    sys.path.insert(0, "/app/backend")
    from vat import compute_vat, vat_rate
    assert vat_rate("GP") == 8.5
    assert vat_rate("MQ") == 8.5
    assert vat_rate("GF") == 0.0
    assert vat_rate("FR") == 20.0
    assert vat_rate("DE") == 0.0
    assert vat_rate("US") == 0.0
    v = compute_vat(10000, "GP")
    assert v["rate"] == 8.5 and v["vat_cents"] == 850 and v["ttc_cents"] == 10850
    v = compute_vat(10000, "FR")
    assert v["ttc_cents"] == 12000


# ============ Public profiles ============
def test_public_member_profiles():
    r = requests.get(f"{API}/public/member-profiles")
    assert r.status_code == 200
    data = r.json()
    profiles = data["profiles"]
    slugs = {p["slug"] for p in profiles}
    assert "vendor" in slugs and "buyer" in slugs
    for p in profiles:
        if p["slug"] in ("vendor", "buyer"):
            assert "fr" in p["titles"] and "en" in p["titles"] and "es" in p["titles"]
            assert p.get("space_route")
            assert p.get("convention_template")


# ============ CRUD admin member profiles ============
def test_admin_member_profiles_crud(admin_session):
    # LIST
    r = admin_session.get(f"{API}/admin/member-profiles")
    assert r.status_code == 200
    initial = r.json()
    assert len(initial["profiles"]) >= 2

    # CREATE
    body = {
        "titles": {"fr": "Partenaire Test Iter48", "en": "Test Partner", "es": "Socio Test"},
        "descriptions": {"fr": "profil test"},
        "space_route": "/espace-acheteur",
        "convention_template": "v2_0_buyer",
        "creates_vendor_record": False,
        "active": True,
        "sort_order": 99,
    }
    r = admin_session.post(f"{API}/admin/member-profiles", json=body)
    assert r.status_code == 200, r.text
    created = r.json()
    slug = created["slug"]
    assert created["titles"]["fr"] == "Partenaire Test Iter48"
    assert created.get("system") is False

    # UPDATE
    r = admin_session.put(f"{API}/admin/member-profiles/{slug}", json={
        "titles": {"fr": "Partenaire Test Iter48 (modifié)", "en": "Test Partner", "es": "Socio Test"},
        "active": False,
    })
    assert r.status_code == 200
    assert r.json()["active"] is False

    # DELETE (non-system, no adhesions)
    r = admin_session.delete(f"{API}/admin/member-profiles/{slug}")
    assert r.status_code == 200
    assert r.json().get("deleted") is True

    # DELETE system → 400
    r = admin_session.delete(f"{API}/admin/member-profiles/vendor")
    assert r.status_code == 400


# ============ /vendor-onboarding/start with TVA ============
@pytest.mark.parametrize("country,expected_rate", [("GP", 8.5), ("FR", 20.0), ("US", 0.0)])
def test_vendor_onboarding_start_vat(country, expected_rate):
    # Use known plan slug — verify price via Mongo
    slug = "ess-acces-pro"
    from motor.motor_asyncio import AsyncIOMotorClient as _C
    async def _price():
        c = _C(os.environ.get("MONGO_URL"))
        d = c[os.environ.get("DB_NAME", "b2b_ess_db")]
        p = await d.subscription_plans.find_one({"slug": slug, "active": True})
        return p["price_cents"] if p else None
    price_ht = asyncio.get_event_loop().run_until_complete(_price())
    if not price_ht:
        pytest.skip(f"Plan {slug} not seeded")

    email = f"test-iter48-{country.lower()}@example.com"
    body = {
        "company": f"TEST Iter48 {country}", "contact_name": "QA Bot",
        "email": email, "phone": "+590590000000", "siret": "12345678900010",
        "plan_slug": slug, "origin_url": BASE_URL,
        "member_type": "vendor", "locale": "fr", "country": country,
    }
    r = requests.post(f"{API}/vendor-onboarding/start", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "checkout_url" in data and "checkout.stripe.com" in data["checkout_url"]
    oid = data["onboarding_id"]

    # Inspect DB directly via async
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "b2b_ess_db")

    async def _check():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        doc = await db.vendor_onboarding.find_one({"id": oid})
        return doc

    doc = asyncio.get_event_loop().run_until_complete(_check())
    assert doc is not None
    assert doc["country"] == country
    assert doc["vat_rate"] == expected_rate
    assert doc["amount_ht_cents"] == price_ht
    expected_vat = round(price_ht * expected_rate / 100)
    assert doc["vat_cents"] == expected_vat
    assert doc["amount_cents"] == price_ht + expected_vat


# ============ Funnel ============
def test_admin_funnel(admin_session):
    for days in (30, 0):
        r = admin_session.get(f"{API}/vendor-onboarding/admin/funnel", params={"days": days})
        assert r.status_code == 200
        d = r.json()
        assert d["started"] >= d["paid"] >= d["signed"] >= d["activated"]


# ============ Adhesions CSV export ============
def test_admin_export_csv(admin_session):
    r = admin_session.get(f"{API}/vendor-onboarding/admin/export.csv")
    assert r.status_code == 200
    txt = r.content.decode("utf-8-sig")
    first_line = txt.splitlines()[0]
    assert "entreprise" in first_line and "taux TVA" in first_line and "relances" in first_line


# ============ Accounting journal + export ============
def test_accounting_journal(admin_session):
    r = admin_session.get(f"{API}/admin/accounting/journal", params={"date_from": "2025-01-01"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "entries" in d and "totals" in d and "by_type" in d and "by_month" in d
    totals = d["totals"]
    # Sanity: ht + vat == ttc (roughly, per entry)
    for e in d["entries"][:5]:
        assert e["ht_cents"] + e["vat_cents"] == e["ttc_cents"]


def test_accounting_export_csv(admin_session):
    r = admin_session.get(f"{API}/admin/accounting/export.csv")
    assert r.status_code == 200
    txt = r.content.decode("utf-8-sig")
    assert "HT (EUR)" in txt.splitlines()[0]


# ============ Admin plans target_profiles ============
def test_admin_plans_target_profiles(admin_session):
    r = admin_session.get(f"{API}/admin/plans/subscriptions", params={"include_inactive": True})
    assert r.status_code == 200, r.text
    plans = r.json()
    assert len(plans) > 0
    for p in plans:
        assert p.get("target_profiles"), f"plan {p['slug']} missing target_profiles"

    # PUT a plan target_profiles=['vendor'] then revert (uses PATCH per code)
    target_plan = plans[0]
    pid = target_plan["id"]
    original = target_plan.get("target_profiles") or ["all"]

    r = admin_session.patch(f"{API}/admin/plans/subscriptions/{pid}", json={"target_profiles": ["vendor"]})
    assert r.status_code == 200, r.text
    assert r.json()["target_profiles"] == ["vendor"]

    r = admin_session.patch(f"{API}/admin/plans/subscriptions/{pid}", json={"target_profiles": original})
    assert r.status_code == 200
    assert r.json()["target_profiles"] == original


# ============ PDF page counts ============
def test_build_convention_pdf_pages():
    import sys
    sys.path.insert(0, "/app/backend")
    from vendor_convention import build_convention_pdf
    from pypdf import PdfReader

    ob_vendor = {
        "id": "test-vend-0001-page-count", "company": "TEST V", "email": "test-iter48@example.com",
        "phone": "+590590000000", "siret": "12345678900010", "plan_slug": "ess-acces-pro",
        "plan_name": "TEST", "member_type": "vendor", "locale": "fr", "country": "GP",
        "convention_template": "v1_5_vendor",
        "convention": {"forme_sociale": "SAS", "capital": "10000", "rcs_ville": "Basse-Terre",
                       "adresse": "1 rue test", "rep_nom": "Doe", "rep_prenom": "Jane",
                       "rep_qualite": "Présidente", "territoires": ["Guadeloupe"],
                       "lieu_signature": "Pointe-à-Pitre"},
    }
    ob_buyer = {**ob_vendor, "member_type": "buyer", "convention_template": "v2_0_buyer"}

    pdf_v = build_convention_pdf(ob_vendor)
    pdf_b = build_convention_pdf(ob_buyer)
    n_v = len(PdfReader(io.BytesIO(pdf_v)).pages)
    n_b = len(PdfReader(io.BytesIO(pdf_b)).pages)
    # Vendor: fiche + V1.5 ~33p → ~34p; buyer: fiche + V2.0 29p + attestation 3p → ~33p
    assert n_v >= 30, f"Vendor PDF pages={n_v} (expected ~34)"
    assert n_b >= 30, f"Buyer PDF pages={n_b} (expected ~33)"


# ============ Weekly report guard ============
def test_weekly_report_weekday_guard():
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    from vendor_weekly_report import send_weekly_unpaid_report
    from datetime import datetime, timezone
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "b2b_ess_db")

    async def _run():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        # Just call — if not Monday, function returns None without side-effects.
        before = await db.system_flags.count_documents({"key": "weekly_unpaid_report"})
        result = await send_weekly_unpaid_report(db)
        after = await db.system_flags.count_documents({"key": "weekly_unpaid_report"})
        is_monday = datetime.now(timezone.utc).weekday() == 0
        return before, after, is_monday, result

    before, after, is_monday, result = asyncio.get_event_loop().run_until_complete(_run())
    if not is_monday:
        # Guard must prevent writes
        assert after == before, "weekday guard failed: system_flags mutated on non-Monday"


# ============ Cleanup ============
def test_cleanup_test_adhesions():
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "b2b_ess_db")

    async def _cleanup():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        r = await db.vendor_onboarding.delete_many({"email": {"$in": TEST_EMAILS}})
        return r.deleted_count

    n = asyncio.get_event_loop().run_until_complete(_cleanup())
    print(f"Cleaned up {n} test onboarding docs")
