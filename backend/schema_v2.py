"""
KDMARCHE × O'SCOP B2B Platform - Core Schema (MongoDB Adaptation)
Based on PostgreSQL production schema, adapted for MongoDB with references

Phase 1: Core (orgs, users, memberships, applications)
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============== ENUMS (Production Schema) ==============

class OrgStatus(str, Enum):
    """Organization status state machine"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class ApplicationStatus(str, Enum):
    """B2B Application status"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SubscriptionStatus(str, Enum):
    """Subscription billing status"""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    CANCELED = "CANCELED"


class PartnerProvisionStatus(str, Enum):
    """KDMARCHE partner provisioning status"""
    NOT_PROVISIONED = "NOT_PROVISIONED"
    PROVISIONED = "PROVISIONED"
    ACCESS_ENABLED = "ACCESS_ENABLED"
    ACCESS_DISABLED = "ACCESS_DISABLED"
    DEPROVISIONED = "DEPROVISIONED"


class LedgerStatus(str, Enum):
    """Wallet ledger entry status"""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    CANCELED = "CANCELED"


class LedgerDirection(str, Enum):
    """Wallet ledger direction"""
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class WalletStatus(str, Enum):
    """Wallet status"""
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class DocType(str, Enum):
    """Application document types"""
    REGISTRATION_DOC = "REGISTRATION_DOC"  # KBIS, extrait RCS
    ID_SIGNATORY = "ID_SIGNATORY"          # Pièce d'identité signataire
    PROOF_ADDRESS = "PROOF_ADDRESS"        # Justificatif adresse
    OTHER = "OTHER"


class DocStatus(str, Enum):
    """Document verification status"""
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ZoneKind(str, Enum):
    """Zone type"""
    OM = "OM"        # Outre-mer
    EXPORT = "EXPORT"


class BillingPeriod(str, Enum):
    """Billing period"""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class InvoiceType(str, Enum):
    """Invoice type"""
    SUBSCRIPTION = "SUBSCRIPTION"
    CREDITS_TOPUP = "CREDITS_TOPUP"


class InvoiceStatus(str, Enum):
    """Invoice status"""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    FAILED = "FAILED"
    VOID = "VOID"


class DeliveryMode(str, Enum):
    """Delivery mode for logistics"""
    DIRECT = "DIRECT"        # Standard LOGI'SCOP delivery
    ESS_ROUTE = "ESS_ROUTE"  # Tournées Mutualisées ESS


class FulfillmentMode(str, Enum):
    """Fulfillment mode for orders"""
    EXW = "EXW"                        # Customer pickup
    LOGISCOP_DELIVERY = "LOGISCOP_DELIVERY"  # LOGI'SCOP delivery


class TourStatus(str, Enum):
    """ESS Tour status"""
    OPEN = "open"          # Accepting bookings
    FULL = "full"          # Capacity reached
    IN_PROGRESS = "in_progress"  # Currently running
    COMPLETED = "completed"       # Tour finished


class ESSBookingStatus(str, Enum):
    """ESS Route booking status"""
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"
    NO_SHOW = "no_show"


class EntitlementSource(str, Enum):
    """Zone entitlement source"""
    INCLUDED = "INCLUDED"  # Included in plan
    OPTION = "OPTION"      # Purchased addon


class EntitlementStatus(str, Enum):
    """Zone entitlement status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ============== RBAC ROLES ==============

class OscopRole(str, Enum):
    """O'SCOP internal roles"""
    OSCOP_SUPER_ADMIN = "OSCOP_SUPER_ADMIN"
    OSCOP_COMPLIANCE_ADMIN = "OSCOP_COMPLIANCE_ADMIN"
    OSCOP_BILLING_ADMIN = "OSCOP_BILLING_ADMIN"
    OSCOP_SUPPORT_AGENT = "OSCOP_SUPPORT_AGENT"


class KdmRole(str, Enum):
    """KDMARCHE roles"""
    KDM_B2B_ADMIN = "KDM_B2B_ADMIN"
    KDM_B2B_SALES = "KDM_B2B_SALES"
    KDM_WAREHOUSE = "KDM_WAREHOUSE"
    KDM_FINANCE = "KDM_FINANCE"


class CustomerRole(str, Enum):
    """Customer organization roles"""
    CUSTOMER_ORG_OWNER = "CUSTOMER_ORG_OWNER"
    CUSTOMER_ORG_BUYER = "CUSTOMER_ORG_BUYER"
    CUSTOMER_ORG_VIEWER = "CUSTOMER_ORG_VIEWER"


# ============== PHASE 1: CORE MODELS ==============

# --- Organizations ---

class OrgCreate(BaseModel):
    """Create organization request"""
    legal_name: str = Field(..., min_length=2, max_length=255)
    registration_country: str = Field(default="FR", max_length=2)
    registration_id: str = Field(..., min_length=9, max_length=20)  # SIRET
    territory: str = Field(...)  # Primary zone code
    contact_email: EmailStr
    contact_name: str
    contact_phone: str
    address: Optional[str] = None


class OrgResponse(BaseModel):
    """Organization response"""
    id: str
    legal_name: str
    registration_country: str
    registration_id: str
    territory: str
    status: str
    status_reason_code: Optional[str] = None
    status_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgInDB(BaseModel):
    """Organization in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    legal_name: str
    registration_country: str = "FR"
    registration_id: str  # SIRET/SIREN
    territory: str
    status: str = OrgStatus.DRAFT.value
    status_reason_code: Optional[str] = None
    status_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Users (IAM simplified) ---

class UserCreate(BaseModel):
    """Create user request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(BaseModel):
    """User in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Organization Memberships (RBAC) ---

class OrgMembershipCreate(BaseModel):
    """Add user to organization"""
    user_id: str
    role: CustomerRole = CustomerRole.CUSTOMER_ORG_BUYER


class OrgMembershipResponse(BaseModel):
    """Membership response"""
    id: str
    org_id: str
    user_id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrgMembershipInDB(BaseModel):
    """Membership in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    user_id: str
    role: str = CustomerRole.CUSTOMER_ORG_BUYER.value
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- B2B Applications ---

class ApplicationCreate(BaseModel):
    """Create B2B application"""
    org_id: str


class ApplicationDecision(BaseModel):
    """Application decision by compliance"""
    decision: str  # "APPROVED" or "REJECTED"
    reason_code: Optional[str] = None
    comment: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Application response"""
    id: str
    org_id: str
    status: str
    submitted_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    decision_at: Optional[datetime] = None
    decision_reason_code: Optional[str] = None
    decision_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationInDB(BaseModel):
    """Application in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    status: str = ApplicationStatus.DRAFT.value
    submitted_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    decision_at: Optional[datetime] = None
    decision_reason_code: Optional[str] = None
    decision_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Application Documents ---

class DocumentUpload(BaseModel):
    """Upload document"""
    doc_type: DocType
    file_url: str
    checksum_sha256: str


class DocumentResponse(BaseModel):
    """Document response"""
    id: str
    application_id: str
    org_id: str
    doc_type: str
    file_url: str
    checksum_sha256: str
    status: str
    reviewed_by_user_id: Optional[str] = None
    review_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentInDB(BaseModel):
    """Document in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str
    org_id: str
    doc_type: str
    file_url: str
    checksum_sha256: str
    status: str = DocStatus.UPLOADED.value
    reviewed_by_user_id: Optional[str] = None
    review_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PHASE 2: BILLING MODELS ==============

# --- Plans ---

class PlanResponse(BaseModel):
    """Subscription plan"""
    id: str
    code: str
    name: str
    price_ht_cents: int
    billing_period: str
    is_active: bool
    features: List[str] = []
    zones_included: List[str] = []

    class Config:
        from_attributes = True


class PlanInDB(BaseModel):
    """Plan in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str  # ESS_ACCES, ESS_VOLUME, ESS_IMPACT
    name: str
    price_ht_cents: int
    billing_period: str = BillingPeriod.MONTHLY.value
    is_active: bool = True
    features: List[str] = []
    zones_included: List[str] = []


# --- Subscriptions ---

class SubscriptionCreate(BaseModel):
    """Create subscription"""
    plan_id: str
    payment_method_token: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Subscription response"""
    id: str
    org_id: str
    plan_id: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionInDB(BaseModel):
    """Subscription in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    plan_id: str
    status: str = SubscriptionStatus.INACTIVE.value
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Billing Invoices ---

class InvoiceResponse(BaseModel):
    """Invoice response"""
    id: str
    org_id: str
    subscription_id: Optional[str] = None
    invoice_type: str
    status: str
    amount_ht_cents: int
    tax_cents: int
    amount_ttc_cents: int
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    provider_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceInDB(BaseModel):
    """Invoice in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    subscription_id: Optional[str] = None
    invoice_type: str = InvoiceType.SUBSCRIPTION.value
    status: str = InvoiceStatus.DRAFT.value
    amount_ht_cents: int
    tax_cents: int = 0
    amount_ttc_cents: int
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    provider_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PHASE 3: WALLET MODELS ==============

# --- Wallets ---

class WalletResponse(BaseModel):
    """Wallet response"""
    org_id: str
    balance_credits: int
    status: str
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletInDB(BaseModel):
    """Wallet in database (1 per org)"""
    org_id: str  # PK
    balance_credits: int = 0
    status: str = WalletStatus.ACTIVE.value
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Wallet Ledger (append-only) ---

class LedgerEntryCreate(BaseModel):
    """Create ledger entry (credit or debit)"""
    direction: LedgerDirection
    amount_credits: int = Field(..., gt=0)
    reason_code: str
    correlation_id: str  # Idempotency key


class LedgerEntryResponse(BaseModel):
    """Ledger entry response"""
    id: str
    org_id: str
    direction: str
    amount_credits: int
    reason_code: str
    correlation_id: str
    status: str
    created_by_user_id: Optional[str] = None
    related_invoice_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LedgerEntryInDB(BaseModel):
    """Ledger entry in database (immutable)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    direction: str  # CREDIT or DEBIT
    amount_credits: int
    reason_code: str
    correlation_id: str
    status: str = LedgerStatus.PENDING.value
    created_by_user_id: Optional[str] = None
    related_invoice_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PHASE 4: ZONES & ENTITLEMENTS ==============

# --- Zones ---

class ZoneResponse(BaseModel):
    """Zone response"""
    id: str
    code: str
    name: str
    kind: str
    exw_only: bool
    pickup_required: bool
    is_active: bool
    
    # LOGI'SCOP delivery fields
    logiscop_delivery_enabled: bool = False
    delivery_min_cartons: int = 1
    delivery_max_cartons: int = 100
    
    # VAT configuration
    vat_rate: float = 8.5
    vat_exonerated: bool = False

    class Config:
        from_attributes = True


class ZoneInDB(BaseModel):
    """Zone in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str  # GUADELOUPE, MARTINIQUE, etc.
    name: str
    kind: str = ZoneKind.OM.value
    exw_only: bool = True
    pickup_required: bool = True
    is_active: bool = True
    
    # LOGI'SCOP delivery fields
    logiscop_delivery_enabled: bool = False
    delivery_min_cartons: int = 1
    delivery_max_cartons: int = 100
    
    # VAT configuration
    vat_rate: float = 8.5  # DOM default
    vat_exonerated: bool = False  # True for Guyane, Mayotte


# --- Zone Entitlements ---

class EntitlementResponse(BaseModel):
    """Zone entitlement response"""
    id: str
    org_id: str
    zone_id: str
    source: str
    status: str
    starts_at: datetime
    ends_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EntitlementInDB(BaseModel):
    """Zone entitlement in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    zone_id: str
    source: str = EntitlementSource.INCLUDED.value
    status: str = EntitlementStatus.ACTIVE.value
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    ends_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Runtime Preferences ---

class RuntimePreferencesInDB(BaseModel):
    """Org runtime preferences (selected zone)"""
    org_id: str  # PK
    selected_zone_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PHASE 5: PARTNER & AUDIT ==============

# --- Partner Accounts (KDMARCHE) ---

class PartnerAccountResponse(BaseModel):
    """Partner account response"""
    id: str
    org_id: str
    partner: str
    status: str
    partner_org_ref: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PartnerAccountInDB(BaseModel):
    """Partner account in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    partner: str = "KDMARCHE"
    status: str = PartnerProvisionStatus.NOT_PROVISIONED.value
    partner_org_ref: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Audit Log (append-only) ---

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    target_type: str  # ORG, APPLICATION, SUBSCRIPTION, WALLET, PARTNER_ACCOUNT
    target_id: Optional[str] = None
    reason_code: Optional[str] = None
    comment: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Outbox Events (for webhooks) ---

class OutboxEventStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DEAD = "DEAD"


class OutboxEvent(BaseModel):
    """Outbox event for reliable delivery"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any]
    status: str = OutboxEventStatus.PENDING.value
    attempts: int = 0
    next_retry_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== DEFAULT ZONES CATALOG ==============

DEFAULT_ZONES = [
    {
        "code": "GUADELOUPE",
        "name": "Guadeloupe",
        "kind": ZoneKind.OM.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "MARTINIQUE", 
        "name": "Martinique",
        "kind": ZoneKind.OM.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "GUYANE",
        "name": "Guyane",
        "kind": ZoneKind.OM.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "REUNION",
        "name": "La Réunion",
        "kind": ZoneKind.OM.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "MAYOTTE",
        "name": "Mayotte",
        "kind": ZoneKind.OM.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "EUROPE",
        "name": "Europe",
        "kind": ZoneKind.EXPORT.value,
        "exw_only": True,
        "pickup_required": True,
    },
    {
        "code": "CARIBBEAN",
        "name": "Caraïbes",
        "kind": ZoneKind.EXPORT.value,
        "exw_only": True,
        "pickup_required": True,
    },
]


# ============== DEFAULT PLANS ==============

DEFAULT_PLANS = [
    {
        "code": "ESS_ACCES",
        "name": "ESS Accès Pro",
        "price_ht_cents": 9900,  # 99€ HT/mois
        "billing_period": BillingPeriod.MONTHLY.value,
        "features": [
            "Accès catalogue KDMARCHE",
            "1 zone incluse",
            "100 crédits offerts",
            "Support standard",
        ],
        "zones_included": ["territory"],  # Uses org territory
    },
    {
        "code": "ESS_VOLUME",
        "name": "ESS Volume Pro",
        "price_ht_cents": 19900,  # 199€ HT/mois
        "billing_period": BillingPeriod.MONTHLY.value,
        "features": [
            "Accès catalogue KDMARCHE",
            "2 zones incluses",
            "500 crédits offerts",
            "Prix mutualisés (-30%)",
            "Support prioritaire",
        ],
        "zones_included": ["territory", "+1"],
    },
    {
        "code": "ESS_IMPACT",
        "name": "ESS Impact Pro",
        "price_ht_cents": 39900,  # 399€ HT/mois
        "billing_period": BillingPeriod.MONTHLY.value,
        "features": [
            "Accès catalogue KDMARCHE",
            "Toutes zones incluses",
            "1000 crédits offerts",
            "Prix mutualisés (-50%)",
            "Support dédié",
            "API accès",
        ],
        "zones_included": ["ALL"],
    },
]
