"""
Iter 53 — Validation du lot :
1) Score de Liquidité admin (routes_consultations /liquidity)
2) Benchmark Catégorie vendeur (routes_benchmark)
3) Récurrence templates (routes_consultation_templates /recurrence + run_recurring_templates)
4) Settings admin CPC (benchmark_cost = 15)
5) Régression rapide : /api/cpc/checkout, /api/cpc/me, /api/consultations/tracking
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

TEST_CAT = f"test-iter53-{uuid.uuid4().hex[:6]}"
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


def _mongo():
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ============================================================
# 4) Settings admin CPC — benchmark_cost=15
# ============================================================
def test_settings_contains_benchmark_cost_15(admin_token):
    r = requests.get(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "benchmark_cost" in data
    assert data["benchmark_cost"] == 15
    # Sauvegarder l'état actuel pour restauration
    STATE["settings_orig"] = data


def test_settings_put_invalid_benchmark_cost_rejected(admin_token):
    orig = STATE.get("settings_orig", {"standard_cost": 20, "interterritorial_cost": 40,
                                        "report_cost": 10, "benchmark_cost": 15,
                                        "low_balance_alert": True})
    payload = {k: orig.get(k) for k in ["standard_cost", "interterritorial_cost", "report_cost",
                                         "benchmark_cost", "low_balance_alert"]}
    payload["benchmark_cost"] = 0
    r = requests.put(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), json=payload, timeout=30)
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"

    payload["benchmark_cost"] = -5
    r = requests.put(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), json=payload, timeout=30)
    assert r.status_code == 400


def test_settings_put_valid_ok(admin_token):
    orig = STATE.get("settings_orig")
    payload = {k: orig.get(k) for k in ["standard_cost", "interterritorial_cost", "report_cost",
                                         "benchmark_cost", "low_balance_alert"]}
    # remets bien à 15 pour la suite
    payload["benchmark_cost"] = 15
    r = requests.put(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), json=payload, timeout=30)
    assert r.status_code == 200


# ============================================================
# 1) Score de Liquidité
# ============================================================
def test_liquidity_score_via_instantiate(admin_token):
    """Instancie tpl-emballage-enchere → BROUILLON, puis GET /liquidity."""
    # S'assurer que le template existe (list appelle ensure_default_templates)
    r = requests.get(f"{BASE}/api/admin/consultation-templates", headers=H(admin_token), timeout=30)
    assert r.status_code == 200

    r = requests.post(f"{BASE}/api/admin/consultation-templates/tpl-emballage-enchere/instantiate",
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    cons = r.json()
    cid = cons["id"]
    STATE["cid_liquidity"] = cid
    assert cons["category"] == "emballage"
    assert cons["status"] == "BROUILLON"

    r = requests.get(f"{BASE}/api/admin/consultations/{cid}/liquidity",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("eligible_vendors", "historical_participants", "recommendation", "message"):
        assert k in d, f"missing key {k}"
    assert d["recommendation"] in ("NEGOCIATION_DIRECTE", "SCELLEE", "ENCHERE_POSSIBLE")


def test_liquidity_thresholds_with_seeded_vendors(admin_token):
    """Insère des vendor_products factices pour tester les 3 seuils (0/1, 2, ≥3)."""
    async def run():
        db = _mongo()
        # nouvelle consultation dédiée avec catégorie unique
        cat = f"iter53-liq-{uuid.uuid4().hex[:6]}"
        # créer un template temporaire pour cette cat
        tpl_body = {
            "name": f"TEST_iter53 liq {cat}",
            "title": "TEST liquidité", "type": "STANDARD", "procedure": "SCELLEE",
            "category": cat, "products": [], "territories": ["GUADELOUPE"],
            "specs": "test", "max_rounds": 3, "duration_days": 7
        }
        r = requests.post(f"{BASE}/api/admin/consultation-templates",
                          headers=H(admin_token), json=tpl_body, timeout=30)
        assert r.status_code == 200, r.text
        tpl_id = r.json()["id"]
        STATE["tpl_liq"] = tpl_id
        STATE["cat_liq"] = cat

        async def instantiate():
            rr = requests.post(f"{BASE}/api/admin/consultation-templates/{tpl_id}/instantiate",
                               headers=H(admin_token), timeout=30)
            assert rr.status_code == 200, rr.text
            return rr.json()["id"]

        async def get_liq(cid):
            rr = requests.get(f"{BASE}/api/admin/consultations/{cid}/liquidity",
                              headers=H(admin_token), timeout=30)
            assert rr.status_code == 200, rr.text
            return rr.json()

        # ---- 0 vendors ----
        cid0 = await instantiate()
        d = await get_liq(cid0)
        assert d["eligible_vendors"] == 0
        assert d["recommendation"] == "NEGOCIATION_DIRECTE"

        # ---- 1 vendor ----
        vid1 = f"TEST_iter53_v1_{uuid.uuid4().hex[:6]}"
        await db.vendors.insert_one({"id": vid1, "email": f"TEST_iter53_{vid1}@ex.fr",
                                     "siret": f"TEST{uuid.uuid4().hex[:10]}",
                                     "TEST_iter53": True})
        await db.vendor_products.insert_one({"id": f"vp_{uuid.uuid4().hex}",
                                              "vendor_id": vid1, "category": cat,
                                              "TEST_iter53": True})
        cid1 = await instantiate()
        d = await get_liq(cid1)
        assert d["eligible_vendors"] == 1, d
        assert d["recommendation"] == "NEGOCIATION_DIRECTE"

        # ---- 2 vendors ----
        vid2 = f"TEST_iter53_v2_{uuid.uuid4().hex[:6]}"
        await db.vendors.insert_one({"id": vid2, "email": f"TEST_iter53_{vid2}@ex.fr",
                                     "siret": f"TEST{uuid.uuid4().hex[:10]}",
                                     "TEST_iter53": True})
        await db.vendor_products.insert_one({"id": f"vp_{uuid.uuid4().hex}",
                                              "vendor_id": vid2, "category": cat,
                                              "TEST_iter53": True})
        cid2 = await instantiate()
        d = await get_liq(cid2)
        assert d["eligible_vendors"] == 2, d
        assert d["recommendation"] == "SCELLEE"

        # ---- 3 vendors ----
        vid3 = f"TEST_iter53_v3_{uuid.uuid4().hex[:6]}"
        await db.vendors.insert_one({"id": vid3, "email": f"TEST_iter53_{vid3}@ex.fr",
                                     "siret": f"TEST{uuid.uuid4().hex[:10]}",
                                     "TEST_iter53": True})
        await db.vendor_products.insert_one({"id": f"vp_{uuid.uuid4().hex}",
                                              "vendor_id": vid3, "category": cat,
                                              "TEST_iter53": True})
        cid3 = await instantiate()
        d = await get_liq(cid3)
        assert d["eligible_vendors"] == 3, d
        assert d["recommendation"] == "ENCHERE_POSSIBLE"

        STATE["liq_cids"] = [cid0, cid1, cid2, cid3]

    asyncio.run(run())


# ============================================================
# 2) Benchmark Catégorie
# ============================================================
def test_benchmark_404_when_no_closed(vendor_token):
    r = requests.post(f"{BASE}/api/consultations-benchmark/{TEST_CAT}",
                      headers=H(vendor_token), timeout=30)
    assert r.status_code == 404, r.text


def test_benchmark_debit_and_idempotency(admin_token, vendor_token):
    """Crée une consultation clôturée dans une catégorie de test avec 1 offre valide, puis benchmark."""
    async def setup():
        db = _mongo()
        cat = TEST_CAT
        # Get vendor user_id
        vu = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
        assert vu, "vendor introuvable"
        vendor_uid = vu["id"]
        # solde initial
        acc = await db.cpc_accounts.find_one({"user_id": vendor_uid}, {"_id": 0, "balance": 1})
        STATE["balance_before"] = (acc or {}).get("balance", 0)

        # Créer une consultation CLOTUREE directement en DB
        cid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.consultations.insert_one({
            "id": cid, "ref": f"CONS-TEST-{uuid.uuid4().hex[:4]}", "version": 1,
            "title": "TEST_iter53 benchmark", "type": "STANDARD", "procedure": "SCELLEE",
            "category": cat, "legal_status": "VERT", "products": [], "territories": ["GUADELOUPE"],
            "specs": "", "cpc_cost": 20, "max_rounds": 3, "criteria": [],
            "opens_at": now, "closes_at": now, "status": "CLOTUREE",
            "created_by": "test", "created_at": now, "updated_at": now,
            "TEST_iter53": True,
        })
        # entry
        eid = str(uuid.uuid4())
        await db.consultation_entries.insert_one({
            "id": eid, "consultation_id": cid, "vendor_user_id": vendor_uid,
            "status": "INSCRIT", "created_at": now, "TEST_iter53": True,
        })
        # bid VALIDE
        await db.bids.insert_one({
            "id": str(uuid.uuid4()), "consultation_id": cid, "entry_id": eid,
            "vendor_user_id": vendor_uid, "amount_ht_cents": 12345,
            "status": "VALIDE", "server_ts": now, "TEST_iter53": True,
        })
        STATE["bench_cid"] = cid
        STATE["vendor_uid"] = vendor_uid

    asyncio.run(setup())

    # 1er appel : débit
    r = requests.post(f"{BASE}/api/consultations-benchmark/{TEST_CAT}",
                      headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("consultations", "offers", "avg_offer_ht_cents", "median_offer_ht_cents",
              "min_offer_ht_cents", "max_offer_ht_cents", "avg_participants"):
        assert k in d, f"missing {k}"
    assert d["consultations"] >= 1
    assert d["offers"] >= 1
    assert d["avg_offer_ht_cents"] == 12345

    # Vérifier débit -15 dans le ledger
    async def check_debit():
        db = _mongo()
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"bench:{TEST_CAT}:{STATE['vendor_uid']}:{month}"
        entry = await db.cpc_ledger.find_one({"idempotency_key": key}, {"_id": 0})
        assert entry, "aucun mouvement idempotency_key trouvé"
        assert entry["qty"] == -15, f"qty attendu -15, obtenu {entry.get('qty')}"
        assert entry["type"] == "REPORT_PURCHASE"
        STATE["ledger_id_first"] = entry.get("id")

    asyncio.run(check_debit())

    # 2e appel : idempotent (pas de nouveau débit, données retournées)
    r2 = requests.post(f"{BASE}/api/consultations-benchmark/{TEST_CAT}",
                       headers=H(vendor_token), timeout=30)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["consultations"] == d["consultations"]

    async def check_no_double_debit():
        db = _mongo()
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"bench:{TEST_CAT}:{STATE['vendor_uid']}:{month}"
        count = await db.cpc_ledger.count_documents({"idempotency_key": key})
        assert count == 1, f"double débit détecté: {count} entrées"

    asyncio.run(check_no_double_debit())


# ============================================================
# 3) Récurrence templates
# ============================================================
def test_recurrence_invalid_interval(admin_token):
    # crée un template dédié
    r = requests.post(f"{BASE}/api/admin/consultation-templates",
                      headers=H(admin_token), json={
                          "name": f"TEST_iter53 rec {uuid.uuid4().hex[:6]}",
                          "title": "TEST rec", "type": "STANDARD", "procedure": "SCELLEE",
                          "category": f"iter53-rec-{uuid.uuid4().hex[:6]}",
                          "products": [], "territories": ["GUADELOUPE"], "specs": ""
                      }, timeout=30)
    assert r.status_code == 200
    STATE["tpl_rec"] = r.json()["id"]

    r = requests.post(f"{BASE}/api/admin/consultation-templates/{STATE['tpl_rec']}/recurrence",
                      headers=H(admin_token), json={"interval": "daily"}, timeout=30)
    assert r.status_code == 400


def test_recurrence_monthly_sets_next_run(admin_token):
    tid = STATE["tpl_rec"]
    r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/recurrence",
                      headers=H(admin_token), json={"interval": "monthly"}, timeout=30)
    assert r.status_code == 200, r.text
    rec = r.json()["recurrence"]
    assert rec["interval"] == "monthly"
    assert rec["next_run_at"]
    dt = datetime.fromisoformat(rec["next_run_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = (dt - now).total_seconds()
    # ~30 jours (entre 25 et 35 jours de tolérance)
    assert 25*86400 < delta < 35*86400, f"delta = {delta/86400} jours"


def test_recurrence_quarterly(admin_token):
    tid = STATE["tpl_rec"]
    r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/recurrence",
                      headers=H(admin_token), json={"interval": "quarterly"}, timeout=30)
    assert r.status_code == 200
    rec = r.json()["recurrence"]
    dt = datetime.fromisoformat(rec["next_run_at"].replace("Z", "+00:00"))
    delta = (dt - datetime.now(timezone.utc)).total_seconds()
    assert 80*86400 < delta < 100*86400


def test_recurrence_none_clears(admin_token):
    tid = STATE["tpl_rec"]
    r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/recurrence",
                      headers=H(admin_token), json={"interval": "none"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["recurrence"] is None


def test_run_recurring_templates_creates_and_reschedules(admin_token):
    """Force next_run_at dans le passé, exécute run_recurring_templates, vérifie création + reschedule."""
    tid = STATE["tpl_rec"]

    # remettre monthly
    r = requests.post(f"{BASE}/api/admin/consultation-templates/{tid}/recurrence",
                      headers=H(admin_token), json={"interval": "monthly"}, timeout=30)
    assert r.status_code == 200

    async def run():
        db = _mongo()
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        await db.consultation_templates.update_one(
            {"id": tid}, {"$set": {"recurrence.next_run_at": past}})

        # Import + rebind DB modules (routes_consultation_templates uses module-level db)
        import routes_consultation_templates as rct
        import routes_consultations as rc
        import routes_cpc_admin as rca
        import routes_legal_matrix as rlm
        import consultation_audit as ca
        rct.db = db
        rc.db = db
        rca.db = db
        try:
            rlm.db = db
        except Exception:
            pass
        ca.db = db

        # avant
        before = await db.consultations.count_documents({"template_id": tid, "created_by": "scheduler"})

        created = await rct.run_recurring_templates(db)
        assert created == 1, f"expected 1 created, got {created}"

        after = await db.consultations.count_documents({"template_id": tid, "created_by": "scheduler"})
        assert after == before + 1

        # dernière conso créée
        cons = await db.consultations.find_one({"template_id": tid, "created_by": "scheduler"},
                                                {"_id": 0}, sort=[("created_at", -1)])
        assert cons["status"] == "BROUILLON"
        assert cons["ref"].startswith("CONS-")
        STATE.setdefault("recurring_cons_ids", []).append(cons["id"])

        # audit LOT_CREATED with from_template
        audit_ok = await db.audit_journal.find_one(
            {"event_type": "LOT_CREATED", "consultation_id": cons["id"]}, {"_id": 0})
        assert audit_ok, "audit LOT_CREATED manquant"
        assert audit_ok.get("payload", {}).get("from_template") == tid

        # 2e run immédiat → pas de nouvelle création (next_run_at déjà futur)
        created2 = await rct.run_recurring_templates(db)
        assert created2 == 0, f"expected 0, got {created2}"

    asyncio.run(run())


# ============================================================
# 5) Régression
# ============================================================
def test_cpc_me(vendor_token):
    r = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "balance" in d


def test_cpc_checkout_returns_url(vendor_token):
    # récupérer un pack
    r = requests.get(f"{BASE}/api/cpc/packs", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    packs = r.json().get("items", [])
    assert packs, "aucun pack"
    pid = packs[0]["id"]
    r = requests.post(f"{BASE}/api/cpc/checkout",
                      headers=H(vendor_token),
                      json={"pack_id": pid, "origin_url": BASE}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "checkout_url" in d
    assert "checkout.stripe.com" in d["checkout_url"]


def test_consultations_tracking(vendor_token):
    r = requests.get(f"{BASE}/api/consultations/tracking",
                     headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d.get("items", []), list)


# ============================================================
# Cleanup
# ============================================================
def test_zz_cleanup(admin_token):
    async def cleanup():
        db = _mongo()
        # Liquidity consultations (via cid_liquidity + liq_cids)
        cids = list(STATE.get("liq_cids", []))
        if STATE.get("cid_liquidity"):
            cids.append(STATE["cid_liquidity"])
        if STATE.get("bench_cid"):
            cids.append(STATE["bench_cid"])
        for cid in STATE.get("recurring_cons_ids", []):
            cids.append(cid)
        if cids:
            await db.consultations.delete_many({"id": {"$in": cids}})
            await db.consultation_entries.delete_many({"consultation_id": {"$in": cids}})
            await db.bids.delete_many({"consultation_id": {"$in": cids}})
            await db.audit_journal.delete_many({"consultation_id": {"$in": cids}})

        # Templates créés
        tpls = [t for t in [STATE.get("tpl_liq"), STATE.get("tpl_rec")] if t]
        if tpls:
            await db.consultation_templates.delete_many({"id": {"$in": tpls}})

        # Vendor_products/vendors TEST_iter53
        await db.vendor_products.delete_many({"TEST_iter53": True})
        await db.vendors.delete_many({"TEST_iter53": True})

        # Ledger benchmark débit test (uniquement notre catégorie de test)
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        uid = STATE.get("vendor_uid")
        if uid:
            key = f"bench:{TEST_CAT}:{uid}:{month}"
            await db.cpc_ledger.delete_many({"idempotency_key": key})
            # Restaurer solde vendor si drifté
            acc = await db.cpc_accounts.find_one({"user_id": uid}, {"_id": 0, "balance": 1})
            cur = (acc or {}).get("balance", 0)
            # Cible : ~60 pour la démo (par la consigne)
            target = 60
            if cur != target:
                diff = target - cur
                if diff != 0:
                    # Correction directe DB (append-only bypass ok pour cleanup)
                    from cpc_ledger import add_cpc_movement
                    import cpc_ledger as cl
                    cl.db = db
                    try:
                        await add_cpc_movement(uid, "ADMIN_CORRECTION", diff,
                                               idempotency_key=f"iter53-reset-{uuid.uuid4().hex[:8]}",
                                               reason="[réf iter53] reset solde démo à 60",
                                               author=ADMIN_EMAIL, allow_frozen=True)
                    except Exception as e:
                        print(f"reset solde non appliqué: {e}")

    asyncio.run(cleanup())
