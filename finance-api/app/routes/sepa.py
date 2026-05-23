"""SEPA mandates — Core (B2C) and B2B."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.party import Party
from app.models.sepa_mandate import SepaMandate, MANDATE_SCHEMES
from app.schemas.all import SepaMandateCreate, SepaMandateOut
from app.services import ledger_service

router = APIRouter(prefix="/sepa", tags=["sepa"])


def _next_umr(db: Session) -> str:
    """Generate a unique mandate reference UMR-YYYYMMDD-NNNN."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"UMR-{today}-"
    count_today = db.execute(
        select(SepaMandate).where(SepaMandate.reference.like(prefix + "%"))
    ).scalars().all()
    return f"{prefix}{len(count_today) + 1:04d}"


@router.post("/mandates", response_model=SepaMandateOut, status_code=201)
def create_mandate(payload: SepaMandateCreate, db: Session = Depends(get_db), _: str = Depends(require_user)):
    if payload.scheme not in MANDATE_SCHEMES:
        raise HTTPException(status_code=400, detail=f"scheme doit être l'un de {MANDATE_SCHEMES}")
    party = db.get(Party, payload.party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Partie cible introuvable")

    mandate = SepaMandate(
        party_id=payload.party_id,
        scheme=payload.scheme,
        status="DRAFT",
        reference=_next_umr(db),
        debtor_name=payload.debtor_name,
        iban_masked=payload.iban_masked,
        bic=payload.bic,
        psp_provider=payload.psp_provider,
        psp_mandate_id=payload.psp_mandate_id,
        metadata_json=payload.metadata_json,
    )
    db.add(mandate)
    db.flush()

    ledger_service.record(
        db,
        kind="MANDATE_CREATED",
        currency="EUR",
        party_id=mandate.party_id,
        mandate_id=mandate.id,
        notes=f"{mandate.scheme} {mandate.reference}",
        extra_payload={"iban_masked": mandate.iban_masked, "psp_provider": mandate.psp_provider},
    )
    db.commit()
    db.refresh(mandate)
    return mandate


@router.post("/mandates/{mandate_id}/activate", response_model=SepaMandateOut)
def activate_mandate(mandate_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    mandate = db.get(SepaMandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandat introuvable")
    if mandate.status in ("ACTIVE",):
        return mandate
    if mandate.status in ("REVOKED", "EXPIRED"):
        raise HTTPException(status_code=409, detail=f"Mandat {mandate.status} — réactivation impossible")

    now = datetime.now(timezone.utc)
    if not mandate.signed_at:
        mandate.signed_at = now
    mandate.activated_at = now
    mandate.status = "ACTIVE"

    ledger_service.record(
        db,
        kind="MANDATE_ACTIVATED",
        currency="EUR",
        party_id=mandate.party_id,
        mandate_id=mandate.id,
        notes=f"{mandate.scheme} {mandate.reference}",
    )
    db.commit()
    db.refresh(mandate)
    return mandate


@router.post("/mandates/{mandate_id}/revoke", response_model=SepaMandateOut)
def revoke_mandate(mandate_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    mandate = db.get(SepaMandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandat introuvable")
    if mandate.status == "REVOKED":
        return mandate
    mandate.status = "REVOKED"
    mandate.revoked_at = datetime.now(timezone.utc)
    ledger_service.record(
        db,
        kind="MANDATE_REVOKED",
        currency="EUR",
        party_id=mandate.party_id,
        mandate_id=mandate.id,
        notes=f"{mandate.scheme} {mandate.reference}",
    )
    db.commit()
    db.refresh(mandate)
    return mandate


@router.get("/mandates", response_model=List[SepaMandateOut])
def list_mandates(db: Session = Depends(get_db), _: str = Depends(require_user)):
    return list(db.execute(select(SepaMandate).order_by(SepaMandate.created_at.desc())).scalars().all())
