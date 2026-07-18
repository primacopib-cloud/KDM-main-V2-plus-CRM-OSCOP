"""Promotions de crédits (bonus & réductions) gérées par le super admin — /api/admin/credit-promotions."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

promotions_router = APIRouter(prefix="/api/admin/credit-promotions", tags=["Credit Promotions"])

db = None


def set_promotions_database(database) -> None:
    global db
    db = database


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class PromotionPayload(BaseModel):
    name: str
    promo_type: str  # bonus_purchase | discount_action
    value_percent: float
    scope_profile: str = "all"      # all | vendor | buyer
    scope_territory: str = "ALL"    # ALL | GUADELOUPE | MARTINIQUE | ...
    scope_category: str = "all"     # all | slug catégorie produit
    scope_action: str = "all"       # all | action du barème
    active: bool = True


def _matches(promo: dict, profile: str, territory: str | None, category: str | None, action: str | None) -> bool:
    if promo.get("archived") or not promo.get("active"):
        return False
    if promo.get("scope_profile", "all") not in ("all", profile):
        return False
    if promo.get("scope_territory", "ALL") != "ALL" and territory and promo["scope_territory"] != territory:
        return False
    if promo.get("scope_territory", "ALL") != "ALL" and not territory:
        return False
    if promo.get("scope_category", "all") != "all" and promo["scope_category"] != (category or ""):
        return False
    if promo.get("scope_action", "all") != "all" and promo["scope_action"] != (action or ""):
        return False
    return True


async def get_discount_percent(action: str, profile: str = "vendor",
                               territory: str | None = None, category: str | None = None) -> float:
    """Meilleure réduction active applicable à une consommation."""
    best = 0.0
    async for promo in db.credit_promotions.find({"promo_type": "discount_action", "active": True, "archived": {"$ne": True}}):
        if _matches(promo, profile, territory, category, action):
            best = max(best, float(promo.get("value_percent") or 0))
    return min(best, 100.0)


async def get_purchase_bonus_percent(profile: str = "vendor", territory: str | None = None) -> float:
    """Meilleur bonus actif applicable à un achat de pack de crédits."""
    best = 0.0
    async for promo in db.credit_promotions.find({"promo_type": "bonus_purchase", "active": True, "archived": {"$ne": True}}):
        if _matches(promo, profile, territory, None, None):
            best = max(best, float(promo.get("value_percent") or 0))
    return best


def apply_discount(cost: int, percent: float) -> int:
    return max(0, math.ceil(cost * (1 - percent / 100)))


@promotions_router.get("")
async def list_promotions(include_archived: bool = False, _: dict = Depends(_admin)):
    query = {} if include_archived else {"archived": {"$ne": True}}
    docs = await db.credit_promotions.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"promotions": docs, "total": len(docs)}


@promotions_router.post("")
async def create_promotion(payload: PromotionPayload, admin: dict = Depends(_admin)):
    if payload.promo_type not in ("bonus_purchase", "discount_action"):
        raise HTTPException(status_code=400, detail="Type invalide")
    if not 0 < payload.value_percent <= 100:
        raise HTTPException(status_code=400, detail="Pourcentage invalide (1-100)")
    doc = {
        "id": str(uuid.uuid4()), **payload.model_dump(), "archived": False,
        "created_by": admin["email"], "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.credit_promotions.insert_one({**doc})
    return {"status": "SUCCESS", "promotion": doc}


@promotions_router.put("/{promo_id}")
async def update_promotion(promo_id: str, payload: PromotionPayload, admin: dict = Depends(_admin)):
    result = await db.credit_promotions.update_one(
        {"id": promo_id},
        {"$set": {**payload.model_dump(), "updated_by": admin["email"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}


@promotions_router.post("/{promo_id}/archive")
async def archive_promotion(promo_id: str, _: dict = Depends(_admin)):
    result = await db.credit_promotions.update_one(
        {"id": promo_id}, {"$set": {"archived": True, "active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}


@promotions_router.delete("/{promo_id}")
async def delete_promotion(promo_id: str, _: dict = Depends(_admin)):
    result = await db.credit_promotions.delete_one({"id": promo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}
