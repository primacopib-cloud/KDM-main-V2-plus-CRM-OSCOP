"""Catalogue relais LOLODRIVE : soumission gérant + validation super admin + catalogue POS."""
import os
import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
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
    try:
        await _notify_admins_new_product(doc)
    except Exception as exc:
        logger.warning("Notification admins nouvelle fiche : %s", exc)
    return doc


class CounterSaleItem(BaseModel):
    sku: str
    qty: int = 1


class CounterSaleBody(BaseModel):
    items: list
    payment_method: str = "CASH"


@relay_products_router.post("/pos/counter-sale")
async def pos_counter_sale(body: CounterSaleBody, user: dict = Depends(get_current_user)):
    """Vente au comptoir : le gérant encaisse directement les produits de son relais."""
    point = await _manager_point(user["id"])
    items = [CounterSaleItem(**i) for i in (body.items or []) if i.get("sku") and int(i.get("qty", 0)) > 0]
    if not items:
        raise HTTPException(status_code=400, detail="Aucun article à encaisser")
    skus = [i.sku for i in items]
    prods = await db.lolodrive_products.find(
        {"sku": {"$in": skus}, "is_active": {"$ne": False},
         "$or": [{"point_code": {"$exists": False}}, {"point_code": None},
                 {"point_code": point["code"], "status": "APPROVED"}]},
        {"_id": 0}).to_list(100)
    by_sku = {p["sku"]: p for p in prods}
    from favorite_promo_alerts import _active_discount_promos, _matches_product
    promos = await _active_discount_promos(db)
    lines, total, discount = [], 0, 0
    for it in items:
        p = by_sku.get(it.sku)
        if not p:
            continue
        unit = p.get("price_public_cents", 0)
        pct = max((pr.get("value_percent") or 0 for pr in promos if _matches_product(pr, p)), default=0) if promos else 0
        if pct:
            disc_unit = round(unit * (1 - pct / 100))
            discount += (unit - disc_unit) * it.qty
            unit = disc_unit
        total += unit * it.qty
        lines.append({"sku": p["sku"], "name": p["name"], "qty": it.qty,
                      "unit_cents": unit, "promo_percent": pct or None})
    if not lines:
        raise HTTPException(status_code=400, detail="Articles introuvables au catalogue du relais")
    now = datetime.utcnow()
    order = {
        "id": str(uuid.uuid4()),
        "order_number": f"LC-{now:%Y%m%d}-{str(uuid.uuid4())[:6].upper()}",
        "channel": "COUNTER",
        "fulfillment_type": "COUNTER",
        "lolo_point_id": point["id"],
        "user_id": None,
        "items": lines,
        "subtotal_cents": total,
        "promo_discount_cents": discount,
        "fees_cents": 0,
        "total_cents": total,
        "payment_method": "CARD" if body.payment_method.upper() == "CARD" else "CASH",
        "status": "FULFILLED",
        "created_at": now, "updated_at": now, "paid_at": now, "fulfilled_at": now,
    }
    await db.lolodrive_orders.insert_one(order)
    order.pop("_id", None)
    order["point_name"] = point.get("name")
    return {"ok": True, "order_number": order["order_number"],
            "total_cents": total, "promo_discount_cents": discount,
            "payment_method": order["payment_method"], "order": order}


@relay_products_router.get("/pos/counter-journal")
async def pos_counter_journal(user: dict = Depends(get_current_user)):
    """Journal de caisse du jour : totaux espèces / CB des ventes au comptoir."""
    point = await _manager_point(user["id"])
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start}},
        {"_id": 0, "order_number": 1, "total_cents": 1, "payment_method": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(300)
    cash = sum(o.get("total_cents", 0) for o in orders if o.get("payment_method") == "CASH")
    card = sum(o.get("total_cents", 0) for o in orders if o.get("payment_method") == "CARD")
    return {"date": start.strftime("%d/%m/%Y"), "count": len(orders),
            "cash_cents": cash, "card_cents": card, "total_cents": cash + card, "sales": orders}


@relay_products_router.get("/pos/counter-journal/export")
async def export_counter_journal(month: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Export CSV du journal de caisse du mois (comptabilité)."""
    point = await _manager_point(user["id"])
    now = datetime.utcnow()
    try:
        y, m = map(int, (month or now.strftime("%Y-%m")).split("-"))
        start = datetime(y, m, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format mois invalide (attendu : YYYY-MM)")
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0}).sort("created_at", 1).to_list(3000)
    rows = ["date;heure;numero;paiement;articles;remise_promo_eur;total_eur"]
    for o in orders:
        items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
        pay = "CB" if o.get("payment_method") == "CARD" else "Especes"
        rows.append(f"{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};{pay};"
                    f"\"{items}\";{(o.get('promo_discount_cents') or 0) / 100:.2f};{o.get('total_cents', 0) / 100:.2f}")
    cash = sum(o.get("total_cents", 0) for o in orders if o.get("payment_method") == "CASH")
    card = sum(o.get("total_cents", 0) for o in orders if o.get("payment_method") == "CARD")
    rows += ["", f"TOTAL ESPECES;;;;;;{cash / 100:.2f}", f"TOTAL CB;;;;;;{card / 100:.2f}",
             f"TOTAL CAISSE;;;;;;{(cash + card) / 100:.2f}"]
    return PlainTextResponse(
        "\ufeff" + "\n".join(rows), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=caisse-{point['code']}-{y}-{m:02d}.csv"})


@relay_products_router.get("/pos/top-products")
async def pos_top_products(days: int = 30, user: dict = Depends(get_current_user)):
    """Top des produits les plus vendus au comptoir du relais."""
    point = await _manager_point(user["id"])
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    agg = {}
    async for o in db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": since}},
            {"_id": 0, "items": 1}):
        for l in o.get("items", []):
            e = agg.setdefault(l["sku"], {"sku": l["sku"], "name": l["name"], "qty": 0, "revenue_cents": 0})
            e["qty"] += l.get("qty", 0)
            e["revenue_cents"] += l.get("unit_cents", 0) * l.get("qty", 0)
    top = sorted(agg.values(), key=lambda x: (x["qty"], x["revenue_cents"]), reverse=True)[:5]
    return {"days": days, "top": top}


@relay_products_router.post("/pos/counter-sale/{order_id}/email-ticket")
async def email_counter_ticket(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Envoie le ticket de caisse d'une vente au comptoir par email."""
    email = ((payload or {}).get("email") or "").strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide")
    point = await _manager_point(user["id"])
    order = await db.lolodrive_orders.find_one(
        {"id": order_id, "channel": "COUNTER", "lolo_point_id": point["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Vente introuvable pour ce relais")
    from brevo_service import send_email, _wrap_html

    def _row(l):
        promo = f" <span style='color:#b45309;font-size:11px'>-{l['promo_percent']:g}%</span>" if l.get("promo_percent") else ""
        return (f"<tr><td style='padding:4px 8px'>{l['name']}{promo}</td>"
                f"<td style='padding:4px 8px;text-align:center'>× {l['qty']}</td>"
                f"<td style='padding:4px 8px;text-align:right'>{l['unit_cents'] * l['qty'] / 100:.2f} €</td></tr>")

    rows = "".join(_row(l) for l in order.get("items", []))
    discount = order.get("promo_discount_cents") or 0
    subject = f"🧾 Ticket de caisse — {order['order_number']} ({point['name']})"
    body = f"""
      <p><strong>{point['name']}</strong> — vente au comptoir du {order['created_at'].strftime('%d/%m/%Y %H:%M')}</p>
      <table style='width:100%;border-collapse:collapse;font-size:13px;border-top:1px dashed #ccc;border-bottom:1px dashed #ccc'>{rows}</table>
      {f"<p style='margin:8px 0 0;color:#b45309'>⚡ Remise promo : −{discount / 100:.2f} €</p>" if discount else ''}
      <p style='margin:10px 0 0;font-size:15px'>Total encaissé : <strong>{order['total_cents'] / 100:.2f} €</strong>
      ({'carte bancaire' if order.get('payment_method') == 'CARD' else 'espèces'})</p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Merci de votre visite — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=email, to_name=None, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Ticket {order['order_number']} — total {order['total_cents'] / 100:.2f} €.",
                     tags=["counter_ticket"])
    return {"ok": True, "sent_to": email}


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
        "brand": (body.brand or product.get("brand") or point["name"]).strip(),
        "description": body.description.strip(),
        "price_public_cents": body.price_public_cents,
        "price_pass_cents": body.price_pass_cents,
        "image_url": body.image_url or product.get("image_url"),
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
