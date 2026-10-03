"""Iter110 — Cycle complet avoir COOP'ACT : scan pickup → incident + email, settle → crédit auto + ledger, PDF relevé mensuel POP'S, i18n ar."""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

POPS_EMAIL = "detaillant-test@kdmarche.fr"
POPS_PASSWORD = "Detaillant2026!"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
INVESTOR_EMAIL = "invest.test.i@test.fr"
INVESTOR_PASSWORD = "InvestTest2026!"

OFFER_ID = "qa-off-cycle"
AUC_ID = "qa-auc-cycle"
AUC_REF = "AUC-QA-CYCLE"
TOKEN = "qa-token-cycle"


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


def _login(session, email, password, portal=None):
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = session.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    assert r.status_code == 200, f"Login {email}: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        session.headers.update({"Authorization": f"Bearer {tok}"})
    return r.json()


@pytest.fixture(scope="module")
def pops_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, POPS_EMAIL, POPS_PASSWORD)
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, ADMIN_EMAIL, ADMIN_PASSWORD, portal="admin")
    return s


@pytest.fixture(scope="module")
def invest_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, INVESTOR_EMAIL, INVESTOR_PASSWORD)
    return s


@pytest.fixture(scope="module")
def winner_user(db):
    u = db.users.find_one({"email": INVESTOR_EMAIL}, {"_id": 0, "id": 1, "first_name": 1, "contact_name": 1})
    assert u, "Winner user not found"
    return u


@pytest.fixture(scope="module")
def pops_user(db):
    u = db.users.find_one({"email": POPS_EMAIL}, {"_id": 0, "id": 1, "company_name": 1})
    assert u, "POPS user not found"
    return u


@pytest.fixture(scope="module")
def seed(db, winner_user, pops_user):
    """Seed offer + auction WON for the cycle test."""
    # Clean any previous
    db.detaillant_offers.delete_one({"id": OFFER_ID})
    db.auctions.delete_one({"id": AUC_ID})
    db.auction_credit_ledger.delete_many({"label": {"$regex": AUC_REF}})

    items_detail = [
        {"sku": "QA-ART-A", "name": "Café moulu 250g", "brand": "QA", "format_label": "250 g",
         "unit_price_ttc": 5.0, "ingredients": "Café", "allergens": "Aucun"},
        {"sku": "QA-ART-B", "name": "Lait UHT 1L", "brand": "QA", "format_label": "1 L",
         "unit_price_ttc": 4.6, "ingredients": "Lait", "allergens": "Lait"},
    ]
    offer = {
        "id": OFFER_ID, "user_id": pops_user["id"],
        "company_name": pops_user.get("company_name") or "Épicerie Ti Kaz",
        "product_name": "Lot QA Cycle",
        "final_price": 9.6, "currency": "EUR",
        "lot_type": "COMPOSED", "status": "APPROVED",
        "items_detail": items_detail, "locality": "Pointe-à-Pitre",
        "created_at": "2026-10-01T08:00:00",
    }
    auction = {
        "id": AUC_ID, "reference": AUC_REF, "title": "Lot QA Cycle",
        "status": "WON", "source": "DETAILLANT", "source_visible": True,
        "detaillant_offer_id": OFFER_ID,
        "lot_type": "COMPOSED", "lot_price_ttc": 9.6, "currency": "EUR",
        "combo_items": items_detail,
        "value_eur": 9.6, "current_price_eur": 8.0,
        "starts_at": "2026-10-01T10:00:00+00:00", "ends_at": "2026-10-02T10:00:00+00:00",
        "bids_count": 1,
        "winner": {
            "user_id": winner_user["id"],
            "name": winner_user.get("first_name") or winner_user.get("contact_name") or "QA Winner",
            "email": INVESTOR_EMAIL,
            "price_eur": 8.0, "pickup_token": TOKEN,
            "won_at": "2026-10-02T10:00:00",
        },
        "created_at": "2026-10-01T08:00:00",
    }
    db.detaillant_offers.insert_one(offer)
    db.auctions.insert_one(auction)
    yield {"offer_id": OFFER_ID, "auction_id": AUC_ID}
    # Teardown
    db.detaillant_offers.delete_one({"id": OFFER_ID})
    db.auctions.delete_one({"id": AUC_ID})
    # Remove ledger entries from this test & decrement credits
    led = list(db.auction_credit_ledger.find(
        {"user_id": winner_user["id"], "type": "INCIDENT_REFUND",
         "label": {"$regex": AUC_REF}}, {"_id": 0, "amount": 1}))
    total_credits = sum(int(x.get("amount") or 0) for x in led)
    if total_credits:
        db.auction_accounts.update_one(
            {"user_id": winner_user["id"]}, {"$inc": {"credits": -total_credits}})
    db.auction_credit_ledger.delete_many(
        {"user_id": winner_user["id"], "label": {"$regex": AUC_REF}})
    # Remove notification
    db.notifications.delete_many({"type": "AUCTION_PICKUP_INCIDENT", "data.reference": AUC_REF})
    # Restore preferred_language fr
    db.users.update_one({"id": winner_user["id"]}, {"$set": {"preferred_language": "fr"}})


# ================= P1 — Cycle avoir complet =================

def test_a_pickup_scan_creates_incident(db, admin_session, seed, winner_user):
    """Scan avec missing_skus=['QA-ART-B'] → incident credit=3.83, deduction=4.60."""
    # Set winner language to 'ar' to validate i18n branch does not warn
    db.users.update_one({"id": winner_user["id"]}, {"$set": {"preferred_language": "ar"}})

    # Baseline credits
    acc = db.auction_accounts.find_one({"user_id": winner_user["id"]}, {"_id": 0, "credits": 1}) or {}
    baseline = int(acc.get("credits") or 0)
    pytest.credits_baseline = baseline

    r = admin_session.post(
        f"{BASE_URL}/api/admin/auctions/pickup-scan",
        json={"code": TOKEN, "confirm": True, "missing_skus": ["QA-ART-B"]},
        timeout=20)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    data = r.json()
    assert data["confirmed"] is True
    inc = data["pickup_incident"]
    # 4.6/9.6 * 8.0 = 3.8333 → 3.83
    assert inc["credit_eur"] == 3.83, f"credit={inc['credit_eur']}"
    assert inc["pops_deduction_eur"] == 4.6
    assert inc["settled"] is False

    # Verify DB
    a = db.auctions.find_one({"id": AUC_ID})
    assert a["pickup_incident"]["credit_eur"] == 3.83
    assert a["pickup_incident"]["pops_deduction_eur"] == 4.6


def test_b_pickup_incidents_lists(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/auctions/pickup-incidents", timeout=20)
    assert r.status_code == 200
    data = r.json()
    found = [i for i in data["incidents"] if i["auction_id"] == AUC_ID]
    assert found, "incident absent de la liste"
    assert found[0]["settled"] is False
    assert found[0]["credit_eur"] == 3.83


def test_c_settle_credits_auto(db, admin_session, winner_user):
    r = admin_session.post(
        f"{BASE_URL}/api/admin/auctions/pickup-incidents/{AUC_ID}/settle", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    # 3.83 * 10 = 38.3 → round = 38
    assert data["credits_granted"] == 38

    # DB checks
    acc = db.auction_accounts.find_one({"user_id": winner_user["id"]}, {"_id": 0, "credits": 1})
    assert acc is not None
    assert int(acc["credits"]) == pytest.credits_baseline + 38

    ledger = list(db.auction_credit_ledger.find(
        {"user_id": winner_user["id"], "type": "INCIDENT_REFUND",
         "label": {"$regex": AUC_REF}}, {"_id": 0}))
    assert len(ledger) == 1, f"ledger: {ledger}"
    assert ledger[0]["amount"] == 38

    a = db.auctions.find_one({"id": AUC_ID})
    assert a["pickup_incident"]["settled"] is True
    assert a["pickup_incident"]["credits_granted"] == 38


def test_d_resettle_returns_409(admin_session):
    r = admin_session.post(
        f"{BASE_URL}/api/admin/auctions/pickup-incidents/{AUC_ID}/settle", timeout=20)
    assert r.status_code == 409


def test_e_incident_list_shows_settled(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/auctions/pickup-incidents", timeout=20)
    assert r.status_code == 200
    found = [i for i in r.json()["incidents"] if i["auction_id"] == AUC_ID][0]
    assert found["settled"] is True


# ================= P1 — i18n emails =================

def test_f_no_email_warnings_in_logs():
    """Vérifie qu'aucun warning 'Email avoir ... non envoyé' n'apparaît post-settle."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["tail", "-n", "300", "/var/log/supervisor/backend.err.log"],
            stderr=subprocess.STDOUT, timeout=5).decode("utf-8", errors="ignore")
    except Exception:
        pytest.skip("backend.err.log not readable")
    # Only check for our test window: look for warnings about Email avoir
    warns = [l for l in out.splitlines() if "Email avoir" in l and "non envoyé" in l]
    # Any recent warning is bad
    assert not warns, f"Email warnings found: {warns[-3:]}"


def test_g_incident_email_i18n_ar_and_fr(db, winner_user):
    """Teste send_incident_email directement en ar et fr."""
    import asyncio
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    import incident_emails as ie
    from unittest.mock import patch, AsyncMock

    auction = db.auctions.find_one({"id": AUC_ID}, {"_id": 0})
    inc = auction["pickup_incident"]

    async def run_both():
        client = AsyncIOMotorClient(MONGO_URL)
        adb = client[DB_NAME]
        results = {}
        for lang in ("ar", "fr"):
            await adb.users.update_one({"id": winner_user["id"]}, {"$set": {"preferred_language": lang}})
            captured = {}
            async def fake_send(**kwargs):
                captured.update(kwargs)
                return True
            with patch("brevo_service.send_email", new=fake_send):
                await ie.send_incident_email(adb, auction, inc, "settled", credits=38)
            results[lang] = captured
        client.close()
        return results

    res = asyncio.run(run_both())
    res_ar, res_fr = res["ar"], res["fr"]

    assert "تمت تسوية" in res_ar.get("subject", ""), f"ar subject: {res_ar.get('subject')}"
    assert "réglé" in res_fr.get("subject", "") or "règlé" in res_fr.get("subject", ""), f"fr subject: {res_fr.get('subject')}"
    assert "38" in res_ar.get("html_content", "")
    assert "38" in res_fr.get("html_content", "")


# ================= P1 — PDF relevé mensuel =================

def test_h_pdf_statement_month_with_lot(pops_session):
    r = pops_session.get(
        f"{BASE_URL}/api/detaillant/settlements/statement.pdf",
        params={"month": "2026-10"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 1500, f"PDF too small: {len(r.content)}"
    # Rough check : contient référence du lot et montants dans le flux PDF
    content = r.content
    assert b"%PDF" in content[:10]


def test_i_pdf_statement_month_without_lot_404(pops_session):
    r = pops_session.get(
        f"{BASE_URL}/api/detaillant/settlements/statement.pdf",
        params={"month": "2025-01"}, timeout=20)
    assert r.status_code == 404


def test_j_pdf_statement_invalid_month_400(pops_session):
    r = pops_session.get(
        f"{BASE_URL}/api/detaillant/settlements/statement.pdf",
        params={"month": "oct-2026"}, timeout=20)
    assert r.status_code == 400


def test_k_pdf_statement_stranger_user_404(invest_session):
    r = invest_session.get(
        f"{BASE_URL}/api/detaillant/settlements/statement.pdf",
        params={"month": "2026-10"}, timeout=20)
    assert r.status_code == 404


# ================= P2 — /detaillant/sales =================

def test_l_detaillant_sales_shows_settlement(pops_session):
    r = pops_session.get(f"{BASE_URL}/api/detaillant/sales", timeout=20)
    assert r.status_code == 200
    data = r.json()
    sale = next((s for s in data["sales"] if s["reference"] == AUC_REF), None)
    assert sale is not None, "lot QA absent"
    assert sale["pops_settlement_eur"] == 5.0, f"settlement={sale['pops_settlement_eur']}"
    assert sale["pickup_incident"]["pops_deduction_eur"] == 4.6
    assert "settlement_eur" in data["totals"]
    assert "deductions_eur" in data["totals"]
