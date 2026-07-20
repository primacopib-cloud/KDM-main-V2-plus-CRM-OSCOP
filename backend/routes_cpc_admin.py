"""Administration CPC — packs (tarifs, historique), attributions promo/solidaires, corrections motivées, comptes."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from cpc_ledger import add_cpc_movement, get_cpc_account

logger = logging.getLogger(__name__)

cpc_admin_router = APIRouter(prefix="/api/admin/cpc", tags=["cpc-admin"])

db = None


def set_cpc_admin_database(database):
    global db
    db = database


async def _user_by_email(email: str) -> dict:
    u = await db.users.find_one({"email": email.lower().strip()}, {"_id": 0, "id": 1, "email": 1, "full_name": 1, "name": 1})
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return u


DEFAULT_SETTINGS = {"standard_cost": 20, "interterritorial_cost": 40, "report_cost": 10,
                    "benchmark_cost": 15, "referral_bonus": 10, "referral_welcome_bonus": 5,
                    "low_balance_alert": True}


async def get_cpc_settings() -> dict:
    s = await db.cpc_settings.find_one({"_id": "settings"})
    return {**DEFAULT_SETTINGS, **{k: v for k, v in (s or {}).items() if k != "_id"}}


class SettingsBody(BaseModel):
    standard_cost: int
    interterritorial_cost: int
    report_cost: int
    benchmark_cost: int = 15
    referral_bonus: int = 10
    referral_welcome_bonus: int = 5
    low_balance_alert: bool = True


@cpc_admin_router.get("/settings")
async def read_settings(admin: dict = Depends(require_admin)):
    return await get_cpc_settings()


@cpc_admin_router.put("/settings")
async def update_settings(body: SettingsBody, admin: dict = Depends(require_admin)):
    if min(body.standard_cost, body.interterritorial_cost, body.report_cost, body.benchmark_cost) <= 0 or min(body.referral_bonus, body.referral_welcome_bonus) < 0:
        raise HTTPException(status_code=400, detail="Coûts invalides")
    await db.cpc_settings.update_one({"_id": "settings"}, {"$set": {
        **body.dict(), "updated_by": admin.get("email"),
        "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True}


class PackBody(BaseModel):
    label: str
    credits: int
    price_ht_cents: int
    validity_months: int = 12
    active: bool = True


@cpc_admin_router.get("/packs")
async def admin_packs(admin: dict = Depends(require_admin)):
    from routes_cpc import ensure_default_packs
    await ensure_default_packs()
    items = await db.cpc_packs.find({}, {"_id": 0}).sort("credits", 1).to_list(50)
    history = await db.cpc_pack_price_history.find({}, {"_id": 0}).sort("changed_at", -1).limit(30).to_list(30)
    return {"items": items, "price_history": history}


@cpc_admin_router.put("/packs/{pack_id}")
async def update_pack(pack_id: str, body: PackBody, admin: dict = Depends(require_admin)):
    """Modification sans effet rétroactif : les achats passés conservent leur prix (snapshot dans cpc_purchases)."""
    if body.credits <= 0 or body.price_ht_cents < 0 or body.validity_months <= 0:
        raise HTTPException(status_code=400, detail="Valeurs invalides")
    old = await db.cpc_packs.find_one({"id": pack_id}, {"_id": 0})
    if not old:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    await db.cpc_packs.update_one({"id": pack_id}, {"$set": body.dict()})
    if old.get("price_ht_cents") != body.price_ht_cents or old.get("credits") != body.credits:
        await db.cpc_pack_price_history.insert_one({
            "pack_id": pack_id, "old_price_ht_cents": old.get("price_ht_cents"),
            "new_price_ht_cents": body.price_ht_cents, "old_credits": old.get("credits"),
            "new_credits": body.credits, "changed_by": admin.get("email"),
            "changed_at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True}


@cpc_admin_router.post("/packs")
async def create_pack(body: PackBody, admin: dict = Depends(require_admin)):
    doc = {**body.dict(), "id": f"cpc-pack-{uuid.uuid4().hex[:8]}",
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.cpc_packs.insert_one({**doc})
    return doc


class GrantBody(BaseModel):
    user_email: str
    credits: int
    kind: str = "promo"  # promo | solidaire
    reason: str


@cpc_admin_router.post("/grant")
async def grant_cpc(body: GrantBody, admin: dict = Depends(require_admin)):
    if body.credits <= 0:
        raise HTTPException(status_code=400, detail="Quantité invalide")
    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="Motif obligatoire")
    user = await _user_by_email(body.user_email)
    entry = await add_cpc_movement(
        user["id"], "PROMO_GRANT", body.credits,
        idempotency_key=f"grant:{uuid.uuid4()}",
        reason=f"[{body.kind}] {body.reason.strip()}", author=admin.get("email"))
    return {"ok": True, "balance": entry["balance_after"]}


class CorrectionBody(BaseModel):
    user_email: str
    qty: int  # positif ou négatif
    reason: str
    reference: str


@cpc_admin_router.post("/correction")
async def correction_cpc(body: CorrectionBody, admin: dict = Depends(require_admin)):
    if not body.reason.strip() or not body.reference.strip():
        raise HTTPException(status_code=400, detail="Motif et référence obligatoires")
    user = await _user_by_email(body.user_email)
    entry = await add_cpc_movement(
        user["id"], "ADMIN_CORRECTION", body.qty,
        idempotency_key=f"corr:{uuid.uuid4()}",
        reason=f"[réf {body.reference.strip()}] {body.reason.strip()}",
        author=admin.get("email"), allow_frozen=True)
    return {"ok": True, "balance": entry["balance_after"]}


@cpc_admin_router.post("/unfreeze/{user_email}")
async def unfreeze_account(user_email: str, admin: dict = Depends(require_admin)):
    user = await _user_by_email(user_email)
    await db.cpc_accounts.update_one({"user_id": user["id"]}, {"$set": {
        "status": "ACTIF", "unfrozen_by": admin.get("email"),
        "unfrozen_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True}


@cpc_admin_router.get("/accounts")
async def list_accounts(admin: dict = Depends(require_admin)):
    accounts = await db.cpc_accounts.find({}, {"_id": 0}).sort("updated_at", -1).limit(200).to_list(200)
    out = []
    for a in accounts:
        u = await db.users.find_one({"id": a["user_id"]}, {"_id": 0, "email": 1, "full_name": 1, "name": 1})
        out.append({**a, "email": (u or {}).get("email"), "name": (u or {}).get("full_name") or (u or {}).get("name")})
    return {"items": out}


@cpc_admin_router.get("/ledger")
async def admin_ledger(user_email: Optional[str] = None, admin: dict = Depends(require_admin)):
    q = {}
    if user_email:
        user = await _user_by_email(user_email)
        q["user_id"] = user["id"]
    items = await db.cpc_ledger.find(q, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@cpc_admin_router.get("/purchases")
async def admin_purchases(admin: dict = Depends(require_admin)):
    items = await db.cpc_purchases.find({}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@cpc_admin_router.get("/audit")
async def audit_journal(consultation_id: Optional[str] = None, admin: dict = Depends(require_admin)):
    q = {"consultation_id": consultation_id} if consultation_id else {}
    items = await db.audit_journal.find(q, {"_id": 0}).sort("seq", -1).limit(200).to_list(200)
    return {"items": items}


@cpc_admin_router.get("/audit/verify")
async def audit_verify(admin: dict = Depends(require_admin)):
    from consultation_audit import verify_chain
    return await verify_chain()
