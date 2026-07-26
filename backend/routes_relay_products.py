"""Catalogue relais LOLODRIVE : soumission gérant + validation super admin + catalogue POS."""
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin, cents_to_uc

logger = logging.getLogger(__name__)
relay_products_router = APIRouter(prefix="/api/lolodrive", tags=["Relay Products"])
db = None


def set_relay_products_database(database):
    global db
    db = database


class RelayProductSubmit(BaseModel):
    name: str
    category: str
    brand: Optional[str] = None
    description: str
    price_public_cents: int
    price_pass_cents: Optional[int] = None
    catalog_type: str = "NORMAL"
    image_url: Optional[str] = None


async def _manager_point(user_id: str) -> dict:
    point = await db.lolodrive_points.find_one({"manager_user_id": user_id}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun relais LOLODRIVE assigné à ce compte")
    return point


@relay_products_router.post("/manager/products")
async def submit_relay_product(body: RelayProductSubmit, user: dict = Depends(get_current_user)):
    """Le gérant soumet une fiche produit complète — validée ensuite par le super admin."""
    point = await _manager_point(user["id"])
    if not body.name.strip() or not body.description.strip() or body.price_public_cents <= 0:
        raise HTTPException(status_code=400, detail="Fiche incomplète : nom, description et prix requis")
    slug = re.sub(r"[^A-Z0-9]+", "-", body.name.upper()).strip("-")[:18]
    doc = {
        "id": str(uuid.uuid4()),
        "sku": f"{point['code']}-{slug}-{str(uuid.uuid4())[:4].upper()}",
        "name": body.name.strip(),
        "category": body.category.strip(),
        "brand": (body.brand or point["name"]).strip(),
        "description": body.description.strip(),
        "price_public_cents": body.price_public_cents,
        "price_pass_cents": body.price_pass_cents,
        "catalog_type": body.catalog_type if body.catalog_type in ("ESSENTIAL", "NORMAL") else "NORMAL",
        "image_url": body.image_url,
        "territories": [point["territory"]] if point.get("territory") else [],
        "point_id": point["id"],
        "point_code": point["code"],
        "status": "PENDING",
        "is_active": False,
        "submitted_by": user["id"],
        "submitted_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.lolodrive_products.insert_one(doc)
    doc.pop("_id", None)
    return doc


@relay_products_router.get("/manager/products")
async def my_relay_products(user: dict = Depends(get_current_user)):
    point = await _manager_point(user["id"])
    products = await db.lolodrive_products.find(
        {"point_code": point["code"]}, {"_id": 0}).sort("submitted_at", -1).to_list(100)
    return {"point": {"code": point["code"], "name": point["name"]}, "products": products}


@relay_products_router.get("/pos/catalog")
async def pos_catalog(point_code: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Catalogue du relais pour l'opérateur POS : produits globaux + produits relais approuvés, en € et UC."""
    if not point_code:
        point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
        point_code = (point or {}).get("code")
    query = {"is_active": {"$ne": False}, "$or": [
        {"point_code": {"$exists": False}}, {"point_code": None}]}
    if point_code:
        query["$or"].append({"point_code": point_code, "status": "APPROVED"})
    products = await db.lolodrive_products.find(query, {"_id": 0}).sort("name", 1).to_list(300)
    for p in products:
        p["uc_public"] = cents_to_uc(p.get("price_public_cents", 0))
        p["uc_pass"] = cents_to_uc(p["price_pass_cents"]) if p.get("price_pass_cents") else None
    return {"point_code": point_code, "products": products}


@relay_products_router.get("/admin/relay-products")
async def admin_relay_products(status: str = "PENDING", admin: dict = Depends(require_admin)):
    products = await db.lolodrive_products.find(
        {"point_code": {"$ne": None}, "status": status}, {"_id": 0}).sort("submitted_at", -1).to_list(200)
    return {"products": products}


@relay_products_router.post("/admin/relay-products/{sku}/review")
async def review_relay_product(sku: str, payload: dict, admin: dict = Depends(require_admin)):
    action = (payload or {}).get("action")
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action doit être approve ou reject")
    product = await db.lolodrive_products.find_one({"sku": sku, "point_code": {"$ne": None}})
    if not product:
        raise HTTPException(status_code=404, detail="Produit relais introuvable")
    updates = ({"status": "APPROVED", "is_active": True, "approved_at": datetime.utcnow()}
               if action == "approve"
               else {"status": "REJECTED", "is_active": False,
                     "reject_reason": (payload.get("reason") or "").strip() or None})
    updates["updated_at"] = datetime.utcnow()
    await db.lolodrive_products.update_one({"sku": sku}, {"$set": updates})
    try:
        submitter = await db.users.find_one({"id": product.get("submitted_by")}, {"_id": 0, "email": 1, "contact_name": 1})
        if submitter and submitter.get("email"):
            from brevo_service import send_email, _wrap_html
            ok = action == "approve"
            subject = (f"✅ Produit \"{product['name']}\" approuvé — en ligne sur votre catalogue"
                       if ok else f"❌ Produit \"{product['name']}\" refusé")
            body = (f"<p>Votre fiche produit <strong>{product['name']}</strong> a été approuvée par le super admin : "
                    f"elle est désormais visible sur le catalogue de votre relais et pour les titulaires PASS.</p>"
                    if ok else
                    f"<p>Votre fiche produit <strong>{product['name']}</strong> a été refusée."
                    f"{' Motif : ' + updates['reject_reason'] if updates.get('reject_reason') else ''}"
                    f" Vous pouvez la corriger et la soumettre à nouveau.</p>")
            await send_email(to_email=submitter["email"], to_name=submitter.get("contact_name"),
                             subject=subject, html_content=_wrap_html(subject, body),
                             text_content=subject, tags=["relay_product_review"])
    except Exception as exc:
        logger.warning("Email review produit relais : %s", exc)
    return {"ok": True, "sku": sku, "status": updates["status"]}


@relay_products_router.get("/admin/lolo-points/pro-status")
async def admin_points_pro_status(admin: dict = Depends(require_admin)):
    """Statut d'abonnement Acheteur Pro de chaque gérant de relais (vue admin)."""
    out = {}
    async for point in db.lolodrive_points.find({}, {"_id": 0, "code": 1, "manager_user_id": 1}):
        uid = point.get("manager_user_id")
        if not uid:
            out[point["code"]] = {"has_manager": False, "pro_active": False}
            continue
        mgr = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "contact_name": 1})
        membership = await db.org_memberships.find_one({"user_id": uid})
        sub = await db.subscriptions.find_one(
            {"org_id": membership["org_id"], "status": "ACTIVE"},
            {"_id": 0, "current_period_end": 1}) if membership else None
        org = await db.orgs.find_one({"id": membership["org_id"]}, {"_id": 0, "status": 1}) if membership else None
        out[point["code"]] = {
            "has_manager": True,
            "manager_email": (mgr or {}).get("email"),
            "pro_active": bool(org and org.get("status") == "APPROVED" and sub),
            "period_end": (sub or {}).get("current_period_end"),
        }
    return {"statuses": out}
