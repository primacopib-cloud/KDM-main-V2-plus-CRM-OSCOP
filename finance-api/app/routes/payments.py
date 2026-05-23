"""Payments — initiate, refund, list."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.party import Party
from app.models.payment import Payment, PAYMENT_METHODS
from app.models.receivable import Receivable
from app.schemas.all import PaymentCreate, PaymentOut, PaymentRefundIn
from app.services import ledger_service, psp_adapters, reconciliation_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut, status_code=201)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db), _: str = Depends(require_user)):
    if payload.method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail=f"method doit être l'un de {PAYMENT_METHODS}")

    party = db.get(Party, payload.party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Partie cible introuvable")

    if payload.receivable_id:
        r = db.get(Receivable, payload.receivable_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Créance cible introuvable")

    # Initiate PSP session
    session = psp_adapters.create_checkout(
        provider=payload.psp_provider,
        amount_cents=payload.amount_cents,
        currency=payload.currency,
        party_email=party.email or "",
        description=payload.metadata_json.get("description", f"Payment {payload.amount_cents} {payload.currency}"),
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        metadata=payload.metadata_json,
    )

    payment_ok = session.get("status") != "FAILED"
    payment = Payment(
        party_id=payload.party_id,
        receivable_id=payload.receivable_id,
        method=payload.method,
        status="PENDING" if session.get("status") in ("PENDING", "SUCCEEDED") else "FAILED",
        amount_cents=payload.amount_cents,
        currency=payload.currency,
        psp_provider=payload.psp_provider,
        psp_account=payload.psp_account,
        psp_payment_id=session.get("psp_payment_id", ""),
        psp_session_id=session.get("psp_session_id", ""),
        hosted_url=session.get("hosted_url", ""),
        metadata_json=payload.metadata_json,
        failure_reason="" if payment_ok else str(session.get("raw", {}).get("error", "")),
    )
    db.add(payment)
    db.flush()

    ledger_service.record(
        db,
        kind="PAYMENT_INITIATED",
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        party_id=payment.party_id,
        receivable_id=payment.receivable_id or "",
        payment_id=payment.id,
        notes=f"PSP {payment.psp_provider} session={payment.psp_session_id}",
        extra_payload={"method": payment.method, "ok": payment_ok},
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{payment_id}/mark-paid", response_model=PaymentOut)
def mark_paid(payment_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    """Manual confirmation (cash, wire, sandbox PSP). Webhooks do this automatically in real life."""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if payment.status == "SUCCEEDED":
        return payment
    if payment.status in ("REFUNDED", "PARTIAL_REFUND", "CANCELLED"):
        raise HTTPException(status_code=409, detail=f"Paiement déjà {payment.status} — opération refusée")
    reconciliation_service.apply_payment_success(db, payment=payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{payment_id}/refund", response_model=PaymentOut)
def refund(payment_id: str, payload: PaymentRefundIn, db: Session = Depends(get_db), _: str = Depends(require_user)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if payment.status not in ("SUCCEEDED", "PARTIAL_REFUND"):
        raise HTTPException(status_code=409, detail=f"Impossible de rembourser un paiement {payment.status}")

    refundable = payment.amount_cents - (payment.amount_refunded_cents or 0)
    amount = payload.amount_cents if payload.amount_cents is not None else refundable
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount_cents doit être > 0")
    if amount > refundable:
        raise HTTPException(status_code=400, detail=f"Montant trop élevé (max remboursable={refundable})")

    # PSP refund (manual provider always succeeds)
    psp_adapters.refund_payment(
        provider=payment.psp_provider, psp_payment_id=payment.psp_payment_id,
        amount_cents=amount, reason=payload.reason,
    )
    reconciliation_service.apply_payment_refund(db, payment=payment, amount_cents=amount, reason=payload.reason)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=List[PaymentOut])
def list_payments(
    db: Session = Depends(get_db),
    _: str = Depends(require_user),
    party_id: Optional[str] = None,
    receivable_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Payment)
    if party_id:
        stmt = stmt.where(Payment.party_id == party_id)
    if receivable_id:
        stmt = stmt.where(Payment.receivable_id == receivable_id)
    if status:
        stmt = stmt.where(Payment.status == status)
    stmt = stmt.order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    return p
