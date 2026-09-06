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
    doc = await db.app_settings.find_one({"key": "lolodrive_home_carousel"}, {"_id": 0})
    return {"product_ids": (doc or {}).get("product_ids", []),
            "max_count": (doc or {}).get("max_count", DEFAULT_MAX),
            "promo_percent": (doc or {}).get("promo_percent", 0)}


class CarouselConfig(BaseModel):
    product_ids: list[str] = []
    max_count: int = Field(default=DEFAULT_MAX, ge=1, le=24)
    promo_percent: int = Field(default=0, ge=0, le=90)


@lolodrive_home_router.put("/admin/lolodrive-carousel")
async def set_carousel_config(body: CarouselConfig, admin: dict = Depends(require_admin)):
    await db.app_settings.update_one(
        {"key": "lolodrive_home_carousel"},
        {"$set": {"product_ids": body.product_ids, "max_count": body.max_count,
                  "promo_percent": body.promo_percent,
                  "updated_by": admin.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    return {"saved": True, "product_ids": body.product_ids, "max_count": body.max_count,
            "promo_percent": body.promo_percent}


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
