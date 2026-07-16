"""Core zones + organizations routes (split from server.py)."""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from models import (
    UserRole, OrgStatus, SubscriptionStatus, KdmAccessStatus,
    Zone, ZoneEntitlement,
    OrganizationCreate, OrganizationResponse, OrganizationInDB, OrgDecision,
    NotificationType,
)
from db import get_database
from core_deps import get_current_user, check_admin, create_notification

logger = logging.getLogger(__name__)

orgs_core_router = APIRouter(prefix="/api")


# ============== ZONES ROUTES ==============

DEFAULT_ZONES = [
    {"code": "971", "name": "Guadeloupe", "country": "FR"},
    {"code": "972", "name": "Martinique", "country": "FR"},
    {"code": "973", "name": "Guyane", "country": "FR"},
    {"code": "974", "name": "La Réunion", "country": "FR"},
    {"code": "976", "name": "Mayotte", "country": "FR"},
    {"code": "75", "name": "Île-de-France", "country": "FR"},
]


@orgs_core_router.get("/zones", response_model=List[Zone])
async def get_zones():
    """Get all available zones."""
    db = get_database()
    zones = await db.zones.find({"is_active": True}).to_list(100)

    # Initialize zones if empty
    if not zones:
        for z in DEFAULT_ZONES:
            zone_doc = {
                "id": str(uuid.uuid4()),
                "code": z["code"],
                "name": z["name"],
                "country": z["country"],
                "is_active": True,
                "created_at": datetime.utcnow()
            }
            await db.zones.insert_one(zone_doc)
        zones = await db.zones.find({"is_active": True}).to_list(100)

    return [Zone(**z) for z in zones]


@orgs_core_router.post("/zones", response_model=Zone)
async def create_zone(
    zone: Zone,
    current_user: dict = Depends(get_current_user)
):
    """Create a new zone (admin only)."""
    await check_admin(current_user)
    db = get_database()

    zone_doc = zone.dict()
    zone_doc["id"] = str(uuid.uuid4())
    zone_doc["created_at"] = datetime.utcnow()

    await db.zones.insert_one(zone_doc)
    return Zone(**zone_doc)


# ============== ORGANIZATIONS ROUTES ==============

@orgs_core_router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate, current_user: dict = Depends(get_current_user)):
    """Create a new organization (B2B application)."""
    db = get_database()

    existing = await db.organizations.find_one({"siret": org.siret})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une organisation avec ce SIRET existe déjà"
        )

    org_doc = OrganizationInDB(
        legal_name=org.legal_name,
        siret=org.siret,
        contact_email=org.contact_email,
        contact_name=org.contact_name,
        contact_phone=org.contact_phone,
        territory=org.territory,
        address=org.address,
        owner_user_id=current_user["id"],
        documents=org.documents or []
    ).dict()

    await db.organizations.insert_one(org_doc)

    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"org_id": org_doc["id"], "role": UserRole.CUSTOMER_ORG_OWNER.value}}
    )

    logger.info(f"Organization created: {org.legal_name} (SIRET: {org.siret})")

    return OrganizationResponse(**org_doc)


@orgs_core_router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get organization details."""
    db = get_database()
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return OrganizationResponse(**org)


@orgs_core_router.post("/organizations/{org_id}/submit", response_model=dict)
async def submit_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    """Submit organization for review."""
    db = get_database()
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if org.get("owner_user_id") != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    if org["status"] != OrgStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="L'organisation n'est pas en brouillon")

    # Transition: DRAFT → SUBMITTED → PENDING_REVIEW
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {"status": OrgStatus.PENDING_REVIEW.value, "updated_at": datetime.utcnow()}}
    )

    await create_notification(
        notification_type=NotificationType.ORG_SUBMITTED.value,
        title="Nouvelle demande d'adhésion",
        message=f"{org['legal_name']} a soumis une demande d'adhésion B2B",
        target_roles=["oscop_super_admin", "oscop_compliance_admin"],
        data={"org_id": org_id, "legal_name": org["legal_name"], "siret": org["siret"]}
    )

    logger.info(f"Organization submitted for review: {org['legal_name']}")

    return {"message": "Dossier soumis pour validation", "status": OrgStatus.PENDING_REVIEW.value}


@orgs_core_router.post("/organizations/{org_id}/decision", response_model=dict)
async def decide_organization(
    org_id: str,
    decision: OrgDecision,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject organization (compliance admin only)."""
    await check_admin(current_user)
    db = get_database()

    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if org["status"] != OrgStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=400, detail="L'organisation n'est pas en attente de validation")

    if decision.decision == "approve":
        new_status = OrgStatus.APPROVED.value
        notification_type = NotificationType.ORG_APPROVED.value
        notification_title = "Demande approuvée"
        notification_message = f"Votre demande d'adhésion pour {org['legal_name']} a été approuvée !"

        # Enable KDM access and activate subscription
        await db.organizations.update_one(
            {"id": org_id},
            {"$set": {
                "status": new_status,
                "subscription_status": SubscriptionStatus.ACTIVE.value,
                "kdm_access_status": KdmAccessStatus.ACCESS_ENABLED.value,
                "credits": 100,  # Initial credits
                "updated_at": datetime.utcnow()
            }}
        )

        # Add default zone entitlement
        zone = await db.zones.find_one({"code": org["territory"]})
        if zone:
            await db.organizations.update_one(
                {"id": org_id},
                {"$push": {"zone_entitlements": {
                    "zone_id": zone["id"],
                    "zone_code": zone["code"],
                    "zone_name": zone["name"],
                    "included_in_plan": True,
                    "is_addon": False,
                    "activated_at": datetime.utcnow().isoformat()
                }}}
            )
    else:
        new_status = OrgStatus.REJECTED.value
        notification_type = NotificationType.ORG_REJECTED.value
        notification_title = "Demande refusée"
        notification_message = f"Votre demande d'adhésion pour {org['legal_name']} a été refusée. Raison: {decision.comment or decision.reason_code}"

        await db.organizations.update_one(
            {"id": org_id},
            {"$set": {
                "status": new_status,
                "rejection_reason": decision.comment or decision.reason_code,
                "updated_at": datetime.utcnow()
            }}
        )

    # Notify organization owner
    await create_notification(
        notification_type=notification_type,
        title=notification_title,
        message=notification_message,
        target_user_id=org.get("owner_user_id"),
        data={"org_id": org_id, "decision": decision.decision}
    )

    logger.info(f"Organization {decision.decision}d: {org['legal_name']} by {current_user['email']}")

    return {
        "message": f"Organisation {'approuvée' if decision.decision == 'approve' else 'refusée'}",
        "status": new_status
    }


@orgs_core_router.post("/organizations/{org_id}/suspend", response_model=dict)
async def suspend_organization(
    org_id: str,
    reason: str = "compliance",
    current_user: dict = Depends(get_current_user)
):
    """Suspend an organization (admin only)."""
    await check_admin(current_user)
    db = get_database()

    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if org["status"] not in [OrgStatus.APPROVED.value]:
        raise HTTPException(status_code=400, detail="Impossible de suspendre cette organisation")

    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {
            "status": OrgStatus.SUSPENDED.value,
            "kdm_access_status": KdmAccessStatus.ACCESS_DISABLED.value,
            "updated_at": datetime.utcnow()
        }}
    )

    await create_notification(
        notification_type="org_suspended",
        title="Compte suspendu",
        message=f"Le compte {org['legal_name']} a été suspendu. Raison: {reason}",
        target_user_id=org.get("owner_user_id"),
        data={"org_id": org_id, "reason": reason}
    )

    return {"message": "Organisation suspendue", "status": OrgStatus.SUSPENDED.value}


@orgs_core_router.get("/organizations/{org_id}/zones", response_model=List[ZoneEntitlement])
async def get_org_zones(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get zones for organization."""
    db = get_database()
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return [ZoneEntitlement(**z) for z in org.get("zone_entitlements", [])]


@orgs_core_router.post("/organizations/{org_id}/zones", response_model=dict)
async def add_org_zone(
    org_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Add a zone to organization (as addon)."""
    db = get_database()
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")

    existing = [z for z in org.get("zone_entitlements", []) if z.get("zone_id") == zone_id]
    if existing:
        raise HTTPException(status_code=400, detail="Zone déjà ajoutée")

    entitlement = {
        "zone_id": zone["id"],
        "zone_code": zone["code"],
        "zone_name": zone["name"],
        "included_in_plan": False,
        "is_addon": True,
        "activated_at": datetime.utcnow().isoformat()
    }

    await db.organizations.update_one(
        {"id": org_id},
        {"$push": {"zone_entitlements": entitlement}}
    )

    return {"message": f"Zone {zone['name']} ajoutée", "zone": entitlement}


@orgs_core_router.post("/organizations/{org_id}/select-zone", response_model=dict)
async def select_zone(
    org_id: str,
    zone_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Select active zone for organization."""
    db = get_database()
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    entitled_zones = [z.get("zone_code") for z in org.get("zone_entitlements", [])]
    if zone_code not in entitled_zones:
        raise HTTPException(status_code=403, detail="Zone non autorisée pour cette organisation")

    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {"selected_zone": zone_code, "updated_at": datetime.utcnow()}}
    )

    return {"message": f"Zone {zone_code} sélectionnée", "selected_zone": zone_code}
