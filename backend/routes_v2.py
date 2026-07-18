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
    from auth import decode_token, extract_user_id_from_request
    
    user_id = extract_user_id_from_request(request)
    
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
    org_doc = org.dict()
    org_doc["member_type"] = org_data.member_type if org_data.member_type in ("BUYER_PRO", "VENDOR_PRO") else "BUYER_PRO"
    await db.orgs.insert_one(org_doc)
    
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


