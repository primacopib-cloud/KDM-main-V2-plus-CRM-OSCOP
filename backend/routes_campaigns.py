"""Campagnes multi-lots : regroupement de consultations sous un calendrier commun."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

campaigns_router = APIRouter(prefix="/api/admin/campaigns", tags=["campaigns"])

db = None

PRE_PUBLICATION = ["BROUILLON", "EN_VALIDATION", "VALIDEE"]


def set_campaigns_database(database):
    global db
    db = database


class CampaignBody(BaseModel):
    name: str
    opens_at: str
    closes_at: str


class AttachBody(BaseModel):
    consultation_id: str


@campaigns_router.get("")
async def list_campaigns(admin: dict = Depends(require_admin)):
    campaigns = await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for camp in campaigns:
        camp["lots"] = await db.consultations.find(
            {"campaign_id": camp["id"]},
            {"_id": 0, "id": 1, "ref": 1, "title": 1, "status": 1, "opens_at": 1, "closes_at": 1}).to_list(100)
    return {"items": campaigns}


@campaigns_router.post("")
async def create_campaign(body: CampaignBody, admin: dict = Depends(require_admin)):
    if not body.name.strip() or body.closes_at <= body.opens_at:
        raise HTTPException(status_code=400, detail="Nom requis et clôture postérieure à l'ouverture")
    doc = {"id": str(uuid.uuid4()), "name": body.name.strip(),
           "opens_at": body.opens_at, "closes_at": body.closes_at,
           "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.campaigns.insert_one({**doc})
    await audit("CAMPAIGN_CREATED", admin.get("email"), None, {"campaign_id": doc["id"], "name": doc["name"]})
    return doc


@campaigns_router.put("/{camp_id}")
async def update_campaign(camp_id: str, body: CampaignBody, admin: dict = Depends(require_admin)):
    if body.closes_at <= body.opens_at:
        raise HTTPException(status_code=400, detail="Clôture postérieure à l'ouverture requise")
    res = await db.campaigns.update_one({"id": camp_id}, {"$set": {
        "name": body.name.strip(), "opens_at": body.opens_at, "closes_at": body.closes_at,
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return {"ok": True}


@campaigns_router.post("/{camp_id}/attach")
async def attach_lot(camp_id: str, body: AttachBody, admin: dict = Depends(require_admin)):
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    c = await db.consultations.find_one({"id": body.consultation_id}, {"_id": 0, "id": 1, "ref": 1, "status": 1})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    if c["status"] not in PRE_PUBLICATION:
        raise HTTPException(status_code=409, detail="Seuls les lots non publiés peuvent rejoindre une campagne")
    await db.consultations.update_one({"id": c["id"]}, {"$set": {
        "campaign_id": camp_id, "opens_at": camp["opens_at"], "closes_at": camp["closes_at"],
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit("CAMPAIGN_LOT_ATTACHED", admin.get("email"), c["id"],
                {"campaign_id": camp_id, "ref": c["ref"], "calendar_applied": True})
    return {"ok": True, "message": f"{c['ref']} rattaché — calendrier de campagne appliqué"}


@campaigns_router.post("/{camp_id}/detach")
async def detach_lot(camp_id: str, body: AttachBody, admin: dict = Depends(require_admin)):
    res = await db.consultations.update_one(
        {"id": body.consultation_id, "campaign_id": camp_id}, {"$unset": {"campaign_id": ""}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lot non rattaché à cette campagne")
    await audit("CAMPAIGN_LOT_DETACHED", admin.get("email"), body.consultation_id, {"campaign_id": camp_id})
    return {"ok": True}


@campaigns_router.post("/{camp_id}/apply-calendar")
async def apply_calendar(camp_id: str, admin: dict = Depends(require_admin)):
    """Ré-applique le calendrier de la campagne à tous ses lots non publiés."""
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    res = await db.consultations.update_many(
        {"campaign_id": camp_id, "status": {"$in": PRE_PUBLICATION}},
        {"$set": {"opens_at": camp["opens_at"], "closes_at": camp["closes_at"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit("CAMPAIGN_CALENDAR_APPLIED", admin.get("email"), None,
                {"campaign_id": camp_id, "lots_updated": res.modified_count})
    return {"ok": True, "lots_updated": res.modified_count}


@campaigns_router.delete("/{camp_id}")
async def delete_campaign(camp_id: str, admin: dict = Depends(require_admin)):
    await db.consultations.update_many({"campaign_id": camp_id}, {"$unset": {"campaign_id": ""}})
    res = await db.campaigns.delete_one({"id": camp_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    await audit("CAMPAIGN_DELETED", admin.get("email"), None, {"campaign_id": camp_id})
    return {"ok": True}
