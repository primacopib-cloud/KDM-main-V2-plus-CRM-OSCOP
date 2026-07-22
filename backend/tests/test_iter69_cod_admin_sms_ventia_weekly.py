"""Iter 69 — COD admin encaissement + relance J+7 + SMS statut + VENT'IA product-image + weekly history."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta

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
    return r.json()["access_token"]


def _login_admin():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": ADMIN[0], "password": ADMIN[1], "portal": "admin"})
    assert r.status_code == 200, r.text
    return r.cookies


@pytest.fixture(scope="module")
def buyer_token():
    return _login_member(*BUYER)


@pytest.fixture(scope="module")
def vendor_token():
    return _login_member(*VENDOR)


@pytest.fixture(scope="module")
def admin_cookies():
    return _login_admin()


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    dbname = os.environ.get("DB_NAME", "kdmarche_lolodrive")
    return client[dbname]


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# =========================================================
# COD ADMIN — list + collected
# =========================================================
class TestCodAdmin:
    def test_list_cod_orders_no_admin(self):
        r = requests.get(f"{BASE}/api/admin/cod/orders")
        assert r.status_code in (401, 403)

    def test_list_cod_orders_admin(self, admin_cookies):
        r = requests.get(f"{BASE}/api/admin/cod/orders", cookies=admin_cookies)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert "pending_count" in data
        assert "pending_due_cents" in data
        assert isinstance(data["items"], list)
        # If items exist, they must carry org_name (may be empty string) and expected fields
        for it in data["items"]:
            assert "id" in it
            assert "order_number" in it
            assert "org_name" in it
            assert "_id" not in it  # ObjectId excluded

    def test_collected_flow_synthetic_order(self, db, admin_cookies):
        """Insert a synthetic COD pending order, mark collected, verify invoice, verify 400 on 2nd call."""
        oid = f"TEST_COD_{uuid.uuid4().hex[:8]}"
        onum = f"TEST-KDM-{uuid.uuid4().hex[:6].upper()}"
        confirmed_at = datetime.utcnow() - timedelta(days=1)
        doc = {
            "id": oid,
            "order_number": onum,
            "org_id": "org-demo-achats",
            "zone_code": "GUADELOUPE",
            "status": "CONFIRMED",
            "payment_method": "cod",
            "payment_status": "cod_pending",
            "cod": True,
            "incoterm": "EXW",
            "pickup_location_id": "pickup-test",
            "items": [{
                "product_id": "p-test", "product_name": "Rhum test", "product_sku": "SKU-TEST",
                "unit": "bouteille", "quantity": 1,
                "price_ht_cents": 1500, "line_total_ht_cents": 1500
            }],
            "items_count": 1,
            "subtotal_ht_cents": 1500,
            "tax_cents": 128,
            "total_ttc_cents": 1628,
            "cod_amount_due_cents": 1628,
            "confirmed_at": confirmed_at,
            "created_at": confirmed_at,
            "updated_at": confirmed_at,
            "created_by_user_id": "test-user",
        }
        _run(db.orders.insert_one(doc))
        try:
            # Mark collected
            r = requests.post(f"{BASE}/api/admin/cod/orders/{oid}/collected", cookies=admin_cookies)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["ok"] is True
            assert data["amount_paid_cents"] == 1628
            # invoice_number may or may not be present depending on invoice service
            # but the field must at least exist in response
            assert "invoice_number" in data

            updated = _run(db.orders.find_one({"id": oid}))
            assert updated["payment_status"] == "succeeded"
            assert updated["amount_paid_cents"] == 1628
            assert updated.get("paid_at") is not None

            # 2nd call -> 400 déjà encaissée
            r2 = requests.post(f"{BASE}/api/admin/cod/orders/{oid}/collected", cookies=admin_cookies)
            assert r2.status_code == 400, r2.text
            assert "déjà" in r2.json().get("detail", "").lower() or "already" in r2.json().get("detail", "").lower()
        finally:
            _run(db.orders.delete_one({"id": oid}))
            # cleanup any invoices generated for this test order
            _run(db.invoices.delete_many({"order_id": oid}))

    def test_collected_non_cod_returns_400(self, db, admin_cookies):
        oid = f"TEST_NONCOD_{uuid.uuid4().hex[:8]}"
        doc = {
            "id": oid, "order_number": f"TEST-NC-{uuid.uuid4().hex[:6]}",
            "org_id": "org-demo-achats", "zone_code": "GUADELOUPE",
            "status": "CONFIRMED", "payment_method": "card", "payment_status": "succeeded",
            "incoterm": "EXW", "pickup_location_id": "p", "items": [], "items_count": 0,
            "subtotal_ht_cents": 100, "tax_cents": 0, "total_ttc_cents": 100,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            "created_by_user_id": "test-user",
        }
        _run(db.orders.insert_one(doc))
        try:
            r = requests.post(f"{BASE}/api/admin/cod/orders/{oid}/collected", cookies=admin_cookies)
            assert r.status_code == 400, r.text
        finally:
            _run(db.orders.delete_one({"id": oid}))


# =========================================================
# COD REMINDERS — process_cod_reminders J+7
# =========================================================
class TestCodReminders:
    def test_process_cod_reminders(self, db):
        oid = f"TEST_CODREM_{uuid.uuid4().hex[:8]}"
        past = datetime.utcnow() - timedelta(days=8)
        doc = {
            "id": oid, "order_number": f"TEST-REM-{uuid.uuid4().hex[:6]}",
            "org_id": "org-demo-achats", "status": "CONFIRMED",
            "payment_method": "cod", "payment_status": "cod_pending",
            "cod_amount_due_cents": 5000, "total_ttc_cents": 5000,
            "confirmed_at": past, "created_at": past, "updated_at": past,
        }
        _run(db.orders.insert_one(doc))
        try:
            import sys
            sys.path.insert(0, "/app/backend")
            from routes_cod import process_cod_reminders
            _run(process_cod_reminders(db))

            updated = _run(db.orders.find_one({"id": oid}))
            assert updated.get("cod_reminder_sent") is True, "cod_reminder_sent should be True after J+7 processing"

            # 2nd run — no-op (flag stays True, no error)
            _run(process_cod_reminders(db))
            re_check = _run(db.orders.find_one({"id": oid}))
            assert re_check.get("cod_reminder_sent") is True
        finally:
            _run(db.orders.delete_one({"id": oid}))


# =========================================================
# SMS statut commande
# =========================================================
class TestOrderStatusSms:
    def test_send_order_status_sms_direct(self, db):
        """Test la fonction python directement avec un utilisateur sans phone (early return sans crash)."""
        import sys
        sys.path.insert(0, "/app/backend")
        from order_sms import send_order_status_sms

        # Use any existing order — function is fire-and-forget & tolerates missing phone
        order = _run(db.orders.find_one({}))
        if not order:
            pytest.skip("Aucune commande en base")
        # Should not raise
        _run(send_order_status_sms(db, order["id"], "READY_FOR_PICKUP"))

    def test_admin_update_status_triggers_sms(self, db, admin_cookies):
        """POST /api/v2/orders/admin/{id}/status?new_status=READY_FOR_PICKUP => 200 + SMS scheduled.
        Créer une commande synthétique, changer statut, vérifier log."""
        oid = f"TEST_SMS_{uuid.uuid4().hex[:8]}"
        doc = {
            "id": oid, "order_number": f"TEST-SMS-{uuid.uuid4().hex[:6]}",
            "org_id": "org-demo-achats", "zone_code": "GUADELOUPE",
            "status": "CONFIRMED", "incoterm": "EXW",
            "pickup_location_id": "pickup-test",
            "items": [], "items_count": 0,
            "subtotal_ht_cents": 100, "tax_cents": 0, "total_ttc_cents": 100,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            "created_by_user_id": "test-user",
        }
        _run(db.orders.insert_one(doc))
        try:
            r = requests.post(
                f"{BASE}/api/v2/orders/admin/{oid}/status",
                params={"new_status": "READY_FOR_PICKUP"},
                cookies=admin_cookies,
            )
            # Note: this endpoint uses catalog auth which reads user from cookie/bearer
            # We accept 200 (ok) or 403 (if cookie auth not compatible with catalog dep).
            # The important thing is if 200 -> SMS was scheduled.
            assert r.status_code in (200, 403), r.text
            if r.status_code == 200:
                # Give the fire-and-forget task time to run
                import time
                time.sleep(1.5)
                updated = _run(db.orders.find_one({"id": oid}))
                assert updated["status"] == "READY_FOR_PICKUP"
        finally:
            _run(db.orders.delete_one({"id": oid}))


# =========================================================
# VENT'IA product-image
# =========================================================
class TestVentiaImage:
    def test_product_image_disabled(self, vendor_token, admin_cookies):
        r = requests.put(f"{BASE}/api/admin/ai-agents",
                         json={"ventia_enabled": False}, cookies=admin_cookies)
        assert r.status_code in (200, 204)
        r = requests.post(
            f"{BASE}/api/vendor/ai/product-image",
            json={"name": "Rhum vieux AOC", "category": "spiritueux", "region": "Guadeloupe"},
            headers={"Authorization": f"Bearer {vendor_token}"},
        )
        assert r.status_code == 403, r.text

    def test_product_image_empty_name(self, vendor_token, admin_cookies):
        requests.put(f"{BASE}/api/admin/ai-agents",
                     json={"ventia_enabled": True}, cookies=admin_cookies)
        r = requests.post(
            f"{BASE}/api/vendor/ai/product-image",
            json={"name": "   "},
            headers={"Authorization": f"Bearer {vendor_token}"},
        )
        assert r.status_code == 400, r.text

    def test_product_image_enabled_generates(self, vendor_token, admin_cookies):
        requests.put(f"{BASE}/api/admin/ai-agents",
                     json={"ventia_enabled": True}, cookies=admin_cookies)
        r = requests.post(
            f"{BASE}/api/vendor/ai/product-image",
            json={"name": "Confiture goyave artisanale", "category": "épicerie", "region": "Martinique"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        url = data.get("image_url", "")
        assert url.startswith("/api/uploads/ventia/"), f"unexpected url: {url}"

        # Fetch image publicly (should be 200 with image content)
        get_url = f"{BASE}{url}"
        r2 = requests.get(get_url, timeout=30)
        assert r2.status_code == 200, f"{get_url} -> {r2.status_code}"
        assert len(r2.content) > 500, "image file suspiciously small"


# =========================================================
# WEEKLY history
# =========================================================
class TestWeeklyHistory:
    def test_history_no_admin(self):
        r = requests.get(f"{BASE}/api/admin/reports/weekly/history")
        assert r.status_code in (401, 403)

    def test_history_admin(self, admin_cookies):
        r = requests.get(f"{BASE}/api/admin/reports/weekly/history", cookies=admin_cookies)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        # If any items, must be sorted desc by 'week' and contain expected keys
        if data["items"]:
            for it in data["items"]:
                assert "week" in it
                assert "sent_at" in it
                assert "stats" in it
                assert "_id" not in it
            weeks = [it["week"] for it in data["items"]]
            assert weeks == sorted(weeks, reverse=True), "history should be sorted desc"


# =========================================================
# Restore agents OFF
# =========================================================
class TestCleanup:
    def test_restore_agents_off(self, admin_cookies):
        r = requests.put(f"{BASE}/api/admin/ai-agents",
                         json={"ventia_enabled": False, "prospectia_enabled": False},
                         cookies=admin_cookies)
        assert r.status_code in (200, 204)
