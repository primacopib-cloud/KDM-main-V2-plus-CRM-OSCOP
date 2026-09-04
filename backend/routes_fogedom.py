"""FOGEDOM-SCIC : registre des décisions d'appui — jamais garant, assureur ou prêteur."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2

fogedom_router = APIRouter(prefix="/api/admin/fogedom", tags=["FOGEDOM-SCIC"])
db = None


def set_fogedom_database(database):
    global db
    db = database


DISCLAIMER = ("FOGEDOM-SCIC est un fonds interne analytique d'appui et de prévention. Son intervention est "
              "facultative, individualisée et limitée aux ressources disponibles. Elle ne constitue ni une "
              "garantie automatique, ni une assurance, ni un engagement de remboursement de l'investisseur.")

PURPOSES = ["EXPERTISE", "CONTROLE_QUALITE", "MESURE_LOGISTIQUE_CORRECTIVE", "STOCKAGE_EXCEPTIONNEL",
            "PREVENTION", "RECONDITIONNEMENT", "CONTINUITE_OPERATION"]

FORBIDDEN_TERMS = ["capital garanti", "garantie automatique", "assurance fogedom", "remboursement automatique",
                   "couverture systématique", "garanti par fogedom"]


class DecisionCreate(BaseModel):
    operation_id: str
    requested_amount: float = Field(gt=0)
    purpose: str
    description: Optional[str] = None
    decision_body: str = "Organe de décision FOGEDOM-SCIC"


class DecisionUpdate(BaseModel):
    status: str
    approved_amount: Optional[float] = Field(default=None, ge=0)
    available_resources_checked: bool = False
    comment: Optional[str] = None


def _check_forbidden(text: str):
    low = (text or "").lower()
    for term in FORBIDDEN_TERMS:
        if term in low:
            raise HTTPException(status_code=409,
                                detail=f"Formulation interdite (« {term} ») : FOGEDOM-SCIC n'est ni garant, ni assureur, ni un remboursement automatique")


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@fogedom_router.get("/decisions")
async def list_decisions(admin: dict = Depends(_admin)):
    decisions = await db.fogedom_decisions.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"decisions": decisions, "purposes": PURPOSES, "disclaimer": DISCLAIMER}


@fogedom_router.post("/decisions")
async def create_decision(payload: DecisionCreate, admin: dict = Depends(_admin)):
    if payload.purpose not in PURPOSES:
        raise HTTPException(status_code=400, detail=f"Objet invalide. Autorisés : {PURPOSES}")
    _check_forbidden(payload.description)
    op = await db.purchase_resale_operations.find_one({"id": payload.operation_id}, {"_id": 0, "reference": 1})
    if not op:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    dec = {"id": str(uuid.uuid4()), **payload.dict(),
           "operation_reference": op["reference"],
           "approved_amount": None, "status": "PENDING",
           "available_resources_checked": False,
           "decision_date": None, "supporting_documents": [],
           "disclaimer": DISCLAIMER,
           "created_by": admin.get("email"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.fogedom_decisions.insert_one(dict(dec))
    return dec


@fogedom_router.patch("/decisions/{decision_id}")
async def decide(decision_id: str, payload: DecisionUpdate, admin: dict = Depends(_admin)):
    if payload.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Statut : APPROVED ou REJECTED")
    _check_forbidden(payload.comment)
    dec = await db.fogedom_decisions.find_one({"id": decision_id}, {"_id": 0})
    if not dec:
        raise HTTPException(status_code=404, detail="Décision introuvable")
    if payload.status == "APPROVED":
        if not payload.available_resources_checked:
            raise HTTPException(status_code=409, detail="La vérification des ressources disponibles est obligatoire avant approbation")
        if not payload.approved_amount or payload.approved_amount <= 0:
            raise HTTPException(status_code=400, detail="Montant approuvé requis")
        if payload.approved_amount > dec["requested_amount"]:
            raise HTTPException(status_code=409, detail="Le montant approuvé ne peut dépasser le montant demandé")
    now = datetime.now(timezone.utc).isoformat()
    await db.fogedom_decisions.update_one(
        {"id": decision_id},
        {"$set": {"status": payload.status, "approved_amount": payload.approved_amount,
                  "available_resources_checked": payload.available_resources_checked,
                  "comment": payload.comment, "decision_date": now, "decided_by": admin.get("email")}})
    if payload.status == "APPROVED":
        await db.purchase_resale_operations.update_one(
            {"id": dec["operation_id"]}, {"$inc": {"fogedom_support_amount": payload.approved_amount}})
    return {"success": True, "status": payload.status, "disclaimer": DISCLAIMER}
