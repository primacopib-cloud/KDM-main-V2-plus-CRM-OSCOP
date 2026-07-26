"""Produits favoris LOLODRIVE (synchronisés pour les alertes promo email)."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lolodrive_helpers import get_current_user

lolodrive_favorites_router = APIRouter(prefix="/api/lolodrive", tags=["Lolodrive Favorites"])
db = None


def set_lolodrive_favorites_database(database):
    global db
    db = database


class FavBody(BaseModel):
    skus: List[str] = []


@lolodrive_favorites_router.get("/favorites")
async def get_favorites(user: dict = Depends(get_current_user)):
    doc = await db.lolodrive_favorites.find_one({"user_id": user["id"]}, {"_id": 0, "skus": 1})
    return {"skus": (doc or {}).get("skus", [])}


@lolodrive_favorites_router.post("/favorites")
async def save_favorites(body: FavBody, user: dict = Depends(get_current_user)):
    skus = [s for s in body.skus if isinstance(s, str) and s][:100]
    await db.lolodrive_favorites.update_one(
        {"user_id": user["id"]},
        {"$set": {"skus": skus, "updated_at": datetime.utcnow()}},
        upsert=True)
    return {"ok": True, "count": len(skus)}
