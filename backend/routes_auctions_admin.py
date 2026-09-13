"""Administration des enchères produits à prix descendant (superadmin)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
import auction_helpers as ah

logger = logging.getLogger(__name__)

auctions_admin_router = APIRouter(prefix="/api/admin/auctions", tags=["auctions-admin"])

DEFAULT_TYPES = [
    {"id": "auc-type-standard", "label": "Standard — mise 10 crédits / −1 €",
     "bid_cost_credits": 10, "price_drop_eur": 1.0, "active": True},
]
DEFAULT_PLANS = [
    {"id": "auc-plan-decouverte", "label": "CREDI'SCOP Enchères Découverte",
     "price_ht_cents": 990, "credits": 100, "validity_days": 30, "active": True},
    {"id": "auc-plan-passion", "label": "CREDI'SCOP Enchères Passion",
     "price_ht_cents": 2900, "credits": 400, "validity_days": 30, "active": True},
    {"id": "auc-plan-premium", "label": "CREDI'SCOP Enchères Premium",
     "price_ht_cents": 5900, "credits": 1000, "validity_days": 30, "active": True},
]


async def ensure_auction_defaults():
    now = datetime.now(timezone.utc).isoformat()
    for t in DEFAULT_TYPES:
        await ah.db.auction_types.update_one(
            {"id": t["id"]}, {"$setOnInsert": {**t, "created_at": now}}, upsert=True)
    for p in DEFAULT_PLANS:
        await ah.db.auction_plans.update_one(
            {"id": p["id"]}, {"$setOnInsert": {**p, "created_at": now}}, upsert=True)


# ---------- Sélecteur de produits (catalogue LOLODRIVE + catalogue vendeurs) ----------

@auctions_admin_router.get("/products")
async def pick_products(source: str = "lolodrive", q: str = "", admin: dict = Depends(require_admin)):
    q = q.strip()
    items = []
    if source == "lolodrive":
        query = {"is_active": {"$ne": False}}
        if q:
            query["name"] = {"$regex": q, "$options": "i"}
        async for p in ah.db.lolodrive_products.find(query, {"_id": 0}).sort("name", 1).limit(40):
            items.append({"product_id": p["id"], "name": p["name"], "image_url": p.get("image_url"),
                          "value_eur": round((p.get("price_public_cents") or 0) / 100, 2),
                          "category": p.get("category"), "sku": p.get("sku")})
    else:
        query = {"status": "approved"}
        if q:
            query["name"] = {"$regex": q, "$options": "i"}
        async for p in ah.db.vendor_products.find(query, {"_id": 0}).sort("name", 1).limit(40):
            img = (p.get("images") or [{}])[0].get("url") if p.get("images") else None
            items.append({"product_id": p["id"], "name": p["name"], "image_url": img,
                          "value_eur": round((p.get("price_ttc_cents") or 0) / 100, 2),
                          "category": p.get("category"), "sku": p.get("sku")})
    return {"items": items}


# ---------- Enchères ----------

class AuctionBody(BaseModel):
    title: str
    image_url: Optional[str] = None
    description: str = ""
    source: str = "LOLODRIVE"
    source_visible: bool = True
    product_id: Optional[str] = None
    category_id: Optional[str] = None
    type_id: Optional[str] = None
    value_eur: float
    floor_eur: float = 0
    bid_cost_credits: int = 10
    price_drop_eur: float = 1.0
    starts_at: str
    ends_at: str
    recurrence: str = "NONE"


def _validate(body: AuctionBody):
    if body.source not in ah.SOURCES:
        raise HTTPException(status_code=400, detail=f"Provenance invalide ({'/'.join(ah.SOURCES)})")
    if body.recurrence not in ah.RECURRENCES:
        raise HTTPException(status_code=400, detail="Récurrence invalide (NONE/DAILY/MONTHLY/YEARLY)")
    if body.value_eur <= 0:
        raise HTTPException(status_code=400, detail="La valeur du produit doit être positive")
    if body.floor_eur < 0 or body.floor_eur >= body.value_eur:
        raise HTTPException(status_code=400, detail="Le prix plancher doit être ≥ 0 et inférieur à la valeur")
    if body.bid_cost_credits <= 0 or body.price_drop_eur <= 0:
        raise HTTPException(status_code=400, detail="Coût de mise et baisse de prix doivent être positifs")
    starts, ends = ah.parse_dt(body.starts_at), ah.parse_dt(body.ends_at)
    if not starts or not ends or ends <= starts:
        raise HTTPException(status_code=400, detail="Dates invalides : la fin doit être après le début")
    return starts, ends


@auctions_admin_router.get("")
async def list_auctions(admin: dict = Depends(require_admin)):
    await ensure_auction_defaults()
    await ah.sync_auction_statuses()
    items = await ah.db.auctions.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for a in items:
        a["status"] = ah.effective_status(a)
        a["price_credits"] = ah.eur_to_credits(a.get("current_price_eur") or 0)
    return {"items": items, "labels": await ah.taxonomy_labels()}


@auctions_admin_router.post("")
async def create_auction(body: AuctionBody, admin: dict = Depends(require_admin)):
    starts, ends = _validate(body)
    now = ah.now_utc()
    doc = {
        **body.dict(), "id": str(uuid.uuid4()),
        "reference": f"AUC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        "starts_at": starts.isoformat(), "ends_at": ends.isoformat(),
        "status": "SCHEDULED", "current_price_eur": body.value_eur, "bids_count": 0,
        "created_by": admin.get("email"), "created_at": now.isoformat(),
    }
    await ah.db.auctions.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@auctions_admin_router.put("/{auction_id}")
async def update_auction(auction_id: str, body: AuctionBody, admin: dict = Depends(require_admin)):
    starts, ends = _validate(body)
    a = await ah.db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Enchère introuvable")
    if a.get("status") in ("WON", "CANCELLED"):
        raise HTTPException(status_code=409, detail="Enchère terminée : créez-en une nouvelle")
    updates = {**body.dict(), "starts_at": starts.isoformat(), "ends_at": ends.isoformat(),
               "updated_at": ah.now_utc().isoformat()}
    if a.get("bids_count", 0) == 0:
        updates["current_price_eur"] = body.value_eur
    await ah.db.auctions.update_one({"id": auction_id}, {"$set": updates})
    return {"ok": True}


@auctions_admin_router.post("/{auction_id}/cancel")
async def cancel_auction(auction_id: str, admin: dict = Depends(require_admin)):
    res = await ah.db.auctions.update_one(
        {"id": auction_id, "status": {"$in": ["SCHEDULED", "LIVE"]}},
        {"$set": {"status": "CANCELLED", "cancelled_at": ah.now_utc().isoformat(),
                  "cancelled_by": admin.get("email")}})
    if res.modified_count == 0:
        raise HTTPException(status_code=409, detail="Enchère déjà terminée ou annulée")
    return {"ok": True}


# ---------- Catégories & types d'enchères ----------

class LabelBody(BaseModel):
    label: str
    active: bool = True
    sort_order: int = 10


class TypeBody(LabelBody):
    bid_cost_credits: int = 10
    price_drop_eur: float = 1.0


def _taxo(kind: str):
    return ah.db.auction_categories if kind == "categories" else ah.db.auction_types


@auctions_admin_router.get("/taxonomy/{kind}")
async def list_taxonomy(kind: str, admin: dict = Depends(require_admin)):
    if kind not in ("categories", "types"):
        raise HTTPException(status_code=404, detail="Inconnu")
    items = await _taxo(kind).find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return {"items": items}


@auctions_admin_router.post("/taxonomy/categories")
async def create_category(body: LabelBody, admin: dict = Depends(require_admin)):
    doc = {**body.dict(), "id": str(uuid.uuid4()), "created_at": ah.now_utc().isoformat()}
    await ah.db.auction_categories.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@auctions_admin_router.post("/taxonomy/types")
async def create_type(body: TypeBody, admin: dict = Depends(require_admin)):
    if body.bid_cost_credits <= 0 or body.price_drop_eur <= 0:
        raise HTTPException(status_code=400, detail="Valeurs de mise invalides")
    doc = {**body.dict(), "id": str(uuid.uuid4()), "created_at": ah.now_utc().isoformat()}
    await ah.db.auction_types.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@auctions_admin_router.put("/taxonomy/{kind}/{item_id}")
async def update_taxonomy(kind: str, item_id: str, body: dict, admin: dict = Depends(require_admin)):
    if kind not in ("categories", "types"):
        raise HTTPException(status_code=404, detail="Inconnu")
    allowed = {k: v for k, v in (body or {}).items()
               if k in ("label", "active", "sort_order", "bid_cost_credits", "price_drop_eur")}
    if not allowed:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    res = await _taxo(kind).update_one({"id": item_id}, {"$set": allowed})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    return {"ok": True}


@auctions_admin_router.delete("/taxonomy/{kind}/{item_id}")
async def delete_taxonomy(kind: str, item_id: str, admin: dict = Depends(require_admin)):
    if kind not in ("categories", "types"):
        raise HTTPException(status_code=404, detail="Inconnu")
    field = "category_id" if kind == "categories" else "type_id"
    used = await ah.db.auctions.count_documents({field: item_id})
    if used:
        raise HTTPException(status_code=400, detail=f"{used} enchère(s) utilisent cet élément : désactivez-le plutôt")
    await _taxo(kind).delete_one({"id": item_id})
    return {"deleted": True}


# ---------- Plans CREDI'SCOP-Enchères ----------

class PlanBody(BaseModel):
    label: str
    price_ht_cents: int
    credits: int
    validity_days: int = 30
    active: bool = True


@auctions_admin_router.get("/plans")
async def admin_plans(admin: dict = Depends(require_admin)):
    await ensure_auction_defaults()
    items = await ah.db.auction_plans.find({}, {"_id": 0}).sort("price_ht_cents", 1).to_list(20)
    subs = await ah.db.auction_pass_purchases.find(
        {"status": "ACTIVE"}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"items": items, "purchases": subs}


@auctions_admin_router.post("/plans")
async def create_plan(body: PlanBody, admin: dict = Depends(require_admin)):
    if body.price_ht_cents <= 0 or body.credits <= 0 or body.validity_days <= 0:
        raise HTTPException(status_code=400, detail="Valeurs de plan invalides")
    doc = {**body.dict(), "id": f"auc-plan-{uuid.uuid4().hex[:8]}", "created_at": ah.now_utc().isoformat()}
    await ah.db.auction_plans.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@auctions_admin_router.put("/plans/{plan_id}")
async def update_plan(plan_id: str, body: PlanBody, admin: dict = Depends(require_admin)):
    if body.price_ht_cents <= 0 or body.credits <= 0 or body.validity_days <= 0:
        raise HTTPException(status_code=400, detail="Valeurs de plan invalides")
    res = await ah.db.auction_plans.update_one({"id": plan_id}, {"$set": {
        **body.dict(), "updated_at": ah.now_utc().isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    return {"ok": True}
