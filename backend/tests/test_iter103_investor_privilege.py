"""Tests for Investor Privilège (FCRL) packs - iteration 103"""
import os
import requests
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oscop-platform-3.preview.emergentagent.com').rstrip('/')
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = os.environ.get('DB_NAME', 'test_database')

INVEST_EMAIL = "invest.test.i@test.fr"
INVEST_PWD = "InvestTest2026!"
ALT_EMAIL = "marie@example.com"
ALT_PWD = "Demo2026!"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"


def _login(email, pwd, portal=None):
    body = {"email": email, "password": pwd}
    if portal:
        body["portal"] = portal
    r = requests.post(f"{BASE_URL}/api/auth/login", json=body, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="module")
def db_name():
    # read from backend .env
    try:
        with open('/app/backend/.env') as f:
            for line in f:
                if line.startswith('DB_NAME='):
                    return line.strip().split('=', 1)[1].strip('"').strip("'")
    except Exception:
        pass
    return DB_NAME


@pytest.fixture(scope="module")
def clean_db(db_name):
    """Cleanup investor_privilege_subs before and after"""
    async def _cleanup():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[db_name]
        # cleanup test users' subs
        u1 = await db.users.find_one({"email": INVEST_EMAIL})
        u2 = await db.users.find_one({"email": ALT_EMAIL})
        ids = [u["id"] for u in [u1, u2] if u]
        if ids:
            await db.investor_privilege_subs.delete_many({"user_id": {"$in": ids}})
        client.close()
    asyncio.run(_cleanup())
    yield
    asyncio.run(_cleanup())
    # remove is_investor on marie
    async def _reset_marie():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[db_name]
        await db.users.update_one({"email": ALT_EMAIL}, {"$set": {"is_investor": False}})
        # ensure invest stays true
        await db.users.update_one({"email": INVEST_EMAIL}, {"$set": {"is_investor": True}})
        client.close()
    asyncio.run(_reset_marie())


@pytest.fixture(scope="module")
def invest_token(clean_db):
    return _login(INVEST_EMAIL, INVEST_PWD)


@pytest.fixture(scope="module")
def alt_token(clean_db):
    return _login(ALT_EMAIL, ALT_PWD)


@pytest.fixture(scope="module")
def admin_token(clean_db):
    return _login(ADMIN_EMAIL, ADMIN_PWD, portal="admin")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ==== Public packs ====
def test_public_packs_structure():
    r = requests.get(f"{BASE_URL}/api/investor/privilege/packs", timeout=10)
    assert r.status_code == 200
    data = r.json()
    packs = {p["id"]: p for p in data["packs"]}
    assert set(packs.keys()) == {"BRONZE", "ARGENT", "OR"}
    assert packs["BRONZE"]["amount_eur"] == 50000
    assert packs["BRONZE"]["credits_eur"] == 57500
    assert packs["ARGENT"]["amount_eur"] == 150000
    assert packs["ARGENT"]["credits_eur"] == 180000
    assert packs["OR"]["amount_eur"] == 500000
    assert packs["OR"]["credits_eur"] == 650000
    assert len(data["convention"]["articles"]) == 7


# ==== TRANSFER subscription ====
def test_subscribe_transfer_missing_accept(invest_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(invest_token),
                      json={"pack_id": "BRONZE", "payment_method": "TRANSFER",
                            "signer_name": "Jean Test", "company_name": "TestCo", "accept": False})
    assert r.status_code == 400


def test_subscribe_transfer_empty_signer(invest_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(invest_token),
                      json={"pack_id": "BRONZE", "payment_method": "TRANSFER",
                            "signer_name": "", "company_name": "TestCo", "accept": True})
    assert r.status_code == 400


def test_subscribe_transfer_invalid_pack(invest_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(invest_token),
                      json={"pack_id": "XYZ", "payment_method": "TRANSFER",
                            "signer_name": "Jean Test", "company_name": "TestCo", "accept": True})
    assert r.status_code == 400


def test_subscribe_transfer_success(invest_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(invest_token),
                      json={"pack_id": "BRONZE", "payment_method": "TRANSFER",
                            "signer_name": "Jean Investisseur",
                            "company_name": "TestInvest SAS",
                            "siret": "12345678900012",
                            "accept": True})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "PENDING_TRANSFER"
    assert d["reference"].startswith("FCRL-")
    assert "instructions" in d
    pytest.transfer_ref = d["reference"]


def test_subscribe_duplicate_409(invest_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(invest_token),
                      json={"pack_id": "ARGENT", "payment_method": "TRANSFER",
                            "signer_name": "Jean", "company_name": "Co", "accept": True})
    assert r.status_code == 409


def test_me_pending_zero_credits(invest_token):
    r = requests.get(f"{BASE_URL}/api/investor/privilege/me", headers=_auth(invest_token))
    assert r.status_code == 200
    d = r.json()
    assert d["credits_eur"] == 0
    assert len(d["subscriptions"]) >= 1
    assert "privileges" in d["subscriptions"][0]
    assert isinstance(d["subscriptions"][0]["privileges"], list)


def test_convention_pdf_user(invest_token):
    r = requests.get(f"{BASE_URL}/api/investor/privilege/convention/pdf",
                     headers=_auth(invest_token))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


# ==== Admin registry & activation ====
def test_admin_registry(admin_token):
    r = requests.get(f"{BASE_URL}/api/investor/privilege/admin/registry",
                     headers=_auth(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "stats" in d and "subscriptions" in d
    for k in ["total", "active", "pending_transfer", "collected_eur", "credits_issued_eur"]:
        assert k in d["stats"]
    assert d["stats"]["pending_transfer"] >= 1


def test_admin_registry_filter_status(admin_token):
    r = requests.get(f"{BASE_URL}/api/investor/privilege/admin/registry?status=PENDING_TRANSFER",
                     headers=_auth(admin_token))
    assert r.status_code == 200
    subs = r.json()["subscriptions"]
    assert all(s["status"] == "PENDING_TRANSFER" for s in subs)


def test_admin_registry_search(admin_token):
    r = requests.get(f"{BASE_URL}/api/investor/privilege/admin/registry?q=TestInvest",
                     headers=_auth(admin_token))
    assert r.status_code == 200
    subs = r.json()["subscriptions"]
    assert len(subs) >= 1


def test_admin_activate_transfer(admin_token, invest_token):
    # get sub id
    r = requests.get(f"{BASE_URL}/api/investor/privilege/admin/registry?q=TestInvest",
                     headers=_auth(admin_token))
    sub = r.json()["subscriptions"][0]
    sub_id = sub["id"]
    pytest.sub_id = sub_id
    r2 = requests.post(f"{BASE_URL}/api/investor/privilege/admin/{sub_id}/activate",
                       headers=_auth(admin_token))
    assert r2.status_code == 200, r2.text
    # verify /me now has credits
    r3 = requests.get(f"{BASE_URL}/api/investor/privilege/me", headers=_auth(invest_token))
    assert r3.status_code == 200
    assert r3.json()["credits_eur"] == 57500
    # reactivation idempotent
    r4 = requests.post(f"{BASE_URL}/api/investor/privilege/admin/{sub_id}/activate",
                       headers=_auth(admin_token))
    assert r4.status_code == 200
    assert r4.json().get("already") is True


def test_admin_convention_pdf(admin_token):
    sub_id = pytest.sub_id
    r = requests.get(f"{BASE_URL}/api/investor/privilege/admin/{sub_id}/convention/pdf",
                     headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ==== Stripe checkout via alt user ====
def test_subscribe_stripe_checkout_url(alt_token):
    r = requests.post(f"{BASE_URL}/api/investor/privilege/subscribe",
                      headers=_auth(alt_token),
                      json={"pack_id": "BRONZE", "payment_method": "STRIPE",
                            "signer_name": "Marie Test", "company_name": "MarieTest SARL",
                            "accept": True,
                            "origin_url": "https://example.com"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "PENDING"
    assert d["checkout_url"].startswith("https://checkout.stripe.com") or "stripe.com" in d["checkout_url"]
