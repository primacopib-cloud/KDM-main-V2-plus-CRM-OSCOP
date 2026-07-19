"""
Iter 52 — Validation du lot de 5 nouvelles fonctionnalités :
1) Modèles de consultations (templates + instantiate) — routes_consultation_templates
2) Abonnements mensuels CPC (plans + checkout + handle_cpc_subscription_event) — routes_cpc_subscriptions
3) Alerte Rapport Dispo (notify_report_available idempotent + close_due_consultations) — consultation_notify
4) Recharge CPC semi-automatique (settings + checkout/{token} + maybe_send_recharge_link) — routes_cpc_recharge
5) Régression : /api/cpc/checkout (pack), /api/cpc/me, /api/consultations/tracking
"""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env", override=True)

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PASS = "Demo2026!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PASS = "Demo2026!"

TEST_CAT = f"test-iter52-{uuid.uuid4().hex[:6]}"
STATE = {}


def _login(email, password, portal=None):
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = requests.post(f"{BASE}/api/auth/login", json=body, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS, "admin")


@pytest.fixture(scope="module")
def vendor_token():
    return _login(VENDOR_EMAIL, VENDOR_PASS)


@pytest.fixture(scope="module")
def buyer_token():
    return _login(BUYER_EMAIL, BUYER_PASS)


def _db():
    """Create fresh motor client. MUST be called inside async function to bind to current loop."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client, client[os.environ["DB_NAME"]]


def _run(coro_fn):
    """Helper: create client inside async, run, cleanup."""
    async def _inner():
        client, db = _db()
        return await coro_fn(db)
    return asyncio.run(_inner())


# ---------- 1) TEMPLATES ----------

class TestTemplates:
    def test_01_list_default_templates(self, admin_token):
        r = requests.get(f"{BASE}/api/admin/consultation-templates", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        ids = {t["id"] for t in r.json()["items"]}
        expected = {"tpl-alimentaire-scellee", "tpl-emballage-enchere",
                    "tpl-transport-enchere", "tpl-hygiene-enchere"}
        assert expected.issubset(ids), f"missing default templates: {expected - ids}"

    def test_02_requires_admin(self, vendor_token):
        r = requests.get(f"{BASE}/api/admin/consultation-templates", headers=H(vendor_token), timeout=30)
        assert r.status_code in (401, 403)

    def test_03_create_custom_template(self, admin_token):
        r = requests.post(f"{BASE}/api/admin/consultation-templates",
                          json={"name": f"TEST_iter52 custom {TEST_CAT}",
                                "title": "TEST_iter52 template custom",
                                "type": "STANDARD", "procedure": "ENCHERE_INVERSEE",
                                "category": TEST_CAT, "products": [{"label": "P1"}],
                                "territories": ["GUADELOUPE"], "specs": "test", "duration_days": 5},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"].startswith("tpl-")
        STATE["custom_tid"] = d["id"]

    def test_04_seed_legal_matrix_vert_for_category(self, admin_token):
        # sinon resolve_legal_status renvoie NON_CLASSE
        r = requests.post(f"{BASE}/api/admin/legal-matrix",
                          json={"scope": "category", "category": TEST_CAT, "status": "VERT",
                                "legal_reason": "TEST_iter52"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_05_instantiate_custom_template(self, admin_token):
        tid = STATE["custom_tid"]
        r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/instantiate",
                          json={}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ref"].startswith("CONS-"), f"ref should start with CONS- got {d['ref']}"
        assert d["status"] == "BROUILLON"
        assert d["legal_status"] == "VERT"
        assert d["procedure"] == "ENCHERE_INVERSEE"  # not overridden (only ROUGE forces SCELLEE)
        assert d["cpc_cost"] == 20  # STANDARD => standard_cost
        assert d["template_id"] == tid
        STATE["cid_from_custom"] = d["id"]

    def test_06_instantiate_default_alimentaire_forces_scellee_when_rouge(self, admin_token):
        # Classify default 'alimentaire' as ROUGE to test forced SCELLEE
        # But we must not pollute prod - use a special ROUGE category via custom template
        # Create a template with a new red category
        red_cat = f"test-iter52-red-{uuid.uuid4().hex[:6]}"
        STATE["red_cat"] = red_cat
        r = requests.post(f"{BASE}/api/admin/legal-matrix",
                          json={"scope": "category", "category": red_cat, "status": "ROUGE",
                                "legal_reason": "TEST_iter52 rouge"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/admin/consultation-templates",
                          json={"name": f"TEST_iter52 rouge {red_cat}", "title": "T rouge",
                                "type": "STANDARD", "procedure": "ENCHERE_INVERSEE",  # will be overridden
                                "category": red_cat, "territories": ["GUADELOUPE"]},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        tid = r.json()["id"]
        STATE["red_tid"] = tid
        r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/instantiate",
                          json={}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["legal_status"] == "ROUGE"
        assert d["procedure"] == "SCELLEE", f"ROUGE MUST force SCELLEE, got {d['procedure']}"
        STATE["cid_from_red"] = d["id"]

    def test_07_instantiate_interterritorial_cpc_cost_40(self, admin_token):
        # tpl-transport-enchere is INTERTERRITORIALE — but category='transport' may not be VERT
        # Seed VERT for transport just in case (idempotent add version)
        requests.post(f"{BASE}/api/admin/legal-matrix",
                      json={"scope": "category", "category": "transport", "status": "VERT",
                            "legal_reason": "TEST_iter52 (backup already existing)"},
                      headers=H(admin_token), timeout=30)
        r = requests.post(f"{BASE}/api/admin/consultation-templates/tpl-transport-enchere/instantiate",
                          json={}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["cpc_cost"] == 40, f"INTERTERRITORIALE cost expected 40 got {d['cpc_cost']}"
        assert d["type"] == "INTERTERRITORIALE"
        STATE["cid_transport"] = d["id"]

    def test_08_put_template(self, admin_token):
        tid = STATE["custom_tid"]
        r = requests.put(f"{BASE}/api/admin/consultation-templates/{tid}",
                         json={"name": "TEST_iter52 renamed", "title": "T2", "category": TEST_CAT,
                               "type": "STANDARD", "procedure": "SCELLEE", "duration_days": 3},
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_09_delete_template(self, admin_token):
        tid = STATE["custom_tid"]
        r = requests.delete(f"{BASE}/api/admin/consultation-templates/{tid}",
                            headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        # Verify GONE from active list
        items = requests.get(f"{BASE}/api/admin/consultation-templates",
                             headers=H(admin_token), timeout=30).json()["items"]
        assert tid not in [t["id"] for t in items]

    def test_10_put_404(self, admin_token):
        r = requests.put(f"{BASE}/api/admin/consultation-templates/tpl-nonexistent-xxx",
                         json={"name": "x", "title": "x", "category": "x"},
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 404


# ---------- 2) ABONNEMENTS CPC ----------

class TestSubscriptions:
    def test_20_list_plans(self):
        r = requests.get(f"{BASE}/api/cpc/subscription/plans", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        ids = {p["id"] for p in items}
        assert {"cpc-plan-pro", "cpc-plan-expert", "cpc-plan-reseau"}.issubset(ids)
        pro = next(p for p in items if p["id"] == "cpc-plan-pro")
        assert pro["price_ht_cents"] == 4900
        assert pro["monthly_cpc"] == 60

    def test_21_subscription_checkout_creates_pending(self, vendor_token):
        r = requests.post(f"{BASE}/api/cpc/subscription/checkout",
                          json={"plan_id": "cpc-plan-pro",
                                "origin_url": "https://example.com"},
                          headers=H(vendor_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout_url" in d
        assert "checkout.stripe.com" in d["checkout_url"], f"not stripe live url: {d['checkout_url']}"
        STATE["sub_session_id"] = d["session_id"]

    def test_22_subscription_pending_persisted(self):
        client, db = _db()
        async def run():
            s = await db.cpc_subscriptions.find_one({"stripe_session_id": STATE["sub_session_id"]})
            assert s is not None
            assert s["status"] == "PENDING"
            assert s["plan_id"] == "cpc-plan-pro"
            STATE["sub_id"] = s["id"]
            STATE["sub_user_id"] = s["user_id"]
        asyncio.run(run())

    def test_23_second_checkout_conflicts_with_active(self, vendor_token):
        # Simulate ACTIVE state by upserting; test 409
        client, db = _db()
        async def prep():
            await db.cpc_subscriptions.update_one({"id": STATE["sub_id"]},
                                                 {"$set": {"status": "ACTIVE",
                                                           "stripe_subscription_id": f"sub_TEST_{uuid.uuid4().hex[:8]}"}})
        asyncio.run(prep())
        r = requests.post(f"{BASE}/api/cpc/subscription/checkout",
                          json={"plan_id": "cpc-plan-expert", "origin_url": "https://example.com"},
                          headers=H(vendor_token), timeout=30)
        assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text}"
        # Reset PENDING for further tests
        client, db = _db()
        async def reset():
            await db.cpc_subscriptions.update_one({"id": STATE["sub_id"]},
                                                 {"$set": {"status": "PENDING"},
                                                  "$unset": {"stripe_subscription_id": ""}})
        asyncio.run(reset())

    def test_24_handle_checkout_session_completed(self):
        """Directly invoke handle_cpc_subscription_event with a fake event."""
        from routes_cpc_subscriptions import handle_cpc_subscription_event, set_cpc_subs_database
        client, db = _db()
        async def run():
            set_cpc_subs_database(db)
            fake_sub_id = f"sub_TESTiter52_{uuid.uuid4().hex[:10]}"
            STATE["fake_sub_id"] = fake_sub_id
            event = {
                "id": f"evt_TESTiter52_{uuid.uuid4().hex[:8]}",
                "type": "checkout.session.completed",
                "data": {"object": {
                    "id": STATE["sub_session_id"],
                    "mode": "subscription",
                    "subscription": fake_sub_id,
                    "customer": f"cus_TEST_{uuid.uuid4().hex[:8]}",
                    "metadata": {"kind": "CPC_SUBSCRIPTION", "user_id": STATE["sub_user_id"],
                                 "plan_id": "cpc-plan-pro"},
                }},
            }
            handled = await handle_cpc_subscription_event(event)
            assert handled is True
            s = await db.cpc_subscriptions.find_one({"id": STATE["sub_id"]})
            assert s["status"] == "ACTIVE"
            assert s["stripe_subscription_id"] == fake_sub_id
        asyncio.run(run())

    def test_25_handle_invoice_paid_credits_60_cpc(self):
        """Invoice.paid must credit +60 CPC (SUBSCRIPTION_GRANT) + create cpc_purchases with expires_at+3mo."""
        from routes_cpc_subscriptions import handle_cpc_subscription_event, set_cpc_subs_database
        from cpc_ledger import set_cpc_ledger_database, get_cpc_account
        client, db = _db()
        async def run():
            set_cpc_subs_database(db)
            set_cpc_ledger_database(db)
            user_id = STATE["sub_user_id"]
            before = (await get_cpc_account(user_id))["cpc_balance"]
            invoice_id = f"in_TESTiter52_{uuid.uuid4().hex[:10]}"
            STATE["fake_invoice_id"] = invoice_id
            event = {
                "id": f"evt_TESTiter52_{uuid.uuid4().hex[:8]}",
                "type": "invoice.paid",
                "data": {"object": {
                    "id": invoice_id,
                    "customer_email": VENDOR_EMAIL,
                    "subscription_details": {"metadata": {
                        "kind": "CPC_SUBSCRIPTION", "user_id": user_id,
                        "plan_id": "cpc-plan-pro", "monthly_cpc": "60"}},
                }},
            }
            handled = await handle_cpc_subscription_event(event)
            assert handled is True
            after = (await get_cpc_account(user_id))["cpc_balance"]
            assert after - before == 60, f"expected +60 CPC, got {before}->{after}"
            # cpc_purchases entry
            p = await db.cpc_purchases.find_one({"id": f"subcpc-{invoice_id}"})
            assert p is not None
            assert p["credits"] == 60
            assert p["validity_months"] == 3
            # Ledger entry SUBSCRIPTION_GRANT
            l = await db.cpc_ledger.find_one({"idempotency_key": f"subinv:{invoice_id}"})
            assert l is not None
            assert l["type"] == "SUBSCRIPTION_GRANT"
            assert l["qty"] == 60
            STATE["balance_after_grant"] = after
        asyncio.run(run())

    def test_26_handle_invoice_paid_replay_idempotent(self):
        """Replay same invoice.paid → NO double credit."""
        from routes_cpc_subscriptions import handle_cpc_subscription_event, set_cpc_subs_database
        from cpc_ledger import set_cpc_ledger_database, get_cpc_account
        client, db = _db()
        async def run():
            set_cpc_subs_database(db)
            set_cpc_ledger_database(db)
            user_id = STATE["sub_user_id"]
            event = {
                "id": f"evt_TESTiter52_{uuid.uuid4().hex[:8]}",
                "type": "invoice.paid",
                "data": {"object": {
                    "id": STATE["fake_invoice_id"],
                    "customer_email": VENDOR_EMAIL,
                    "subscription_details": {"metadata": {
                        "kind": "CPC_SUBSCRIPTION", "user_id": user_id,
                        "plan_id": "cpc-plan-pro", "monthly_cpc": "60"}},
                }},
            }
            await handle_cpc_subscription_event(event)
            after = (await get_cpc_account(user_id))["cpc_balance"]
            assert after == STATE["balance_after_grant"], \
                f"REPLAY MUST NOT double-credit: {STATE['balance_after_grant']} -> {after}"
        asyncio.run(run())

    def test_27_handle_subscription_deleted(self):
        from routes_cpc_subscriptions import handle_cpc_subscription_event, set_cpc_subs_database
        client, db = _db()
        async def run():
            set_cpc_subs_database(db)
            event = {
                "id": f"evt_TESTiter52_{uuid.uuid4().hex[:8]}",
                "type": "customer.subscription.deleted",
                "data": {"object": {
                    "id": STATE["fake_sub_id"],
                    "metadata": {"kind": "CPC_SUBSCRIPTION"},
                }},
            }
            handled = await handle_cpc_subscription_event(event)
            assert handled is True
            s = await db.cpc_subscriptions.find_one({"id": STATE["sub_id"]})
            assert s["status"] == "CANCELLED", f"expected CANCELLED got {s['status']}"
        asyncio.run(run())

    def test_28_ignore_non_cpc_subscription_event(self):
        """Event without kind=CPC_SUBSCRIPTION must be ignored (returns False)."""
        from routes_cpc_subscriptions import handle_cpc_subscription_event, set_cpc_subs_database
        client, db = _db()
        async def run():
            set_cpc_subs_database(db)
            event = {
                "id": "evt_ignored",
                "type": "invoice.paid",
                "data": {"object": {"id": "in_ignored", "subscription_details": {
                    "metadata": {"kind": "SOMETHING_ELSE"}}}},
            }
            handled = await handle_cpc_subscription_event(event)
            assert handled is False
        asyncio.run(run())

    def test_29_admin_list_plans(self, admin_token):
        r = requests.get(f"{BASE}/api/admin/cpc/plans", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "items" in d and len(d["items"]) >= 3
        assert "subscriptions" in d


# ---------- 3) ALERTE RAPPORT DISPO ----------

class TestReportAlert:
    def test_40_setup_and_close_consultation_triggers_alert(self, admin_token, vendor_token):
        # Ensure vendor has enough CPC
        client, db = _db()
        async def top_up():
            from cpc_ledger import set_cpc_ledger_database, get_cpc_account
            set_cpc_ledger_database(db)
            acc = await get_cpc_account(STATE["sub_user_id"])
            STATE["initial_balance_before_report_test"] = acc["cpc_balance"]
        asyncio.run(top_up())

        # Ensure at least 30 CPC
        cur = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        if cur < 30:
            r = requests.post(f"{BASE}/api/admin/cpc/correction",
                              json={"user_email": VENDOR_EMAIL, "qty": 30,
                                    "reason": "TEST_iter52 report alert", "reference": "iter52-alert"},
                              headers=H(admin_token), timeout=30)
            assert r.status_code == 200

        # Create consultation
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter52 report alert",
                                "category": TEST_CAT,
                                "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "P"}],
                                "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        STATE["cid_alert"] = cid
        # Workflow to EN_COURS
        for step in [("transition", {"to": "EN_VALIDATION"}),
                     ("validate/commercial", None),
                     ("publish", None),
                     ("transition", {"to": "INSCRIPTIONS_OUVERTES"}),
                     ("transition", {"to": "EN_COURS"})]:
            path, body = step
            r = requests.post(f"{BASE}/api/admin/consultations/{cid}/{path}",
                              json=body if body else {}, headers=H(admin_token), timeout=30)
            assert r.status_code == 200, f"{path}: {r.text}"
        # Vendor registers (-20 CPC)
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": True}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200
        # Close → report alert should fire
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "CLOTUREE"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_41_report_alert_flag_and_audit(self):
        import time
        # notify_report_available runs as asyncio.create_task after transition → poll up to 30s
        async def check():
            cid = STATE["cid_alert"]
            c = await db.consultations.find_one({"id": cid})
            assert c.get("report_alert_sent") is True, \
                f"report_alert_sent flag not set: {c.get('report_alert_sent')}"
            assert c.get("report_alert_at") is not None
            # audit is written AFTER Brevo emails send — may take a few seconds
            a = None
            for _ in range(30):
                a = await db.audit_journal.find_one(
                    {"consultation_id": cid, "event_type": "REPORT_ALERT_SENT"})
                if a:
                    break
                await asyncio.sleep(1)
            assert a is not None, "audit REPORT_ALERT_SENT missing after 30s wait"
        # allow initial delay for the background task
        time.sleep(2)
        client, db = _db()
        asyncio.run(check())

    def test_42_notify_report_available_second_call_noop(self):
        """Idempotent : 2nd call must return 0 (already flagged)."""
        from consultation_notify import notify_report_available, set_notify_database
        client, db = _db()
        async def run():
            set_notify_database(db)
            res = await notify_report_available(STATE["cid_alert"])
            assert res == 0, f"expected 0 (idempotent), got {res}"
        asyncio.run(run())

    def test_43_close_due_consultations_cron(self, admin_token, vendor_token):
        """Cron : consultation EN_COURS avec closes_at dans le passé doit être clôturée."""
        # Create consultation, workflow to EN_COURS, then rewrite closes_at to past
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter52 cron",
                                "category": TEST_CAT, "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "P"}], "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        STATE["cid_cron"] = cid
        for step in [("transition", {"to": "EN_VALIDATION"}),
                     ("validate/commercial", None),
                     ("publish", None),
                     ("transition", {"to": "INSCRIPTIONS_OUVERTES"}),
                     ("transition", {"to": "EN_COURS"})]:
            path, body = step
            rr = requests.post(f"{BASE}/api/admin/consultations/{cid}/{path}",
                          json=body if body else {}, headers=H(admin_token), timeout=30)
            assert rr.status_code == 200, f"cron setup {path}: {rr.status_code} {rr.text}"

        # Rewrite closes_at to past
        async def force_past_and_run():
            from motor.motor_asyncio import AsyncIOMotorClient
            import consultation_notify as cn
            import consultation_audit as ca
            import routes_cpc_admin as rca
            client2 = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db2 = client2[os.environ["DB_NAME"]]
            # Force re-bind of module dbs to the current loop's client
            cn.db = db2
            ca.db = db2
            rca.db = db2
            try:
                past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
                await db2.consultations.update_one({"id": cid}, {"$set": {"closes_at": past}})
                closed = await cn.close_due_consultations(db2)
                assert closed >= 1, f"expected >=1 closed, got {closed}"
                c = await db2.consultations.find_one({"id": cid})
                assert c["status"] == "CLOTUREE", f"expected CLOTUREE got {c['status']}"
                assert c.get("report_alert_sent") is True
            finally:
                client2.close()
        asyncio.run(force_past_and_run())


# ---------- 4) RECHARGE SEMI-AUTOMATIQUE ----------

class TestRecharge:
    def test_60_get_default_settings(self, vendor_token):
        r = requests.get(f"{BASE}/api/cpc/recharge/settings", headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        # Default may be from DB (previous) or default dict
        d = r.json()
        assert "enabled" in d
        assert "threshold" in d
        assert "pack_id" in d

    def test_61_put_settings(self, admin_token, vendor_token):
        # threshold must exceed current balance so ANY debit fires alert
        cur = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        thr = max(cur + 500, 500)
        STATE["recharge_threshold"] = thr
        r = requests.put(f"{BASE}/api/cpc/recharge/settings",
                         json={"enabled": True, "threshold": thr, "pack_id": "cpc-pack-50"},
                         headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.get(f"{BASE}/api/cpc/recharge/settings", headers=H(vendor_token), timeout=30)
        d = r.json()
        assert d["enabled"] is True
        assert d["threshold"] == thr
        assert d["pack_id"] == "cpc-pack-50"

    def test_62_put_invalid_pack_404(self, vendor_token):
        thr = STATE.get("recharge_threshold", 500)
        r = requests.put(f"{BASE}/api/cpc/recharge/settings",
                         json={"enabled": True, "threshold": thr, "pack_id": "cpc-pack-doesnotexist"},
                         headers=H(vendor_token), timeout=30)
        assert r.status_code == 404
        # Re-apply valid settings (previous PUT succeeded but let's re-set enabled)
        requests.put(f"{BASE}/api/cpc/recharge/settings",
                     json={"enabled": True, "threshold": thr, "pack_id": "cpc-pack-50"},
                     headers=H(vendor_token), timeout=30)

    def test_63_debit_under_threshold_creates_token_and_alert_active(self, admin_token, vendor_token):
        """Trigger a debit that brings balance below threshold=200 (currently maybe ~60 already after grant).
        Actually 200 is above current balance so alert should fire on ANY debit while enabled+threshold=200."""
        # Ensure current balance > 0 and <200 or force a debit — simplest: force a small debit
        cur = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        # Reset alert_active to False first
        client, db = _db()
        async def reset_alert():
            await db.cpc_recharge_settings.update_one(
                {"user_id": STATE["sub_user_id"]}, {"$set": {"alert_active": False}})
            # Delete any prior tokens for cleanliness
            await db.cpc_recharge_tokens.delete_many({"user_id": STATE["sub_user_id"]})
        asyncio.run(reset_alert())
        # Debit small amount via admin correction (-1 CPC)
        r = requests.post(f"{BASE}/api/admin/cpc/correction",
                          json={"user_email": VENDOR_EMAIL, "qty": -1,
                                "reason": "TEST_iter52 trigger recharge alert",
                                "reference": "iter52-recharge"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        # Verify token created + alert_active=True
        client, db = _db()
        async def check():
            tok = await db.cpc_recharge_tokens.find_one(
                {"user_id": STATE["sub_user_id"], "used": {"$ne": True}})
            assert tok is not None, "recharge token NOT created after under-threshold debit"
            STATE["recharge_token"] = tok["token"]
            s = await db.cpc_recharge_settings.find_one({"user_id": STATE["sub_user_id"]})
            assert s.get("alert_active") is True, f"alert_active not set: {s.get('alert_active')}"
        asyncio.run(check())

    def test_64_second_debit_no_new_token(self, admin_token, vendor_token):
        """Anti-spam : while alert_active=True, no new token should be created."""
        client, db = _db()
        async def count_before():
            return await db.cpc_recharge_tokens.count_documents({"user_id": STATE["sub_user_id"]})
        before = asyncio.run(count_before())
        r = requests.post(f"{BASE}/api/admin/cpc/correction",
                          json={"user_email": VENDOR_EMAIL, "qty": -1,
                                "reason": "TEST_iter52 second debit", "reference": "iter52-2"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        client, db = _db()
        async def count_after():
            return await db.cpc_recharge_tokens.count_documents({"user_id": STATE["sub_user_id"]})
        after = asyncio.run(count_after())
        assert after == before, f"anti-spam FAILED: {before} tokens -> {after} tokens"

    def test_65_recharge_checkout_redirects_303(self):
        """GET /api/cpc/recharge/checkout/{token} without auth → 303 to checkout.stripe.com."""
        token = STATE["recharge_token"]
        r = requests.get(f"{BASE}/api/cpc/recharge/checkout/{token}",
                         allow_redirects=False, timeout=60)
        assert r.status_code == 303, f"expected 303 got {r.status_code} {r.text[:200]}"
        loc = r.headers.get("Location", "")
        assert "checkout.stripe.com" in loc, f"redirect target not Stripe: {loc}"

    def test_66_recharge_checkout_token_reused_410(self):
        """2nd call with same token → 410."""
        token = STATE["recharge_token"]
        r = requests.get(f"{BASE}/api/cpc/recharge/checkout/{token}",
                         allow_redirects=False, timeout=30)
        assert r.status_code == 410, f"expected 410 got {r.status_code}"

    def test_67_recharge_checkout_invalid_token_410(self):
        r = requests.get(f"{BASE}/api/cpc/recharge/checkout/invalid-token-xxxxx",
                         allow_redirects=False, timeout=30)
        assert r.status_code == 410

    def test_68_credit_above_threshold_resets_alert_active(self, admin_token, vendor_token):
        """Recréditer massivement au-dessus du seuil → alert_active repasse False au mouvement suivant."""
        thr = STATE.get("recharge_threshold", 500)
        # Top up FAR above threshold so any subsequent movement resets alert_active
        r = requests.post(f"{BASE}/api/admin/cpc/correction",
                          json={"user_email": VENDOR_EMAIL, "qty": thr + 1000,
                                "reason": "TEST_iter52 reset above threshold",
                                "reference": "iter52-reset"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        # Then any next movement should reset alert_active=False; do a tiny +1
        r = requests.post(f"{BASE}/api/admin/cpc/correction",
                          json={"user_email": VENDOR_EMAIL, "qty": 1,
                                "reason": "TEST_iter52 tick above threshold",
                                "reference": "iter52-tick"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        client, db = _db()
        async def check():
            s = await db.cpc_recharge_settings.find_one({"user_id": STATE["sub_user_id"]})
            assert s.get("alert_active") is False, \
                f"alert_active must reset to False after balance>=threshold, got {s.get('alert_active')}"
        asyncio.run(check())

    def test_69_disable_recharge_settings(self, vendor_token):
        r = requests.put(f"{BASE}/api/cpc/recharge/settings",
                         json={"enabled": False, "threshold": 20, "pack_id": "cpc-pack-50"},
                         headers=H(vendor_token), timeout=30)
        assert r.status_code == 200


# ---------- 5) RÉGRESSION ----------

class TestRegression:
    def test_80_cpc_packs_still_work(self):
        r = requests.get(f"{BASE}/api/cpc/packs", timeout=30)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()["items"]}
        assert {"cpc-pack-50", "cpc-pack-150", "cpc-pack-500"}.issubset(ids)

    def test_81_pack_checkout_returns_stripe_url(self, vendor_token):
        r = requests.post(f"{BASE}/api/cpc/checkout",
                          json={"pack_id": "cpc-pack-50", "origin_url": "https://example.com"},
                          headers=H(vendor_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout_url" in d
        assert "checkout.stripe.com" in d["checkout_url"]

    def test_82_consultations_tracking_still_works(self, buyer_token):
        r = requests.get(f"{BASE}/api/consultations/tracking", headers=H(buyer_token), timeout=30)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_83_cpc_me(self, vendor_token):
        r = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token), timeout=30)
        assert r.status_code == 200
        assert "balance" in r.json()


# ---------- CLEANUP ----------

class TestCleanup:
    def test_99_cleanup(self):
        client, db = _db()
        async def run():
            # consultations
            for k in ("cid_from_custom", "cid_from_red", "cid_transport", "cid_alert", "cid_cron"):
                cid = STATE.get(k)
                if not cid:
                    continue
                await db.consultations.delete_many({"id": cid})
                await db.consultation_entries.delete_many({"consultation_id": cid})
                await db.bids.delete_many({"consultation_id": cid})
                await db.consultation_audit.delete_many({"consultation_id": cid})
                await db.cpc_ledger.delete_many({"consultation_id": cid})
            # templates
            for k in ("custom_tid", "red_tid"):
                tid = STATE.get(k)
                if tid:
                    await db.consultation_templates.delete_many({"id": tid})
            # legal_matrix
            await db.legal_matrix.delete_many({"category": TEST_CAT})
            if STATE.get("red_cat"):
                await db.legal_matrix.delete_many({"category": STATE["red_cat"]})
            # fake subscription
            if STATE.get("sub_id"):
                await db.cpc_subscriptions.delete_many({"id": STATE["sub_id"]})
            if STATE.get("fake_invoice_id"):
                await db.cpc_purchases.delete_many({"id": f"subcpc-{STATE['fake_invoice_id']}"})
                await db.cpc_ledger.delete_many({"idempotency_key": f"subinv:{STATE['fake_invoice_id']}"})
            # recharge tokens
            if STATE.get("sub_user_id"):
                await db.cpc_recharge_tokens.delete_many({"user_id": STATE["sub_user_id"]})
        asyncio.run(run())
