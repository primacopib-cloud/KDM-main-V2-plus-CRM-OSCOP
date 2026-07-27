"""Catalogue relais LOLODRIVE : soumission gérant + validation super admin + catalogue POS."""
import os
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin, cents_to_uc

logger = logging.getLogger(__name__)
TEAM_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
relay_products_router = APIRouter(prefix="/api/lolodrive", tags=["Relay Products"])
db = None


def set_relay_products_database(database):
    global db
    db = database


class RelayProductSubmit(BaseModel):
    name: str
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    description: str
    price_public_cents: int
    price_pass_cents: Optional[int] = None
    catalog_type: str = "NORMAL"
    image_url: Optional[str] = None
    stock_qty: Optional[int] = None
    barcode: Optional[str] = None
    tva_rate: Optional[float] = None


async def log_stock_movement(sku, name, mtype, delta, stock_after, point_code=None, ref=None):
    await db.stock_movements.insert_one({
        "id": str(uuid.uuid4()), "sku": sku, "name": name, "type": mtype,
        "delta": delta, "stock_after": stock_after, "point_code": point_code,
        "ref": ref, "created_at": datetime.utcnow()})


async def _check_goal_reached(point: dict):
    """Email de félicitations au gérant dès que l'objectif mensuel de caisse est atteint (1×/mois)."""
    goal = point.get("monthly_goal_cents") or 0
    if goal <= 0:
        return
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_tag = month_start.strftime("%Y-%m")
    if await db.goal_reached_sent.find_one({"point_id": point["id"], "month": month_tag}):
        return
    total = 0
    async for o in db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": month_start}},
            {"_id": 0, "total_cents": 1}):
        total += o.get("total_cents", 0)
    if total < goal:
        return
    mgr = await db.users.find_one({"id": point.get("manager_user_id")}, {"_id": 0, "email": 1, "contact_name": 1})
    if not mgr or not mgr.get("email"):
        return
    await db.goal_reached_sent.insert_one({"point_id": point["id"], "month": month_tag, "sent_at": now})
    from brevo_service import send_email, _wrap_html
    subject = f"🎉 Objectif de caisse atteint — {point['name']} !"
    body = f"""
      <p>Félicitations <strong>{(mgr.get('contact_name') or '').split(' ')[0]}</strong> ! 🏆</p>
      <p>Votre relais <strong>{point['name']} ({point['code']})</strong> vient d'atteindre son
      <strong>objectif mensuel de caisse</strong> :</p>
      <div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);border-radius:12px;padding:14px;margin:12px 0'>
        <p style='margin:0;font-size:16px'><strong>{total / 100:.2f} €</strong> encaissés
        / objectif de {goal / 100:.2f} € ✅</p>
      </div>
      <p>Bravo à toute l'équipe — et pourquoi ne pas viser encore plus haut le mois prochain ?</p>
    """
    await send_email(to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Objectif atteint : {total / 100:.2f} € / {goal / 100:.2f} €.",
                     tags=["objectif_atteint"])


async def _notify_negative_balance(user_id: str, point: dict, new_balance, fee_uc, order_number: str):
    from brevo_service import send_email, _wrap_html
    mgr = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    recipients = {TEAM_EMAIL}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    if mgr and mgr.get("email"):
        recipients.add(mgr["email"].lower())
    subject = f"⚠️ CREDI'SCOP négatif — {point['name']} ({new_balance} UC)"
    body = f"""
      <p>Le CREDI'SCOP du gérant du relais <strong>{point['name']} ({point['code']})</strong> vient de passer en négatif :</p>
      <div style='background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:14px;margin:12px 0;'>
        <p style='margin:0;font-size:15px'>Solde actuel : <strong style='color:#dc2626'>{new_balance} UC</strong></p>
        <p style='margin:6px 0 0;font-size:13px'>Dernier débit : {fee_uc} UC (frais produits relais — vente {order_number}).</p>
      </div>
      <p>Le gérant est invité à recharger son CREDI'SCOP depuis son espace POS (bandeau "Règle réseau" → Recharger).</p>
    """
    for email in recipients:
        try:
            await send_email(to_email=email, to_name=None, subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"CREDI'SCOP négatif : {new_balance} UC ({point['code']}).",
                             tags=["credi_scop_negative"])
        except Exception as exc:
            logger.warning("Alerte solde négatif à %s : %s", email, exc)


async def get_relay_fee_uc() -> float:
    doc = await db.lolodrive_settings.find_one({"key": "relay_product_fee_uc"}, {"_id": 0})
    return doc.get("value_uc", 3) if doc else 3


async def _manager_point(user_id: str) -> dict:
    point = await db.lolodrive_points.find_one({"manager_user_id": user_id}, {"_id": 0})
    if not point:
        u = await db.users.find_one(
            {"id": user_id, "role": "OPERATEUR_POS", "is_archived": {"$ne": True}},
            {"_id": 0, "pos_point_id": 1})
        if u and u.get("pos_point_id"):
            point = await db.lolodrive_points.find_one({"id": u["pos_point_id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun relais LOLODRIVE assigné à ce compte")
    return point


@relay_products_router.post("/manager/products/photo")
async def upload_product_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Photo de la fiche produit du gérant (jpg/png/webp, 4 Mo max)."""
    point = await _manager_point(user["id"])
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(status_code=400, detail="Format non supporté (jpg, png, webp)")
    data = await file.read()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 4 Mo)")
    up_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
    os.makedirs(up_dir, exist_ok=True)
    fname = f"product-{point['code'].lower()}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(up_dir, fname), "wb") as f:
        f.write(data)
    return {"ok": True, "image_url": f"/api/uploads/products/{fname}"}


async def _notify_admins_new_product(product: dict):
    from brevo_service import send_email, _wrap_html
    recipients = {TEAM_EMAIL}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    subject = f"🗂️ Fiche produit relais à valider — {product['name']} ({product['point_code']})"
    body = f"""
      <p>Une nouvelle fiche produit vient d'être soumise par le relais <strong>{product['point_code']}</strong> :</p>
      <div style='background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:14px;margin:12px 0;'>
        <p style='margin:0;font-weight:bold'>{product['name']} — {product['price_public_cents'] / 100:.2f} €</p>
        <p style='margin:6px 0 0;font-size:13px'>{product['category']}{' · ' + product['brand'] if product.get('brand') else ''}</p>
        <p style='margin:6px 0 0;font-size:13px;color:#555'>{product['description']}</p>
      </div>
      <p>Rendez-vous dans <strong>Admin → Réseau LOLODRIVE</strong> pour l'approuver ou la refuser.</p>
    """
    for email in recipients:
        try:
            await send_email(to_email=email, to_name=None, subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Fiche produit relais à valider : {product['name']} ({product['point_code']}).",
                             tags=["relay_product_pending"])
        except Exception as exc:
            logger.warning("Alerte nouvelle fiche à %s : %s", email, exc)


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
        "subcategory": (body.subcategory or "").strip() or None,
        "brand": (body.brand or point["name"]).strip(),
        "description": body.description.strip(),
        "price_public_cents": body.price_public_cents,
        "price_pass_cents": body.price_pass_cents,
        "catalog_type": body.catalog_type if body.catalog_type in ("ESSENTIAL", "NORMAL") else "NORMAL",
        "image_url": body.image_url,
        "barcode": (body.barcode or "").strip() or None,
        "tva_rate": min(max(float(body.tva_rate), 0), 30) if body.tva_rate is not None else 8.5,
        "stock_qty": body.stock_qty if body.stock_qty is not None and body.stock_qty >= 0 else None,
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
    if doc.get("stock_qty") is not None:
        await log_stock_movement(doc["sku"], doc["name"], "INITIAL", doc["stock_qty"],
                                 doc["stock_qty"], point["code"])
    try:
        await _notify_admins_new_product(doc)
    except Exception as exc:
        logger.warning("Notification admins nouvelle fiche : %s", exc)
    return doc


@relay_products_router.put("/manager/products/{sku}")
async def update_relay_product(sku: str, body: RelayProductSubmit, user: dict = Depends(get_current_user)):
    """Le gérant corrige une fiche refusée et la re-soumet pour validation."""
    point = await _manager_point(user["id"])
    product = await db.lolodrive_products.find_one({"sku": sku, "point_code": point["code"]})
    if not product:
        raise HTTPException(status_code=404, detail="Fiche produit introuvable pour ce relais")
    if product.get("status") != "REJECTED":
        raise HTTPException(status_code=400, detail="Seules les fiches refusées peuvent être corrigées et re-soumises")
    if not body.name.strip() or not body.description.strip() or body.price_public_cents <= 0:
        raise HTTPException(status_code=400, detail="Fiche incomplète : nom, description et prix requis")
    updates = {
        "name": body.name.strip(),
        "category": body.category.strip(),
        "subcategory": (body.subcategory or "").strip() or product.get("subcategory"),
        "brand": (body.brand or product.get("brand") or point["name"]).strip(),
        "description": body.description.strip(),
        "price_public_cents": body.price_public_cents,
        "price_pass_cents": body.price_pass_cents,
        "image_url": body.image_url or product.get("image_url"),
        "barcode": (body.barcode or "").strip() or product.get("barcode"),
        "tva_rate": min(max(float(body.tva_rate), 0), 30) if body.tva_rate is not None else product.get("tva_rate", 8.5),
        "stock_qty": body.stock_qty if body.stock_qty is not None and body.stock_qty >= 0 else product.get("stock_qty"),
        "status": "PENDING",
        "is_active": False,
        "reject_reason": None,
        "submitted_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.lolodrive_products.update_one({"sku": sku}, {"$set": updates})
    fresh = await db.lolodrive_products.find_one({"sku": sku}, {"_id": 0})
    try:
        await _notify_admins_new_product(fresh)
    except Exception as exc:
        logger.warning("Notification admins fiche corrigée : %s", exc)
    return fresh


@relay_products_router.get("/manager/products")
async def my_relay_products(user: dict = Depends(get_current_user)):
    point = await _manager_point(user["id"])
    products = await db.lolodrive_products.find(
        {"point_code": point["code"]}, {"_id": 0}).sort("submitted_at", -1).to_list(100)
    return {"point": {"code": point["code"], "name": point["name"]}, "products": products}


@relay_products_router.get("/pos/catalog")
async def pos_catalog(point_code: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Catalogue du relais pour l'opérateur POS : produits globaux + produits relais approuvés, en € et UC."""
    try:
        point = await _manager_point(user["id"])
        point_code = point["code"]
    except HTTPException:
        pass
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
