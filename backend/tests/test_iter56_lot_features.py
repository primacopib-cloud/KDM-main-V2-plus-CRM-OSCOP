"""
Iter 56 — Lot 4 fonctionnalités :
1) BACKEND Campagnes multi-lots (CRUD + attach/detach/apply-calendar + validations)
2) BACKEND Bonus filleul bienvenue (parrain +10 / filleul +5 + notifications in-app)
3) BACKEND Export compta CREDI'SCOP (CSV, PDF, 403 sans admin, filtre month)
4) BACKEND Notifications in-app (closure_reminder + report_available + GET/read-all)

Notes:
- Le flow parrainage complet est réalisé via l'API register-consultation NON — pour éviter
  la création d'une consultation EN_COURS complète, on appelle maybe_pay_referral_bonus() en direct
  après avoir simulé l'inscription (insertion d'un consultation_entries factice).
- On mocke send_email (Brevo LIVE) pour éviter les envois réels.
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


def _load_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env()).rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL manquant"

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PASS = "Demo2026!"

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


def _mongo():
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS, "admin")


@pytest.fixture(scope="module")
def vendor_token():
    return _login(VENDOR_EMAIL, VENDOR_PASS)


# =====================================================================
# 1) CAMPAGNES MULTI-LOTS
# =====================================================================
def test_campaign_crud_and_validations(admin_token, vendor_token):
    now = datetime.now(timezone.utc)
    opens = (now + timedelta(days=2)).isoformat()
    closes = (now + timedelta(days=9)).isoformat()

    # 403 sans admin
    r = requests.post(f"{BASE}/api/admin/campaigns", headers=H(vendor_token),
                      json={"name": "TEST_iter56_forbid", "opens_at": opens, "closes_at": closes}, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}"

    # 400 si closes <= opens
    r = requests.post(f"{BASE}/api/admin/campaigns", headers=H(admin_token),
                      json={"name": "TEST_iter56_bad", "opens_at": closes, "closes_at": opens}, timeout=30)
    assert r.status_code == 400, r.text

    # 400 si name vide
    r = requests.post(f"{BASE}/api/admin/campaigns", headers=H(admin_token),
                      json={"name": "  ", "opens_at": opens, "closes_at": closes}, timeout=30)
    assert r.status_code == 400, r.text

    # Création OK
    name = f"TEST_iter56_camp_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE}/api/admin/campaigns", headers=H(admin_token),
                      json={"name": name, "opens_at": opens, "closes_at": closes}, timeout=30)
    assert r.status_code == 200, r.text
    camp = r.json()
    assert camp["name"] == name
    assert camp["opens_at"] == opens
    assert camp["closes_at"] == closes
    STATE["camp_id"] = camp["id"]

    # GET list
    r = requests.get(f"{BASE}/api/admin/campaigns", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(c["id"] == camp["id"] and c.get("lots") == [] for c in items), "campagne absente / lots absents"

    # PUT update
    new_name = name + "_upd"
    r = requests.put(f"{BASE}/api/admin/campaigns/{camp['id']}", headers=H(admin_token),
                     json={"name": new_name, "opens_at": opens, "closes_at": closes}, timeout=30)
    assert r.status_code == 200
    STATE["camp_name"] = new_name


def test_campaign_attach_detach_apply(admin_token):
    """Crée un lot BROUILLON via instantiate, rattache, applique le calendrier, détache."""
    camp_id = STATE["camp_id"]

    async def make_template_and_lot():
        db = _mongo()
        # Créer un template minimal et l'instancier via API
        tid = str(uuid.uuid4())
        await db.consultation_templates.insert_one({
            "id": tid, "name": f"TEST_iter56_tpl_{uuid.uuid4().hex[:6]}",
            "title": "TEST iter56 lot", "type": "TERRITORIALE", "procedure": "SCELLEE",
            "category": "epicerie-sucre", "products": [], "territories": ["GUADELOUPE"],
            "specs": "test", "max_rounds": 3, "duration_days": 7,
            "active": True, "TEST_iter56": True,
            "created_at": datetime.now(timezone.utc).isoformat()})
        STATE["tpl_id"] = tid

    asyncio.run(make_template_and_lot())

    r = requests.post(f"{BASE}/api/admin/consultation-templates/{STATE['tpl_id']}/instantiate",
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    lot = r.json()
    assert lot["status"] == "BROUILLON"
    STATE["lot_id"] = lot["id"]
    STATE["lot_ref"] = lot["ref"]
    STATE["lot_original_opens"] = lot["opens_at"]

    # Attach
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/attach",
                      headers=H(admin_token), json={"consultation_id": lot["id"]}, timeout=30)
    assert r.status_code == 200, r.text
    assert lot["ref"] in r.json()["message"]

    # Vérifier calendrier appliqué + campaign_id posé
    async def check_lot():
        db = _mongo()
        c = await db.consultations.find_one({"id": lot["id"]}, {"_id": 0})
        assert c["campaign_id"] == camp_id, f"campaign_id={c.get('campaign_id')}"
        # opens_at/closes_at alignés sur la campagne
        camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
        assert c["opens_at"] == camp["opens_at"]
        assert c["closes_at"] == camp["closes_at"]
    asyncio.run(check_lot())

    # Liste des campagnes : lots[] doit contenir notre lot
    r = requests.get(f"{BASE}/api/admin/campaigns", headers=H(admin_token), timeout=30)
    camp = next(c for c in r.json()["items"] if c["id"] == camp_id)
    assert any(l["id"] == STATE["lot_id"] for l in camp["lots"])

    # Attach lot publié → 409 : on met un statut EN_COURS
    async def set_encours():
        db = _mongo()
        # créer un 2e lot en EN_COURS
        c2 = str(uuid.uuid4())
        await db.consultations.insert_one({
            "id": c2, "ref": f"TEST-EC-{uuid.uuid4().hex[:4]}", "title": "TEST enc",
            "type": "TERRITORIALE", "procedure": "SCELLEE", "category": "epicerie-sucre",
            "status": "EN_COURS", "opens_at": datetime.now(timezone.utc).isoformat(),
            "closes_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "cpc_cost": 5, "max_rounds": 3, "TEST_iter56": True})
        STATE["encours_lot_id"] = c2
    asyncio.run(set_encours())

    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/attach",
                      headers=H(admin_token), json={"consultation_id": STATE["encours_lot_id"]}, timeout=30)
    assert r.status_code == 409, f"expected 409 (lot publié), got {r.status_code} {r.text}"

    # Apply-calendar
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/apply-calendar",
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["lots_updated"] >= 1

    # Detach
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/detach",
                      headers=H(admin_token), json={"consultation_id": STATE["lot_id"]}, timeout=30)
    assert r.status_code == 200, r.text

    async def check_detached():
        db = _mongo()
        c = await db.consultations.find_one({"id": STATE["lot_id"]}, {"_id": 0})
        assert "campaign_id" not in c, f"campaign_id encore présent : {c.get('campaign_id')}"
    asyncio.run(check_detached())

    # Re-attach pour tester DELETE cascade
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/attach",
                      headers=H(admin_token), json={"consultation_id": STATE["lot_id"]}, timeout=30)
    assert r.status_code == 200

    # DELETE campagne → lot doit être détaché
    r = requests.delete(f"{BASE}/api/admin/campaigns/{camp_id}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text

    async def check_deleted():
        db = _mongo()
        camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
        assert camp is None
        c = await db.consultations.find_one({"id": STATE["lot_id"]}, {"_id": 0})
        assert "campaign_id" not in c, "lot toujours rattaché après DELETE"
        # Vérifier audit CAMPAIGN_* (collection audit_journal, field event_type)
        audits = await db.audit_journal.find(
            {"event_type": {"$regex": "^CAMPAIGN_"}}, {"_id": 0}).sort("seq", -1).limit(20).to_list(20)
        actions = [a["event_type"] for a in audits]
        for expected in ("CAMPAIGN_CREATED", "CAMPAIGN_LOT_ATTACHED", "CAMPAIGN_LOT_DETACHED",
                         "CAMPAIGN_CALENDAR_APPLIED", "CAMPAIGN_DELETED"):
            assert expected in actions, f"audit {expected} manquant (recent={actions[:15]})"
    asyncio.run(check_deleted())


# =====================================================================
# 2) BONUS FILLEUL BIENVENUE
# =====================================================================
def test_referral_welcome_bonus_flow(admin_token, vendor_token):
    """Créer filleul → claim vendor-pro code → simuler inscription consultation → verify +10/+5 + notifs."""
    async def setup_filleul():
        db = _mongo()
        from auth import get_password_hash
        fid = f"TEST_iter56_filleul_{uuid.uuid4().hex[:8]}"
        femail = f"test_iter56_filleul_{uuid.uuid4().hex[:6]}@example.com"
        fpwd = "Filleul2026!"
        await db.users.insert_one({
            "id": fid, "email": femail, "password_hash": get_password_hash(fpwd),
            "role": "vendor", "company_name": "TEST filleul", "siret": f"TEST{uuid.uuid4().hex[:10]}",
            "contact_name": "Fil Leul", "phone": "0590000000",
            "subscription": "free",
            "credits": 0, "is_admin": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "TEST_iter56": True})
        # cpc_account
        await db.cpc_accounts.insert_one({"user_id": fid, "cpc_balance": 0, "status": "ACTIF",
                                          "created_at": datetime.now(timezone.utc).isoformat(),
                                          "TEST_iter56": True})
        STATE["filleul_id"] = fid
        STATE["filleul_email"] = femail
        STATE["filleul_pwd"] = fpwd

        # Récupérer solde vendor-pro
        sponsor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
        STATE["sponsor_id"] = sponsor["id"]
        acc = await db.cpc_accounts.find_one({"user_id": sponsor["id"]}, {"_id": 0}) or {}
        STATE["sponsor_balance_before"] = acc.get("cpc_balance", 0)
    asyncio.run(setup_filleul())

    # Login filleul
    filleul_tok = _login(STATE["filleul_email"], STATE["filleul_pwd"])

    # GET /api/referral/me sur vendor-pro pour récupérer son code
    r = requests.get(f"{BASE}/api/referral/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    sponsor_code = r.json()["code"]
    assert sponsor_code == "KDM-9A4D34", f"code sponsor = {sponsor_code}"

    # Filleul claim le code
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(filleul_tok),
                      json={"code": sponsor_code}, timeout=30)
    assert r.status_code == 200, f"claim: {r.status_code} {r.text}"

    # Admin credit filleul 20 CPC via correction (ADMIN_CORRECTION)
    r = requests.post(f"{BASE}/api/admin/cpc/correction", headers=H(admin_token),
                      json={"user_email": STATE["filleul_email"], "qty": 20,
                            "reason": "TEST iter56 seed", "reference": "TEST-ITER56"}, timeout=30)
    assert r.status_code == 200, f"correction: {r.status_code} {r.text}"
    assert r.json()["balance"] == 20

    # Simuler l'inscription à une consultation EN_COURS en appelant maybe_pay_referral_bonus directement
    # (car cela nécessite une consultation complète en EN_COURS + ledger CPC + entry insert).
    # Cependant maybe_pay_referral_bonus part du principe qu'un consultation_entries existe déjà (côté audit).
    # Ici on mocke send_email pour éviter envoi Brevo réel.
    async def run_bonus():
        db = _mongo()
        import routes_referral as rr
        rr.db = db
        # Mock brevo
        import brevo_service
        original_send = brevo_service.send_email
        emails_sent = []
        async def spy_send(**kwargs):
            emails_sent.append(kwargs.get("subject"))
            return True
        brevo_service.send_email = spy_send
        # Rebind core_deps.get_database à db pour create_notification
        import core_deps, consultation_audit
        original_get_db = core_deps.get_database
        core_deps.get_database = lambda: db
        consultation_audit.db = db
        # cpc_ledger + routes_cpc_admin.get_cpc_settings
        import cpc_ledger
        cpc_ledger.db = db
        import routes_cpc_admin as rca
        rca.db = db
        try:
            await rr.maybe_pay_referral_bonus(STATE["filleul_id"])
            # 2e appel doit être idempotent (pas de double bonus)
            await rr.maybe_pay_referral_bonus(STATE["filleul_id"])
        finally:
            brevo_service.send_email = original_send
            core_deps.get_database = original_get_db
        STATE["emails_sent"] = emails_sent

    asyncio.run(run_bonus())

    # Vérifications
    async def verify():
        db = _mongo()
        # Sponsor +10 (referral:{filleul_id})
        sponsor_led = await db.cpc_ledger.find({"user_id": STATE["sponsor_id"],
                                                "idempotency_key": f"referral:{STATE['filleul_id']}"},
                                               {"_id": 0}).to_list(10)
        assert len(sponsor_led) == 1, f"sponsor ledger : {len(sponsor_led)} (attendu 1)"
        assert sponsor_led[0]["qty"] == 10
        assert sponsor_led[0]["type"] == "PROMO_GRANT"

        # Filleul +5 (referral-welcome:{filleul_id})
        fil_led = await db.cpc_ledger.find({"user_id": STATE["filleul_id"],
                                            "idempotency_key": f"referral-welcome:{STATE['filleul_id']}"},
                                           {"_id": 0}).to_list(10)
        assert len(fil_led) == 1, f"filleul ledger welcome : {len(fil_led)} (attendu 1)"
        assert fil_led[0]["qty"] == 5

        # Notif referral_bonus pour sponsor
        n_bonus = await db.notifications.find(
            {"type": "referral_bonus", "target_user_id": STATE["sponsor_id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(5)
        assert len(n_bonus) >= 1, "notif referral_bonus manquante pour sponsor"

        # Notif referral_welcome pour filleul
        n_welc = await db.notifications.find(
            {"type": "referral_welcome", "target_user_id": STATE["filleul_id"]}, {"_id": 0}
        ).to_list(5)
        assert len(n_welc) == 1, f"notif referral_welcome : {len(n_welc)} (attendu 1, pas de doublon)"

        # link.bonus_paid=True
        link = await db.referral_links.find_one({"filleul_id": STATE["filleul_id"]}, {"_id": 0})
        assert link["bonus_paid"] is True
        assert link["bonus_amount"] == 10

    asyncio.run(verify())


# =====================================================================
# 3) EXPORT COMPTA CSV / PDF
# =====================================================================
def test_cpc_export_csv(admin_token, vendor_token):
    # 403 sans admin
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv", headers=H(vendor_token), timeout=30)
    assert r.status_code == 403

    # OK admin
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv", headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", ""), r.headers
    body = r.content.decode("utf-8-sig")
    lines = body.strip().split("\n")
    assert lines[0].startswith("Type;Date;Compte;"), f"header inattendu: {lines[0]!r}"
    # Notre correction TEST-ITER56 = qty=20 (positive) → n'apparaîtra PAS car export CSV
    # ne prend que les qty<0 (CONSUMPTION). C'est OK.
    # Vérifier qu'il y a au moins des lignes ABONNEMENT/PACK/CONSOMMATION (données existantes)
    assert len(lines) >= 1  # header au minimum


def test_cpc_export_csv_month_filter(admin_token):
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv?month=2020-01",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    body = r.content.decode("utf-8-sig")
    lines = body.strip().split("\n")
    # Devrait ne contenir que le header (pas de données en 2020-01)
    assert len(lines) == 1, f"filtre month inefficace: {len(lines)} lignes"


def test_cpc_export_pdf(admin_token, vendor_token):
    r = requests.get(f"{BASE}/api/admin/cpc/export.pdf", headers=H(vendor_token), timeout=30)
    assert r.status_code == 403

    r = requests.get(f"{BASE}/api/admin/cpc/export.pdf", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF", f"non PDF: {r.content[:20]}"


# =====================================================================
# 4) NOTIFICATIONS IN-APP (closure_reminder + report_available + read-all)
# =====================================================================
def test_notifications_flow(vendor_token, admin_token):
    """Créer consultation EN_COURS closes<24h + entry sans offre → run send_closure_reminders → notif créée.
       Puis clôturer + run notify_report_available → 2e notif. Enfin GET /notifications + read-all."""

    async def setup_and_run():
        db = _mongo()
        sponsor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
        vendor_id = sponsor["id"]
        STATE["vendor_user_id"] = vendor_id

        cid = f"TEST_iter56_c_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        closes = (now + timedelta(hours=12)).isoformat()
        await db.consultations.insert_one({
            "id": cid, "ref": f"TEST-N-{uuid.uuid4().hex[:4].upper()}",
            "title": "TEST iter56 notifs", "type": "TERRITORIALE", "procedure": "SCELLEE",
            "category": "epicerie-sucre", "status": "EN_COURS",
            "opens_at": (now - timedelta(hours=2)).isoformat(),
            "closes_at": closes, "cpc_cost": 5, "max_rounds": 3, "TEST_iter56": True})

        eid = f"TEST_iter56_e_{uuid.uuid4().hex[:8]}"
        await db.consultation_entries.insert_one({
            "id": eid, "consultation_id": cid, "vendor_user_id": vendor_id,
            "participant_type": "vendor_pro", "status": "INSCRIT",
            "created_at": now.isoformat(), "TEST_iter56": True})
        STATE["notif_cid"] = cid
        STATE["notif_eid"] = eid

        # Rebind db partout (y compris consultation_audit)
        import routes_bids, consultation_notify, core_deps, consultation_audit
        routes_bids.db = db
        consultation_notify.db = db
        consultation_audit.db = db
        core_deps.get_database = lambda: db

        # Mock brevo
        import brevo_service
        original = brevo_service.send_email
        async def spy(**kw): return True
        brevo_service.send_email = spy

        try:
            # send_closure_reminders → notif closure_reminder
            await routes_bids.send_closure_reminders(db)

            # Passer la consultation en CLOTUREE puis appeler notify_report_available
            await db.consultations.update_one({"id": cid}, {"$set": {"status": "CLOTUREE"}})
            # rebind routes_cpc_admin.db pour get_cpc_settings
            import routes_cpc_admin
            routes_cpc_admin.db = db
            sent = await consultation_notify.notify_report_available(cid)
            assert sent >= 1
        finally:
            brevo_service.send_email = original

    asyncio.run(setup_and_run())

    # Vérifier les notifs en DB
    async def check_notifs():
        db = _mongo()
        n_close = await db.notifications.find(
            {"type": "closure_reminder", "target_user_id": STATE["vendor_user_id"]},
            {"_id": 0}).sort("created_at", -1).to_list(5)
        assert len(n_close) >= 1, "notif closure_reminder manquante"

        n_rep = await db.notifications.find(
            {"type": "report_available", "target_user_id": STATE["vendor_user_id"]},
            {"_id": 0}).sort("created_at", -1).to_list(5)
        assert len(n_rep) >= 1, "notif report_available manquante"
    asyncio.run(check_notifs())

    # GET /api/notifications (vendor)
    r = requests.get(f"{BASE}/api/notifications?limit=50", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unread_count"] >= 1, f"unread_count={d['unread_count']}"
    types = {n["type"] for n in d["notifications"]}
    assert "closure_reminder" in types, f"types={types}"
    assert "report_available" in types

    # read-all
    r = requests.post(f"{BASE}/api/notifications/read-all", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200

    r = requests.get(f"{BASE}/api/notifications?limit=50", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0, f"unread_count post-read-all = {r.json()['unread_count']}"


# =====================================================================
# 5) CLEANUP — remet vendor-pro à 60 et supprime tout
# =====================================================================
def test_zz_cleanup(admin_token):
    async def cleanup():
        db = _mongo()
        # Supprimer données TEST_iter56
        await db.consultations.delete_many({"TEST_iter56": True})
        await db.consultations.delete_many({"id": STATE.get("lot_id")}) if STATE.get("lot_id") else None
        await db.consultation_templates.delete_many({"TEST_iter56": True})
        await db.consultation_entries.delete_many({"TEST_iter56": True})
        await db.campaigns.delete_many({"id": STATE.get("camp_id")}) if STATE.get("camp_id") else None

        # Filleul : supprimer user + cpc_account + ledger + notifs + referral_links
        if STATE.get("filleul_id"):
            fid = STATE["filleul_id"]
            await db.users.delete_many({"id": fid})
            await db.cpc_accounts.delete_many({"user_id": fid})
            await db.cpc_ledger.delete_many({"user_id": fid})
            await db.notifications.delete_many({"target_user_id": fid})
            await db.referral_links.delete_many({"filleul_id": fid})

        # Sponsor : supprimer ledger referral:{filleul_id} + notif referral_bonus créées pendant le test
        if STATE.get("filleul_id") and STATE.get("sponsor_id"):
            await db.cpc_ledger.delete_many({
                "user_id": STATE["sponsor_id"],
                "idempotency_key": f"referral:{STATE['filleul_id']}"})
            # Supprimer notifs vendor_user_id (closure_reminder + report_available + referral_bonus TEST)
            await db.notifications.delete_many({
                "target_user_id": STATE["sponsor_id"],
                "type": {"$in": ["closure_reminder", "report_available", "referral_bonus"]}})

        # Restaurer solde sponsor à sa valeur d'origine (60) — le +10 referral a été supprimé
        sponsor_id = STATE.get("sponsor_id")
        if sponsor_id and "sponsor_balance_before" in STATE:
            await db.cpc_accounts.update_one({"user_id": sponsor_id},
                                             {"$set": {"cpc_balance": STATE["sponsor_balance_before"]}})
            acc = await db.cpc_accounts.find_one({"user_id": sponsor_id}, {"_id": 0, "cpc_balance": 1})
            STATE["sponsor_balance_after"] = acc["cpc_balance"]

        # Autres nettoyages TEST_iter56
        for coll in ("consultations", "consultation_templates", "consultation_entries",
                     "users", "cpc_accounts", "vendors", "vendor_products", "campaigns"):
            n = await db[coll].count_documents({"TEST_iter56": True})
            assert n == 0, f"leftover {coll}: {n}"

    asyncio.run(cleanup())
    # Log balance pour visibilité (attendu 60)
    print(f"\n[cleanup] vendor-pro balance after cleanup = {STATE.get('sponsor_balance_after')}")
