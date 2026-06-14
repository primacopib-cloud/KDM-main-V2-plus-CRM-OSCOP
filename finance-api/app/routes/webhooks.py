"""PSP webhooks — Stripe / GoCardless intake with idempotency + signature verify.

These endpoints are intentionally *unauthenticated* (PSPs sign with HMAC):
  • Stripe : header `Stripe-Signature` — verified via STRIPE_WEBHOOK_SECRET
  • GoCardless : header `Webhook-Signature` — verified via GOCARDLESS_WEBHOOK_SECRET
Every event is stored in `webhook_events` with its raw payload for replay/audit
and processed exactly once (idempotency on `external_event_id`).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.webhook_event import WebhookEvent
from app.models.payment import Payment
from app.services import psp_adapters, reconciliation_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _store_event(db: Session, provider: str, payload: dict, signature_valid: bool) -> WebhookEvent:
    external_id = (
        payload.get("id")
        or payload.get("event_id")
        or (payload.get("events", [{}]) or [{}])[0].get("id", "")
    )
    if not external_id:
        external_id = f"{provider}_{payload.get('type', 'unknown')}_{id(payload)}"
    existing = db.execute(
        select(WebhookEvent).where(WebhookEvent.external_event_id == external_id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    event = WebhookEvent(
        provider=provider,
        external_event_id=external_id,
        event_type=str(payload.get("type") or (payload.get("events", [{}]) or [{}])[0].get("action", "")),
        signature_valid=signature_valid,
        processed=False,
        raw_payload=payload,
    )
    db.add(event)
    db.flush()
    return event


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    """Stripe webhook intake — verifies signature when secret is configured."""
    raw_body = await request.body()
    verified_event = psp_adapters.verify_stripe_signature(
        payload=raw_body, signature_header=stripe_signature or "",
    )
    if verified_event is not None:
        payload = dict(verified_event)
        signature_valid = True
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {"error": "invalid json"}
        signature_valid = False

    event = await _store_event(db, "stripe", payload, signature_valid)
    if event.processed:
        return {"received": True, "duplicate": True, "event_id": event.id, "signature_valid": signature_valid}

    event_type = (payload.get("type") or "").lower()
    data = (payload.get("data") or {}).get("object", {})
    psp_session_id = data.get("id") or data.get("payment_intent") or ""

    if event_type in ("checkout.session.completed", "payment_intent.succeeded") and psp_session_id:
        payment = db.execute(
            select(Payment).where(
                (Payment.psp_session_id == psp_session_id)
                | (Payment.psp_payment_id == psp_session_id)
            )
        ).scalar_one_or_none()
        if payment and payment.status not in ("SUCCEEDED",):
            reconciliation_service.apply_payment_success(
                db, payment=payment, psp_payment_id=data.get("payment_intent") or psp_session_id,
            )

    if event_type == "charge.refunded" and psp_session_id:
        payment = db.execute(
            select(Payment).where(Payment.psp_payment_id == psp_session_id)
        ).scalar_one_or_none()
        if payment:
            amount = int(data.get("amount_refunded") or 0)
            if amount > 0:
                refundable = payment.amount_cents - (payment.amount_refunded_cents or 0)
                reconciliation_service.apply_payment_refund(
                    db, payment=payment, amount_cents=min(amount, refundable), reason="stripe.charge.refunded",
                )

    event.processed = True
    db.commit()
    return {"received": True, "event_id": event.id, "signature_valid": signature_valid}


@router.post("/gocardless")
async def gocardless_webhook(
    request: Request,
    db: Session = Depends(get_db),
    webhook_signature: Optional[str] = Header(None, alias="Webhook-Signature"),
):
    raw_body = await request.body()
    verified = psp_adapters.verify_gocardless_signature(
        payload=raw_body, signature_header=webhook_signature or "",
    )
    if verified is not None:
        payload = verified
        signature_valid = True
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {"error": "invalid json"}
        signature_valid = False

    event = await _store_event(db, "gocardless", payload, signature_valid)
    if event.processed:
        return {"received": True, "duplicate": True, "event_id": event.id, "signature_valid": signature_valid}
    # TODO: handle mandate.created / mandate.active / payment.confirmed
    event.processed = True
    db.commit()
    return {"received": True, "event_id": event.id, "signature_valid": signature_valid}
