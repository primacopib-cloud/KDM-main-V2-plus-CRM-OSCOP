"""
Iter 57 — Lot 4 fonctionnalités :
1) BACKEND Publication groupée : POST /api/admin/campaigns/{id}/publish-all
2) BACKEND Récap hebdo vendeur : send_weekly_recaps (Monday-only + idempotence)
3) BACKEND Filtres export compta : ?types= et ?email= sur /api/admin/cpc/export.csv|.pdf
4) BACKEND Régression notifications (inscription consultation ne casse pas + parrainage idempotent)

Aucun email réel envoyé — Brevo mocké.
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


def _fe_url():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _fe_url()).rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL manquant"

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PASS = "Demo2026!"
VENDOR_USER_ID = "user-vendor-pro"

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
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client, client[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS, portal="admin")


@pytest.fixture(scope="module")
def vendor_token():
    return _login(VENDOR_EMAIL, VENDOR_PASS)


# ─────────────────────────────────────────────────────────────────
# Helpers pour créer une consultation en statut VALIDEE
# ─────────────────────────────────────────────────────────────────

def _make_valid_consultation(atoken, title_suffix):
    """Crée une consultation BROUILLON → EN_VALIDATION → VALIDEE via API."""
    now = datetime.now(timezone.utc)
    opens = (now + timedelta(hours=1)).isoformat()
    closes = (now + timedelta(days=7)).isoformat()
    body = {
        "title": f"TEST_iter57 {title_suffix}",
        "type": "STANDARD",
        "procedure": "SCELLEE",
        "category": "transport",  # VERT dans legal_matrix
        "products": [{"name": "Test produit", "qty": 100, "unit": "u"}],
        "territories": ["GUADELOUPE"],
        "specs": "Test iter57",
        "max_rounds": 3,
        "opens_at": opens,
        "closes_at": closes,
    }
    r = requests.post(f"{BASE}/api/admin/consultations", json=body, headers=H(atoken), timeout=30)
    assert r.status_code == 200, f"create consultation: {r.status_code} {r.text}"
    c = r.json()
    cid = c["id"]
    # BROUILLON → EN_VALIDATION
    r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                      json={"to": "EN_VALIDATION"}, headers=H(atoken), timeout=30)
    assert r.status_code == 200, f"transition EN_VAL: {r.text}"
    # validate/commercial (STANDARD non-INTERTERRITORIALE + status non ORANGE → un seul suffit)
    r = requests.post(f"{BASE}/api/admin/consultations/{cid}/validate/commercial",
                      json={}, headers=H(atoken), timeout=30)
    assert r.status_code == 200, f"validate commercial: {r.text}"
    assert r.json().get("status") == "VALIDEE"
    return cid, c["ref"]


# ─────────────────────────────────────────────────────────────────
# 1) BACKEND Publication groupée
# ─────────────────────────────────────────────────────────────────

def test_1_publish_all_campaign(admin_token):
    # Créer campagne
    now = datetime.now(timezone.utc)
    opens = (now + timedelta(hours=1)).isoformat()
    closes = (now + timedelta(days=14)).isoformat()
    r = requests.post(f"{BASE}/api/admin/campaigns",
                      json={"name": "TEST_iter57 campagne", "opens_at": opens, "closes_at": closes},
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    camp_id = r.json()["id"]
    STATE["camp_id"] = camp_id

    # 2 lots VALIDEE + 1 lot BROUILLON
    v1, ref1 = _make_valid_consultation(admin_token, "V1")
    v2, ref2 = _make_valid_consultation(admin_token, "V2")

    # Un lot BROUILLON (ne passe pas EN_VALIDATION)
    now = datetime.now(timezone.utc)
    r = requests.post(f"{BASE}/api/admin/consultations", json={
        "title": "TEST_iter57 BROUILLON", "type": "STANDARD", "procedure": "SCELLEE",
        "category": "transport",
        "products": [{"name": "P", "qty": 1, "unit": "u"}],
        "territories": ["GUADELOUPE"], "specs": "b",
        "max_rounds": 3,
        "opens_at": (now + timedelta(hours=1)).isoformat(),
        "closes_at": (now + timedelta(days=7)).isoformat(),
    }, headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    brouillon_id = r.json()["id"]

    STATE["lot_ids"] = [v1, v2, brouillon_id]

    # Attach les 3 lots
    for lid in (v1, v2, brouillon_id):
        r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/attach",
                          json={"consultation_id": lid}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, f"attach {lid}: {r.text}"

    # publish-all
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/publish-all",
                      json={}, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["published"] == 2, f"expected published=2, got {data}"
    refs = {r_["ref"] for r_ in data["results"] if r_["ok"]}
    assert ref1 in refs and ref2 in refs

    # Vérifier lots PUBLIEE + BROUILLON toujours BROUILLON
    for lid in (v1, v2):
        r = requests.get(f"{BASE}/api/admin/consultations/{lid}", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "PUBLIEE", f"lot {lid} still {r.json()['status']}"
    r = requests.get(f"{BASE}/api/admin/consultations/{brouillon_id}", headers=H(admin_token), timeout=30)
    assert r.json()["status"] == "BROUILLON"

    # Re-appel publish-all → published=0 (tous déjà PUBLIEE)
    r = requests.post(f"{BASE}/api/admin/campaigns/{camp_id}/publish-all",
                      json={}, headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert r.json()["published"] == 0

    # Audit CAMPAIGN_PUBLISH_ALL
    async def check_audit():
        client, db = _mongo()
        try:
            evt = await db.audit_journal.find_one(
                {"event_type": "CAMPAIGN_PUBLISH_ALL", "payload.campaign_id": camp_id})
            assert evt is not None, "audit CAMPAIGN_PUBLISH_ALL manquant"
            assert evt["payload"]["published"] in (0, 2)
        finally:
            client.close()
    asyncio.get_event_loop().run_until_complete(check_audit())


def test_1_publish_all_forbidden_without_admin(vendor_token):
    r = requests.post(f"{BASE}/api/admin/campaigns/{STATE.get('camp_id', 'x')}/publish-all",
                      json={}, headers=H(vendor_token), timeout=30)
    assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────
# 2) BACKEND Récap hebdo
# ─────────────────────────────────────────────────────────────────

def test_2_weekly_recap_idempotence_and_scheduler_wiring():
    """Vérifie : (a) idempotence via weekly_recap_sent, (b) scheduler branché,
    (c) code path 'weekday != 0 → return 0'."""
    # (c) code review : la ligne 15 de vendor_weekly_recap.py fait `if now.weekday() != 0: return 0`
    src = open("/app/backend/vendor_weekly_recap.py").read()
    assert "if now.weekday() != 0:" in src and "return 0" in src.split("if now.weekday() != 0:")[1][:50]
    # (b) scheduler wiring
    sch = open("/app/backend/scheduler.py").read()
    assert "from vendor_weekly_recap import send_weekly_recaps" in sch
    assert "await send_weekly_recaps(_db)" in sch
    # (a) idempotence : send_weekly_recaps insère weekly_recap_sent et skip si déjà présent
    assert "weekly_recap_sent" in src and "find_one" in src

    # Test partiel réel : appeler la fonction. On est LUNDI (weekday==0).
    # Pour éviter d'envoyer un email réel, on pre-insert weekly_recap_sent pour vendor-pro
    # (déjà fait dans le setup module cf. tests précédents / DB actuelle), puis on mocke send_email.
    async def run():
        client, db = _mongo()
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            week = now.strftime("%G-W%V")
            weekday = now.weekday()

            # S'assurer que vendor-pro a bien un weekly_recap_sent pour cette semaine (idempotence)
            existing = await db.weekly_recap_sent.find_one({"user_id": VENDOR_USER_ID, "week": week})
            if not existing:
                await db.weekly_recap_sent.insert_one({
                    "user_id": VENDOR_USER_ID, "week": week,
                    "sent_at": now.isoformat(), "pre_inserted_by_test_iter57": True})

            # Mock send_email pour éviter tout envoi
            import brevo_service
            sent_calls = []
            orig = brevo_service.send_email
            async def _fake_send(**kwargs):
                sent_calls.append(kwargs)
                return {"ok": True}
            brevo_service.send_email = _fake_send
            try:
                import vendor_weekly_recap
                result = await vendor_weekly_recap.send_weekly_recaps(db)
            finally:
                brevo_service.send_email = orig

            if weekday != 0:
                assert result == 0, f"Hors lundi doit retourner 0, got {result}"
                assert len(sent_calls) == 0
            else:
                # Lundi : vendor-pro déjà présent dans weekly_recap_sent → doit être skip
                # Aucun autre vendor n'a de cpc_account (cf. setup) donc sent_calls=0
                accts_count = await db.cpc_accounts.count_documents({})
                # Compter les comptes non déjà envoyés
                pending = 0
                async for a in db.cpc_accounts.find({}, {"_id": 0, "user_id": 1}):
                    if not await db.weekly_recap_sent.find_one({"user_id": a["user_id"], "week": week}):
                        pending += 1
                assert result == pending, f"Attendu {pending} emails (comptes sans weekly_recap_sent), got {result}"
                # Idempotence : vendor-pro toujours 1 seule entrée pour cette semaine
                cnt = await db.weekly_recap_sent.count_documents(
                    {"user_id": VENDOR_USER_ID, "week": week})
                assert cnt == 1, f"vendor-pro weekly_recap_sent count={cnt}, attendu 1 (idempotence)"
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(run())


# ─────────────────────────────────────────────────────────────────
# 3) BACKEND Filtres export compta
# ─────────────────────────────────────────────────────────────────

def test_3_export_forbidden_without_admin(vendor_token):
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv", headers=H(vendor_token), timeout=30)
    assert r.status_code == 403
    r = requests.get(f"{BASE}/api/admin/cpc/export.pdf", headers=H(vendor_token), timeout=30)
    assert r.status_code == 403


def test_3_export_csv_types_and_email_filters(admin_token):
    """Créer 1 débit réel CONSOMMATION en inscrivant vendor-pro à une consultation ouverte."""
    # 1. Créer consultation VALIDEE puis publier + ouvrir inscriptions
    cid, ref = _make_valid_consultation(admin_token, "EXPORT")
    STATE["export_lot_id"] = cid
    # PUBLIEE (publish endpoint)
    r = requests.post(f"{BASE}/api/admin/consultations/{cid}/publish",
                      json={}, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    # PUBLIEE → INSCRIPTIONS_OUVERTES
    r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                      json={"to": "INSCRIPTIONS_OUVERTES"}, headers=H(admin_token), timeout=30)
    assert r.status_code == 200

    # 2. Vendor s'inscrit → débit -20 CPC
    v_tok = _login(VENDOR_EMAIL, VENDOR_PASS)
    # Récupérer solde avant
    r = requests.get(f"{BASE}/api/vendor/cpc/balance", headers=H(v_tok), timeout=30)
    balance_before = r.json().get("balance") if r.status_code == 200 else None
    STATE["balance_before"] = balance_before

    r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                      json={"accept_rules": True}, headers=H(v_tok), timeout=30)
    assert r.status_code == 200, f"register: {r.status_code} {r.text}"
    STATE["registered"] = True

    # 3. Export CSV avec ?types=CONSOMMATION → doit contenir la ligne
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv?types=CONSOMMATION",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    lines = [ln for ln in text.strip().split("\n") if ln]
    assert lines[0].startswith("Type;Date;Compte")
    data_lines = lines[1:]
    assert all(ln.split(";")[0] == "CONSOMMATION" for ln in data_lines), \
        f"types=CONSOMMATION doit filtrer, got: {data_lines[:3]}"
    assert len(data_lines) >= 1, "au moins 1 ligne CONSOMMATION attendue"

    # 4. Export CSV avec ?email=vendor-pro → doit contenir la ligne
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv?email={VENDOR_EMAIL}",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    data_lines = [ln for ln in text.strip().split("\n")[1:] if ln]
    for ln in data_lines:
        cells = ln.split(";")
        assert cells[2].lower() == VENDOR_EMAIL.lower(), f"email filter fail: {ln}"

    # 5. Export CSV avec ?types=PACK → aucune ligne CONSOMMATION
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv?types=PACK",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    data_lines = [ln for ln in text.strip().split("\n")[1:] if ln]
    for ln in data_lines:
        assert ln.split(";")[0] != "CONSOMMATION"

    # 6. types invalide → CSV avec header seulement, pas 500
    r = requests.get(f"{BASE}/api/admin/cpc/export.csv?types=XYZ",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    lines = [ln for ln in text.strip().split("\n") if ln]
    assert len(lines) == 1, f"types=XYZ doit renvoyer que le header, got {len(lines)} lignes"

    # 7. PDF avec filtres → 200 + %PDF
    r = requests.get(f"{BASE}/api/admin/cpc/export.pdf?types=CONSOMMATION&email={VENDOR_EMAIL}",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ─────────────────────────────────────────────────────────────────
# 4) BACKEND Régression : parrainage déjà payé → pas de re-crédit
# ─────────────────────────────────────────────────────────────────

def test_4_referral_no_recredit_for_existing_vendor(admin_token):
    """L'inscription vendor-pro (fait test 3) ne doit pas déclencher un re-crédit filleul.
    Ici on vérifie juste que vendor-pro n'a pas reçu de PROMO_GRANT de type referral-welcome."""
    async def check():
        client, db = _mongo()
        try:
            # Rechercher un mouvement referral-welcome pour vendor-pro (filleul) sur la dernière minute
            recent = await db.cpc_ledger.find_one({
                "user_id": VENDOR_USER_ID,
                "idempotency_key": {"$regex": "^referral-welcome:"}})
            # vendor-pro peut avoir un ancien referral-welcome (compte de test)
            # → on vérifie qu'un NOUVEAU n'a pas été inséré à cette date
            now = datetime.now(timezone.utc)
            recent_new = await db.cpc_ledger.find_one({
                "user_id": VENDOR_USER_ID,
                "idempotency_key": {"$regex": "^referral-welcome:"},
                "created_at": {"$gte": (now - timedelta(minutes=5)).isoformat()}})
            assert recent_new is None, f"Nouveau referral-welcome inattendu: {recent_new}"
        finally:
            client.close()
    asyncio.get_event_loop().run_until_complete(check())


# ─────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────

def test_zz_cleanup(admin_token):
    """Restaure vendor-pro à 60 CPC + supprime consultations/campagnes/entries de test."""
    # +20 correction si vendor s'est inscrit (débit -20 CPC)
    if STATE.get("registered"):
        r = requests.post(f"{BASE}/api/admin/cpc/correction", json={
            "user_email": VENDOR_EMAIL, "qty": 20,
            "reason": "Restauration après test iter57 (débit inscription -20)",
            "reference": "TEST_iter57_CLEANUP"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    async def clean():
        client, db = _mongo()
        try:
            # Supprimer consultations TEST_iter57 + leurs entries
            cursor = db.consultations.find({"title": {"$regex": "^TEST_iter57"}}, {"_id": 0, "id": 1})
            cids = [c["id"] async for c in cursor]
            if cids:
                await db.consultation_entries.delete_many({"consultation_id": {"$in": cids}})
                await db.consultations.delete_many({"id": {"$in": cids}})
            # Supprimer campagne test
            await db.campaigns.delete_many({"name": {"$regex": "^TEST_iter57"}})
            # Supprimer weekly_recap_sent pré-insérés par le test (garder ceux légitimes)
            await db.weekly_recap_sent.delete_many({"pre_inserted_by_test_iter57": True})
            # Supprimer les mouvements CPC liés aux consultations de test
            if cids:
                await db.cpc_ledger.delete_many({"consultation_id": {"$in": cids}})
            # Vérifier solde vendor-pro
            acct = await db.cpc_accounts.find_one({"user_id": VENDOR_USER_ID}, {"_id": 0, "cpc_balance": 1})
            print(f"vendor-pro balance post-cleanup: {acct.get('cpc_balance') if acct else 'N/A'}")
        finally:
            client.close()
    asyncio.get_event_loop().run_until_complete(clean())
