"""
Iter 54 — Validation lot 4 fonctionnalités :
1) Solde unifié header + page /mon-crediscop (statement JSON + PDF)
2) Alerte Benchmark Mensuel (send_monthly_benchmarks direct python)
3) Historique Liquidité (snapshot_liquidity + GET /api/admin/liquidity/history)
4) Programme Parrainage (GET /me, POST /claim + hook bonus)
"""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone

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
# 5) Settings — referral_bonus
# ============================================================
def test_settings_contains_referral_bonus(admin_token):
    r = requests.get(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("referral_bonus") == 10, f"referral_bonus attendu 10, obtenu {d.get('referral_bonus')}"
    STATE["settings_orig"] = d


def test_settings_put_negative_referral_rejected(admin_token):
    orig = STATE["settings_orig"]
    payload = {k: orig.get(k) for k in ["standard_cost", "interterritorial_cost", "report_cost",
                                         "benchmark_cost", "referral_bonus", "low_balance_alert"]}
    payload["referral_bonus"] = -1
    r = requests.put(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), json=payload, timeout=30)
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


# ============================================================
# 4) Parrainage — GET /me, POST /claim
# ============================================================
def test_referral_me_vendor(vendor_token):
    r = requests.get(f"{BASE}/api/referral/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["code"].startswith("KDM-") and len(d["code"]) == 10
    assert d["bonus"] == 10
    assert isinstance(d.get("referred"), list)
    STATE["sponsor_code"] = d["code"]
    STATE["sponsor_email"] = VENDOR_EMAIL


def test_referral_claim_own_code_rejected(vendor_token):
    code = STATE["sponsor_code"]
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(vendor_token),
                      json={"code": code}, timeout=30)
    assert r.status_code == 400, r.text


def test_referral_claim_unknown_code(vendor_token):
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(vendor_token),
                      json={"code": "KDM-ZZZZZZ"}, timeout=30)
    assert r.status_code == 404, r.text


def test_referral_full_flow_with_test_filleul(admin_token, vendor_token):
    """Crée un vendeur de test SANS entries, claim vendor-pro's code, simule inscription → bonus payé."""
    async def setup_filleul():
        db = _mongo()
        # Get sponsor (vendor-pro) user_id
        sponsor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
        STATE["sponsor_id"] = sponsor["id"]
        # Solde initial CPC sponsor
        acc = await db.cpc_accounts.find_one({"user_id": sponsor["id"]}, {"_id": 0, "cpc_balance": 1})
        STATE["sponsor_balance_before"] = (acc or {}).get("cpc_balance", 0)

        # Créer un user vendor de test avec password hashé
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        filleul_email = f"TEST_iter54_filleul_{uuid.uuid4().hex[:6]}@example.com"
        filleul_id = str(uuid.uuid4())
        vendor_id = f"TEST_iter54_vendor_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        await db.users.insert_one({
            "id": filleul_id, "email": filleul_email,
            "password_hash": pwd_ctx.hash("TestFilleul2026!"),
            "role": "vendor", "vendor_id": vendor_id,
            "full_name": "TEST_iter54 Filleul",
            "company_name": "TEST_iter54 Filleul SARL", "siret": f"TEST{uuid.uuid4().hex[:10]}",
            "contact_name": "TEST Filleul", "phone": "+590590000000",
            "subscription": "FREE", "credits": 0,
            "created_at": now, "TEST_iter54": True,
        })
        # Le vendor entity aussi
        await db.vendors.insert_one({
            "id": vendor_id, "email": filleul_email,
            "siret": f"TEST{uuid.uuid4().hex[:10]}",
            "name": "TEST_iter54 Filleul Vendor",
            "status": "approved", "credits": 0,
            "TEST_iter54": True,
        })
        STATE["filleul_id"] = filleul_id
        STATE["filleul_email"] = filleul_email
        STATE["filleul_vendor_id"] = vendor_id

    asyncio.run(setup_filleul())

    # Login filleul
    filleul_token = _login(STATE["filleul_email"], "TestFilleul2026!")

    # Claim inconnu → 404
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(filleul_token),
                      json={"code": "KDM-XXYYZZ"}, timeout=30)
    assert r.status_code == 404

    # Claim propre code → 400
    r_me = requests.get(f"{BASE}/api/referral/me", headers=H(filleul_token), timeout=30)
    assert r_me.status_code == 200
    own_code = r_me.json()["code"]
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(filleul_token),
                      json={"code": own_code}, timeout=30)
    assert r.status_code == 400

    # Claim vendor-pro's code → OK
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(filleul_token),
                      json={"code": STATE["sponsor_code"]}, timeout=30)
    assert r.status_code == 200, r.text

    # 2e claim → 409
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(filleul_token),
                      json={"code": STATE["sponsor_code"]}, timeout=30)
    assert r.status_code == 409, r.text

    # Simuler inscription à une consultation via insertion consultation_entries + hook direct
    async def simulate_registration():
        db = _mongo()
        # Créer entry
        eid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.consultation_entries.insert_one({
            "id": eid, "consultation_id": cid,
            "vendor_user_id": STATE["filleul_id"], "status": "INSCRIT",
            "created_at": now, "TEST_iter54": True,
        })
        STATE["entry_id"] = eid
        STATE["fake_cid"] = cid
        # Rebinder les modules
        import routes_referral as rr
        import routes_cpc_admin as rca
        import cpc_ledger as cl
        import consultation_audit as ca
        rr.db = db
        rca.db = db
        cl.db = db
        ca.db = db
        # Appeler le hook
        await rr.maybe_pay_referral_bonus(STATE["filleul_id"])
        # Vérifier ledger sponsor
        entry = await db.cpc_ledger.find_one(
            {"idempotency_key": f"referral:{STATE['filleul_id']}"}, {"_id": 0})
        assert entry, "aucun mouvement PROMO_GRANT trouvé"
        assert entry["type"] == "PROMO_GRANT"
        assert entry["qty"] == 10
        assert entry["user_id"] == STATE["sponsor_id"]
        STATE["bonus_ledger_key"] = f"referral:{STATE['filleul_id']}"
        # referral_links bonus_paid
        link = await db.referral_links.find_one({"filleul_id": STATE["filleul_id"]}, {"_id": 0})
        assert link["bonus_paid"] is True
        assert link.get("bonus_amount") == 10
        # audit
        audit = await db.audit_journal.find_one({"event_type": "REFERRAL_BONUS_PAID"}, {"_id": 0},
                                                 sort=[("created_at", -1)])
        assert audit, "audit REFERRAL_BONUS_PAID manquant"

        # 2e appel : pas de double bonus
        await rr.maybe_pay_referral_bonus(STATE["filleul_id"])
        count = await db.cpc_ledger.count_documents(
            {"idempotency_key": f"referral:{STATE['filleul_id']}"})
        assert count == 1, f"double bonus détecté : {count}"

    asyncio.run(simulate_registration())

    # Vérifier via API sponsor : referred contient le filleul + total_earned=10
    r = requests.get(f"{BASE}/api/referral/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["total_earned"] >= 10
    emails = [f["email"] for f in d["referred"]]
    assert STATE["filleul_email"] in emails
    match = next(f for f in d["referred"] if f["email"] == STATE["filleul_email"])
    assert match["bonus_paid"] is True

    # Claim doit refuser si filleul a des entries (409) — deja fait plus haut car link existe
    # Verifions le cas "vendeur avec entries" via un autre user de test
    async def test_entries_blocks_claim():
        db = _mongo()
        # Créer un 2e filleul de test avec une entry existante
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        email2 = f"TEST_iter54_hasentries_{uuid.uuid4().hex[:6]}@example.com"
        fid2 = str(uuid.uuid4())
        vid2 = f"TEST_iter54_v_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        await db.users.insert_one({
            "id": fid2, "email": email2,
            "password_hash": pwd_ctx.hash("TestFilleul2026!"),
            "role": "vendor", "vendor_id": vid2,
            "full_name": "TEST_iter54 HasEntries",
            "company_name": "TEST_iter54 HasEntries SARL", "siret": f"TEST{uuid.uuid4().hex[:10]}",
            "contact_name": "TEST HasEntries", "phone": "+590590000001",
            "subscription": "FREE", "credits": 0,
            "created_at": now, "TEST_iter54": True,
        })
        await db.vendors.insert_one({"id": vid2, "email": email2, "siret": f"TEST{uuid.uuid4().hex[:10]}",
                                     "name": "TEST HasEntries", "status": "approved", "TEST_iter54": True})
        # Existing entry
        await db.consultation_entries.insert_one({
            "id": str(uuid.uuid4()), "consultation_id": str(uuid.uuid4()),
            "vendor_user_id": fid2, "status": "INSCRIT", "created_at": now,
            "TEST_iter54": True,
        })
        STATE["filleul2_id"] = fid2
        STATE["filleul2_email"] = email2
        STATE["filleul2_vendor_id"] = vid2

    asyncio.run(test_entries_blocks_claim())
    tok2 = _login(STATE["filleul2_email"], "TestFilleul2026!")
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(tok2),
                      json={"code": STATE["sponsor_code"]}, timeout=30)
    assert r.status_code == 409, f"expected 409 (has entries), got {r.status_code}: {r.text}"


# ============================================================
# 1) Relevé unifié /api/me/crediscop + statement + PDF
# ============================================================
def test_me_crediscop_href(vendor_token):
    r = requests.get(f"{BASE}/api/me/crediscop", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("href") == "/mon-crediscop"
    assert "cpc_balance" in d
    assert "balance" in d


def test_crediscop_statement(vendor_token):
    r = requests.get(f"{BASE}/api/me/crediscop/statement", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    kinds = [b["kind"] for b in d.get("balances", [])]
    assert "vendor" in kinds, f"kinds={kinds}"
    assert "consultations" in kinds, f"kinds={kinds}"
    # entries : au moins un mouvement consultations
    sources = {e.get("source") for e in d.get("entries", [])}
    assert "consultations" in sources or "vendor" in sources, f"sources={sources}"


def test_crediscop_statement_pdf(vendor_token):
    r = requests.get(f"{BASE}/api/me/crediscop/statement.pdf", headers=H(vendor_token), timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"


# ============================================================
# 3) Historique liquidité
# ============================================================
def test_liquidity_history_endpoint(admin_token):
    r = requests.get(f"{BASE}/api/admin/liquidity/history", headers=H(admin_token), timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    items = d.get("items", [])
    assert isinstance(items, list)
    for it in items[:3]:
        for k in ("category", "current", "trend", "series"):
            assert k in it
        assert isinstance(it["series"], list)


def test_snapshot_liquidity_idempotent_same_day():
    async def run():
        db = _mongo()
        import routes_liquidity as rl
        rl.db = db
        # Premier snapshot
        n1 = await rl.snapshot_liquidity(db)
        # Comptage par catégorie/jour
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Choisir une catégorie non vide
        cats = await db.vendor_products.distinct("category")
        cats = [c for c in cats if c]
        assert cats, "aucune catégorie vendor_products — pas de snapshot possible"
        # Deuxième appel — doit être idempotent (upsert par category+day)
        n2 = await rl.snapshot_liquidity(db)
        assert n1 == n2
        # Vérifier 1 seul document par (category, day) pour la première catégorie
        for cat in cats[:3]:
            count = await db.liquidity_snapshots.count_documents({"category": cat, "day": day})
            assert count == 1, f"cat={cat} count={count}"
    asyncio.run(run())


# ============================================================
# 2) Benchmark mensuel — send_monthly_benchmarks
# ============================================================
def test_send_monthly_benchmarks(admin_token):
    """Crée une subscription factice ACTIVE cpc-plan-expert pour vendor-pro puis exécute send_monthly_benchmarks."""
    async def run():
        db = _mongo()
        # Get vendor-pro user_id
        u = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1, "vendor_id": 1})
        uid = u["id"]
        STATE["vendor_uid"] = uid
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        # S'assurer qu'aucune subscription active existante ne va être flaggée à cause de nous
        existing_sub = await db.cpc_subscriptions.find_one(
            {"user_id": uid, "plan_id": "cpc-plan-expert"}, {"_id": 0})
        assert not existing_sub, "subscription vendor-pro existe déjà — abandon pour éviter effets de bord"

        # Créer la sub factice
        sub_id = f"TEST_iter54_sub_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        await db.cpc_subscriptions.insert_one({
            "id": sub_id, "user_id": uid, "plan_id": "cpc-plan-expert",
            "plan_label": "Expert (TEST_iter54)",
            "status": "ACTIVE", "created_at": now,
            "TEST_iter54": True,
        })
        STATE["fake_sub_id"] = sub_id

        # Get main category
        import routes_benchmark as rb
        import routes_bids as rbids
        rb.db = db
        rbids.db = db
        cat = await rb._main_category(u)
        STATE["vendor_main_cat"] = cat

        # S'assurer qu'une consultation clôturée existe dans cette catégorie
        created_bench_cid = None
        if cat:
            existing = await db.consultations.find_one(
                {"category": cat, "status": {"$in": rb.CLOSED_STATUSES}}, {"_id": 0, "id": 1})
            if not existing:
                cid = str(uuid.uuid4())
                await db.consultations.insert_one({
                    "id": cid, "ref": f"CONS-TEST54-{uuid.uuid4().hex[:4]}", "version": 1,
                    "title": "TEST_iter54 monthly bench", "type": "STANDARD", "procedure": "SCELLEE",
                    "category": cat, "legal_status": "VERT", "products": [],
                    "territories": ["GUADELOUPE"], "specs": "", "cpc_cost": 20,
                    "max_rounds": 3, "criteria": [],
                    "opens_at": now, "closes_at": now, "status": "CLOTUREE",
                    "created_by": "test", "created_at": now, "updated_at": now,
                    "TEST_iter54": True,
                })
                eid = str(uuid.uuid4())
                await db.consultation_entries.insert_one({
                    "id": eid, "consultation_id": cid, "vendor_user_id": uid,
                    "status": "INSCRIT", "created_at": now, "TEST_iter54": True,
                })
                await db.bids.insert_one({
                    "id": str(uuid.uuid4()), "consultation_id": cid, "entry_id": eid,
                    "vendor_user_id": uid, "amount_ht_cents": 9999,
                    "status": "VALIDE", "server_ts": now, "TEST_iter54": True,
                })
                created_bench_cid = cid
        STATE["created_bench_cid"] = created_bench_cid

        # 1er run
        n1 = await rb.send_monthly_benchmarks(db)
        # Vérifier benchmark_sent_month posé
        sub_after = await db.cpc_subscriptions.find_one({"id": sub_id}, {"_id": 0})
        assert sub_after.get("benchmark_sent_month") == month, \
            f"expected {month}, got {sub_after.get('benchmark_sent_month')}"
        # 2e run immédiat → 0 envois (idempotent par mois)
        n2 = await rb.send_monthly_benchmarks(db)
        assert n2 == 0, f"expected 0 sur 2e run, got {n2}"
        STATE["monthly_n1"] = n1
        STATE["monthly_n2"] = n2

    asyncio.run(run())


# ============================================================
# Régression rapide
# ============================================================
def test_regression_cpc_me(vendor_token):
    r = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    assert "balance" in r.json()


def test_regression_checkout(vendor_token):
    r = requests.get(f"{BASE}/api/cpc/packs", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200
    packs = r.json().get("items", [])
    assert packs
    r = requests.post(f"{BASE}/api/cpc/checkout", headers=H(vendor_token),
                      json={"pack_id": packs[0]["id"], "origin_url": BASE}, timeout=60)
    assert r.status_code == 200, r.text
    assert "checkout.stripe.com" in r.json().get("checkout_url", "")


def test_regression_benchmark_paid(vendor_token):
    # Ping /api/consultations-benchmark/{cat} sans catégorie clôturée → 404 attendu
    r = requests.post(f"{BASE}/api/consultations-benchmark/inexistant-cat-iter54",
                      headers=H(vendor_token), timeout=30)
    assert r.status_code == 404


# ============================================================
# Cleanup
# ============================================================
def test_zz_cleanup(admin_token):
    async def cleanup():
        db = _mongo()
        # 1. Supprimer users, vendors, consultation_entries TEST_iter54
        await db.consultation_entries.delete_many({"TEST_iter54": True})
        await db.consultations.delete_many({"TEST_iter54": True})
        await db.bids.delete_many({"TEST_iter54": True})
        await db.users.delete_many({"TEST_iter54": True})
        await db.vendors.delete_many({"TEST_iter54": True})
        # 2. Referral links de test
        for fid in [STATE.get("filleul_id"), STATE.get("filleul2_id")]:
            if fid:
                await db.referral_links.delete_many({"filleul_id": fid})
                await db.referral_codes.delete_many({"user_id": fid})
                await db.cpc_accounts.delete_many({"user_id": fid})
                await db.cpc_ledger.delete_many({"user_id": fid})
        # 3. Ledger bonus parrainage (sponsor side) — supprimer par idempotency_key
        if STATE.get("bonus_ledger_key"):
            entry = await db.cpc_ledger.find_one({"idempotency_key": STATE["bonus_ledger_key"]}, {"_id": 0})
            if entry:
                await db.cpc_ledger.delete_many({"idempotency_key": STATE["bonus_ledger_key"]})
        # 4. Subscription factice
        if STATE.get("fake_sub_id"):
            await db.cpc_subscriptions.delete_many({"id": STATE["fake_sub_id"]})
        # 5. Restaurer solde vendor-pro à 60 CPC
        uid = STATE.get("sponsor_id")
        if uid:
            acc = await db.cpc_accounts.find_one({"user_id": uid}, {"_id": 0, "cpc_balance": 1})
            cur = (acc or {}).get("cpc_balance", 0)
            target = 60
            if cur != target:
                diff = target - cur
                # Reset direct via ledger avec compensation append-only
                from cpc_ledger import add_cpc_movement
                import cpc_ledger as cl
                cl.db = db
                await add_cpc_movement(
                    uid, "ADMIN_CORRECTION", diff,
                    idempotency_key=f"iter54-reset-{uuid.uuid4().hex[:8]}",
                    reason="[réf iter54-cleanup] reset solde démo à 60",
                    author=ADMIN_EMAIL, allow_frozen=True)
        # 6. Audit REFERRAL_* du test
        await db.audit_journal.delete_many({
            "event_type": {"$in": ["REFERRAL_CLAIMED", "REFERRAL_BONUS_PAID"]},
            "payload.filleul_id": {"$in": [STATE.get("filleul_id"), STATE.get("filleul2_id")]}
        })
        # audit_journal peut aussi être sur actor_id
        for fid in [STATE.get("filleul_id"), STATE.get("filleul2_id")]:
            if fid:
                await db.audit_journal.delete_many({"actor_id": fid,
                                                     "event_type": "REFERRAL_CLAIMED"})
    asyncio.run(cleanup())
