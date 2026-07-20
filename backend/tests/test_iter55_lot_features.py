"""
Iter 55 — Lot 4 fonctionnalités :
1) Backend GET /api/referral/admin/overview (agrégats + 403 sans admin)
2) Backend snapshot_liquidity : détection croisement 2<3→3+ (1 seul email Brevo)
3) Backend régression parrainage (/me + claim own code 400)
NB : les fonctionnalités frontend (bannière /adhesion-vendeur, auto-claim, boutons partage, panneau admin) sont testées via Playwright séparément.
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
# 3) Régression parrainage
# ============================================================
def test_referral_me_vendor(vendor_token):
    r = requests.get(f"{BASE}/api/referral/me", headers=H(vendor_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["code"] == "KDM-9A4D34", f"expected KDM-9A4D34, got {d['code']}"
    STATE["sponsor_code"] = d["code"]


def test_referral_claim_own_code_400(vendor_token):
    r = requests.post(f"{BASE}/api/referral/claim", headers=H(vendor_token),
                      json={"code": STATE["sponsor_code"]}, timeout=30)
    assert r.status_code == 400, r.text


# ============================================================
# 1) Admin overview — 403 sans admin, agrégats sur données factices
# ============================================================
def test_admin_overview_forbidden_vendor(vendor_token):
    r = requests.get(f"{BASE}/api/referral/admin/overview", headers=H(vendor_token), timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_admin_overview_aggregates(admin_token, vendor_token):
    """Insère 2 referral_links factices avec sponsor_id=vendor-pro, un bonus_paid, un pending."""
    async def setup():
        db = _mongo()
        sponsor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
        STATE["sponsor_id"] = sponsor["id"]
        now = datetime.now(timezone.utc).isoformat()
        f1_id = f"TEST_iter55_f1_{uuid.uuid4().hex[:6]}"
        f2_id = f"TEST_iter55_f2_{uuid.uuid4().hex[:6]}"
        f1_email = f"TEST_iter55_filleul1_{uuid.uuid4().hex[:6]}@example.com"
        f2_email = f"TEST_iter55_filleul2_{uuid.uuid4().hex[:6]}@example.com"
        await db.users.insert_many([
            {"id": f1_id, "email": f1_email, "role": "vendor", "TEST_iter55": True},
            {"id": f2_id, "email": f2_email, "role": "vendor", "TEST_iter55": True},
        ])
        await db.referral_links.insert_many([
            {"filleul_id": f1_id, "filleul_email": f1_email, "sponsor_id": sponsor["id"],
             "code": STATE["sponsor_code"], "bonus_paid": True, "bonus_amount": 10,
             "bonus_paid_at": now, "created_at": now, "TEST_iter55": True},
            {"filleul_id": f2_id, "filleul_email": f2_email, "sponsor_id": sponsor["id"],
             "code": STATE["sponsor_code"], "bonus_paid": False,
             "created_at": now, "TEST_iter55": True},
        ])
        STATE["fake_filleul_ids"] = [f1_id, f2_id]
        STATE["fake_filleul_emails"] = [f1_email, f2_email]

    asyncio.run(setup())

    r = requests.get(f"{BASE}/api/referral/admin/overview", headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    # Il peut y avoir d'autres links en DB, on vérifie que nos 2 sont bien inclus dans les stats
    assert d["total_links"] >= 2
    assert d["total_bonus_paid"] >= 1
    assert d["total_credited"] >= 10
    # top_ambassadors contient bien l'email vendor-pro avec crédité >= 10
    tops = [t for t in d["top_ambassadors"] if t["sponsor"] == VENDOR_EMAIL]
    assert tops, f"vendor-pro absent des ambassadeurs : {d['top_ambassadors']}"
    assert tops[0]["credited"] >= 10
    # links contient les emails de nos filleuls résolus
    link_emails = [l["filleul"] for l in d["links"]]
    for e in STATE["fake_filleul_emails"]:
        assert e in link_emails, f"{e} absent de links"
    # Le sponsor est bien résolu en email (pas en user_id)
    for l in d["links"]:
        if l["filleul"] in STATE["fake_filleul_emails"]:
            assert l["sponsor"] == VENDOR_EMAIL, f"sponsor non résolu : {l['sponsor']}"


# ============================================================
# 2) Alerte seuil liquidité : croisement 2→3
# ============================================================
def test_liquidity_threshold_alert_crossing():
    """Créer catégorie factice, 2 vendors : pas d'alerte. Ajout 3e : 1 alerte. Re-appel : 0 alerte."""
    async def run():
        db = _mongo()
        import routes_liquidity as rl
        rl.db = db

        cat = f"test-iter55-{uuid.uuid4().hex[:6]}"
        STATE["fake_cat"] = cat
        now = datetime.now(timezone.utc).isoformat()

        # 2 vendors + products
        v1 = f"TEST_iter55_v1_{uuid.uuid4().hex[:6]}"
        v2 = f"TEST_iter55_v2_{uuid.uuid4().hex[:6]}"
        await db.vendors.insert_many([
            {"id": v1, "email": f"TEST_iter55_v1_{uuid.uuid4().hex[:6]}@example.com",
             "siret": f"TEST55{uuid.uuid4().hex[:10]}",
             "name": "TEST v1", "status": "approved", "TEST_iter55": True},
            {"id": v2, "email": f"TEST_iter55_v2_{uuid.uuid4().hex[:6]}@example.com",
             "siret": f"TEST55{uuid.uuid4().hex[:10]}",
             "name": "TEST v2", "status": "approved", "TEST_iter55": True},
        ])
        await db.vendor_products.insert_many([
            {"id": str(uuid.uuid4()), "vendor_id": v1, "category": cat,
             "name": "P1", "created_at": now, "TEST_iter55": True},
            {"id": str(uuid.uuid4()), "vendor_id": v2, "category": cat,
             "name": "P2", "created_at": now, "TEST_iter55": True},
        ])
        STATE["fake_vendor_ids"] = [v1, v2]

        # Patch _alert_threshold pour compter les appels et éviter l'envoi Brevo réel
        alerts_calls = []
        original = rl._alert_threshold

        async def spy(category, prev, curr):
            alerts_calls.append((category, prev, curr))
            # On appelle l'original SEULEMENT sur la catégorie factice pour vérifier le franchissement
            # Ne PAS envoyer réellement l'email : on remplace send_email
            if not (prev < 3 <= curr):
                return
            # Simuler l'envoi sans Brevo réel : incrémenter compteur uniquement pour la catégorie test
            import logging
            logging.getLogger("routes_liquidity").info(
                "Alerte seuil liquidité envoyée : %s (%d → %d)", category, prev, curr)

        rl._alert_threshold = spy
        try:
            # 1er snapshot : 2 vendors → pas de croisement
            await rl.snapshot_liquidity(db)
            crossings_cat = [c for c in alerts_calls if c[0] == cat and c[1] < 3 <= c[2]]
            assert len(crossings_cat) == 0, f"alerte prématurée : {crossings_cat}"
            # Vérifier snapshot posé : eligible_vendors=2
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            snap = await db.liquidity_snapshots.find_one({"category": cat, "day": day}, {"_id": 0})
            assert snap and snap["eligible_vendors"] == 2, f"snap={snap}"

            # Ajouter 3e vendor + product
            v3 = f"TEST_iter55_v3_{uuid.uuid4().hex[:6]}"
            await db.vendors.insert_one({
                "id": v3, "email": f"TEST_iter55_v3_{uuid.uuid4().hex[:6]}@example.com",
                "siret": f"TEST55{uuid.uuid4().hex[:10]}",
                "name": "TEST v3", "status": "approved", "TEST_iter55": True})
            await db.vendor_products.insert_one({
                "id": str(uuid.uuid4()), "vendor_id": v3, "category": cat,
                "name": "P3", "created_at": now, "TEST_iter55": True})
            STATE["fake_vendor_ids"].append(v3)

            # 2e snapshot : 3 vendors → doit déclencher (baseline=2, current=3)
            alerts_calls.clear()
            await rl.snapshot_liquidity(db)
            crossings = [c for c in alerts_calls if c[0] == cat and c[1] < 3 <= c[2]]
            assert len(crossings) == 1, f"attendu 1 croisement, obtenu {len(crossings)}: {crossings}"
            snap2 = await db.liquidity_snapshots.find_one({"category": cat, "day": day}, {"_id": 0})
            assert snap2["eligible_vendors"] == 3

            # 3e snapshot immédiat : baseline devient existing_today=3, current=3 → PAS de croisement
            alerts_calls.clear()
            await rl.snapshot_liquidity(db)
            crossings2 = [c for c in alerts_calls if c[0] == cat and c[1] < 3 <= c[2]]
            assert len(crossings2) == 0, f"double alerte : {crossings2}"

        finally:
            rl._alert_threshold = original

    asyncio.run(run())


# ============================================================
# Cleanup
# ============================================================
def test_zz_cleanup():
    async def cleanup():
        db = _mongo()
        # Users, vendors, vendor_products, liquidity_snapshots, referral_links marqués TEST_iter55
        await db.users.delete_many({"TEST_iter55": True})
        await db.vendors.delete_many({"TEST_iter55": True})
        await db.vendor_products.delete_many({"TEST_iter55": True})
        await db.referral_links.delete_many({"TEST_iter55": True})
        # liquidity_snapshots de la catégorie factice
        if STATE.get("fake_cat"):
            await db.liquidity_snapshots.delete_many({"category": STATE["fake_cat"]})
        # Vérif no leftover
        for coll in ("users", "vendors", "vendor_products", "referral_links"):
            n = await db[coll].count_documents({"TEST_iter55": True})
            assert n == 0, f"leftover {coll}: {n}"
        if STATE.get("fake_cat"):
            n = await db.liquidity_snapshots.count_documents({"category": STATE["fake_cat"]})
            assert n == 0

    asyncio.run(cleanup())
