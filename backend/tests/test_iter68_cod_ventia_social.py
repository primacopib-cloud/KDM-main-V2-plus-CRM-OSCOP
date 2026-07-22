"""Iter 68 — COD, VENT'IA, pipeline PROSPECT'IA, témoignages verified + traduction, reminders."""
import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
VENDOR = ("vendor-pro@kdmarche.fr", "Demo2026!")
ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")


# ------------- helpers -------------
def _login_member(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.cookies


def _login_admin():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1], "portal": "admin"})
    assert r.status_code == 200, r.text
    return r.cookies


@pytest.fixture(scope="module")
def buyer_token():
    tok, _ = _login_member(*BUYER)
    return tok


@pytest.fixture(scope="module")
def vendor_token():
    tok, _ = _login_member(*VENDOR)
    return tok


@pytest.fixture(scope="module")
def admin_cookies():
    return _login_admin()


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    dbname = os.environ.get("DB_NAME", "kdmarche")
    return client[dbname]


# ------------- COD eligibility -------------
class TestCod:
    def test_eligibility_no_token(self):
        r = requests.get(f"{BASE}/api/v2/checkout/cod-eligibility")
        assert r.status_code == 401

    def test_eligibility_buyer_pro(self, buyer_token):
        r = requests.get(f"{BASE}/api/v2/checkout/cod-eligibility",
                         headers={"Authorization": f"Bearer {buyer_token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("eligible") is True

    def test_confirm_cod_invalid_order(self, buyer_token):
        # Non existing order -> 404 or 400
        r = requests.post(f"{BASE}/api/v2/checkout/confirm-cod",
                          params={"order_id": "does-not-exist"},
                          headers={"Authorization": f"Bearer {buyer_token}"})
        assert r.status_code in (400, 403, 404)

    def test_confirm_cod_on_pending_order(self, buyer_token, db):
        """Utilise une commande PENDING existante de l'org org-demo-achats, sinon skip."""
        async def _find():
            return await db.orders.find_one({"org_id": "org-demo-achats", "status": "PENDING"})

        order = asyncio.get_event_loop().run_until_complete(_find())
        if not order:
            pytest.skip("Pas de commande PENDING dispo pour org-demo-achats")
        oid = order["id"]
        r = requests.post(f"{BASE}/api/v2/checkout/confirm-cod",
                          params={"order_id": oid},
                          headers={"Authorization": f"Bearer {buyer_token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True

        async def _check():
            return await db.orders.find_one({"id": oid})
        updated = asyncio.get_event_loop().run_until_complete(_check())
        assert updated["status"] == "CONFIRMED"
        assert updated["payment_status"] == "cod_pending"
        assert updated["payment_method"] == "cod"
        assert updated.get("cod_amount_due_cents")


# ------------- PROSPECT'IA pipeline -------------
class TestProspectiaPipeline:
    def test_pipeline_unauthenticated(self):
        r = requests.get(f"{BASE}/api/admin/prospectia/pipeline")
        assert r.status_code in (401, 403)

    def test_pipeline_admin(self, admin_cookies):
        r = requests.get(f"{BASE}/api/admin/prospectia/pipeline", cookies=admin_cookies)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total" in data
        assert "conversion_rate" in data
        assert "stages" in data
        assert len(data["stages"]) == 5
        keys = [s["key"] for s in data["stages"]]
        assert keys == ["a_contacter", "contacte", "relance", "clique", "converti"]


# ------------- VENT'IA -------------
class TestVentia:
    def test_product_copy_disabled(self, vendor_token, admin_cookies):
        # Force disable to confirm 403
        r = requests.put(f"{BASE}/api/admin/ai-agents", json={"ventia_enabled": False}, cookies=admin_cookies)
        assert r.status_code in (200, 204)
        r = requests.post(f"{BASE}/api/vendor/ai/product-copy",
                          json={"name": "Rhum vieux AOC", "category": "spiritueux", "region": "Guadeloupe"},
                          headers={"Authorization": f"Bearer {vendor_token}"})
        assert r.status_code == 403, r.text

    def test_product_copy_enabled(self, vendor_token, admin_cookies):
        r = requests.put(f"{BASE}/api/admin/ai-agents", json={"ventia_enabled": True}, cookies=admin_cookies)
        assert r.status_code in (200, 204)
        r = requests.post(f"{BASE}/api/vendor/ai/product-copy",
                          json={"name": "Rhum vieux AOC", "category": "spiritueux", "region": "Guadeloupe"},
                          headers={"Authorization": f"Bearer {vendor_token}"},
                          timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("description")
        assert data.get("price_advice")
        wc = len(data["description"].split())
        assert 40 <= wc <= 160, f"description word count {wc}"

    def test_product_copy_empty_name(self, vendor_token):
        r = requests.post(f"{BASE}/api/vendor/ai/product-copy",
                          json={"name": "  "},
                          headers={"Authorization": f"Bearer {vendor_token}"})
        assert r.status_code == 400


# ------------- Testimonials verified_member + traduction -------------
class TestSocialProof:
    def test_public_submit_anonymous_not_verified(self, db):
        r = requests.post(f"{BASE}/api/public/testimonials", json={
            "name": "TEST Anon Iter68", "text": "Ceci est un test anonyme iter68 pour tester verified.",
            "rating": 5, "email": "TEST_anon68@example.com"
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("verified_member") is False

    def test_public_submit_verified_member(self, buyer_token, db):
        r = requests.post(f"{BASE}/api/public/testimonials",
                          json={"name": "TEST Buyer Verified Iter68",
                                "text": "Excellente coopérative iter68, super parcours acheteur pro."},
                          headers={"Authorization": f"Bearer {buyer_token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("verified_member") is True

        async def _check():
            return await db.testimonials.find_one({"name": "TEST Buyer Verified Iter68"})
        doc = asyncio.get_event_loop().run_until_complete(_check())
        assert doc["verified_member"] is True

    def test_translation_on_approval(self, admin_cookies, db):
        # Create pending testimonial
        r = requests.post(f"{BASE}/api/public/testimonials", json={
            "name": "TEST Translate Iter68", "email": "TEST_translate68@example.com",
            "text": "Cette plateforme coopérative est vraiment excellente pour notre restaurant en Guadeloupe.",
            "rating": 5
        })
        assert r.status_code == 200

        async def _find():
            return await db.testimonials.find_one({"name": "TEST Translate Iter68"})
        doc = asyncio.get_event_loop().run_until_complete(_find())
        tid = doc["id"]

        r = requests.patch(f"{BASE}/api/admin/social-proof/testimonials/{tid}",
                           json={"status": "approved"}, cookies=admin_cookies)
        assert r.status_code == 200, r.text

        # Wait for async translation
        for _ in range(20):
            time.sleep(3)
            d = asyncio.get_event_loop().run_until_complete(
                db.testimonials.find_one({"id": tid}, {"text_en": 1, "text_es": 1}))
            if d and d.get("text_en") and d.get("text_es"):
                break
        assert d.get("text_en"), "text_en not populated"
        assert d.get("text_es"), "text_es not populated"

        # Verify language switch
        r = requests.get(f"{BASE}/api/public/testimonials?lang=en")
        items = r.json()["items"]
        found = next((t for t in items if t["id"] == tid), None)
        assert found and found["text"] == d["text_en"]

        r = requests.get(f"{BASE}/api/public/testimonials?lang=es")
        items = r.json()["items"]
        found = next((t for t in items if t["id"] == tid), None)
        assert found and found["text"] == d["text_es"]

        # cleanup
        asyncio.get_event_loop().run_until_complete(db.testimonials.delete_one({"id": tid}))

    def test_cleanup_test_data(self, db):
        async def _cleanup():
            await db.testimonials.delete_many({"name": {"$regex": "^TEST "}})
            await db.testimonial_invites.delete_many({"email": {"$regex": "^TEST_"}})
        asyncio.get_event_loop().run_until_complete(_cleanup())


# ------------- process_testimonial_reminders + process_abandoned_carts -------------
class TestJobs:
    def test_process_testimonial_reminders(self, db, admin_cookies):
        # Enable prospectia
        requests.put(f"{BASE}/api/admin/ai-agents", json={"prospectia_enabled": True}, cookies=admin_cookies)

        async def _prep():
            # Insert invite J-8
            past = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
            await db.testimonial_invites.delete_many({"email": {"$regex": "^TEST_reminder"}})
            await db.testimonial_invites.insert_one({
                "email": "TEST_reminder68@example.com", "sent_at": past
            })
            # Also insert one already-testified case
            await db.testimonial_invites.insert_one({
                "email": "TEST_reminder_converted68@example.com", "sent_at": past
            })
            await db.testimonials.insert_one({
                "id": "test-conv-iter68", "email": "TEST_reminder_converted68@example.com",
                "name": "TEST Converted", "text": "x" * 20, "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            })

        asyncio.get_event_loop().run_until_complete(_prep())

        # Run job
        import sys
        sys.path.insert(0, "/app/backend")
        from social_proof import process_testimonial_reminders
        asyncio.get_event_loop().run_until_complete(process_testimonial_reminders(db))

        async def _check():
            inv1 = await db.testimonial_invites.find_one({"email": "TEST_reminder68@example.com"})
            inv2 = await db.testimonial_invites.find_one({"email": "TEST_reminder_converted68@example.com"})
            return inv1, inv2

        inv1, inv2 = asyncio.get_event_loop().run_until_complete(_check())
        assert inv1.get("reminder_sent") is True
        assert inv2.get("reminder_sent") is True
        assert inv2.get("converted") is True

        # cleanup
        async def _cleanup():
            await db.testimonial_invites.delete_many({"email": {"$regex": "^TEST_reminder"}})
            await db.testimonials.delete_one({"id": "test-conv-iter68"})
        asyncio.get_event_loop().run_until_complete(_cleanup())

    def test_process_abandoned_carts(self, db, admin_cookies):
        requests.put(f"{BASE}/api/admin/ai-agents", json={"ventia_enabled": True}, cookies=admin_cookies)

        async def _prep():
            await db.carts.delete_many({"id": {"$regex": "^TEST_cart68"}})
            past = datetime.utcnow() - timedelta(hours=30)
            await db.carts.insert_one({
                "id": "TEST_cart68_active", "org_id": "org-demo-achats",
                "status": "ACTIVE",
                "items": [{"product_name": "Rhum test", "quantity": 2}],
                "updated_at": past,
            })
            await db.carts.insert_one({
                "id": "TEST_cart68_converted", "org_id": "org-demo-achats",
                "status": "CONVERTED",
                "items": [{"product_name": "Rhum test", "quantity": 2}],
                "updated_at": past,
            })

        asyncio.get_event_loop().run_until_complete(_prep())

        import sys
        sys.path.insert(0, "/app/backend")
        from ventia_service import process_abandoned_carts
        asyncio.get_event_loop().run_until_complete(process_abandoned_carts(db))

        async def _check():
            active = await db.carts.find_one({"id": "TEST_cart68_active"})
            conv = await db.carts.find_one({"id": "TEST_cart68_converted"})
            return active, conv

        active, conv = asyncio.get_event_loop().run_until_complete(_check())
        assert active.get("ventia_reminder_sent") is True
        assert conv.get("ventia_reminder_sent") is not True

        # Run again -> no-op (still True, no duplicate)
        asyncio.get_event_loop().run_until_complete(process_abandoned_carts(db))

        # cleanup
        asyncio.get_event_loop().run_until_complete(
            db.carts.delete_many({"id": {"$regex": "^TEST_cart68"}}))

    def test_restore_agents_off(self, admin_cookies):
        r = requests.put(f"{BASE}/api/admin/ai-agents",
                         json={"ventia_enabled": False, "prospectia_enabled": False},
                         cookies=admin_cookies)
        assert r.status_code in (200, 204)
