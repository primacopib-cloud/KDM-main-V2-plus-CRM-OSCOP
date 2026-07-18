"""Grille de diffusion des spots vidéo en galerie — paramètres admin, réservation vendeur payée en crédits coopératifs (cc)."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

logger = logging.getLogger(__name__)
diffusion_router = APIRouter(prefix="/api", tags=["Spot Diffusion"])

db = None

UNIT_LABELS = {"hours": "heure(s)", "days": "jour(s)", "months": "mois"}


def set_diffusion_database(database) -> None:
    global db
    db = database


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class GridOptionPayload(BaseModel):
    unit: str  # hours | days | months
    quantity: int
    price_credits: int
    label: str | None = None
    active: bool = True


def _duration(unit: str, quantity: int) -> timedelta:
    if unit == "hours":
        return timedelta(hours=quantity)
    if unit == "months":
        return timedelta(days=30 * quantity)
    return timedelta(days=quantity)


# ---------- Grille (Super Admin) ----------

@diffusion_router.get("/diffusion-grid")
async def list_grid_public():
    """Options de diffusion actives (visibles vendeur)."""
    options = await db.diffusion_grid.find({"active": True}, {"_id": 0}).sort("price_credits", 1).to_list(50)
    return {"options": options, "total": len(options)}


@diffusion_router.get("/admin/diffusion-grid")
async def list_grid_admin(_: dict = Depends(_admin)):
    options = await db.diffusion_grid.find({}, {"_id": 0}).sort("price_credits", 1).to_list(100)
    return {"options": options, "total": len(options)}


@diffusion_router.post("/admin/diffusion-grid")
async def create_grid_option(payload: GridOptionPayload, _: dict = Depends(_admin)):
    if payload.unit not in UNIT_LABELS:
        raise HTTPException(status_code=400, detail="unit doit être hours, days ou months")
    if payload.quantity <= 0 or payload.price_credits <= 0:
        raise HTTPException(status_code=400, detail="quantity et price_credits doivent être positifs")
    option = {
        "id": str(uuid.uuid4()),
        "unit": payload.unit,
        "quantity": payload.quantity,
        "price_credits": payload.price_credits,
        "label": payload.label or f"{payload.quantity} {UNIT_LABELS[payload.unit]}",
        "active": payload.active,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.diffusion_grid.insert_one({**option})
    return {"status": "SUCCESS", "option": option}


@diffusion_router.patch("/admin/diffusion-grid/{option_id}")
async def update_grid_option(option_id: str, payload: dict, _: dict = Depends(_admin)):
    allowed = {k: v for k, v in payload.items() if k in ("unit", "quantity", "price_credits", "label", "active")}
    if not allowed:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable fourni")
    result = await db.diffusion_grid.update_one({"id": option_id}, {"$set": allowed})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Option introuvable")
    return {"status": "SUCCESS"}


@diffusion_router.delete("/admin/diffusion-grid/{option_id}")
async def delete_grid_option(option_id: str, _: dict = Depends(_admin)):
    result = await db.diffusion_grid.delete_one({"id": option_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Option introuvable")
    return {"status": "SUCCESS"}


# ---------- Réservation (Vendeur) ----------

class BookPayload(BaseModel):
    grid_id: str


@diffusion_router.get("/vendor/diffusion/{vendor_id}")
async def vendor_diffusions(vendor_id: str):
    """Diffusions du vendeur, avec statut recalculé."""
    now = datetime.now(timezone.utc).isoformat()
    items = await db.spot_diffusions.find({"vendor_id": vendor_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for item in items:
        item["status"] = "ACTIVE" if item["starts_at"] <= now <= item["ends_at"] else (
            "SCHEDULED" if now < item["starts_at"] else "EXPIRED")
    return {"diffusions": items, "total": len(items)}


@diffusion_router.post("/vendor/diffusion/{vendor_id}/{product_id}/book")
async def book_diffusion(vendor_id: str, product_id: str, payload: BookPayload):
    """Réserve une fenêtre de diffusion en galerie, payée en crédits coopératifs."""
    option = await db.diffusion_grid.find_one({"id": payload.grid_id, "active": True}, {"_id": 0})
    if not option:
        raise HTTPException(status_code=404, detail="Option de diffusion introuvable ou inactive")
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id}, {"_id": 0, "video_url": 1, "name": 1})
    if not product or not product.get("video_url"):
        raise HTTPException(status_code=400, detail="Ce produit n'a pas de spot vidéo")
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "credits": 1})
    balance = int((vendor or {}).get("credits") or 0)
    price = int(option["price_credits"])
    if balance < price:
        raise HTTPException(status_code=402, detail=f"Crédits insuffisants ({balance} cc, requis {price} cc)")

    now = datetime.now(timezone.utc)
    existing = await db.spot_diffusions.find_one(
        {"vendor_id": vendor_id, "product_id": product_id, "ends_at": {"$gt": now.isoformat()}},
        {"_id": 0, "ends_at": 1})
    starts = datetime.fromisoformat(existing["ends_at"]) if existing else now
    ends = starts + _duration(option["unit"], option["quantity"])

    await db.vendors.update_one({"id": vendor_id}, {"$inc": {"credits": -price}})
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "action": "spot_diffusion",
        "cost": price, "detail": f"Diffusion galerie {option['label']} — {product.get('name', product_id)}",
        "balance_after": balance - price, "at": now.isoformat(),
    })
    diffusion = {
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "product_id": product_id,
        "grid_id": option["id"], "label": option["label"], "price_credits": price,
        "starts_at": starts.isoformat(), "ends_at": ends.isoformat(),
        "created_at": now.isoformat(),
    }
    await db.spot_diffusions.insert_one({**diffusion})
    return {"status": "SUCCESS", "diffusion": diffusion, "credits_left": balance - price}


async def active_diffusion_product_ids() -> set | None:
    """IDs produits avec diffusion active. None si la grille n'est pas en service (galerie libre)."""
    has_grid = await db.diffusion_grid.count_documents({"active": True})
    if not has_grid:
        return None
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.spot_diffusions.find(
        {"starts_at": {"$lte": now}, "ends_at": {"$gte": now}}, {"_id": 0, "product_id": 1})
    return {d["product_id"] async for d in cursor}
