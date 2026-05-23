"""PSP webhooks — Stripe / GoCardless intake with idempotency.

These endpoints are intentionally *unauthenticated* (PSPs sign with HMAC).
For now we accept any payload (signature verification is a no-op until
STRIPE_WEBHOOK_SECRET / GoCardless equivalent is provided), but every event
is stored in `webhook_events` with its raw payload for replay/audit.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.webhook_event import WebhookEvent
from app.models.payment import Payment
from app.services import reconciliation_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _store_event(db: Session, provider: str, payload: dict) -> WebhookEvent:
    external_id = (
        payload.get("id")
        or payload.get("event_id")
        or payload.get("events", [{}])[0].get("id", "")
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
        event_type=str(payload.get("type") or payload.get("events", [{}])[0].get("action", "")),
        signature_valid=True,  # TODO: real signature check when keys are wired
        processed=False,
        raw_payload=payload,
    )
    db.add(event)
    db.flush()
    return event


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe webhook intake (idempotent)."""
    payload = await request.json()
    event = await _store_event(db, "stripe", payload)
    if event.processed:
        return {"received": True, "duplicate": True, "event_id": event.id}

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
    return {"received": True, "event_id": event.id}


@router.post("/gocardless")
async def gocardless_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    event = await _store_event(db, "gocardless", payload)
    if event.processed:
        return {"received": True, "duplicate": True, "event_id": event.id}
    # TODO: handle mandate.created / mandate.active / payment.confirmed
    event.processed = True
    db.commit()
    return {"received": True, "event_id": event.id}
