"""
KDMARCHE × O'SCOP B2B Platform - API Routes v2
Phase 1: Core (orgs, users, memberships, applications)
Phase 2: Billing (plans, subscriptions, invoices)
Phase 3: Wallet (wallets, ledger)
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from schema_v2 import (
    # Enums
    OrgStatus, ApplicationStatus, SubscriptionStatus, PartnerProvisionStatus,
    WalletStatus, LedgerStatus, LedgerDirection, CustomerRole,
    DocStatus, DocType, EntitlementSource, EntitlementStatus,
    # Phase 1 Models
    OrgCreate, OrgResponse, OrgInDB,
    UserCreate, UserResponse, UserInDB,
    OrgMembershipCreate, OrgMembershipResponse, OrgMembershipInDB,
    ApplicationCreate, ApplicationDecision, ApplicationResponse, ApplicationInDB,
    DocumentUpload, DocumentResponse, DocumentInDB,
    # Phase 2 Models
    PlanResponse, PlanInDB,
    SubscriptionCreate, SubscriptionResponse, SubscriptionInDB,
    InvoiceResponse, InvoiceInDB,
    # Phase 3 Models
    WalletResponse, WalletInDB,
    LedgerEntryCreate, LedgerEntryResponse, LedgerEntryInDB,
    # Phase 4 Models
    ZoneResponse, ZoneInDB, EntitlementResponse, EntitlementInDB,
    RuntimePreferencesInDB,
    # Phase 5 Models
    PartnerAccountResponse, PartnerAccountInDB, AuditLogEntry, OutboxEvent,
    # Defaults
    DEFAULT_ZONES, DEFAULT_PLANS,
)
from abac_policy import ABACPolicyEngine, PolicyInput, PolicySubject, PolicyResource, PolicyData

logger = logging.getLogger(__name__)

applications_v2_router = APIRouter(prefix="/api/v2")

db = None

def set_applications_v2_database(database):
    global db
    db = database

from routes_v2 import get_current_user_v2, get_user_membership, get_org_data_for_policy, write_audit_log, emit_outbox_event

# ============== PHASE 1: B2B APPLICATIONS ==============

@applications_v2_router.post("/orgs/{org_id}/applications", response_model=ApplicationResponse)
async def create_application(
    org_id: str,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Create B2B application for organization"""
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    # Check ownership
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership or membership["role"] != CustomerRole.CUSTOMER_ORG_OWNER.value:
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut créer une demande")
    
    # Check no active application exists
    existing = await db.b2b_applications.find_one({
        "org_id": org_id,
        "status": {"$in": [
            ApplicationStatus.DRAFT.value,
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.PENDING_REVIEW.value,
        ]}
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une demande est déjà en cours"
        )
    
    app = ApplicationInDB(org_id=org_id, submitted_by_user_id=current_user["id"])
    await db.b2b_applications.insert_one(app.dict())
    
    await write_audit_log(
        action="APPLICATION_CREATED",
        target_type="APPLICATION",
        target_id=app.id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        request=request,
    )
    
    return ApplicationResponse(**app.dict())


@applications_v2_router.post("/applications/{app_id}/documents", response_model=DocumentResponse)
async def upload_document(
    app_id: str,
    doc: DocumentUpload,
    current_user: dict = Depends(get_current_user_v2),
):
    """Upload document for application"""
    app = await db.b2b_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    if app["status"] not in [ApplicationStatus.DRAFT.value]:
        raise HTTPException(status_code=400, detail="La demande ne peut plus être modifiée")
    
    document = DocumentInDB(
        application_id=app_id,
        org_id=app["org_id"],
        doc_type=doc.doc_type.value,
        file_url=doc.file_url,
        checksum_sha256=doc.checksum_sha256,
    )
    await db.application_documents.insert_one(document.dict())
    
    return DocumentResponse(**document.dict())


@applications_v2_router.post("/applications/{app_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    app_id: str,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Submit application for review"""
    app = await db.b2b_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    if app["status"] != ApplicationStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="La demande n'est pas en brouillon")
    
    # Check required documents
    docs = await db.application_documents.find({"application_id": app_id}).to_list(10)
    required_types = {DocType.REGISTRATION_DOC.value, DocType.ID_SIGNATORY.value}
    uploaded_types = {d["doc_type"] for d in docs}
    
    if not required_types.issubset(uploaded_types):
        missing = required_types - uploaded_types
        raise HTTPException(
            status_code=400,
            detail=f"Documents manquants: {', '.join(missing)}"
        )
    
    # Update application status
    await db.b2b_applications.update_one(
        {"id": app_id},
        {"$set": {
            "status": ApplicationStatus.PENDING_REVIEW.value,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    # Update org status
    await db.orgs.update_one(
        {"id": app["org_id"]},
        {"$set": {
            "status": OrgStatus.PENDING_REVIEW.value,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    # Emit event
    await emit_outbox_event(
        event_type="application.submitted",
        org_id=app["org_id"],
        payload={"application_id": app_id},
    )
    
    await write_audit_log(
        action="APPLICATION_SUBMITTED",
        target_type="APPLICATION",
        target_id=app_id,
        org_id=app["org_id"],
        actor_user_id=current_user["id"],
        request=request,
    )
    
    # Create notification for admins
    notification = {
        "id": str(uuid.uuid4()),
        "type": "org_submitted",
        "title": "Nouvelle demande d'adhésion B2B",
        "message": "Une nouvelle demande d'adhésion attend validation",
        "data": {"application_id": app_id, "org_id": app["org_id"]},
        "target_roles": ["oscop_super_admin", "oscop_compliance_admin"],
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow(),
    }
    await db.notifications.insert_one(notification)
    
    updated = await db.b2b_applications.find_one({"id": app_id})
    return ApplicationResponse(**updated)


@applications_v2_router.post("/applications/{app_id}/decision", response_model=ApplicationResponse)
async def decide_application(
    app_id: str,
    decision: ApplicationDecision,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Approve or reject application (compliance admin)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    
    app = await db.b2b_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    if app["status"] != ApplicationStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=400, detail="La demande n'est pas en attente de validation")
    
    org_id = app["org_id"]
    now = datetime.utcnow()
    
    if decision.decision.upper() == "APPROVED":
        new_app_status = ApplicationStatus.APPROVED.value
        new_org_status = OrgStatus.APPROVED.value
        
        # Activate partner access
        await db.partner_accounts.update_one(
            {"org_id": org_id, "partner": "KDMARCHE"},
            {"$set": {
                "status": PartnerProvisionStatus.ACCESS_ENABLED.value,
                "updated_at": now,
            }}
        )
        
        # Add initial credits
        await db.wallets.update_one(
            {"org_id": org_id},
            {"$set": {"balance_credits": 100, "updated_at": now}}
        )
        
        # Create initial ledger entry
        ledger_entry = LedgerEntryInDB(
            org_id=org_id,
            direction=LedgerDirection.CREDIT.value,
            amount_credits=100,
            reason_code="SIGNUP_BONUS",
            correlation_id=f"signup_{org_id}",
            status=LedgerStatus.COMMITTED.value,
        )
        await db.wallet_ledger.insert_one(ledger_entry.dict())
        
        # Add default zone entitlement (territory)
        org = await db.orgs.find_one({"id": org_id})
        zone = await db.zones_v2.find_one({"code": org["territory"]})
        if zone:
            entitlement = EntitlementInDB(
                org_id=org_id,
                zone_id=zone["id"],
                source=EntitlementSource.INCLUDED.value,
            )
            await db.org_zone_entitlements.insert_one(entitlement.dict())
        
        # Enregistrement automatique au registre des membres (Acheteur pro / Vendeur pro)
        owner_ms = await db.org_memberships.find_one({"org_id": org_id, "role": CustomerRole.CUSTOMER_ORG_OWNER.value})
        owner_user = None
        if owner_ms:
            owner_user = await db.users.find_one({"id": owner_ms["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        member_type = (org or {}).get("member_type") or "BUYER_PRO"
        await db.member_registry.update_one(
            {"org_id": org_id},
            {"$set": {
                "member_type": member_type,
                "legal_name": (org or {}).get("legal_name"),
                "siret": (org or {}).get("registration_id"),
                "territory": (org or {}).get("territory"),
                "contact_name": (owner_user or {}).get("contact_name"),
                "contact_email": (owner_user or {}).get("email"),
                "contact_phone": (owner_user or {}).get("phone"),
                "application_id": app_id,
                "registered_at": now,
                "status": "ACTIVE",
            }, "$setOnInsert": {"id": str(uuid.uuid4())}},
            upsert=True,
        )
        logger.info("Member registry: %s enregistré comme %s", (org or {}).get("legal_name"), member_type)
        
        # Emit approval event
        await emit_outbox_event(
            event_type="org.approved",
            org_id=org_id,
            payload={"application_id": app_id},
        )
        
    else:
        new_app_status = ApplicationStatus.REJECTED.value
        new_org_status = OrgStatus.REJECTED.value
        
        await emit_outbox_event(
            event_type="org.rejected",
            org_id=org_id,
            payload={
                "application_id": app_id,
                "reason_code": decision.reason_code,
            },
        )
    
    # Update application
    await db.b2b_applications.update_one(
        {"id": app_id},
        {"$set": {
            "status": new_app_status,
            "reviewed_by_user_id": current_user["id"],
            "decision_at": now,
            "decision_reason_code": decision.reason_code,
            "decision_comment": decision.comment,
            "updated_at": now,
        }}
    )
    
    # Update org
    await db.orgs.update_one(
        {"id": org_id},
        {"$set": {
            "status": new_org_status,
            "status_reason_code": decision.reason_code,
            "status_comment": decision.comment,
            "updated_at": now,
        }}
    )
    
    await write_audit_log(
        action=f"APPLICATION_{decision.decision.upper()}",
        target_type="APPLICATION",
        target_id=app_id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        reason_code=decision.reason_code,
        comment=decision.comment,
        request=request,
    )
    
    updated = await db.b2b_applications.find_one({"id": app_id})
    return ApplicationResponse(**updated)


