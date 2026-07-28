"""Fiches produits (fournisseur), historique retraits catalogue, bons de commande fournisseur."""
import logging
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
product_extras_router = APIRouter(prefix="/api/lolodrive", tags=["Product Extras"])
db = None

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def set_product_extras_database(database):
    global db
    db = database


@product_extras_router.put("/admin/products/{sku}/supplier")
async def admin_set_product_supplier(sku: str, payload: dict, admin: dict = Depends(require_admin)):
    """Nom + email du fournisseur d'un produit (lots défectueux, bons de commande)."""
    supplier = str((payload or {}).get("supplier") or "").strip()[:120]
    email = str((payload or {}).get("supplier_email") or "").strip()[:120]
    if email and not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email fournisseur invalide")
    res = await db.lolodrive_products.update_one(
        {"sku": sku}, {"$set": {"supplier": supplier or None, "supplier_email": email or None}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "sku": sku, "supplier": supplier or None, "supplier_email": email or None}


@product_extras_router.get("/admin/products/toggle-history")
async def admin_toggle_history(limit: int = 50, admin: dict = Depends(require_admin)):
    """Historique des retraits / remises au catalogue (qui, quand, quel produit)."""
    logs = await db.product_toggle_logs.find({}, {"_id": 0}).sort("at", -1).to_list(max(1, min(limit, 200)))
    for l in logs:
        if isinstance(l.get("at"), datetime):
            l["at"] = l["at"].isoformat()
    return {"logs": logs, "count": len(logs)}


@product_extras_router.post("/pos/restock-order")
async def pos_restock_order(payload: dict, user: dict = Depends(get_current_user)):
    """Bon de commande fournisseur depuis les suggestions de réassort (gérant uniquement)."""
    from routes_pos_operators import _owned_point
    point = await _owned_point(user["id"])
    items = (payload or {}).get("items") or []
    clean = []
    for it in items:
        try:
            qty = int(it.get("qty"))
        except (TypeError, ValueError):
            continue
        if 1 <= qty <= 10000 and it.get("sku"):
            clean.append({"sku": str(it["sku"]), "qty": qty})
    if not clean:
        raise HTTPException(status_code=400, detail="Aucune ligne de commande valide")
    skus = [c["sku"] for c in clean]
    prods = {p["sku"]: p for p in await db.lolodrive_products.find(
        {"sku": {"$in": skus}}, {"_id": 0, "sku": 1, "name": 1, "supplier": 1, "supplier_email": 1}).to_list(300)}
    lines = [{**c, "name": prods[c["sku"]]["name"],
              "supplier": prods[c["sku"]].get("supplier"),
              "supplier_email": prods[c["sku"]].get("supplier_email")}
             for c in clean if c["sku"] in prods]
    if not lines:
        raise HTTPException(status_code=400, detail="Produits introuvables")
    groups = {}
    for l in lines:
        groups.setdefault(l["supplier"] or "Fournisseur non renseigné", []).append(l)
    now = datetime.utcnow()
    order_number = f"BC-{now:%Y%m%d}-{str(uuid.uuid4())[:6].upper()}"
    gerant_email = user.get("email")
    gerant_name = user.get("contact_name") or gerant_email
    sent_suppliers = []
    for supplier, ls in groups.items():
        email = ls[0].get("supplier_email")
        if email:
            try:
                await _send_order_email(email, supplier, ls, point, order_number, gerant_name, gerant_email)
                sent_suppliers.append(supplier)
            except Exception as exc:
                logger.warning("Bon de commande %s → %s : %s", order_number, email, exc)
    try:
        await _send_recap_email(gerant_email, gerant_name, groups, sent_suppliers, point, order_number)
    except Exception as exc:
        logger.warning("Récap bon de commande %s : %s", order_number, exc)
    await db.restock_orders.insert_one({
        "id": str(uuid.uuid4()), "order_number": order_number, "point_id": point["id"],
        "point_code": point.get("code"), "by_user_id": user["id"], "by_name": gerant_name,
        "lines": [{k: l[k] for k in ("sku", "name", "qty", "supplier", "supplier_email")} for l in lines],
        "sent_suppliers": sent_suppliers, "status": "PENDING", "created_at": now})
    return {"ok": True, "order_number": order_number,
            "suppliers_emailed": sent_suppliers, "recap_sent_to": gerant_email}


@product_extras_router.get("/pos/restock-orders")
async def pos_restock_orders(limit: int = 20, user: dict = Depends(get_current_user)):
    """Historique des bons de commande fournisseur du relais (gérant uniquement)."""
    from routes_pos_operators import _owned_point
    point = await _owned_point(user["id"])
    orders = await db.restock_orders.find(
        {"point_id": point["id"]}, {"_id": 0}).sort("created_at", -1).to_list(max(1, min(limit, 100)))
    for o in orders:
        for k in ("created_at", "received_at", "reminder_sent_at"):
            if isinstance(o.get(k), datetime):
                o[k] = o[k].isoformat()
    return {"orders": orders, "count": len(orders)}


@product_extras_router.post("/pos/restock-orders/{order_id}/receive")
async def pos_receive_restock_order(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Pointage de la livraison reçue : remet les stocks à jour depuis le bon (gérant)."""
    from routes_pos_operators import _owned_point
    from routes_relay_products import log_stock_movement
    from pymongo import ReturnDocument
    point = await _owned_point(user["id"])
    order = await db.restock_orders.find_one({"id": order_id, "point_id": point["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable")
    if order.get("received_at"):
        raise HTTPException(status_code=400, detail="Réception déjà pointée pour ce bon")
    req = {}
    for it in (payload or {}).get("items") or []:
        try:
            q = int(it.get("qty"))
        except (TypeError, ValueError):
            continue
        if it.get("sku") and 0 <= q <= 10000:
            req[str(it["sku"])] = q
    received, now = [], datetime.utcnow()
    for l in order.get("lines", []):
        qty = req.get(l["sku"], l["qty"]) if req else l["qty"]
        if qty <= 0:
            continue
        res = await db.lolodrive_products.find_one_and_update(
            {"sku": l["sku"]},
            [{"$set": {"stock_qty": {"$add": [{"$ifNull": ["$stock_qty", 0]}, qty]}}}],
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "stock_qty": 1})
        if not res:
            continue
        await log_stock_movement(l["sku"], l.get("name"), "RESTOCK", qty, res["stock_qty"],
                                 point.get("code"), order["order_number"])
        received.append({"sku": l["sku"], "name": l.get("name"), "qty": qty, "stock_after": res["stock_qty"]})
    if not received:
        raise HTTPException(status_code=400, detail="Aucune quantité reçue à pointer")
    got = {r["sku"]: r["qty"] for r in received}
    shortages = [{**l, "received": got.get(l["sku"], 0), "missing": l["qty"] - got.get(l["sku"], 0)}
                 for l in order.get("lines", []) if got.get(l["sku"], 0) < l["qty"]]
    await db.restock_orders.update_one(
        {"id": order_id}, {"$set": {"received_at": now, "received_items": received,
                                    "shortages": shortages, "status": "RECEIVED"}})
    notified = await _notify_shortages(order, shortages, point, user)
    return {"ok": True, "order_number": order["order_number"], "received": received,
            "shortages": shortages, "suppliers_notified": notified}


@product_extras_router.get("/pos/restock-orders/{order_id}/pdf")
async def pos_restock_order_pdf(order_id: str, user: dict = Depends(get_current_user)):
    """Bon de commande en PDF A4 (comptabilité) — gérant du relais uniquement."""
    from fastapi.responses import Response
    from routes_pos_operators import _owned_point
    from restock_pdf import build_restock_pdf
    point = await _owned_point(user["id"])
    order = await db.restock_orders.find_one({"id": order_id, "point_id": point["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable")
    pdf = build_restock_pdf(order, point)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="bon-{order["order_number"]}.pdf"'})


@product_extras_router.get("/admin/restock-orders")
async def admin_restock_orders(limit: int = 100, admin: dict = Depends(require_admin)):
    """Vue réseau super admin : tous les bons de commande fournisseur + retards par relais."""
    orders = await db.restock_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(max(1, min(limit, 300)))
    pts = {p["id"]: p async for p in db.lolodrive_points.find({}, {"_id": 0, "id": 1, "name": 1, "code": 1})}
    now = datetime.utcnow()
    pending = late = 0
    for o in orders:
        pt = pts.get(o.get("point_id"), {})
        o["point_name"], o["point_code"] = pt.get("name"), pt.get("code", o.get("point_code"))
        if not o.get("received_at"):
            pending += 1
            o["days_pending"] = (now - o["created_at"]).days
            if o["days_pending"] >= 5:
                late += 1
        for k in ("created_at", "received_at", "reminder_sent_at"):
            if isinstance(o.get(k), datetime):
                o[k] = o[k].isoformat()
    return {"orders": orders, "count": len(orders), "pending": pending, "late": late}


async def _notify_shortages(order, shortages, point, user):
    """Email au fournisseur : quantités manquantes après une réception partielle (best-effort)."""
    groups = {}
    for s in shortages:
        if s.get("supplier_email"):
            groups.setdefault((s["supplier"] or "Fournisseur", s["supplier_email"]), []).append(s)
    notified = []
    for (supplier, email), ls in groups.items():
        try:
            await _send_shortage_email(email, supplier, ls, point, order, user)
            notified.append(supplier)
        except Exception as exc:
            logger.warning("Écart livraison %s → %s : %s", order.get("order_number"), email, exc)
    return notified


async def _send_shortage_email(email, supplier, ls, point, order, user):
    from brevo_service import send_email, _wrap_html
    subject = f"⚠️ Écart de livraison — bon de commande {order['order_number']}"
    rows = "".join(
        f"<tr><td style='border:1px solid #ccc;padding:6px 10px'>{s['name']}</td>"
        f"<td style='border:1px solid #ccc;padding:6px 10px;text-align:center'>{s['qty']}</td>"
        f"<td style='border:1px solid #ccc;padding:6px 10px;text-align:center'>{s['received']}</td>"
        f"<td style='border:1px solid #ccc;padding:6px 10px;text-align:center;color:#dc2626'><strong>{s['missing']}</strong></td></tr>" for s in ls)
    body = f"""
      <p>Bonjour,</p>
      <p>La livraison du bon de commande <strong>{order['order_number']}</strong>
      (relais <strong>{point.get('name')}</strong>, {point.get('code', '—')}) est incomplète :</p>
      <table style='border-collapse:collapse;font-size:13px;margin:8px 0'>
        <tr><th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Produit</th>
        <th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Commandé</th>
        <th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Reçu</th>
        <th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Manquant</th></tr>{rows}
      </table>
      <p>Merci de compléter la livraison ou d'émettre un avoir.
      Contact : {user.get('contact_name') or user.get('email')} — <a href='mailto:{user.get('email')}'>{user.get('email')}</a></p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Signalement automatique — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=email, to_name=supplier, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Ecart de livraison bon {order['order_number']} : " + ", ".join(f"{s['name']} manque {s['missing']}" for s in ls),
                     tags=["restock_shortage"])


def _lines_table(ls):
    rows = "".join(f"<tr><td style='border:1px solid #ccc;padding:6px 10px'>{l['name']}</td>"
                   f"<td style='border:1px solid #ccc;padding:6px 10px;text-align:center'><strong>{l['qty']}</strong></td></tr>" for l in ls)
    return ("<table style='border-collapse:collapse;font-size:13px;margin:8px 0'>"
            "<tr><th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Produit</th>"
            "<th style='border:1px solid #ccc;padding:6px 10px;background:#f0f0f0'>Quantité</th></tr>"
            f"{rows}</table>")


async def _send_order_email(email, supplier, ls, point, order_number, gerant_name, gerant_email):
    from brevo_service import send_email, _wrap_html
    subject = f"Bon de commande {order_number} — {point.get('name', 'Relais LOLODRIVE')}"
    body = f"""
      <p>Bonjour,</p>
      <p>Veuillez trouver ci-dessous notre bon de commande <strong>{order_number}</strong>
      pour le relais <strong>{point.get('name')}</strong> ({point.get('code', '—')}{', ' + point['city'] if point.get('city') else ''}).</p>
      {_lines_table(ls)}
      <p>Contact pour cette commande : {gerant_name} — <a href='mailto:{gerant_email}'>{gerant_email}</a>{' · ' + point['phone'] if point.get('phone') else ''}</p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Bon de commande généré automatiquement — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=email, to_name=supplier, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Bon de commande {order_number} — " + ", ".join(f"{l['name']} x{l['qty']}" for l in ls),
                     tags=["restock_order"])


async def _send_recap_email(gerant_email, gerant_name, groups, sent_suppliers, point, order_number):
    from brevo_service import send_email, _wrap_html
    subject = f"📦 Récap bon de commande {order_number} — {point.get('name', 'votre relais')}"
    blocks = ""
    for supplier, ls in groups.items():
        status = ("✅ envoyé directement au fournisseur" if supplier in sent_suppliers
                  else "⚠️ pas d'email fournisseur — à transmettre manuellement")
        blocks += f"<h3 style='font-size:14px;margin:14px 0 2px'>{supplier} <span style='font-weight:normal;font-size:11px'>({status})</span></h3>{_lines_table(ls)}"
    body = f"<p>Bonjour {gerant_name},</p><p>Voici le récapitulatif de votre bon de commande <strong>{order_number}</strong> :</p>{blocks}"
    await send_email(to_email=gerant_email, to_name=gerant_name, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Recap bon de commande {order_number}", tags=["restock_order_recap"])
