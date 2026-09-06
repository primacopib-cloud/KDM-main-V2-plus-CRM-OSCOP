"""Accueil particuliers LOLODRIVE : carrousel configurable + statut PASS."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from lolodrive_helpers import require_admin

lolodrive_home_router = APIRouter(prefix="/api", tags=["LOLODRIVE Home"])
db = None


def set_lolodrive_home_database(database):
    global db
    db = database

DEFAULT_MAX = 12


@lolodrive_home_router.get("/public/lolodrive-carousel")
async def get_carousel_config():
    doc = await db.app_settings.find_one({"key": "lolodrive_home_carousel"}, {"_id": 0}) or {}
    promo = doc.get("promo_percent", 0)
    ends_at = doc.get("promo_ends_at")
    if ends_at:
        try:
            if datetime.fromisoformat(ends_at) <= datetime.now(timezone.utc):
                promo = 0
        except ValueError:
            ends_at = None
    return {"product_ids": doc.get("product_ids", []),
            "max_count": doc.get("max_count", DEFAULT_MAX),
            "promo_percent": promo,
            "promo_ends_at": ends_at if promo else None}


class CarouselConfig(BaseModel):
    product_ids: list[str] = []
    max_count: int = Field(default=DEFAULT_MAX, ge=1, le=24)
    promo_percent: int = Field(default=0, ge=0, le=90)
    promo_ends_at: str | None = None


@lolodrive_home_router.put("/admin/lolodrive-carousel")
async def set_carousel_config(body: CarouselConfig, admin: dict = Depends(require_admin)):
    ends_at = None
    if body.promo_ends_at:
        try:
            parsed = datetime.fromisoformat(body.promo_ends_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            ends_at = parsed.isoformat()
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Date de fin de promo invalide")
    await db.app_settings.update_one(
        {"key": "lolodrive_home_carousel"},
        {"$set": {"product_ids": body.product_ids, "max_count": body.max_count,
                  "promo_percent": body.promo_percent, "promo_ends_at": ends_at,
                  "updated_by": admin.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    return {"saved": True, "product_ids": body.product_ids, "max_count": body.max_count,
            "promo_percent": body.promo_percent, "promo_ends_at": ends_at}


@lolodrive_home_router.get("/admin/lolodrive-carousel/pass-clicks")
async def pass_clicks(admin: dict = Depends(require_admin)):
    """Clics PASS depuis le carrousel vs achats réels de PASS (taux de conversion)."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    q = {"cta_id": "pass_lolodrive"}
    total = await db.cta_clicks.count_documents(q)
    d7 = await db.cta_clicks.count_documents({**q, "at": {"$gte": (now - timedelta(days=7)).isoformat()}})
    d30 = await db.cta_clicks.count_documents({**q, "at": {"$gte": (now - timedelta(days=30)).isoformat()}})
    p_total = await db.lolodrive_passes.count_documents({})
    naive30 = (now - timedelta(days=30)).replace(tzinfo=None)
    naive7 = (now - timedelta(days=7)).replace(tzinfo=None)
    p30 = await db.lolodrive_passes.count_documents({"created_at": {"$gte": naive30}})
    p7 = await db.lolodrive_passes.count_documents({"created_at": {"$gte": naive7}})
    conv = round(p30 / d30 * 100, 1) if d30 else None
    return {"total": total, "last_7d": d7, "last_30d": d30,
            "purchases_total": p_total, "purchases_30d": p30, "purchases_7d": p7,
            "conversion_30d_percent": conv}


@lolodrive_home_router.get("/public/lolodrive-pass/active")
async def pass_active(request: Request):
    """Statut PASS LOLODRIVE de l'utilisateur connecté (false pour un visiteur)."""
    from routes_catalog import get_current_user_catalog_optional
    user = await get_current_user_catalog_optional(request)
    if not user:
        return {"active": False}
    now = datetime.utcnow()
    doc = await db.lolodrive_passes.find_one(
        {"user_id": user["id"], "status": "ACTIVE", "ends_at": {"$gt": now}})
    return {"active": bool(doc) or bool(user.get("is_admin"))}
