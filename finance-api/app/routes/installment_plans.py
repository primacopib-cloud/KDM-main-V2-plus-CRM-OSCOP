"""Installment plans — échéanciers."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_user
from app.db.session import get_db
from app.models.installment import Installment, InstallmentPlan
from app.models.party import Party
from app.models.receivable import Receivable
from app.models.sepa_mandate import SepaMandate
from app.schemas.all import InstallmentOut, InstallmentPlanCreate, InstallmentPlanOut
from app.services import ledger_service

router = APIRouter(prefix="/installment-plans", tags=["installments"])


@router.post("", response_model=InstallmentPlanOut, status_code=201)
def create_plan(payload: InstallmentPlanCreate, db: Session = Depends(get_db), _: str = Depends(require_user)):
    if not db.get(Party, payload.party_id):
        raise HTTPException(status_code=404, detail="Partie introuvable")
    receivable = db.get(Receivable, payload.receivable_id)
    if not receivable:
        raise HTTPException(status_code=404, detail="Créance introuvable")
    if payload.mandate_id and not db.get(SepaMandate, payload.mandate_id):
        raise HTTPException(status_code=404, detail="Mandat SEPA introuvable")

    total = sum(item.amount_cents for item in payload.schedule)
    if total != receivable.amount_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Somme des échéances ({total}) ≠ montant de la créance ({receivable.amount_cents})",
        )

    plan = InstallmentPlan(
        party_id=payload.party_id,
        receivable_id=payload.receivable_id,
        mandate_id=payload.mandate_id,
        status="ACTIVE",
        total_amount_cents=total,
        currency=receivable.currency,
        number_of_installments=len(payload.schedule),
        started_at=datetime.now(timezone.utc),
        metadata_json=payload.metadata_json,
    )
    db.add(plan)
    db.flush()

    installments: List[Installment] = []
    for item in payload.schedule:
        inst = Installment(
            plan_id=plan.id,
            sequence=item.sequence,
            amount_cents=item.amount_cents,
            due_at=item.due_at,
            status="SCHEDULED",
        )
        db.add(inst)
        installments.append(inst)
    db.flush()

    ledger_service.record(
        db,
        kind="INSTALLMENT_SCHEDULED",
        amount_cents=total,
        currency=plan.currency,
        party_id=plan.party_id,
        receivable_id=plan.receivable_id,
        mandate_id=plan.mandate_id or "",
        notes=f"Plan {plan.number_of_installments} échéances",
        extra_payload={"schedule_count": plan.number_of_installments},
    )

    db.commit()
    db.refresh(plan)
    plan_out = InstallmentPlanOut.model_validate(plan)
    plan_out.installments = [InstallmentOut.model_validate(i) for i in installments]
    return plan_out


@router.get("", response_model=List[InstallmentPlanOut])
def list_plans(db: Session = Depends(get_db), _: str = Depends(require_user)):
    plans = db.execute(select(InstallmentPlan).order_by(InstallmentPlan.created_at.desc())).scalars().all()
    out: List[InstallmentPlanOut] = []
    for p in plans:
        item = InstallmentPlanOut.model_validate(p)
        item.installments = [
            InstallmentOut.model_validate(i) for i in
            db.execute(select(Installment).where(Installment.plan_id == p.id).order_by(Installment.sequence.asc())).scalars().all()
        ]
        out.append(item)
    return out


@router.get("/{plan_id}", response_model=InstallmentPlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db), _: str = Depends(require_user)):
    plan = db.get(InstallmentPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    plan_out = InstallmentPlanOut.model_validate(plan)
    plan_out.installments = [
        InstallmentOut.model_validate(i) for i in
        db.execute(select(Installment).where(Installment.plan_id == plan_id).order_by(Installment.sequence.asc())).scalars().all()
    ]
    return plan_out
