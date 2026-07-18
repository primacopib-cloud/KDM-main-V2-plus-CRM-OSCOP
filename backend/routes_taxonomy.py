"""Taxonomie gérée par le super admin : catégories produits + taux de TVA — /api/taxonomy/*."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

taxonomy_router = APIRouter(prefix="/api/taxonomy", tags=["Taxonomy"])

db = None

DEFAULT_CATEGORIES = [
    ("alimentaire", "Alimentaire"), ("boissons", "Boissons"), ("hygiene", "Hygiène & Beauté"),
    ("entretien", "Entretien"), ("fournitures", "Fournitures"), ("textile", "Textile"),
    ("equipement", "Équipement"), ("autre", "Autre"),
]
DEFAULT_TVA_RATES = [
    (0.0, "0% (Exonéré)"), (2.1, "2,1% (Super réduit)"), (5.5, "5,5% (Réduit)"),
    (8.5, "8,5% (DOM)"), (10.0, "10% (Intermédiaire)"), (20.0, "20% (Normal)"),
]


def set_taxonomy_database(database) -> None:
    global db
    db = database


async def seed_taxonomy() -> None:
    now = datetime.now(timezone.utc).isoformat()
    if await db.product_categories.count_documents({}) == 0:
        await db.product_categories.insert_many([
            {"id": str(uuid.uuid4()), "value": v, "label": lbl, "builtin": True, "created_at": now}
            for v, lbl in DEFAULT_CATEGORIES
        ])
    if await db.tva_rates.count_documents({}) == 0:
        await db.tva_rates.insert_many([
            {"id": str(uuid.uuid4()), "value": v, "label": lbl, "builtin": True, "created_at": now}
            for v, lbl in DEFAULT_TVA_RATES
        ])


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class CategoryPayload(BaseModel):
    label: str


class TvaPayload(BaseModel):
    value: float
    label: str


@taxonomy_router.get("/categories")
async def list_categories():
    docs = await db.product_categories.find({}, {"_id": 0}).sort("label", 1).to_list(100)
    return {"categories": docs}


@taxonomy_router.post("/categories")
async def add_category(payload: CategoryPayload, admin: dict = Depends(_admin)):
    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="Libellé requis")
    value = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if await db.product_categories.find_one({"value": value}):
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà")
    doc = {"id": str(uuid.uuid4()), "value": value, "label": label, "builtin": False,
           "created_by": admin["email"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.product_categories.insert_one({**doc})
    return {"status": "SUCCESS", "category": doc}


@taxonomy_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, _: dict = Depends(_admin)):
    result = await db.product_categories.delete_one({"id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    return {"status": "SUCCESS"}


@taxonomy_router.get("/tva-rates")
async def list_tva_rates():
    docs = await db.tva_rates.find({}, {"_id": 0}).sort("value", 1).to_list(50)
    return {"rates": docs}


@taxonomy_router.post("/tva-rates")
async def add_tva_rate(payload: TvaPayload, admin: dict = Depends(_admin)):
    if payload.value < 0 or payload.value > 100:
        raise HTTPException(status_code=400, detail="Taux invalide (0-100)")
    if await db.tva_rates.find_one({"value": payload.value}):
        raise HTTPException(status_code=409, detail="Ce taux existe déjà")
    doc = {"id": str(uuid.uuid4()), "value": payload.value, "label": payload.label.strip() or f"{payload.value}%",
           "builtin": False, "created_by": admin["email"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.tva_rates.insert_one({**doc})
    return {"status": "SUCCESS", "rate": doc}


@taxonomy_router.delete("/tva-rates/{rate_id}")
async def delete_tva_rate(rate_id: str, _: dict = Depends(_admin)):
    result = await db.tva_rates.delete_one({"id": rate_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Taux introuvable")
    return {"status": "SUCCESS"}
