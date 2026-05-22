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

# Router with /api/v2 prefix
api_v2_router = APIRouter(prefix="/api/v2")


# ============== DEPENDENCY INJECTION ==============

# This will be set by server.py
db = None

def set_database(database):
    """Set database reference from main server"""
    global db
    db = database


async def get_current_user_v2(request: Request):
    """Get current authenticated user with v2 schema"""
    from auth import decode_token
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = auth_header.split(" ")[1]
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    # Try v2 users collection first
    user = await db.users_v2.find_one({"id": user_id})
    if not user:
        # Fallback to legacy users collection
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


async def get_user_membership(user_id: str, org_id: str = None):
    """Get user's membership and role"""
    query = {"user_id": user_id}
    if org_id:
        query["org_id"] = org_id
    
    membership = await db.org_memberships.find_one(query)
    return membership


async def get_org_data_for_policy(org_id: str) -> PolicyData:
    """Load all org data needed for policy evaluation"""
    org = await db.orgs.find_one({"id": org_id})
    subscription = await db.subscriptions.find_one({"org_id": org_id, "status": {"$nin": ["CANCELED"]}})
    partner = await db.partner_accounts.find_one({"org_id": org_id, "partner": "KDMARCHE"})
    wallet = await db.wallets.find_one({"org_id": org_id})
    
    # Get entitled zones
    entitlements = await db.org_zone_entitlements.find(
        {"org_id": org_id, "status": EntitlementStatus.ACTIVE.value}
    ).to_list(100)
    entitled_zone_ids = [e["zone_id"] for e in entitlements]
    
    return PolicyData(
        org=org,
        subscription=subscription,
        partner_account=partner,
        wallet=wallet,
        entitlements=entitled_zone_ids,
    )


async def write_audit_log(
    action: str,
    target_type: str,
    target_id: str = None,
    org_id: str = None,
    actor_user_id: str = None,
    actor_role: str = None,
    reason_code: str = None,
    comment: str = None,
    meta: dict = None,
    request: Request = None,
):
    """Write to audit log (append-only)"""
    entry = AuditLogEntry(
        org_id=org_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason_code=reason_code,
        comment=comment,
        ip=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
        meta=meta,
    )
    await db.audit_log.insert_one(entry.dict())
    return entry


async def emit_outbox_event(event_type: str, org_id: str = None, payload: dict = None):
    """Emit event to outbox for reliable delivery"""
    event = OutboxEvent(
        org_id=org_id,
        event_type=event_type,
        payload=payload or {},
    )
    await db.outbox_events.insert_one(event.dict())
    return event


# ============== USER PROFILE ==============

@api_v2_router.get("/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user_v2),
):
    """Get current user profile with organization info"""
    user_id = current_user["id"]
    
    # Get user's membership to find org_id
    membership = await db.org_memberships.find_one({"user_id": user_id})
    
    # Build response
    response = {
        "id": user_id,
        "email": current_user.get("email"),
        "company_name": current_user.get("company_name"),
        "contact_name": current_user.get("contact_name"),
        "phone": current_user.get("phone"),
        "is_admin": current_user.get("is_admin", False),
        "organization_id": membership["org_id"] if membership else None,
        "role": membership["role"] if membership else None,
    }
    
    # If org_id exists, load wallet info
    if membership:
        org_id = membership["org_id"]
        wallet = await db.wallets.find_one({"org_id": org_id})
        if wallet:
            response["wallet"] = {
                "balance_cents": wallet.get("balance_cents", 0),
                "balance_credits": wallet.get("balance_credits", 0),
                "status": wallet.get("status", "ACTIVE"),
            }
        
        # Load org info
        org = await db.orgs.find_one({"id": org_id})
        if org:
            response["organization"] = {
                "id": org["id"],
                "legal_name": org.get("legal_name"),
                "territory": org.get("territory"),
                "status": org.get("status"),
            }
    
    return response


# ============== PHASE 1: ORGANIZATIONS ==============

@api_v2_router.post("/orgs", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    org_data: OrgCreate,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Create a new organization (B2B entity)"""
    # Check if org with same registration_id exists
    existing = await db.orgs.find_one({
        "registration_country": org_data.registration_country,
        "registration_id": org_data.registration_id,
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une organisation avec ce SIRET existe déjà"
        )
    
    # Create org
    org = OrgInDB(
        legal_name=org_data.legal_name,
        registration_country=org_data.registration_country,
        registration_id=org_data.registration_id,
        territory=org_data.territory,
    )
    await db.orgs.insert_one(org.dict())
    
    # Create membership for creator as OWNER
    membership = OrgMembershipInDB(
        org_id=org.id,
        user_id=current_user["id"],
        role=CustomerRole.CUSTOMER_ORG_OWNER.value,
    )
    await db.org_memberships.insert_one(membership.dict())
    
    # Create wallet
    wallet = WalletInDB(org_id=org.id)
    await db.wallets.insert_one(wallet.dict())
    
    # Create partner account placeholder
    partner = PartnerAccountInDB(org_id=org.id)
    await db.partner_accounts.insert_one(partner.dict())
    
    # Audit
    await write_audit_log(
        action="ORG_CREATED",
        target_type="ORG",
        target_id=org.id,
        org_id=org.id,
        actor_user_id=current_user["id"],
        request=request,
    )
    
    logger.info(f"Organization created: {org.legal_name} ({org.registration_id})")
    
    return OrgResponse(**org.dict())


@api_v2_router.get("/orgs/{org_id}", response_model=OrgResponse)
async def get_org(org_id: str, current_user: dict = Depends(get_current_user_v2)):
    """Get organization details"""
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    # Check access
    membership = await get_user_membership(current_user["id"], org_id)
    is_admin = current_user.get("is_admin", False)
    
    if not membership and not is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return OrgResponse(**org)


@api_v2_router.get("/orgs", response_model=List[OrgResponse])
async def list_user_orgs(current_user: dict = Depends(get_current_user_v2)):
    """List organizations for current user"""
    memberships = await db.org_memberships.find(
        {"user_id": current_user["id"]}
    ).to_list(100)
    
    org_ids = [m["org_id"] for m in memberships]
    orgs = await db.orgs.find({"id": {"$in": org_ids}}).to_list(100)
    
    return [OrgResponse(**o) for o in orgs]


# ============== PHASE 1: B2B APPLICATIONS ==============

@api_v2_router.post("/orgs/{org_id}/applications", response_model=ApplicationResponse)
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


@api_v2_router.post("/applications/{app_id}/documents", response_model=DocumentResponse)
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


@api_v2_router.post("/applications/{app_id}/submit", response_model=ApplicationResponse)
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
        "message": f"Une nouvelle demande d'adhésion attend validation",
        "data": {"application_id": app_id, "org_id": app["org_id"]},
        "target_roles": ["oscop_super_admin", "oscop_compliance_admin"],
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow(),
    }
    await db.notifications.insert_one(notification)
    
    updated = await db.b2b_applications.find_one({"id": app_id})
    return ApplicationResponse(**updated)


@api_v2_router.post("/applications/{app_id}/decision", response_model=ApplicationResponse)
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


# ============== PHASE 2: PLANS & SUBSCRIPTIONS ==============

@api_v2_router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """List available subscription plans"""
    plans = await db.plans.find({"is_active": True}).to_list(10)
    
    # Initialize if empty
    if not plans:
        for p in DEFAULT_PLANS:
            plan = PlanInDB(**p)
            await db.plans.insert_one(plan.dict())
        plans = await db.plans.find({"is_active": True}).to_list(10)
    
    return [PlanResponse(**p) for p in plans]


@api_v2_router.post("/orgs/{org_id}/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    org_id: str,
    sub_data: SubscriptionCreate,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Create subscription for organization"""
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    # Check ownership
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership or membership["role"] != CustomerRole.CUSTOMER_ORG_OWNER.value:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Check no active subscription
    existing = await db.subscriptions.find_one({
        "org_id": org_id,
        "status": {"$in": [
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.PAST_DUE.value,
            SubscriptionStatus.GRACE_PERIOD.value,
        ]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="Un abonnement est déjà actif")
    
    # Validate plan
    plan = await db.plans.find_one({"id": sub_data.plan_id, "is_active": True})
    if not plan:
        raise HTTPException(status_code=400, detail="Plan invalide")
    
    now = datetime.utcnow()
    period_end = now + timedelta(days=30)
    
    subscription = SubscriptionInDB(
        org_id=org_id,
        plan_id=sub_data.plan_id,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_start=now,
        current_period_end=period_end,
    )
    await db.subscriptions.insert_one(subscription.dict())
    
    # Create invoice
    invoice = InvoiceInDB(
        org_id=org_id,
        subscription_id=subscription.id,
        invoice_type="SUBSCRIPTION",
        amount_ht_cents=plan["price_ht_cents"],
        tax_cents=int(plan["price_ht_cents"] * 0.2),  # 20% TVA
        amount_ttc_cents=int(plan["price_ht_cents"] * 1.2),
        status="ISSUED",
        issued_at=now,
    )
    await db.billing_invoices.insert_one(invoice.dict())
    
    await emit_outbox_event(
        event_type="subscription.activated",
        org_id=org_id,
        payload={"subscription_id": subscription.id, "plan_code": plan["code"]},
    )
    
    await write_audit_log(
        action="SUBSCRIPTION_CREATED",
        target_type="SUBSCRIPTION",
        target_id=subscription.id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        request=request,
    )
    
    return SubscriptionResponse(**subscription.dict())


@api_v2_router.get("/orgs/{org_id}/subscriptions", response_model=List[SubscriptionResponse])
async def get_org_subscriptions(
    org_id: str,
    current_user: dict = Depends(get_current_user_v2),
):
    """Get organization subscriptions"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    subs = await db.subscriptions.find({"org_id": org_id}).sort("created_at", -1).to_list(10)
    return [SubscriptionResponse(**s) for s in subs]


# ============== PHASE 3: WALLET ==============

@api_v2_router.get("/orgs/{org_id}/wallet", response_model=WalletResponse)
async def get_wallet(
    org_id: str,
    current_user: dict = Depends(get_current_user_v2),
):
    """Get organization wallet"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    wallet = await db.wallets.find_one({"org_id": org_id})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet non trouvé")
    
    return WalletResponse(**wallet)


@api_v2_router.post("/orgs/{org_id}/wallet/topup", response_model=LedgerEntryResponse)
async def topup_wallet(
    org_id: str,
    amount: int,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Add credits to wallet (purchase)"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide")
    
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership or membership["role"] != CustomerRole.CUSTOMER_ORG_OWNER.value:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    correlation_id = f"topup_{org_id}_{datetime.utcnow().timestamp()}"
    
    # Create ledger entry
    entry = LedgerEntryInDB(
        org_id=org_id,
        direction=LedgerDirection.CREDIT.value,
        amount_credits=amount,
        reason_code="TOPUP_PURCHASE",
        correlation_id=correlation_id,
        created_by_user_id=current_user["id"],
    )
    await db.wallet_ledger.insert_one(entry.dict())
    
    # Update balance (atomic)
    await db.wallets.update_one(
        {"org_id": org_id},
        {
            "$inc": {"balance_credits": amount},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )
    
    # Commit entry
    await db.wallet_ledger.update_one(
        {"id": entry.id},
        {"$set": {"status": LedgerStatus.COMMITTED.value}}
    )
    
    await write_audit_log(
        action="WALLET_TOPUP",
        target_type="WALLET",
        target_id=org_id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        meta={"amount": amount},
        request=request,
    )
    
    return LedgerEntryResponse(**entry.dict())


@api_v2_router.get("/orgs/{org_id}/wallet/ledger", response_model=List[LedgerEntryResponse])
async def get_ledger(
    org_id: str,
    current_user: dict = Depends(get_current_user_v2),
    limit: int = 50,
):
    """Get wallet ledger entries"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    entries = await db.wallet_ledger.find(
        {"org_id": org_id}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return [LedgerEntryResponse(**e) for e in entries]


# ============== PHASE 4: ZONES ==============

@api_v2_router.get("/zones", response_model=List[ZoneResponse])
async def list_zones():
    """List available zones"""
    zones = await db.zones_v2.find({"is_active": True}).to_list(100)
    
    # Initialize if empty
    if not zones:
        for z in DEFAULT_ZONES:
            zone = ZoneInDB(**z)
            await db.zones_v2.insert_one(zone.dict())
        zones = await db.zones_v2.find({"is_active": True}).to_list(100)
    
    return [ZoneResponse(**z) for z in zones]


@api_v2_router.get("/orgs/{org_id}/zones", response_model=List[EntitlementResponse])
async def get_org_entitlements(
    org_id: str,
    current_user: dict = Depends(get_current_user_v2),
):
    """Get organization zone entitlements"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    entitlements = await db.org_zone_entitlements.find({"org_id": org_id}).to_list(100)
    return [EntitlementResponse(**e) for e in entitlements]


@api_v2_router.post("/orgs/{org_id}/zones/{zone_id}", response_model=EntitlementResponse)
async def add_zone_entitlement(
    org_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Add zone entitlement (addon purchase)"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership or membership["role"] != CustomerRole.CUSTOMER_ORG_OWNER.value:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Check zone exists
    zone = await db.zones_v2.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    # Check not already entitled
    existing = await db.org_zone_entitlements.find_one({"org_id": org_id, "zone_id": zone_id})
    if existing:
        raise HTTPException(status_code=400, detail="Zone déjà ajoutée")
    
    entitlement = EntitlementInDB(
        org_id=org_id,
        zone_id=zone_id,
        source=EntitlementSource.OPTION.value,
    )
    await db.org_zone_entitlements.insert_one(entitlement.dict())
    
    await emit_outbox_event(
        event_type="zones.updated",
        org_id=org_id,
        payload={"zone_id": zone_id, "action": "added"},
    )
    
    await write_audit_log(
        action="ZONE_ADDED",
        target_type="ENTITLEMENT",
        target_id=entitlement.id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        meta={"zone_id": zone_id},
        request=request,
    )
    
    return EntitlementResponse(**entitlement.dict())


@api_v2_router.post("/orgs/{org_id}/select-zone", response_model=dict)
async def select_zone(
    org_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user_v2),
):
    """Select active zone for runtime"""
    membership = await get_user_membership(current_user["id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Check zone is entitled
    entitlement = await db.org_zone_entitlements.find_one({
        "org_id": org_id,
        "zone_id": zone_id,
        "status": EntitlementStatus.ACTIVE.value,
    })
    if not entitlement:
        raise HTTPException(status_code=403, detail="Zone non autorisée")
    
    # Update runtime preference
    await db.org_runtime_preferences.update_one(
        {"org_id": org_id},
        {"$set": {
            "org_id": org_id,
            "selected_zone_id": zone_id,
            "updated_at": datetime.utcnow(),
        }},
        upsert=True,
    )
    
    return {"selected_zone_id": zone_id}


# ============== ADMIN ROUTES ==============

@api_v2_router.get("/admin/applications", response_model=List[ApplicationResponse])
async def list_applications(
    current_user: dict = Depends(get_current_user_v2),
    status_filter: str = None,
    limit: int = 50,
):
    """List all applications (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    apps = await db.b2b_applications.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    return [ApplicationResponse(**a) for a in apps]


@api_v2_router.get("/admin/orgs", response_model=List[OrgResponse])
async def list_all_orgs(
    current_user: dict = Depends(get_current_user_v2),
    status_filter: str = None,
    limit: int = 100,
):
    """List all organizations (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    orgs = await db.orgs.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    return [OrgResponse(**o) for o in orgs]


@api_v2_router.post("/admin/orgs/{org_id}/suspend", response_model=OrgResponse)
async def suspend_org(
    org_id: str,
    reason: str = "compliance",
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Suspend organization (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    now = datetime.utcnow()
    
    # Suspend org
    await db.orgs.update_one(
        {"id": org_id},
        {"$set": {
            "status": OrgStatus.SUSPENDED.value,
            "status_reason_code": reason,
            "updated_at": now,
        }}
    )
    
    # Disable partner access
    await db.partner_accounts.update_one(
        {"org_id": org_id, "partner": "KDMARCHE"},
        {"$set": {
            "status": PartnerProvisionStatus.ACCESS_DISABLED.value,
            "updated_at": now,
        }}
    )
    
    await emit_outbox_event(
        event_type="org.suspended",
        org_id=org_id,
        payload={"reason": reason},
    )
    
    await write_audit_log(
        action="ORG_SUSPENDED",
        target_type="ORG",
        target_id=org_id,
        org_id=org_id,
        actor_user_id=current_user["id"],
        reason_code=reason,
        request=request,
    )
    
    updated = await db.orgs.find_one({"id": org_id})
    return OrgResponse(**updated)


@api_v2_router.get("/admin/audit-log", response_model=List[dict])
async def get_audit_log(
    current_user: dict = Depends(get_current_user_v2),
    org_id: str = None,
    action: str = None,
    limit: int = 100,
):
    """Get audit log entries (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    query = {}
    if org_id:
        query["org_id"] = org_id
    if action:
        query["action"] = action
    
    entries = await db.audit_log.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Remove MongoDB _id
    return [{k: v for k, v in e.items() if k != "_id"} for e in entries]
