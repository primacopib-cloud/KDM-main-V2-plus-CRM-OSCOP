"""Reporting + audit endpoints."""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.ledger import LedgerEntry
from app.models.party import Party
from app.models.payment import Payment
from app.models.receivable import Receivable
from app.models.sepa_mandate import SepaMandate
from app.schemas.all import LedgerEntryOut, LedgerVerifyOut
from app.services import ledger_service

router = APIRouter(tags=["reporting"])


@router.get("/reporting/dashboard")
def dashboard(db: Session = Depends(get_db), _: str = Depends(require_user)):
    total_parties = int(db.execute(select(func.count(Party.id))).scalar() or 0)
    total_receivables = int(db.execute(select(func.count(Receivable.id))).scalar() or 0)
    sum_receivables_cents = int(db.execute(select(func.coalesce(func.sum(Receivable.amount_cents), 0))).scalar() or 0)
    sum_paid_cents = int(db.execute(select(func.coalesce(func.sum(Receivable.amount_paid_cents), 0))).scalar() or 0)
    sum_refunded_cents = int(db.execute(select(func.coalesce(func.sum(Receivable.amount_refunded_cents), 0))).scalar() or 0)
    total_payments = int(db.execute(select(func.count(Payment.id))).scalar() or 0)
    total_mandates = int(db.execute(select(func.count(SepaMandate.id))).scalar() or 0)

    by_status = {row[0]: int(row[1]) for row in db.execute(
        select(Receivable.status, func.count(Receivable.id)).group_by(Receivable.status)
    ).all()}

    return {
        "parties": {"total": total_parties},
        "receivables": {
            "total_count": total_receivables,
            "by_status": by_status,
            "total_amount_cents": sum_receivables_cents,
            "total_paid_cents": sum_paid_cents,
            "total_refunded_cents": sum_refunded_cents,
            "outstanding_cents": sum_receivables_cents - sum_paid_cents + sum_refunded_cents,
        },
        "payments": {"total": total_payments},
        "mandates": {"total": total_mandates},
        "ledger": {"total_entries": ledger_service.count_entries(db)},
    }


@router.get("/ledger/entries", response_model=List[LedgerEntryOut])
def list_ledger(
    db: Session = Depends(get_db), _: str = Depends(require_user),
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
):
    stmt = select(LedgerEntry).order_by(LedgerEntry.sequence.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/audit/verify-ledger-chain", response_model=LedgerVerifyOut)
def verify_ledger_chain(db: Session = Depends(get_db), _: str = Depends(require_user)):
    return ledger_service.verify_chain(db)
