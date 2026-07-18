"""Super Admin — CRUD des packs de crédits wallet (dialog 'Acheter des crédits')."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from admin_plans_common import get_current_admin_from_request, slugify
from payment_models import CREDIT_PACKAGES

wallet_packs_router = APIRouter(prefix="/api/admin/wallet-packs", tags=["Admin - Wallet Credit Packs"])

db = None


def set_wallet_packs_database(database):
    global db
    db = database


async def ensure_wallet_packs_seed():
    if await db.wallet_credit_packs.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        await db.wallet_credit_packs.insert_many([
            {**p, "active": True, "sort_order": i, "created_at": now, "updated_at": now}
            for i, p in enumerate(CREDIT_PACKAGES.values())
        ])


async def get_active_wallet_packs() -> list:
    await ensure_wallet_packs_seed()
    return await db.wallet_credit_packs.find(
        {"active": True}, {"_id": 0}
    ).sort("sort_order", 1).to_list(50)


async def get_wallet_pack(pack_id: str) -> Optional[dict]:
    await ensure_wallet_packs_seed()
    return await db.wallet_credit_packs.find_one({"id": pack_id, "active": True}, {"_id": 0})


class WalletPackCreate(BaseModel):
    name: str
    credits: int
    price: float
    description: Optional[str] = ""
    popular: bool = False
    active: bool = True
    sort_order: int = 0


class WalletPackUpdate(BaseModel):
    name: Optional[str] = None
    credits: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None
    popular: Optional[bool] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


async def _require_admin(request: Request) -> dict:
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return admin


@wallet_packs_router.get("")
async def list_wallet_packs(request: Request):
    await _require_admin(request)
    await ensure_wallet_packs_seed()
    packs = await db.wallet_credit_packs.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    purchases = {
        r["_id"]: r["count"]
        async for r in db.payment_transactions.aggregate([
            {"$match": {"payment_status": "paid", "package_id": {"$ne": None}}},
            {"$group": {"_id": "$package_id", "count": {"$sum": 1}}},
        ])
    }
    for p in packs:
        p["purchases_count"] = purchases.get(p["id"], 0)
    return {"packs": packs}


@wallet_packs_router.post("")
async def create_wallet_pack(request: Request, payload: WalletPackCreate):
    await _require_admin(request)
    await ensure_wallet_packs_seed()
    if payload.credits <= 0 or payload.price <= 0:
        raise HTTPException(status_code=400, detail="Crédits et prix doivent être positifs")
    pack_id = slugify(payload.name)
    if await db.wallet_credit_packs.find_one({"id": pack_id}):
        raise HTTPException(status_code=409, detail=f"Un pack '{pack_id}' existe déjà")
    now = datetime.now(timezone.utc)
    doc = {"id": pack_id, **payload.dict(), "created_at": now, "updated_at": now}
    await db.wallet_credit_packs.insert_one(doc)
    doc.pop("_id", None)
    return doc


@wallet_packs_router.patch("/{pack_id}")
async def update_wallet_pack(request: Request, pack_id: str, payload: WalletPackUpdate):
    await _require_admin(request)
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification fournie")
    if "credits" in updates and updates["credits"] <= 0:
        raise HTTPException(status_code=400, detail="Crédits doivent être positifs")
    if "price" in updates and updates["price"] <= 0:
        raise HTTPException(status_code=400, detail="Prix doit être positif")
    updates["updated_at"] = datetime.now(timezone.utc)
    result = await db.wallet_credit_packs.update_one({"id": pack_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    return await db.wallet_credit_packs.find_one({"id": pack_id}, {"_id": 0})


@wallet_packs_router.delete("/{pack_id}")
async def delete_wallet_pack(request: Request, pack_id: str):
    await _require_admin(request)
    result = await db.wallet_credit_packs.delete_one({"id": pack_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    return {"message": f"Pack '{pack_id}' supprimé"}
