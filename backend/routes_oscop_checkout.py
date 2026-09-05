"""Checkout O'SCOP direct : commande client + facture O'SCOP + encaissement Stripe O'SCOP."""
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from stripe_accounts import get_stripe_key

logger = logging.getLogger(__name__)
oscop_checkout_router = APIRouter(prefix="/api/oscop-checkout", tags=["Checkout O'SCOP"])
db = None


def set_oscop_checkout_database(database):
    global db
    db = database


OSCOP_SELLER = "SCIC SAS OBJECTIF SCOP OUTREMER"
FORBIDDEN_METHODS = {"CREDISCOP", "CREDI_SCOP", "SERVICE_CREDITS"}


class SessionCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10000)
    include_logistics: bool = False
    customer_email: EmailStr
    customer_name: str
    origin_url: str
    payment_method: str = "CARD"


async def next_invoice_number() -> str:
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"oscop_invoice_{year}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return f"FAC-OSCOP-{year}-{doc['seq']:04d}"


async def _get_offer(product_id: str) -> dict:
    prod = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not prod:
        prod = await db.catalog_products.find_one({"id": product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if prod.get("sale_model") != "OSCOP_DIRECT_RESALE":
        raise HTTPException(status_code=409, detail="Cette offre n'est pas vendue par O'SCOP")
    if not prod.get("oscop_price_ht_cents"):
        raise HTTPException(status_code=409, detail="Prix de vente O'SCOP non défini sur cette offre")
    return prod


@oscop_checkout_router.get("/offer/{product_id}")
async def get_oscop_offer(product_id: str):
    prod = await _get_offer(product_id)
    return {
        "product_id": product_id,
        "name": prod.get("name"),
        "seller": OSCOP_SELLER,
        "price_ht_cents": prod["oscop_price_ht_cents"],
        "vat_rate": prod.get("oscop_vat_rate", 8.5),
        "logistics_available": bool(prod.get("oscop_logistics_available")),
        "logistics_price_ht_cents": prod.get("oscop_logistics_price_ht_cents", 0),
        "cgv_url": "/conditions-vente-oscop",
    }


@oscop_checkout_router.post("/session")
async def create_session(payload: SessionCreate):
    if payload.payment_method.upper() in FORBIDDEN_METHODS:
        raise HTTPException(status_code=409, detail="CREDI'SCOP-INVEST ne peut jamais servir à payer des produits ou de la logistique")
    prod = await _get_offer(payload.product_id)
    goods_ht = prod["oscop_price_ht_cents"] * payload.quantity
    logistics_ht = 0
    if payload.include_logistics:
        if not prod.get("oscop_logistics_available"):
            raise HTTPException(status_code=409, detail="Logistique LOGI'SCOP non disponible sur cette offre")
        logistics_ht = int(prod.get("oscop_logistics_price_ht_cents", 0))
    vat_rate = float(prod.get("oscop_vat_rate", 8.5))
    total_ht = goods_ht + logistics_ht
    vat_cents = round(total_ht * vat_rate / 100)
    total_ttc = total_ht + vat_cents

    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=500, detail="Compte Stripe O'SCOP non configuré")
    line_items = [{
        "price_data": {"currency": "eur", "unit_amount": prod["oscop_price_ht_cents"] + round(prod["oscop_price_ht_cents"] * vat_rate / 100),
                       "product_data": {"name": f"{prod.get('name')} — vendu par O'SCOP (TTC)"}},
        "quantity": payload.quantity,
    }]
    if logistics_ht:
        line_items.append({
            "price_data": {"currency": "eur", "unit_amount": logistics_ht + round(logistics_ht * vat_rate / 100),
                           "product_data": {"name": "Logistique intégrée LOGI'SCOP (TTC)"}},
            "quantity": 1,
        })
    try:
        session = stripe.checkout.Session.create(
            api_key=key,
            mode="payment",
            line_items=line_items,
            customer_email=payload.customer_email,
            success_url=f"{payload.origin_url}/oscop-checkout/retour?order_id={order_id}",
            cancel_url=f"{payload.origin_url}/catalogue",
            metadata={"oscop_order_id": order_id, "seller": "OSCOP"},
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {getattr(exc, 'user_message', None) or str(exc)}")

    order = {
        "id": order_id,
        "order_number": f"CMD-OSCOP-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}",
        "sale_model": "OSCOP_DIRECT_RESALE",
        "seller_entity": OSCOP_SELLER,
        "invoice_issuer": OSCOP_SELLER,
        "payment_recipient": OSCOP_SELLER,
        "product_id": payload.product_id,
        "product_name": prod.get("name"),
        "quantity": payload.quantity,
        "include_logistics": payload.include_logistics,
        "goods_ht_cents": goods_ht,
        "logistics_ht_cents": logistics_ht,
        "vat_rate": vat_rate,
        "vat_cents": vat_cents,
        "total_ttc_cents": total_ttc,
        "customer_email": payload.customer_email,
        "customer_name": payload.customer_name,
        "stripe_session_id": session.id,
        "status": "pending_payment",
        "invoice_number": None,
        "roles_snapshot": {
            "seller": OSCOP_SELLER, "invoicer": OSCOP_SELLER, "collector": OSCOP_SELLER,
            "logistics_operator": "LOGI'SCOP (établissement de la SCIC SAS OBJECTIF SCOP OUTREMER)" if payload.include_logistics else "Client",
            "immutable": True, "created_at": now.isoformat(),
        },
        "created_at": now.isoformat(),
    }
    await db.oscop_client_orders.insert_one(dict(order))
    return {"order_id": order_id, "checkout_url": session.url,
            "total_ttc_cents": total_ttc, "goods_ht_cents": goods_ht, "logistics_ht_cents": logistics_ht}


@oscop_checkout_router.get("/status/{order_id}")
async def get_order_status(order_id: str):
    order = await db.oscop_client_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] == "pending_payment":
        key = get_stripe_key("oscop")
        try:
            session = stripe.checkout.Session.retrieve(order["stripe_session_id"], api_key=key)
        except stripe.error.StripeError:
            session = None
        if session and session.payment_status == "paid":
            invoice_number = await next_invoice_number()
            now = datetime.now(timezone.utc).isoformat()
            await db.oscop_client_orders.update_one(
                {"id": order_id},
                {"$set": {"status": "paid", "invoice_number": invoice_number, "paid_at": now,
                          "psp_reference": session.payment_intent}})
            order.update({"status": "paid", "invoice_number": invoice_number, "paid_at": now})
            await _send_invoice_email(order)
    return order


def _invoice_doc(order: dict) -> dict:
    eur = lambda c: f"{(c or 0) / 100:,.2f} EUR".replace(",", " ").replace(".", ",")
    sections = [
        ("Client", f"{order.get('customer_name')} — {order.get('customer_email')}"),
        ("Commande", order.get("order_number")),
        ("Vendeur juridique", OSCOP_SELLER),
        ("Produit", f"{order.get('product_name')} × {order.get('quantity')}"),
        ("Marchandises HT", eur(order.get("goods_ht_cents"))),
    ]
    if order.get("include_logistics"):
        sections.append(("Logistique intégrée LOGI'SCOP HT", eur(order.get("logistics_ht_cents"))))
    sections += [
        (f"TVA ({order.get('vat_rate')} %)", eur(order.get("vat_cents"))),
        ("Total TTC réglé", eur(order.get("total_ttc_cents"))),
        ("Référence PSP", order.get("psp_reference") or "-"),
        ("CGV applicables", "Conditions Générales de Vente O'SCOP (/conditions-vente-oscop)"),
    ]
    return {"doc_type": "CLIENT_INVOICE", "doc_number": order["invoice_number"],
            "sections": sections, "created_at": order.get("paid_at", "")}


async def _send_invoice_email(order: dict):
    try:
        import base64
        from operation_docs_pdf import build_operation_pdf
        from brevo_service import send_email, _wrap_html
        pdf = build_operation_pdf(_invoice_doc(order))
        html = _wrap_html("Votre facture O'SCOP", (
            f"<p style='font-size:14px;'>Bonjour {order.get('customer_name')},</p>"
            f"<p style='font-size:14px;'>Votre paiement de la commande <b>{order.get('order_number')}</b> est confirmé. "
            f"Votre facture officielle <b>{order['invoice_number']}</b>, émise par la SCIC SAS OBJECTIF SCOP OUTREMER, est jointe en PDF.</p>"
            f"<p style='font-size:12px;color:#B8A98F;'>Vendeur, émetteur de la facture et bénéficiaire du paiement : SCIC SAS OBJECTIF SCOP OUTREMER.</p>"))
        await send_email(order["customer_email"], order.get("customer_name"),
                         f"Facture O'SCOP {order['invoice_number']} — paiement confirmé", html,
                         tags=["oscop_invoice"],
                         attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{order['invoice_number']}.pdf"}])
        await db.oscop_client_orders.update_one({"id": order["id"]}, {"$set": {"invoice_email_sent": True}})
    except Exception as exc:
        logger.warning(f"Email facture O'SCOP non envoyé: {exc}")


DEFAULT_REMINDER = {"id": "payment_reminder", "delay_hours": 48, "enabled": True}


REMINDER_TONES = [
    ("Rappel — votre commande O'SCOP est en attente de paiement",
     "est toujours en attente de règlement. Vous pouvez finaliser votre paiement en toute simplicité."),
    ("2e rappel — règlement attendu pour votre commande O'SCOP",
     "reste impayée malgré notre premier rappel. Merci de procéder au règlement rapidement afin de maintenir votre commande."),
    ("Dernier rappel avant litige — commande O'SCOP impayée",
     "demeure impayée. Sans règlement sous le délai indiqué, la commande sera signalée en litige et pourra être annulée."),
]


async def run_oscop_payment_reminders(database):
    """Relances échelonnées (3 max, ton croissant) puis signalement en litige."""
    settings = await database.oscop_settings.find_one({"id": "payment_reminder"}) or dict(DEFAULT_REMINDER)
    if not settings.get("enabled"):
        return 0
    from datetime import timedelta
    delay = timedelta(hours=float(settings.get("delay_hours", 48)))
    now = datetime.now(timezone.utc)
    pending = await database.oscop_client_orders.find(
        {"status": "pending_payment"}, {"_id": 0}).to_list(200)
    sent = 0
    for order in pending:
        count = int(order.get("reminder_count", 0) or (1 if order.get("reminder_sent") else 0))
        anchor = order.get("last_reminder_at") or order.get("created_at")
        try:
            anchor_dt = datetime.fromisoformat(anchor.replace("Z", "+00:00"))
        except Exception:
            continue
        if anchor_dt.tzinfo is None:
            anchor_dt = anchor_dt.replace(tzinfo=timezone.utc)
        if now - anchor_dt < delay:
            continue
        key = get_stripe_key("oscop")
        url = None
        try:
            session = stripe.checkout.Session.retrieve(order["stripe_session_id"], api_key=key)
            if session.payment_status == "paid":
                continue
            url = session.url
        except stripe.error.StripeError:
            pass
        if count >= 3:
            await database.oscop_client_orders.update_one(
                {"id": order["id"]},
                {"$set": {"status": "disputed", "disputed_at": now.isoformat()}})
            await database.admin_notifications.insert_one({
                "id": str(uuid.uuid4()), "title": f"Commande en litige — {order.get('order_number')}",
                "message": f"Impayée après 3 relances : {order.get('customer_name')} ({order.get('customer_email')}), "
                           f"{(order.get('total_ttc_cents', 0) / 100):.2f} € TTC.",
                "type": "warning", "category": "achat_revente", "target_user_id": None,
                "action_url": "/super-admin", "metadata": {}, "is_read": False,
                "created_at": now.isoformat()})
            continue
        subject, body_line = REMINDER_TONES[count]
        try:
            from brevo_service import send_email, _wrap_html
            html = _wrap_html(subject, (
                f"<p style='font-size:14px;'>Bonjour {order.get('customer_name')},</p>"
                f"<p style='font-size:14px;'>Votre commande <b>{order.get('order_number')}</b> "
                f"({(order.get('total_ttc_cents', 0) / 100):.2f} € TTC) auprès de la SCIC SAS OBJECTIF SCOP OUTREMER {body_line}</p>"
                + (f"<p style='font-size:14px;'><a href='{url}' style='color:#D9B35A;'>Finaliser mon paiement</a></p>" if url else "")))
            await send_email(order["customer_email"], order.get("customer_name"),
                             f"{subject} — {order.get('order_number')}", html, tags=["oscop_reminder"])
            await database.oscop_client_orders.update_one(
                {"id": order["id"]},
                {"$set": {"reminder_count": count + 1, "reminder_sent": True,
                          "last_reminder_at": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning(f"Relance paiement O'SCOP échouée pour {order.get('id')}: {exc}")
    return sent


from fastapi import Depends
from routes_v2 import get_current_user_v2


async def _admin_only(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@oscop_checkout_router.get("/reminder-settings")
async def get_reminder_settings(admin: dict = Depends(_admin_only)):
    s = await db.oscop_settings.find_one({"id": "payment_reminder"}, {"_id": 0})
    return s or dict(DEFAULT_REMINDER)


@oscop_checkout_router.put("/reminder-settings")
async def update_reminder_settings(payload: dict, admin: dict = Depends(_admin_only)):
    delay = float(payload.get("delay_hours", 48))
    if delay < 1 or delay > 720:
        raise HTTPException(status_code=400, detail="Délai entre 1 et 720 heures")
    await db.oscop_settings.update_one(
        {"id": "payment_reminder"},
        {"$set": {"delay_hours": delay, "enabled": bool(payload.get("enabled", True))}}, upsert=True)
    return {"success": True, "delay_hours": delay, "enabled": bool(payload.get("enabled", True))}


@oscop_checkout_router.get("/disputed-orders")
async def list_disputed_orders(admin: dict = Depends(_admin_only)):
    orders = await db.oscop_client_orders.find(
        {"status": "disputed"}, {"_id": 0}).sort("disputed_at", -1).to_list(100)
    return {"orders": orders}


@oscop_checkout_router.post("/orders/{order_id}/dispute-action")
async def dispute_action(order_id: str, payload: dict, admin: dict = Depends(_admin_only)):
    action = payload.get("action")
    if action not in ("remind", "cancel"):
        raise HTTPException(status_code=400, detail="action: remind ou cancel")
    order = await db.oscop_client_orders.find_one({"id": order_id, "status": "disputed"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande en litige introuvable")
    now = datetime.now(timezone.utc).isoformat()
    if action == "cancel":
        await db.oscop_client_orders.update_one(
            {"id": order_id}, {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_by": admin.get("email")}})
        try:
            from brevo_service import send_email, _wrap_html
            html = _wrap_html("Annulation de votre commande O'SCOP", (
                f"<p style='font-size:14px;'>Bonjour {order.get('customer_name')},</p>"
                f"<p style='font-size:14px;'>Faute de règlement, votre commande <b>{order.get('order_number')}</b> "
                "a été annulée par la SCIC SAS OBJECTIF SCOP OUTREMER. Vous pouvez repasser commande à tout moment.</p>"))
            await send_email(order["customer_email"], order.get("customer_name"),
                             f"Commande {order.get('order_number')} annulée", html, tags=["oscop_reminder"])
        except Exception:
            pass
        return {"success": True, "status": "cancelled"}
    # remind : relance manuelle (repasse en pending, compteur figé à 3, nouvel ancrage)
    url = None
    try:
        session = stripe.checkout.Session.retrieve(order["stripe_session_id"], api_key=get_stripe_key("oscop"))
        if session.payment_status == "paid":
            raise HTTPException(status_code=409, detail="Cette commande est déjà payée — utilisez la vérification de statut")
        url = session.url
    except stripe.error.StripeError:
        pass
    try:
        from brevo_service import send_email, _wrap_html
        subject, body_line = REMINDER_TONES[2]
        html = _wrap_html(subject, (
            f"<p style='font-size:14px;'>Bonjour {order.get('customer_name')},</p>"
            f"<p style='font-size:14px;'>Votre commande <b>{order.get('order_number')}</b> "
            f"({(order.get('total_ttc_cents', 0) / 100):.2f} € TTC) {body_line}</p>"
            + (f"<p style='font-size:14px;'><a href='{url}' style='color:#D9B35A;'>Finaliser mon paiement</a></p>" if url else "")))
        await send_email(order["customer_email"], order.get("customer_name"),
                         f"{subject} — {order.get('order_number')}", html, tags=["oscop_reminder"])
    except Exception:
        pass
    await db.oscop_client_orders.update_one(
        {"id": order_id},
        {"$set": {"status": "pending_payment", "last_reminder_at": now,
                  "manual_remind_by": admin.get("email")}})
    return {"success": True, "status": "pending_payment"}


@oscop_checkout_router.get("/invoice/{order_id}/pdf")
async def download_invoice_pdf(order_id: str):
    from fastapi.responses import Response
    from operation_docs_pdf import build_operation_pdf
    order = await db.oscop_client_orders.find_one({"id": order_id}, {"_id": 0})
    if not order or order.get("status") != "paid":
        raise HTTPException(status_code=404, detail="Facture indisponible")
    pdf = build_operation_pdf(_invoice_doc(order))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{order["invoice_number"]}.pdf"'})
