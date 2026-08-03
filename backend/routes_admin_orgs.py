"""Gestion admin des organisations : création, modification, suppression, masquage — unitaire ou en masse."""
from datetime import datetime
from typing import List, Optional
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from schema_v2 import OrgStatus, OrgResponse, OrgInDB, WalletInDB
from routes_v2 import get_current_user_v2, write_audit_log

logger = logging.getLogger(__name__)

admin_orgs_router = APIRouter(prefix="/api/v2/admin/orgs", tags=["Admin Orgs"])

db = None

VALID_STATUSES = {s.value for s in OrgStatus}


def set_admin_orgs_database(database):
    global db
    db = database


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


class AdminOrgCreate(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=255)
    registration_id: str = Field(..., min_length=9, max_length=20)
    territory: str
    member_type: str = "BUYER_PRO"
    status: str = "APPROVED"
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None


class AdminOrgUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    registration_id: Optional[str] = None
    territory: Optional[str] = None
    member_type: Optional[str] = None
    status: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None


class VisibilityPayload(BaseModel):
    hidden: bool


class BulkPayload(BaseModel):
    action: str  # hide | show | delete | suspend
    org_ids: List[str]


@admin_orgs_router.post("", response_model=OrgResponse, status_code=201)
async def admin_create_org(payload: AdminOrgCreate, admin: dict = Depends(_admin), request: Request = None):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    if await db.orgs.find_one({"registration_id": payload.registration_id}):
        raise HTTPException(status_code=400, detail="Une organisation avec ce SIRET existe déjà")
    org = OrgInDB(
        legal_name=payload.legal_name, registration_id=payload.registration_id,
        territory=payload.territory, contact_name=payload.contact_name,
        contact_email=payload.contact_email, contact_phone=payload.contact_phone,
        city=payload.city, description=payload.description, status=payload.status,
    )
    doc = org.dict()
    doc["member_type"] = payload.member_type if payload.member_type in ("BUYER_PRO", "VENDOR_PRO") else "BUYER_PRO"
    doc["created_by_admin"] = admin.get("email")
    await db.orgs.insert_one(doc)
    await db.wallets.insert_one(WalletInDB(org_id=org.id).dict())
    await write_audit_log(action="ORG_CREATED_BY_ADMIN", target_type="ORG", target_id=org.id,
                          org_id=org.id, actor_user_id=admin["id"], request=request)
    logger.info("Org créée par admin : %s (%s)", payload.legal_name, payload.registration_id)
    return OrgResponse(**{k: v for k, v in doc.items() if k != "_id"})


@admin_orgs_router.patch("/{org_id}", response_model=OrgResponse)
async def admin_update_org(org_id: str, payload: AdminOrgUpdate, admin: dict = Depends(_admin), request: Request = None):
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if updates.get("status") and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    if updates.get("registration_id") and updates["registration_id"] != org.get("registration_id"):
        if await db.orgs.find_one({"registration_id": updates["registration_id"], "id": {"$ne": org_id}}):
            raise HTTPException(status_code=400, detail="Ce SIRET est déjà utilisé par une autre organisation")
    if updates:
        updates["updated_at"] = datetime.utcnow()
        await db.orgs.update_one({"id": org_id}, {"$set": updates})
        await write_audit_log(action="ORG_UPDATED_BY_ADMIN", target_type="ORG", target_id=org_id,
                              org_id=org_id, actor_user_id=admin["id"], request=request)
    updated = await db.orgs.find_one({"id": org_id}, {"_id": 0})
    return OrgResponse(**updated)


async def _delete_org(org_id: str, admin: dict, request: Request = None) -> bool:
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        return False
    await db.orgs.delete_one({"id": org_id})
    await db.org_memberships.delete_many({"org_id": org_id})
    await db.wallets.delete_many({"org_id": org_id})
    await db.partner_accounts.delete_many({"org_id": org_id})
    await write_audit_log(action="ORG_DELETED_BY_ADMIN", target_type="ORG", target_id=org_id,
                          org_id=org_id, actor_user_id=admin["id"], request=request)
    logger.info("Org supprimée par admin : %s", org.get("legal_name"))
    return True


@admin_orgs_router.delete("/{org_id}")
async def admin_delete_org(org_id: str, admin: dict = Depends(_admin), request: Request = None):
    if not await _delete_org(org_id, admin, request):
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    return {"status": "SUCCESS"}


@admin_orgs_router.post("/{org_id}/visibility", response_model=OrgResponse)
async def admin_set_visibility(org_id: str, payload: VisibilityPayload, admin: dict = Depends(_admin), request: Request = None):
    result = await db.orgs.update_one(
        {"id": org_id}, {"$set": {"hidden": payload.hidden, "updated_at": datetime.utcnow()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    await write_audit_log(action="ORG_HIDDEN" if payload.hidden else "ORG_UNHIDDEN", target_type="ORG",
                          target_id=org_id, org_id=org_id, actor_user_id=admin["id"], request=request)
    updated = await db.orgs.find_one({"id": org_id}, {"_id": 0})
    return OrgResponse(**updated)


@admin_orgs_router.post("/bulk")
async def admin_bulk_orgs(payload: BulkPayload, admin: dict = Depends(_admin), request: Request = None):
    if payload.action not in ("hide", "show", "delete", "suspend"):
        raise HTTPException(status_code=400, detail="Action invalide (hide, show, delete, suspend)")
    if not payload.org_ids:
        raise HTTPException(status_code=400, detail="Aucune organisation sélectionnée")
    now = datetime.utcnow()
    affected = 0
    if payload.action == "delete":
        for org_id in payload.org_ids:
            if await _delete_org(org_id, admin, request):
                affected += 1
    elif payload.action == "suspend":
        r = await db.orgs.update_many(
            {"id": {"$in": payload.org_ids}},
            {"$set": {"status": OrgStatus.SUSPENDED.value, "status_reason_code": "admin_bulk", "updated_at": now}})
        affected = r.modified_count
        await write_audit_log(action="ORG_BULK_SUSPENDED", target_type="ORG", target_id=",".join(payload.org_ids),
                              org_id=None, actor_user_id=admin["id"], request=request)
    else:
        hidden = payload.action == "hide"
        r = await db.orgs.update_many(
            {"id": {"$in": payload.org_ids}}, {"$set": {"hidden": hidden, "updated_at": now}})
        affected = r.modified_count
        await write_audit_log(action="ORG_BULK_HIDDEN" if hidden else "ORG_BULK_UNHIDDEN", target_type="ORG",
                              target_id=",".join(payload.org_ids), org_id=None, actor_user_id=admin["id"], request=request)
    return {"status": "SUCCESS", "action": payload.action, "affected": affected}
