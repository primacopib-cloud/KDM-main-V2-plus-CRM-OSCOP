"""Taxonomie LOLODRIVE (catégories → sous-catégories, gérées par le super admin) + frais de retrait/livraison par créneau."""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
taxonomy_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE Taxonomy & Fees"])
db = None


def set_taxonomy_database(database):
    global db
    db = database


DEFAULT_CATEGORIES = [
    {"name": "Épicerie", "subcategories": ["Riz & féculents", "Farines & sucres", "Huiles & condiments",
                                           "Petit-déjeuner & douceurs", "Conserves & bocaux",
                                           "Cafés, thés & laits", "Épices & vanille"]},
    {"name": "Boissons", "subcategories": ["Jus & boissons locales", "Rhums & spiritueux", "Eaux & sodas"]},
    {"name": "Frais", "subcategories": ["Fruits & légumes", "Viandes & volailles", "Œufs & produits laitiers"]},
    {"name": "Cuisine", "subcategories": ["Sauces & aides culinaires", "Épices locales"]},
]

SUBCAT_BACKFILL = {
    "RIZ-5KG": "Riz & féculents", "PATES-500G": "Riz & féculents", "MANIOC-500G": "Riz & féculents",
    "FARINE-1KG": "Farines & sucres", "SUCRE-1KG": "Farines & sucres", "SUCRE-CANNE-RE-1KG": "Farines & sucres",
    "HUILE-1L": "Huiles & condiments",
    "NUTELLA-400G": "Petit-déjeuner & douceurs",
    "CAFE-250G": "Cafés, thés & laits", "LAIT-1L": "Cafés, thés & laits",
    "VANILLE-BOURBON-3G": "Épices & vanille",
    "ACHARDS-LEGUMES-200G": "Conserves & bocaux",
    "JUS-MANGUE-1L": "Jus & boissons locales", "CACHIRI-1L": "Jus & boissons locales",
    "RHUM-AGRICOLE-70CL": "Rhums & spiritueux",
    "OEUFS-12": "Œufs & produits laitiers", "POULET-1KG": "Viandes & volailles", "BANANE-1KG": "Fruits & légumes",
    "TOMACOULI-500G": "Sauces & aides culinaires",
}


async def ensure_categories():
    """Seed idempotent des catégories + backfill des sous-catégories sur les produits démo."""
    if await db.lolodrive_categories.count_documents({}) == 0:
        for i, c in enumerate(DEFAULT_CATEGORIES):
            await db.lolodrive_categories.insert_one(
                {"id": str(uuid.uuid4()), "name": c["name"], "subcategories": c["subcategories"], "position": i})
    for sku, sub in SUBCAT_BACKFILL.items():
        await db.lolodrive_products.update_one(
            {"sku": sku, "$or": [{"subcategory": {"$exists": False}}, {"subcategory": None}]},
            {"$set": {"subcategory": sub}})
    await db.lolodrive_products.update_many(
        {"sku": "RHUM-AGRICOLE-70CL", "tva_rate": {"$exists": False}}, {"$set": {"tva_rate": 20.0}})
    await db.lolodrive_products.update_many(
        {"$or": [{"tva_rate": {"$exists": False}}, {"tva_rate": None}]}, {"$set": {"tva_rate": 8.5}})


@taxonomy_router.get("/categories")
async def list_categories():
    await ensure_categories()
    cats = await db.lolodrive_categories.find({}, {"_id": 0}).sort("position", 1).to_list(100)
    return {"categories": cats}


class CategoryBody(BaseModel):
    name: str
    subcategories: list = []


@taxonomy_router.post("/admin/categories")
async def create_category(body: CategoryBody, admin: dict = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom de catégorie requis")
    if await db.lolodrive_categories.find_one({"name": name}):
        raise HTTPException(status_code=400, detail="Cette catégorie existe déjà")
    count = await db.lolodrive_categories.count_documents({})
    doc = {"id": str(uuid.uuid4()), "name": name,
           "subcategories": [s.strip() for s in body.subcategories if s and s.strip()], "position": count}
    await db.lolodrive_categories.insert_one(doc)
    doc.pop("_id", None)
    return doc


@taxonomy_router.put("/admin/categories/{cid}")
async def update_category(cid: str, body: CategoryBody, admin: dict = Depends(require_admin)):
    cat = await db.lolodrive_categories.find_one({"id": cid}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    name = body.name.strip() or cat["name"]
    subs = [s.strip() for s in body.subcategories if s and s.strip()]
    await db.lolodrive_categories.update_one({"id": cid}, {"$set": {"name": name, "subcategories": subs}})
    if name != cat["name"]:
        await db.lolodrive_products.update_many({"category": cat["name"]}, {"$set": {"category": name}})
    return {"ok": True, "id": cid, "name": name, "subcategories": subs}


@taxonomy_router.delete("/admin/categories/{cid}")
async def delete_category(cid: str, admin: dict = Depends(require_admin)):
    cat = await db.lolodrive_categories.find_one({"id": cid}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    used = await db.lolodrive_products.count_documents({"category": cat["name"]})
    if used:
        raise HTTPException(status_code=400, detail=f"{used} produit(s) utilisent encore cette catégorie")
    await db.lolodrive_categories.delete_one({"id": cid})
    return {"ok": True}


# =======================
# Frais de retrait Drive / livraison par créneau (configurables super admin)
# =======================

DEFAULT_FEES = {
    "pickup_slots": [
        {"id": "AM", "label": "Matin — 8h00 à 12h00", "start": "08:00", "end": "12:00"},
        {"id": "PM", "label": "Après-midi — 12h01 à 20h00", "start": "12:01", "end": "20:00"},
    ],
    "delivery_slots": [
        {"id": "AM", "label": "Matin — 8h00 à 12h00", "start": "08:00", "end": "12:00"},
        {"id": "PM", "label": "Après-midi — 12h01 à 20h00", "start": "12:01", "end": "20:00"},
    ],
    # UC par article, par catégorie ("*" = tarif par défaut toutes catégories) et par créneau
    "pickup_rates": {"*": {"AM": 0.6, "PM": 19}},
    "delivery_rates": {"*": {"AM": 0.6, "PM": 19}},
    # Pénalité de non-retrait après le créneau : UC par article, par catégorie (1 UC = 0,10 €)
    "penalty_rates": {"*": 1},
}


async def get_fees_config_doc() -> dict:
    doc = await db.lolodrive_settings.find_one({"key": "drive_fees"}, {"_id": 0})
    if not doc:
        await db.lolodrive_settings.update_one(
            {"key": "drive_fees"}, {"$setOnInsert": {"key": "drive_fees", "value": DEFAULT_FEES}}, upsert=True)
        return DEFAULT_FEES
    cfg = doc.get("value", DEFAULT_FEES)
    if "penalty_rates" not in cfg:
        cfg["penalty_rates"] = DEFAULT_FEES["penalty_rates"]
    return cfg


def compute_slot_fee_uc(cfg: dict, kind: str, slot_id: str, lines: list, cat_by_sku: dict) -> float:
    """Frais UC = Σ (qty × tarif[catégorie][créneau]), fallback tarif '*'."""
    rates = cfg.get(f"{kind}_rates", {}) or {}
    default = rates.get("*", {}) or {}
    fee = 0.0
    for l in lines:
        cat = cat_by_sku.get(l.get("sku")) or "*"
        rate = (rates.get(cat, {}) or {}).get(slot_id, default.get(slot_id, 0)) or 0
        fee += float(rate) * l.get("qty", 0)
    return round(fee, 2)


async def slot_fee_for_order(kind: str, slot_id: Optional[str], lines: list):
    """Retourne (fee_uc, slot_label) pour une commande, 0 si pas de créneau."""
    if not slot_id:
        return 0.0, None
    cfg = await get_fees_config_doc()
    slot = next((s for s in cfg.get(f"{kind}_slots", []) if s.get("id") == slot_id), None)
    if not slot:
        return 0.0, None
    skus = [l["sku"] for l in lines]
    prods = await db.lolodrive_products.find({"sku": {"$in": skus}}, {"_id": 0, "sku": 1, "category": 1}).to_list(300)
    cat_by_sku = {p["sku"]: p.get("category") for p in prods}
    return compute_slot_fee_uc(cfg, kind, slot_id, lines, cat_by_sku), slot.get("label")


async def compute_penalty_uc(lines: list) -> float:
    """Pénalité de non-retrait : Σ (qty × tarif_pénalité[catégorie]), fallback '*'."""
    cfg = await get_fees_config_doc()
    rates = cfg.get("penalty_rates", {}) or {}
    default = rates.get("*", 1)
    skus = [l["sku"] for l in lines]
    prods = await db.lolodrive_products.find({"sku": {"$in": skus}}, {"_id": 0, "sku": 1, "category": 1}).to_list(300)
    cat_by_sku = {p["sku"]: p.get("category") for p in prods}
    fee = 0.0
    for l in lines:
        rate = rates.get(cat_by_sku.get(l.get("sku")) or "*", default) or 0
        fee += float(rate) * l.get("qty", 0)
    return round(fee, 2)


@taxonomy_router.get("/fees-config")
async def public_fees_config(user: dict = Depends(get_current_user)):
    return await get_fees_config_doc()


@taxonomy_router.put("/admin/fees-config")
async def update_fees_config(payload: dict, admin: dict = Depends(require_admin)):
    cfg = await get_fees_config_doc()
    for key in ("pickup_slots", "delivery_slots"):
        if key in payload:
            slots = [s for s in payload[key] if isinstance(s, dict) and s.get("id") and s.get("label")]
            if not slots:
                raise HTTPException(status_code=400, detail=f"{key} : au moins un créneau requis")
            cfg[key] = slots
    for key in ("pickup_rates", "delivery_rates"):
        if key in payload:
            clean = {}
            for cat, by_slot in (payload[key] or {}).items():
                if not isinstance(by_slot, dict):
                    continue
                entry = {}
                for sid, rate in by_slot.items():
                    try:
                        r = float(rate)
                    except (TypeError, ValueError):
                        continue
                    if 0 <= r <= 100000:
                        entry[sid] = r
                if entry:
                    clean[cat] = entry
            if "*" not in clean:
                raise HTTPException(status_code=400, detail=f"{key} : le tarif par défaut '*' est requis")
            cfg[key] = clean
    if "penalty_rates" in payload:
        clean = {}
        for cat, rate in (payload["penalty_rates"] or {}).items():
            try:
                r = float(rate)
            except (TypeError, ValueError):
                continue
            if 0 <= r <= 100000:
                clean[cat] = r
        if "*" not in clean:
            raise HTTPException(status_code=400, detail="penalty_rates : le tarif par défaut '*' est requis")
        cfg["penalty_rates"] = clean
    await db.lolodrive_settings.update_one({"key": "drive_fees"}, {"$set": {"value": cfg}}, upsert=True)
    return {"ok": True, "config": cfg}
