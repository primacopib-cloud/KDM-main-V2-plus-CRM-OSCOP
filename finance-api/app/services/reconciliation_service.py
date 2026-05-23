"""Reconciliation service — match a payment to a receivable + advance status.

Pure functions, callable from routes (no FastAPI deps here so they stay testable).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.receivable import Receivable
from app.services import ledger_service


def apply_payment_success(
    db: Session,
    *,
    payment: Payment,
    psp_payment_id: Optional[str] = None,
) -> Payment:
    """Mark a payment as succeeded, advance its receivable, journal it."""
    now = datetime.now(timezone.utc)
    payment.status = "SUCCEEDED"
    payment.paid_at = now
    if psp_payment_id:
        payment.psp_payment_id = psp_payment_id

    if payment.receivable_id:
        r: Optional[Receivable] = db.get(Receivable, payment.receivable_id)
        if r is not None:
            r.amount_paid_cents = (r.amount_paid_cents or 0) + payment.amount_cents
            if r.amount_paid_cents >= r.amount_cents:
                r.status = "PAID"
            else:
                r.status = "PARTIAL"

    ledger_service.record(
        db,
        kind="PAYMENT_SUCCEEDED",
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        party_id=payment.party_id or "",
        receivable_id=payment.receivable_id or "",
        payment_id=payment.id,
        notes=f"PSP {payment.psp_provider} session={payment.psp_session_id}",
        extra_payload={"method": payment.method, "psp_payment_id": payment.psp_payment_id},
    )
    return payment


def apply_payment_refund(
    db: Session,
    *,
    payment: Payment,
    amount_cents: int,
    reason: str = "",
) -> Payment:
    now = datetime.now(timezone.utc)
    payment.amount_refunded_cents = (payment.amount_refunded_cents or 0) + amount_cents
    payment.refunded_at = now
    payment.status = (
        "REFUNDED" if payment.amount_refunded_cents >= payment.amount_cents else "PARTIAL_REFUND"
    )

    if payment.receivable_id:
        r: Optional[Receivable] = db.get(Receivable, payment.receivable_id)
        if r is not None:
            r.amount_refunded_cents = (r.amount_refunded_cents or 0) + amount_cents
            if r.amount_refunded_cents >= r.amount_cents:
                r.status = "REFUNDED"

    ledger_service.record(
        db,
        kind="PAYMENT_REFUNDED",
        amount_cents=amount_cents,
        currency=payment.currency,
        party_id=payment.party_id or "",
        receivable_id=payment.receivable_id or "",
        payment_id=payment.id,
        notes=f"Refund {reason}".strip(),
        extra_payload={"reason": reason},
    )
    return payment
