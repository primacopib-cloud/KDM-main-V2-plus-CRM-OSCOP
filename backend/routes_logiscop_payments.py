"""Paiement en ligne Stripe des factures transport LOGI'SCOP (Donneur d'Ordre)."""
import logging
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core_deps import get_current_user, create_notification
from db import get_database

logger = logging.getLogger(__name__)
logiscop_payments_router = APIRouter(prefix="/api/logiscop-transport", tags=["logiscop-transport"])


class PayBody(BaseModel):
    origin_url: str


async def _get_invoice_for_user(db, invoice_id: str, user: dict) -> dict:
    inv = await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    if not user.get("is_admin") and inv["user_id"] != user["id"]:
        m = await db.org_memberships.find_one({"user_id": user["id"], "org_id": inv["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    return inv


@logiscop_payments_router.post("/invoices/{invoice_id}/pay")
async def pay_invoice(invoice_id: str, body: PayBody, current_user: dict = Depends(get_current_user)):
    db = get_database()
    inv = await _get_invoice_for_user(db, invoice_id, current_user)
    if inv["status"] == "PAID":
        raise HTTPException(status_code=409, detail="Facture déjà réglée")
    origin = body.origin_url.rstrip("/")
    if not origin:
        raise HTTPException(status_code=400, detail="origin_url requis")
    from routes_payment import _wallet_stripe_key
    try:
        session = stripe.checkout.Session.create(
            api_key=_wallet_stripe_key(),
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": inv["total_ttc_cents"],
                    "product_data": {"name": f"LOGI'SCOP — Facture transport {inv['ref']} (OT {inv['ot_ref']})"},
                },
                "quantity": 1,
            }],
            success_url=f"{origin}/espace-acheteur?invoice_payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/espace-acheteur?invoice_payment=cancelled",
            metadata={"user_id": current_user["id"], "invoice_id": invoice_id,
                      "invoice_ref": inv["ref"], "source": "logiscop_invoice"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Checkout facture transport %s : %s", invoice_id, e)
        raise HTTPException(status_code=500, detail="Erreur création session de paiement")
    await db.logiscop_invoice_payments.insert_one({
        "id": f"lip_{uuid.uuid4().hex[:12]}", "session_id": session.id,
        "invoice_id": invoice_id, "invoice_ref": inv["ref"],
        "user_id": current_user["id"], "org_id": inv["org_id"],
        "amount_cents": inv["total_ttc_cents"], "currency": "EUR",
        "status": "created", "created_at": datetime.now(timezone.utc).isoformat()})
    return {"checkout_url": session.url, "session_id": session.id}


@logiscop_payments_router.get("/credits")
async def my_credits(current_user: dict = Depends(get_current_user)):
    """Avoirs de service du Donneur d'Ordre (article 22)."""
    db = get_database()
    m = await db.org_memberships.find_one({"user_id": current_user["id"]}, {"_id": 0, "org_id": 1})
    org_id = current_user.get("organization_id") or (m or {}).get("org_id")
    if not org_id:
        return []
    return await db.logiscop_transport_credits.find({"org_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(100)


@logiscop_payments_router.get("/credits/{credit_id}/pdf")
async def credit_note_pdf(credit_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    credit = await db.logiscop_transport_credits.find_one({"id": credit_id}, {"_id": 0})
    if not credit:
        raise HTTPException(status_code=404, detail="Avoir introuvable")
    if not current_user.get("is_admin") and credit["user_id"] != current_user["id"]:
        m = await db.org_memberships.find_one({"user_id": current_user["id"], "org_id": credit["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    ot = await db.logiscop_transport_orders.find_one({"id": credit["ot_id"]}, {"_id": 0}) or {}
    from logiscop_transport_billing import build_credit_note_pdf
    from fastapi.responses import Response
    return Response(content=build_credit_note_pdf(credit, ot), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={credit['ref']}.pdf"})


@logiscop_payments_router.get("/invoices/pay/status/{session_id}")
async def invoice_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    txn = await db.logiscop_invoice_payments.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if not current_user.get("is_admin") and txn["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    from routes_payment import _wallet_stripe_key
    try:
        session = stripe.checkout.Session.retrieve(session_id, api_key=_wallet_stripe_key())
    except Exception:
        raise HTTPException(status_code=502, detail="Vérification Stripe impossible")
    if session.payment_status == "paid" and txn["status"] != "completed":
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.logiscop_transport_invoices.update_one(
            {"id": txn["invoice_id"]},
            {"$set": {"status": "PAID", "paid_at": now_iso, "payment_method": "stripe",
                      "stripe_session_id": session_id}})
        await db.logiscop_invoice_payments.update_one(
            {"session_id": session_id}, {"$set": {"status": "completed", "completed_at": now_iso}})
        await create_notification(
            "logiscop_invoice_paid_online", "Facture transport réglée en ligne",
            f"La facture {txn['invoice_ref']} ({txn['amount_cents'] / 100:.2f} € TTC) a été réglée par carte (Stripe).",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"invoice_id": txn["invoice_id"], "ref": txn["invoice_ref"]})
        logger.info("Facture transport %s réglée via Stripe (%s)", txn["invoice_ref"], session_id)
    inv = await db.logiscop_transport_invoices.find_one({"id": txn["invoice_id"]}, {"_id": 0, "status": 1, "ref": 1})
    return {"session_id": session_id, "payment_status": session.payment_status,
            "invoice_status": (inv or {}).get("status")}
