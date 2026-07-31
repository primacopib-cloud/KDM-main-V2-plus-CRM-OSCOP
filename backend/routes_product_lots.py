"""Étiquettes produits (Promo, Solde…), produits en lot, et programmation EN MASSE (catégorie/sous-catégorie/produits)."""
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
product_lots_router = APIRouter(prefix="/api/lolodrive", tags=["Product Lots & Tags"])
db = None

PRODUCT_TAGS = {"PROMO", "SOLDE", "NOUVEAU", "DESTOCKAGE", "EXCLUSIVITE"}


def set_product_lots_database(database):
    global db
    db = database


async def run_tag_expiry(database) -> int:
    """Retire automatiquement les étiquettes dont la date de fin est dépassée (cron 10 min)."""
    res = await database.lolodrive_products.update_many(
        {"tag": {"$ne": None}, "tag_until": {"$ne": None, "$lte": datetime.utcnow()}},
        {"$set": {"tag": None, "tag_until": None}})
    if res.modified_count:
        logger.info("Étiquettes expirées retirées : %s", res.modified_count)
    return res.modified_count


def _parse_tag(payload):
    """Valide {tag, tag_until} → (tag|None, datetime|None)."""
    tag = (payload or {}).get("tag")
    until = None
    if tag:
        tag = str(tag).upper().strip()
        if tag not in PRODUCT_TAGS:
            raise HTTPException(status_code=400, detail=f"Étiquette invalide (choix : {', '.join(sorted(PRODUCT_TAGS))})")
        raw = (payload or {}).get("tag_until")
        if raw:
            try:
                until = datetime.strptime(str(raw)[:10], "%Y-%m-%d") + timedelta(hours=23, minutes=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Date de fin invalide (AAAA-MM-JJ)")
            if until < datetime.utcnow():
                raise HTTPException(status_code=400, detail="La date de fin est déjà passée")
    else:
        tag = None
    return tag, until


def _parse_lot_qty(payload):
    try:
        paid = int(payload.get("paid_qty"))
        free = int(payload.get("free_qty") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantités invalides")
    if not (2 <= paid <= 50) or not (0 <= free <= 20):
        raise HTTPException(status_code=400, detail="Quantités hors limites (payées : 2-50, offertes : 0-20)")
    return paid, free


def _scope_query(payload):
    """Cible d'une opération en masse : liste de skus OU catégorie (+ sous-catégorie)."""
    skus = (payload or {}).get("skus")
    if skus and isinstance(skus, list):
        return {"sku": {"$in": [str(s) for s in skus][:500]}}
    q = {}
    if (payload or {}).get("category"):
        q["category"] = str(payload["category"])
    if (payload or {}).get("subcategory"):
        q["subcategory"] = str(payload["subcategory"])
    if not q:
        raise HTTPException(status_code=400, detail="Cible requise : catégorie, sous-catégorie ou liste de produits")
    return q


async def _create_lot(base, paid, free, price_public=None, price_pass=None):
    """Construit et insère le produit LOT. Lève 409 si le sku existe déjà."""
    total = paid + free
    sku = f"{base['sku']}-LOT{paid}" + (f"P{free}" if free else "")
    if await db.lolodrive_products.find_one({"sku": sku}, {"_id": 1}):
        raise HTTPException(status_code=409, detail=f"Le lot {sku} existe déjà")
    base_pass = base.get("price_pass_cents")
    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()), "sku": sku,
        "name": f"{base['name']} — Lot ×{total}" + (f" ({free} offert{'s' if free > 1 else ''})" if free else ""),
        "is_lot": True, "base_sku": base["sku"], "lot_paid_qty": paid, "lot_free_qty": free, "lot_total_qty": total,
        "price_public_cents": price_public or base.get("price_public_cents", 0) * paid,
        "price_pass_cents": price_pass or (base_pass * paid if base_pass else None),
        "purchase_price_cents": base["purchase_price_cents"] * total if base.get("purchase_price_cents") else None,
        "lot_ref_price_cents": base.get("price_public_cents", 0) * total,
        "lot_ref_pass_cents": base_pass * total if base_pass else None,
        "catalog_type": base.get("catalog_type"), "category": base.get("category"),
        "subcategory": base.get("subcategory"), "brand": base.get("brand"),
        "territories": base.get("territories"), "tva_rate": base.get("tva_rate"),
        "supplier": base.get("supplier"), "supplier_email": base.get("supplier_email"),
        "image_url": base.get("image_url"), "tag": base.get("tag"),
        "stock_qty": 0, "is_active": True, "created_at": now, "updated_at": now,
    }
    await db.lolodrive_products.insert_one({**doc})
    return doc


@product_lots_router.put("/admin/products/{sku}/tag")
async def admin_set_product_tag(sku: str, payload: dict, admin: dict = Depends(require_admin)):
    """Étiquette commerciale (Promo, Solde…) avec date de fin optionnelle — retrait auto à échéance."""
    tag, until = _parse_tag(payload)
    res = await db.lolodrive_products.update_one({"sku": sku}, {"$set": {"tag": tag, "tag_until": until}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "sku": sku, "tag": tag, "tag_until": until.isoformat() if until else None}


@product_lots_router.post("/admin/products/bulk-tag")
async def admin_bulk_tag(payload: dict, admin: dict = Depends(require_admin)):
    """Applique (ou retire, tag=null) une étiquette EN MASSE par catégorie, sous-catégorie ou produits."""
    tag, until = _parse_tag(payload)
    q = _scope_query(payload)
    res = await db.lolodrive_products.update_many(q, {"$set": {"tag": tag, "tag_until": until}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Aucun produit ne correspond à cette cible")
    return {"ok": True, "matched": res.matched_count, "tag": tag,
            "tag_until": until.isoformat() if until else None}


@product_lots_router.post("/admin/products/bulk-create-lot")
async def admin_bulk_create_lot(payload: dict, admin: dict = Depends(require_admin)):
    """Crée des lots EN MASSE pour tous les produits d'une catégorie/sous-catégorie ou d'une sélection."""
    paid, free = _parse_lot_qty(payload)
    q = {**_scope_query(payload), "is_lot": {"$ne": True}}
    created, skipped = [], 0
    async for base in db.lolodrive_products.find(q, {"_id": 0}):
        try:
            doc = await _create_lot(base, paid, free)
            created.append(doc["sku"])
        except HTTPException:
            skipped += 1
    if not created and not skipped:
        raise HTTPException(status_code=404, detail="Aucun produit ne correspond à cette cible")
    return {"ok": True, "created": created, "created_count": len(created), "skipped_existing": skipped}


@product_lots_router.post("/admin/products/create-lot")
async def admin_create_lot(payload: dict, admin: dict = Depends(require_admin)):
    """Crée un produit LOT à partir d'un produit de base : ×N payés + M offerts. Stock indépendant (en lots)."""
    base_sku = str((payload or {}).get("base_sku") or "").strip()
    paid, free = _parse_lot_qty(payload)
    base = await db.lolodrive_products.find_one({"sku": base_sku}, {"_id": 0})
    if not base:
        raise HTTPException(status_code=404, detail="Produit de base introuvable")
    if base.get("is_lot"):
        raise HTTPException(status_code=400, detail="Impossible de créer un lot à partir d'un lot")

    def _price(key):
        v = (payload or {}).get(key)
        if v in (None, ""):
            return None
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Prix invalide")
        if not 0 < v <= 100_000_000:
            raise HTTPException(status_code=400, detail="Prix hors limites")
        return v

    return await _create_lot(base, paid, free, _price("price_public_cents"), _price("price_pass_cents"))


@product_lots_router.get("/admin/promo-stats")
async def admin_promo_stats(days: int = 30, admin: dict = Depends(require_admin)):
    """Bilan des ventes par étiquette promo (tag figé sur chaque ligne au moment de la vente)."""
    days = max(1, min(int(days), 365))
    cutoff = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"paid_at": {"$gte": cutoff}}},
        {"$unwind": "$items"},
        {"$match": {"items.tag": {"$in": sorted(PRODUCT_TAGS)}}},
        {"$group": {
            "_id": {"tag": "$items.tag", "sku": "$items.sku"},
            "name": {"$last": "$items.name"},
            "qty": {"$sum": "$items.qty"},
            "revenue_cents": {"$sum": {"$multiply": ["$items.unit_cents", "$items.qty"]}},
            "orders": {"$addToSet": "$id"},
            "first": {"$min": "$paid_at"}, "last": {"$max": "$paid_at"},
        }},
    ]
    rows = await db.lolodrive_orders.aggregate(pipeline).to_list(500)
    # Base de comparaison : ventes des mêmes produits SANS étiquette sur la même période
    skus = list({r["_id"]["sku"] for r in rows})
    base_by_sku = {}
    if skus:
        base_rows = await db.lolodrive_orders.aggregate([
            {"$match": {"paid_at": {"$gte": cutoff}}},
            {"$unwind": "$items"},
            {"$match": {"items.sku": {"$in": skus}, "items.tag": {"$nin": sorted(PRODUCT_TAGS)}}},
            {"$group": {"_id": "$items.sku", "qty": {"$sum": "$items.qty"}}},
        ]).to_list(500)
        base_by_sku = {r["_id"]: r["qty"] for r in base_rows}
    tags = {}
    for r in rows:
        t = tags.setdefault(r["_id"]["tag"], {"tag": r["_id"]["tag"], "qty": 0, "revenue_cents": 0,
                                              "order_ids": set(), "products": []})
        t["qty"] += r["qty"]
        t["revenue_cents"] += r["revenue_cents"]
        t["order_ids"].update(r["orders"])
        sku = r["_id"]["sku"]
        promo_days = max(1, (r["last"] - r["first"]).days + 1)
        base_qty = base_by_sku.get(sku, 0)
        base_days = max(1, days - promo_days)
        accel = round((r["qty"] / promo_days) / (base_qty / base_days), 1) if base_qty else None
        t["products"].append({"sku": sku, "name": r["name"], "qty": r["qty"],
                              "revenue_cents": r["revenue_cents"], "orders": len(r["orders"]),
                              "base_qty": base_qty, "accel": accel})
    out = []
    for t in tags.values():
        t["orders"] = len(t.pop("order_ids"))
        t["products"].sort(key=lambda x: -x["revenue_cents"])
        out.append(t)
    out.sort(key=lambda x: -x["revenue_cents"])
    return {"days": days, "tags": out,
            "total_revenue_cents": sum(t["revenue_cents"] for t in out),
            "total_qty": sum(t["qty"] for t in out)}
