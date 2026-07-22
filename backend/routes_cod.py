"""Paiement à la livraison (COD) — éligibilité, confirmation, encaissement admin et relance impayés."""
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from checkout_common import get_current_user_checkout, get_order_with_access_check
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
cod_router = APIRouter(prefix="/api/v2/checkout", tags=["cod"])
cod_admin_router = APIRouter(prefix="/api/admin/cod", tags=["cod-admin"])
db = None


def set_cod_database(database):
    global db
    db = database


async def _is_cod_eligible(user: dict) -> bool:
    from routes_catalog import get_user_org_context
    org, subscription, _, _, _ = await get_user_org_context(user)
    return bool(org and org.get("status") == "APPROVED" and subscription and subscription.get("status") == "ACTIVE")


@cod_router.get("/cod-eligibility")
async def cod_eligibility(current_user: dict = Depends(get_current_user_checkout)):
    eligible = await _is_cod_eligible(current_user)
    return {"eligible": eligible,
            "reason": None if eligible else "Réservé aux acheteurs Pro avec abonnement actif"}


@cod_router.post("/confirm-cod")
async def confirm_cod(order_id: str = Query(...), current_user: dict = Depends(get_current_user_checkout)):
    if not await _is_cod_eligible(current_user):
        raise HTTPException(status_code=403, detail="Paiement à la livraison réservé aux acheteurs Pro avec abonnement actif")
    order, _ = await get_order_with_access_check(order_id, current_user)
    if order["status"] not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(status_code=400, detail="Commande non éligible")
    if order.get("payment_status") in ("succeeded", "paid"):
        raise HTTPException(status_code=400, detail="Commande déjà payée")
    amount = order["total_ttc_cents"]
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "CONFIRMED",
            "payment_status": "cod_pending",
            "payment_method": "cod",
            "cod": True,
            "cod_amount_due_cents": amount,
            "confirmed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }})
    from consultation_audit import audit
    await audit("ORDER_COD_CONFIRMED", current_user.get("email"), None,
                {"order_id": order_id, "order_number": order.get("order_number"), "amount_due_cents": amount})
    try:
        import asyncio
        from erp_webhooks import dispatch_order_event
        asyncio.create_task(dispatch_order_event(order_id, "order.status_changed",
                                                 {"previous_status": order["status"], "new_status": "CONFIRMED", "payment": "cod"}))
    except Exception as exc:
        logger.warning("Webhook ERP COD non envoyé : %s", exc)
    logger.info("Commande %s confirmée en paiement à la livraison (%s cents)", order.get("order_number"), amount)
    return {"success": True, "order_id": order_id, "order_number": order.get("order_number"),
            "amount_due_cents": amount, "message": "Commande confirmée — règlement à la livraison"}


# ============== ADMIN : SUIVI ENCAISSEMENT ==============

@cod_admin_router.get("/orders")
async def list_cod_orders(admin: dict = Depends(require_admin)):
    items = await db.orders.find(
        {"payment_method": "cod"},
        {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "status": 1, "payment_status": 1,
         "total_ttc_cents": 1, "cod_amount_due_cents": 1, "confirmed_at": 1, "paid_at": 1,
         "cod_reminder_sent": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(100)
    org_ids = list({o["org_id"] for o in items if o.get("org_id")})
    orgs = {o["id"]: o.get("legal_name") or o.get("name") for o in
            await db.organizations.find({"id": {"$in": org_ids}}, {"id": 1, "legal_name": 1, "name": 1}).to_list(100)}
    for o in items:
        o["org_name"] = orgs.get(o.get("org_id"), "")
    pending = sum(1 for o in items if o.get("payment_status") == "cod_pending")
    due = sum(o.get("cod_amount_due_cents", 0) for o in items if o.get("payment_status") == "cod_pending")
    return {"items": items, "pending_count": pending, "pending_due_cents": due}


@cod_admin_router.post("/orders/{order_id}/collected")
async def mark_cod_collected(order_id: str, admin: dict = Depends(require_admin)):
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order.get("payment_method") != "cod":
        raise HTTPException(status_code=400, detail="Commande non payable à la livraison")
    if order.get("payment_status") == "succeeded":
        raise HTTPException(status_code=400, detail="Commande déjà encaissée")
    amount = order.get("cod_amount_due_cents") or order["total_ttc_cents"]
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"payment_status": "succeeded", "amount_paid_cents": amount,
                  "paid_at": datetime.utcnow(), "updated_at": datetime.utcnow()}})
    invoice_number = None
    try:
        from routes_invoices import generate_invoice_for_order
        invoice = await generate_invoice_for_order(order_id)
        invoice_number = invoice.get("invoice_number")
    except Exception as exc:
        logger.error("Facture COD non générée : %s", exc)
    from consultation_audit import audit
    await audit("ORDER_COD_COLLECTED", admin.get("email"), None,
                {"order_id": order_id, "order_number": order.get("order_number"), "amount_cents": amount})
    import asyncio
    asyncio.create_task(_send_cod_receipt(order_id, invoice_number))
    logger.info("Encaissement COD confirmé pour %s (%s cents)", order.get("order_number"), amount)
    return {"ok": True, "order_number": order.get("order_number"), "amount_paid_cents": amount,
            "invoice_number": invoice_number}


async def _send_cod_receipt(order_id: str, invoice_number: str = None) -> None:
    """Envoie le reçu d'encaissement PDF par email aux membres de l'org."""
    try:
        import base64
        order = await db.orders.find_one({"id": order_id})
        if not order:
            return
        org = await db.organizations.find_one({"id": order.get("org_id")}, {"legal_name": 1, "name": 1})
        org_name = (org or {}).get("legal_name") or (org or {}).get("name") or ""
        from pdf_cod_receipt import generate_cod_receipt_pdf
        pdf = generate_cod_receipt_pdf(order, org_name, invoice_number)
        members = await db.org_memberships.find({"org_id": order.get("org_id")}).to_list(3)
        users = await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                    {"email": 1, "first_name": 1}).to_list(3)
        amount = (order.get("amount_paid_cents") or 0) / 100
        html = ("<div style='font-family:Arial,sans-serif;max-width:560px'>"
                f"<p>Bonjour,</p><p>Nous confirmons l'encaissement de votre commande "
                f"<b>{order.get('order_number')}</b> ({amount:.2f} € TTC, paiement à la livraison). "
                "Vous trouverez votre reçu d'encaissement en pièce jointe.</p>"
                "<p>Merci pour votre confiance,<br/>KDMARCHÉ × O'SCOP</p></div>")
        from brevo_service import send_email
        for u in users:
            try:
                await send_email(to_email=u["email"], to_name=u.get("first_name"),
                                 subject=f"✅ Reçu d'encaissement — commande {order.get('order_number')}",
                                 html_content=html, tags=["cod-receipt"],
                                 attachments=[{"content": base64.b64encode(pdf).decode(),
                                               "name": f"recu-{order.get('order_number')}.pdf"}])
                logger.info("Reçu d'encaissement envoyé à %s (%s)", u["email"], order.get("order_number"))
            except Exception as exc:
                logger.warning("Envoi reçu COD échoué %s : %s", u.get("email"), exc)
    except Exception as exc:
        logger.error("_send_cod_receipt erreur : %s", exc)


async def process_cod_reminders(database) -> None:
    """Relance par email les commandes COD confirmées depuis 7 jours et toujours impayées (une relance)."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    orders = await database.orders.find({
        "payment_method": "cod", "payment_status": "cod_pending",
        "confirmed_at": {"$lt": cutoff}, "cod_reminder_sent": {"$ne": True},
    }).to_list(20)
    if not orders:
        return
    from brevo_service import send_email
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    admin_email = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    sent = 0
    for o in orders:
        amount = (o.get("cod_amount_due_cents") or o["total_ttc_cents"]) / 100
        members = await database.org_memberships.find({"org_id": o["org_id"]}).to_list(3)
        users = await database.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                          {"email": 1, "first_name": 1}).to_list(3)
        html = ("<div style='font-family:Arial,sans-serif;max-width:560px'>"
                f"<p>Bonjour,</p><p>Votre commande <b>{o.get('order_number')}</b> en paiement à la livraison "
                f"reste à régler : <b>{amount:.2f} € TTC</b>. Merci de préparer le règlement pour la réception "
                "de vos marchandises.</p>"
                f"<p><a href='{base}/commandes' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Voir ma commande</a></p>"
                "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p></div>")
        for u in users:
            try:
                await send_email(to_email=u["email"], to_name=u.get("first_name"),
                                 subject=f"⏰ Règlement à la livraison en attente — commande {o.get('order_number')}",
                                 html_content=html, tags=["cod-reminder"])
                sent += 1
            except Exception as exc:
                logger.warning("Relance COD échouée %s : %s", u.get("email"), exc)
        try:
            await send_email(to_email=admin_email, to_name="Équipe KDMARCHÉ",
                             subject=f"⚠️ COD impayé J+7 — commande {o.get('order_number')} ({amount:.2f} €)",
                             html_content=f"<p>La commande <b>{o.get('order_number')}</b> ({amount:.2f} € TTC, paiement à la livraison) est toujours impayée 7 jours après confirmation. Relance client envoyée.</p>",
                             tags=["cod-reminder-admin"])
        except Exception:
            pass
        await database.orders.update_one({"id": o["id"]}, {"$set": {"cod_reminder_sent": True}})
    if sent:
        logger.info("COD : %s relance(s) impayé J+7 envoyées", sent)
