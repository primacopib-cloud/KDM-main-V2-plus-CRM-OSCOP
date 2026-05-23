"""Parties — clients / adhérents / fournisseurs."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.party import Party, PARTY_TYPES
from app.schemas.all import PartyCreate, PartyOut

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("", response_model=PartyOut, status_code=201)
def create_party(payload: PartyCreate, db: Session = Depends(get_db), _: str = Depends(require_user)):
    if payload.party_type not in PARTY_TYPES:
        raise HTTPException(status_code=400, detail=f"party_type doit être l'un de {PARTY_TYPES}")
    party = Party(**payload.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.get("", response_model=List[PartyOut])
def list_parties(
    db: Session = Depends(get_db),
    _: str = Depends(require_user),
    q: Optional[str] = Query(None, description="Recherche dans display_name / email / SIRET / external_customer_id"),
    party_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Party)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            Party.display_name.ilike(like),
            Party.email.ilike(like),
            Party.siret.ilike(like),
            Party.external_customer_id.ilike(like),
        ))
    if party_type:
        stmt = stmt.where(Party.party_type == party_type)
    stmt = stmt.order_by(Party.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/{party_id}", response_model=PartyOut)
def get_party(party_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    p = db.get(Party, party_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    return p
