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

billing_v2_router = APIRouter(prefix="/api/v2")

db = None

def set_billing_v2_database(database):
    global db
    db = database

from routes_v2 import get_current_user_v2, get_user_membership, get_org_data_for_policy, write_audit_log, emit_outbox_event

# ============== PHASE 2: PLANS & SUBSCRIPTIONS ==============

@billing_v2_router.get("/plans", response_model=List[PlanResponse])
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


@billing_v2_router.post("/orgs/{org_id}/subscriptions", response_model=SubscriptionResponse)
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


@billing_v2_router.get("/orgs/{org_id}/subscriptions", response_model=List[SubscriptionResponse])
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

@billing_v2_router.get("/orgs/{org_id}/wallet", response_model=WalletResponse)
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


@billing_v2_router.post("/orgs/{org_id}/wallet/topup", response_model=LedgerEntryResponse)
async def topup_wallet(
    org_id: str,
    amount: int,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Add credits to wallet (purchase)"""
    raise HTTPException(
        status_code=403,
        detail="Les crédits sont payables exclusivement par carte bancaire. Utilisez « Acheter des crédits » (paiement Stripe).",
    )
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


@billing_v2_router.get("/orgs/{org_id}/wallet/ledger", response_model=List[LedgerEntryResponse])
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

@billing_v2_router.get("/zones", response_model=List[ZoneResponse])
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


@billing_v2_router.get("/orgs/{org_id}/zones", response_model=List[EntitlementResponse])
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


@billing_v2_router.post("/orgs/{org_id}/zones/{zone_id}", response_model=EntitlementResponse)
async def add_zone_entitlement(
    org_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user_v2),
    request: Request = None,
):
    """Add zone entitlement (admin uniquement — les membres passent par l'achat de zone additionnelle)"""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="L'ajout d'une zone se fait via l'achat d'une zone additionnelle (crédits ou carte).")
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


@billing_v2_router.post("/orgs/{org_id}/select-zone", response_model=dict)
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

@billing_v2_router.get("/admin/applications", response_model=List[ApplicationResponse])
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


@billing_v2_router.get("/admin/orgs", response_model=List[OrgResponse])
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


@billing_v2_router.post("/admin/orgs/{org_id}/suspend", response_model=OrgResponse)
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


@billing_v2_router.get("/admin/audit-log", response_model=List[dict])
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
