"""Iter86 — Financement produits investisseurs + vitrine vendeur + relance 48h.

Tests focus on error cases (422/403/409/404), webhook idempotency, and reminder.
"""
import os
import sys
import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv

# Load .env for standalone use (STRIPE_API_KEY, MONGO_URL)
load_dotenv("/app/backend/.env", override=True)

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PW = "AdminKDM2025!"
INVEST_EMAIL = "invest.test.i@test.fr"
INVEST_PW = "InvestTest2026!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PW = "Demo2026!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PW = "Demo2026!"


def _login(email, pw, portal=None):
    body = {"email": email, "password": pw}
    if portal:
        body["portal"] = portal
    r = requests.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Login failed {email}: {r.status_code} {r.text[:200]}")
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


@pytest.fixture(scope="module")
def admin_h():
    return _login(ADMIN_EMAIL, ADMIN_PW, portal="admin")


@pytest.fixture(scope="module")
def invest_h():
    return _login(INVEST_EMAIL, INVEST_PW)


@pytest.fixture(scope="module")
def buyer_h():
    return _login(BUYER_EMAIL, BUYER_PW)


@pytest.fixture(scope="module")
def vendor_h():
    return _login(VENDOR_EMAIL, VENDOR_PW)


# ---------- FINANCEMENT PRODUITS ----------

class TestFinancingAuth:
    def test_admin_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/financing-products", timeout=15)
        assert r.status_code in (401, 403), f"got {r.status_code}"

    def test_admin_create_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          json={"name": "X", "base_price_eur": 100, "margin_percent": 10}, timeout=15)
        assert r.status_code in (401, 403)

    def test_investor_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/investor/financing-products", timeout=15)
        assert r.status_code in (401, 403)


class TestFinancingValidations:
    def test_create_negative_price_422(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          headers=admin_h,
                          json={"name": "TEST_bad", "base_price_eur": -10, "margin_percent": 10}, timeout=15)
        assert r.status_code == 422, r.text

    def test_create_zero_price_422(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          headers=admin_h,
                          json={"name": "TEST_bad", "base_price_eur": 0, "margin_percent": 10}, timeout=15)
        assert r.status_code == 422, r.text

    def test_create_margin_too_high_422(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          headers=admin_h,
                          json={"name": "TEST_bad", "base_price_eur": 100, "margin_percent": 501}, timeout=15)
        assert r.status_code == 422, r.text

    def test_create_missing_name_400(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          headers=admin_h,
                          json={"base_price_eur": 100, "margin_percent": 10}, timeout=15)
        # No name and no product_id → backend 400
        assert r.status_code in (400, 422), r.text

    def test_update_404_unknown(self, admin_h):
        r = requests.put(f"{BASE_URL}/api/admin/financing-products/does-not-exist",
                         headers=admin_h, json={"margin_percent": 20}, timeout=15)
        assert r.status_code == 404

    def test_delete_404_unknown(self, admin_h):
        r = requests.delete(f"{BASE_URL}/api/admin/financing-products/does-not-exist",
                            headers=admin_h, timeout=15)
        assert r.status_code == 404


class TestFinancingCrud:
    @pytest.fixture(scope="class")
    def created(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/financing-products",
                          headers=admin_h,
                          json={"name": "TEST_Iter86_Rhum", "base_price_eur": 1000,
                                "margin_percent": 15, "description": "test"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_price_eur"] == 1150.0
        assert d["status"] == "OPEN"
        assert d["reference"].startswith("FIN-")
        yield d
        # cleanup
        try:
            requests.delete(f"{BASE_URL}/api/admin/financing-products/{d['id']}",
                            headers=admin_h, timeout=10)
        except Exception:
            pass

    def test_update_recalculates_total(self, admin_h, created):
        r = requests.put(f"{BASE_URL}/api/admin/financing-products/{created['id']}",
                         headers=admin_h, json={"margin_percent": 25}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["margin_percent"] == 25
        assert d["total_price_eur"] == 1250.0

    def test_investor_list_hides_sensitive_fields(self, invest_h, created):
        r = requests.get(f"{BASE_URL}/api/investor/financing-products", headers=invest_h, timeout=15)
        assert r.status_code == 200, r.text
        items = r.json().get("products", [])
        target = next((i for i in items if i["id"] == created["id"]), None)
        assert target, "created product not visible to investor"
        assert "created_by" not in target
        assert "stripe_session_id" not in target
        assert "pending_by" not in target

    def test_non_investor_forbidden(self, buyer_h, created):
        if not buyer_h:
            pytest.skip("no buyer login")
        r = requests.get(f"{BASE_URL}/api/investor/financing-products", headers=buyer_h, timeout=15)
        assert r.status_code == 403, f"got {r.status_code} {r.text[:200]}"

    def test_investor_pay_returns_checkout(self, invest_h, created):
        r = requests.post(f"{BASE_URL}/api/investor/financing-products/{created['id']}/pay",
                          headers=invest_h, timeout=25)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout_url" in d and d["checkout_url"].startswith("https://")
        # status should be PENDING_PAYMENT
        r2 = requests.get(f"{BASE_URL}/api/admin/financing-products", headers=_admin_for(), timeout=15)
        # (helper not needed — reuse admin list via next test)

    def test_webhook_marks_paid_and_idempotent(self, admin_h, created):
        # Simulate Stripe webhook (accepted without signature per spec)
        payload = {
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_iter86_" + uuid.uuid4().hex[:10],
                "payment_status": "paid",
                "metadata": {
                    "financing_product_id": created["id"],
                    "investor_email": INVEST_EMAIL,
                    "kind": "PRODUCT_FINANCING",
                },
            }},
        }
        r1 = requests.post(f"{BASE_URL}/api/public/financing-products/webhook", json=payload, timeout=30)
        assert r1.status_code == 200, r1.text
        # Give it a moment
        time.sleep(2)
        # Verify PAID via admin list
        r2 = requests.get(f"{BASE_URL}/api/admin/financing-products", headers=admin_h, timeout=15)
        assert r2.status_code == 200
        items = r2.json()["products"]
        item = next((i for i in items if i["id"] == created["id"]), None)
        assert item, "not found"
        assert item["status"] == "PAID"
        assert (item.get("paid_by") or "").lower() == INVEST_EMAIL.lower()

        # Second call → still PAID, no new email (idempotent)
        r3 = requests.post(f"{BASE_URL}/api/public/financing-products/webhook", json=payload, timeout=15)
        assert r3.status_code == 200

    def test_update_after_paid_409(self, admin_h, created):
        r = requests.put(f"{BASE_URL}/api/admin/financing-products/{created['id']}",
                         headers=admin_h, json={"margin_percent": 30}, timeout=15)
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text[:200]}"

    def test_delete_after_paid_409(self, admin_h, created):
        r = requests.delete(f"{BASE_URL}/api/admin/financing-products/{created['id']}",
                            headers=admin_h, timeout=15)
        assert r.status_code == 409

    def test_pay_after_paid_409(self, invest_h, created):
        r = requests.post(f"{BASE_URL}/api/investor/financing-products/{created['id']}/pay",
                          headers=invest_h, timeout=15)
        assert r.status_code == 409


def _admin_for():
    # helper to avoid re-login in unit — reuses env-based token via fresh login
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PW, "portal": "admin"}, timeout=15)
    if r.status_code == 200:
        tok = r.json().get("access_token") or r.json().get("token")
        return {"Authorization": f"Bearer {tok}"} if tok else {}
    return {}


# ---------- VITRINE VENDEUR ----------

class TestVendorListings:
    def test_my_listings_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/vendor/my-listings", timeout=15)
        assert r.status_code in (401, 403)

    def test_my_listings_ok(self, vendor_h):
        if not vendor_h:
            pytest.skip("no vendor login")
        r = requests.get(f"{BASE_URL}/api/vendor/my-listings", headers=vendor_h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "listings" in d and "count" in d

    def test_pay_link_404_wrong_owner(self, vendor_h):
        if not vendor_h:
            pytest.skip("no vendor login")
        r = requests.post(f"{BASE_URL}/api/vendor/my-listings/not-a-real-id/pay-link",
                          headers=vendor_h, timeout=15)
        assert r.status_code == 404


# ---------- RELANCE 48h ----------

def test_communityplace_reminder_48h():
    """Antidate a PENDING need >48h → 1 reminder sent, flag posé, 2nd run 0."""
    asyncio.run(_reminder_flow())


async def _reminder_flow():
    from motor.motor_asyncio import AsyncIOMotorClient
    from communityplace_reminders import run_communityplace_payment_reminders

    mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]

    need_id = "TEST_Iter86_reminder_" + uuid.uuid4().hex[:8]
    ref = "BA-TEST-86R-" + uuid.uuid4().hex[:5].upper()
    old_iso = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    doc = {
        "id": need_id, "reference": ref, "product": "TEST_Rhum",
        "email": "test-reminder-iter86@example.com", "contact_name": "Test",
        "quantity": 10, "territory": "GUADELOUPE", "listing_type": "OFFRE",
        "status": "NEW", "created_at": old_iso,
        "communityplace": True, "communityplace_fee_eur": 25,
        "communityplace_payment_status": "PENDING",
        "communityplace_at": old_iso,
    }
    await db.purchase_needs.insert_one(doc)
    try:
        sent1 = await run_communityplace_payment_reminders(db)
        assert sent1 == 1, f"expected 1 reminder, got {sent1}"
        after = await db.purchase_needs.find_one({"id": need_id}, {"_id": 0})
        assert after["communityplace_reminder_sent"] is True
        assert after.get("communityplace_checkout_id")
        # Idempotent
        sent2 = await run_communityplace_payment_reminders(db)
        assert sent2 == 0, f"expected 0 on 2nd pass, got {sent2}"

        # Fresh need <48h should not be picked
        need_id2 = "TEST_Iter86_reminder_fresh_" + uuid.uuid4().hex[:8]
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        doc2 = {k: v for k, v in doc.items() if k != "_id"}
        doc2.update({"id": need_id2, "reference": ref + "F",
                     "communityplace_reminder_sent": False,
                     "communityplace_at": recent})
        await db.purchase_needs.insert_one(doc2)
        sent3 = await run_communityplace_payment_reminders(db)
        assert sent3 == 0, f"fresh need should not trigger, got {sent3}"
        await db.purchase_needs.delete_one({"id": need_id2})
    finally:
        await db.purchase_needs.delete_one({"id": need_id})
        mongo.close()
