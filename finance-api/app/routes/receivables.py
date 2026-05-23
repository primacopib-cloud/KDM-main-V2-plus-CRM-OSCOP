"""Receivables — créances / factures / appels à contribution / cotisations / PASS."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.party import Party
from app.models.receivable import Receivable, RECEIVABLE_TYPES, RECEIVABLE_STATUSES
from app.schemas.all import ReceivableCreate, ReceivableOut
from app.services import ledger_service

router = APIRouter(prefix="/receivables", tags=["receivables"])


@router.post("", response_model=ReceivableOut, status_code=201)
def create_receivable(payload: ReceivableCreate, db: Session = Depends(get_db), _: str = Depends(require_user)):
    if payload.receivable_type not in RECEIVABLE_TYPES:
        raise HTTPException(status_code=400, detail=f"receivable_type doit être l'un de {RECEIVABLE_TYPES}")

    party = db.get(Party, payload.party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Partie cible introuvable")

    r = Receivable(**payload.model_dump(), status="OPEN")
    db.add(r)
    db.flush()

    ledger_service.record(
        db,
        kind="RECEIVABLE_CREATED",
        amount_cents=r.amount_cents,
        currency=r.currency,
        party_id=r.party_id,
        receivable_id=r.id,
        notes=f"{r.receivable_type} — {r.title}",
        extra_payload={"reference": r.reference, "external_source": r.external_source, "external_id": r.external_id},
    )
    db.commit()
    db.refresh(r)
    return r


@router.get("", response_model=List[ReceivableOut])
def list_receivables(
    db: Session = Depends(get_db),
    _: str = Depends(require_user),
    party_id: Optional[str] = None,
    status: Optional[str] = None,
    receivable_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    if status and status not in RECEIVABLE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status doit être l'un de {RECEIVABLE_STATUSES}")

    stmt = select(Receivable)
    if party_id:
        stmt = stmt.where(Receivable.party_id == party_id)
    if status:
        stmt = stmt.where(Receivable.status == status)
    if receivable_type:
        stmt = stmt.where(Receivable.receivable_type == receivable_type)
    stmt = stmt.order_by(Receivable.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/{receivable_id}", response_model=ReceivableOut)
def get_receivable(receivable_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    r = db.get(Receivable, receivable_id)
    if not r:
        raise HTTPException(status_code=404, detail="Créance introuvable")
    return r
