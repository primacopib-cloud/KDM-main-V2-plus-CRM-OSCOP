"""Étiquettes produits (Promo, Solde, Nouveau…) + création de produits en lot (×2, ×3+1 offert…)."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
product_lots_router = APIRouter(prefix="/api/lolodrive", tags=["Product Lots & Tags"])
db = None

PRODUCT_TAGS = {"PROMO", "SOLDE", "NOUVEAU", "DESTOCKAGE", "EXCLUSIVITE"}


def set_product_lots_database(database):
    global db
    db = database


@product_lots_router.put("/admin/products/{sku}/tag")
async def admin_set_product_tag(sku: str, payload: dict, admin: dict = Depends(require_admin)):
    """Étiquette commerciale d'un produit (Promo, Solde, Nouveau, Déstockage, Exclusivité) — null pour retirer."""
    tag = (payload or {}).get("tag")
    if tag:
        tag = str(tag).upper().strip()
        if tag not in PRODUCT_TAGS:
            raise HTTPException(status_code=400, detail=f"Étiquette invalide (choix : {', '.join(sorted(PRODUCT_TAGS))})")
    else:
        tag = None
    res = await db.lolodrive_products.update_one({"sku": sku}, {"$set": {"tag": tag}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "sku": sku, "tag": tag}


@product_lots_router.post("/admin/products/create-lot")
async def admin_create_lot(payload: dict, admin: dict = Depends(require_admin)):
    """Crée un produit LOT à partir d'un produit de base : ×N payés + M offerts. Stock indépendant (en lots)."""
    base_sku = str((payload or {}).get("base_sku") or "").strip()
    try:
        paid = int(payload.get("paid_qty"))
        free = int(payload.get("free_qty") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantités invalides")
    if not (2 <= paid <= 50) or not (0 <= free <= 20):
        raise HTTPException(status_code=400, detail="Quantités hors limites (payées : 2-50, offertes : 0-20)")
    base = await db.lolodrive_products.find_one({"sku": base_sku}, {"_id": 0})
    if not base:
        raise HTTPException(status_code=404, detail="Produit de base introuvable")
    if base.get("is_lot"):
        raise HTTPException(status_code=400, detail="Impossible de créer un lot à partir d'un lot")
    total = paid + free
    sku = f"{base_sku}-LOT{paid}" + (f"P{free}" if free else "")
    if await db.lolodrive_products.find_one({"sku": sku}, {"_id": 1}):
        raise HTTPException(status_code=409, detail=f"Le lot {sku} existe déjà")

    def _price(key, default):
        v = (payload or {}).get(key)
        if v in (None, ""):
            return default
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Prix invalide")
        if not 0 < v <= 100_000_000:
            raise HTTPException(status_code=400, detail="Prix hors limites")
        return v

    price_public = _price("price_public_cents", base.get("price_public_cents", 0) * paid)
    base_pass = base.get("price_pass_cents")
    price_pass = _price("price_pass_cents", base_pass * paid if base_pass else None) if base_pass or payload.get("price_pass_cents") else None
    name = f"{base['name']} — Lot ×{total}" + (f" ({free} offert{'s' if free > 1 else ''})" if free else "")
    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()), "sku": sku, "name": name,
        "is_lot": True, "base_sku": base_sku, "lot_paid_qty": paid, "lot_free_qty": free, "lot_total_qty": total,
        "price_public_cents": price_public, "price_pass_cents": price_pass,
        "purchase_price_cents": base["purchase_price_cents"] * total if base.get("purchase_price_cents") else None,
        "catalog_type": base.get("catalog_type"), "category": base.get("category"),
        "subcategory": base.get("subcategory"), "brand": base.get("brand"),
        "territories": base.get("territories"), "tva_rate": base.get("tva_rate"),
        "supplier": base.get("supplier"), "supplier_email": base.get("supplier_email"),
        "image_url": base.get("image_url"), "tag": base.get("tag"),
        "stock_qty": 0, "is_active": True, "created_at": now, "updated_at": now,
    }
    await db.lolodrive_products.insert_one({**doc})
    return doc
