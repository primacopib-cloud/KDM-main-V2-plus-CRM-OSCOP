"""Demandes de partenariat (formulaire public partagé) + gestion COOPER'S & conventions."""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

import brevo_service
from brevo_service import _wrap_html
from auth import get_current_user_id
from admin_guard import require_admin

logger = logging.getLogger(__name__)

partnership_router = APIRouter(prefix="/api/partnership", tags=["Partenariats"])

db = None


def set_partnership_database(database) -> None:
    global db
    db = database


PARTNER_TYPES = {
    "LOGISCOP": "Transporteur LOGI'SCOP",
    "COOPER": "COOPER (coopérateur opérationnel)",
    "FOURNISSEUR": "Fournisseur / Producteur",
    "RELAIS": "Relais LOLODRIVE",
    "AUTRE": "Autre partenariat",
}

CONVENTION_STATUSES = {"RECUE", "EN_NEGOCIATION", "SIGNEE", "RESILIEE", "REFUSEE"}


class PartnershipRequest(BaseModel):
    structure_name: str = Field(..., min_length=2, max_length=200)
    siret: Optional[str] = Field(None, max_length=20)
    partner_type: str = Field(default="AUTRE")
    territory: str = Field(..., min_length=2, max_length=50)
    contact_name: str = Field(..., min_length=2, max_length=120)
    contact_email: str = Field(..., min_length=5, max_length=200)
    contact_phone: Optional[str] = Field(None, max_length=30)
    message: str = Field(..., min_length=10, max_length=5000)


@partnership_router.post("/request")
async def submit_partnership_request(form: PartnershipRequest):
    if "@" not in form.contact_email:
        raise HTTPException(status_code=422, detail="Email invalide")
    partner_type = form.partner_type if form.partner_type in PARTNER_TYPES else "AUTRE"
    ref = f"PART-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    doc = {
        "id": str(uuid.uuid4()),
        "reference": ref,
        "structure_name": form.structure_name.strip(),
        "siret": (form.siret or "").strip() or None,
        "partner_type": partner_type,
        "territory": form.territory.strip(),
        "contact_name": form.contact_name.strip(),
        "contact_email": form.contact_email.strip().lower(),
        "contact_phone": form.contact_phone,
        "message": form.message.strip(),
        "status": "RECUE",
        "history": [{"action": "RECUE", "by": "public-form", "at": datetime.utcnow(), "note": None}],
        "created_at": datetime.utcnow(),
    }
    await db.partnership_requests.insert_one(doc)

    support_email = os.environ.get("SUPPORT_CONTACT_EMAIL", "contact@centrale-ess.fr")
    body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Nouvelle demande de partenariat — {ref}</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        <strong>Structure :</strong> {doc['structure_name']} {f"(SIRET {doc['siret']})" if doc['siret'] else ''}<br/>
        <strong>Type :</strong> {PARTNER_TYPES[partner_type]}<br/>
        <strong>Territoire :</strong> {doc['territory']}<br/>
        <strong>Contact :</strong> {doc['contact_name']} &lt;{doc['contact_email']}&gt; {doc['contact_phone'] or ''}
      </p>
      <div style=\"background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;color:rgba(255,255,255,0.85);font-size:14px;\">{doc['message'].replace(chr(10), '<br/>')}</div>
    """
    try:
        await brevo_service.send_email(
            to_email=support_email, to_name="Partenariats Communityplace",
            subject=f"[Partenariat {ref}] {doc['structure_name']} — {PARTNER_TYPES[partner_type]}",
            html_content=_wrap_html("Demande de partenariat", body),
            tags=["partnership-request"],
        )
    except Exception as e:
        logger.error("Brevo partnership email failed: %s", e)

    return {"ok": True, "reference": ref}


# ============== ADMIN — CONVENTIONS & COOPER'S ==============

class ConventionStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = Field(None, max_length=2000)


@partnership_router.get("/admin/requests")
async def list_partnership_requests(
    status_filter: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    await require_admin(user_id)
    query = {}
    if status_filter in CONVENTION_STATUSES:
        query["status"] = status_filter
    requests = await db.partnership_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)
    counts = {s: await db.partnership_requests.count_documents({"status": s}) for s in CONVENTION_STATUSES}
    return {"requests": requests, "counts": counts}


@partnership_router.patch("/admin/requests/{request_id}/status")
async def update_convention_status(
    request_id: str,
    update: ConventionStatusUpdate,
    user_id: str = Depends(get_current_user_id),
):
    admin = await require_admin(user_id)
    if update.status not in CONVENTION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs: {', '.join(sorted(CONVENTION_STATUSES))}")
    entry = {
        "action": update.status,
        "by": admin.get("email"),
        "at": datetime.utcnow(),
        "note": (update.note or "").strip() or None,
    }
    res = await db.partnership_requests.update_one(
        {"id": request_id},
        {"$set": {"status": update.status, "updated_at": datetime.utcnow()}, "$push": {"history": entry}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return {"ok": True, "status": update.status}


@partnership_router.get("/admin/coopers")
async def list_coopers(user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    coopers = await db.users.find(
        {"role": "COOPER"},
        {"_id": 0, "id": 1, "email": 1, "contact_name": 1, "company_name": 1, "role_granted_at": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(200)
    return {"coopers": coopers, "count": len(coopers)}
