from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class SubscriptionPlan(str, Enum):
    ESS_ACCES_PRO = "ess-acces-pro"
    ESS_VOLUME_PRO = "ess-volume-pro"
    ESS_IMPACT_PRO = "ess-impact-pro"


class QuoteStatus(str, Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    CONVERTED = "converted"


# User Models
class UserBase(BaseModel):
    email: EmailStr
    company_name: str
    siret: str
    contact_name: str
    phone: str


class UserCreate(UserBase):
    password: str
    plan: Optional[SubscriptionPlan] = SubscriptionPlan.ESS_ACCES_PRO
    account_type: Optional[str] = "buyer"  # buyer | vendor


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    portal: str = "member"


class UserResponse(UserBase):
    id: str
    subscription: str
    credits: int
    is_admin: bool = False
    role: Optional[str] = None
    must_change_password: bool = False
    from_quote_id: Optional[str] = None
    from_quote_date: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    password_hash: str
    subscription: str = "ess-acces-pro"
    credits: int = 100
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Token Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None


# Quote Request Models
class QuoteRequestCreate(BaseModel):
    company: str
    contact_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    legal_status: Optional[str] = None
    email: EmailStr
    phone: str
    phone_country: Optional[str] = None
    lang: Optional[str] = "fr"
    plan: Optional[str] = None
    message: Optional[str] = None


class QuoteRequestResponse(BaseModel):
    id: str
    company: str
    contact_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    legal_status: Optional[str] = None
    email: str
    phone: str
    phone_country: Optional[str] = None
    lang: Optional[str] = None
    plan: Optional[str] = None
    message: Optional[str] = None
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteRequestInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company: str
    contact_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    legal_status: Optional[str] = None
    email: str
    phone: str
    phone_country: Optional[str] = None
    lang: Optional[str] = "fr"
    plan: Optional[str] = None
    message: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Subscription Models
class SubscriptionPlanInfo(BaseModel):
    id: str
    name: str
    price: int
    period: str = "mois"
    features: List[str]
    popular: bool = False


class SubscriptionUpdate(BaseModel):
    plan: SubscriptionPlan


# Credits Models
class CreditsAdd(BaseModel):
    amount: int = Field(..., ge=50)


class CreditsResponse(BaseModel):
    credits: int
    message: str


# Password Reset Models
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordResetToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    email: str
    token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Order/Transaction Models for Statistics
class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderCreate(BaseModel):
    items: List[dict]
    total_amount: float
    credits_used: int = 0


class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[dict]
    total_amount: float
    credits_used: int
    savings: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[dict]
    total_amount: float
    credits_used: int = 0
    savings: float = 0.0
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Admin Statistics Models
class AdminStats(BaseModel):
    total_users: int
    total_quotes: int
    total_orders: int
    total_credits_distributed: int
    quotes_by_status: dict
    new_users_this_month: int
    new_quotes_this_month: int


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int


# ============== PHASE 2: RBAC & ORGANIZATION STATES ==============

# Enhanced Roles (RBAC)
class UserRole(str, Enum):
    # O'SCOP Roles
    OSCOP_SUPER_ADMIN = "oscop_super_admin"
    OSCOP_COMPLIANCE_ADMIN = "oscop_compliance_admin"
    OSCOP_BILLING_ADMIN = "oscop_billing_admin"
    OSCOP_SUPPORT_AGENT = "oscop_support_agent"
    # KDMARCHE Roles
    KDM_B2B_ADMIN = "kdm_b2b_admin"
    KDM_B2B_SALES = "kdm_b2b_sales"
    KDM_WAREHOUSE = "kdm_warehouse"
    KDM_FINANCE = "kdm_finance"
    # Customer Roles
    CUSTOMER_ORG_OWNER = "customer_org_owner"
    CUSTOMER_ORG_BUYER = "customer_org_buyer"
    CUSTOMER_ORG_VIEWER = "customer_org_viewer"


# Organization Status (State Machine)
class OrgStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# Subscription Status
class SubscriptionStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    GRACE_PERIOD = "grace_period"
    CANCELED = "canceled"


# KDMARCHE Access Status (Provisioning)
class KdmAccessStatus(str, Enum):
    NOT_PROVISIONED = "not_provisioned"
    PROVISIONED = "provisioned"
    ACCESS_ENABLED = "access_enabled"
    ACCESS_DISABLED = "access_disabled"
    DEPROVISIONED = "deprovisioned"


# Zone Models
class Zone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str  # e.g., "972", "971", "973"
    name: str  # e.g., "Martinique", "Guadeloupe", "Guyane"
    country: str = "FR"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ZoneEntitlement(BaseModel):
    zone_id: str
    zone_code: str
    zone_name: str
    included_in_plan: bool = False  # True if included in subscription
    is_addon: bool = False  # True if purchased as addon
    activated_at: datetime = Field(default_factory=datetime.utcnow)


class OrgZonesUpdate(BaseModel):
    zone_ids: List[str]


# Organization (Enhanced User/Company)
class OrganizationCreate(BaseModel):
    legal_name: str
    siret: str
    contact_email: EmailStr
    contact_name: str
    contact_phone: str
    territory: str  # Primary zone code
    address: Optional[str] = None
    documents: Optional[List[str]] = []  # Document IDs


class OrganizationResponse(BaseModel):
    id: str
    legal_name: str
    siret: str
    contact_email: str
    contact_name: str
    contact_phone: str
    territory: str
    address: Optional[str] = None
    status: str
    subscription_status: str
    kdm_access_status: str
    credits: int
    zone_entitlements: List[ZoneEntitlement] = []
    selected_zone: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    legal_name: str
    siret: str
    contact_email: str
    contact_name: str
    contact_phone: str
    territory: str
    address: Optional[str] = None
    status: str = OrgStatus.DRAFT.value
    subscription_plan: str = "ess-acces-pro"
    subscription_status: str = SubscriptionStatus.INACTIVE.value
    kdm_access_status: str = KdmAccessStatus.NOT_PROVISIONED.value
    credits: int = 0
    zone_entitlements: List[dict] = []
    selected_zone: Optional[str] = None
    owner_user_id: Optional[str] = None
    risk_flags: List[str] = []
    documents: List[str] = []
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Organization Decision (Compliance)
class OrgDecision(BaseModel):
    decision: str  # "approve" or "reject"
    reason_code: Optional[str] = None
    comment: Optional[str] = None


# ============== PHASE 1: NOTIFICATIONS ==============

class NotificationType(str, Enum):
    NEW_QUOTE = "new_quote"
    NEW_USER = "new_user"
    ORG_SUBMITTED = "org_submitted"
    ORG_APPROVED = "org_approved"
    ORG_REJECTED = "org_rejected"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_PAST_DUE = "subscription_past_due"
    LOW_CREDITS = "low_credits"
    SYSTEM_ALERT = "system_alert"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    title: str
    message: str
    data: Optional[dict] = {}
    target_roles: List[str] = []  # Which roles should see this
    target_user_id: Optional[str] = None  # Specific user (optional)
    is_read: bool = False
    read_by: List[str] = []  # User IDs who have read it
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    data: Optional[dict] = {}
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total: int


# Enhanced User with Role
class UserWithRoleResponse(BaseModel):
    id: str
    email: str
    company_name: str
    siret: str
    contact_name: str
    phone: str
    subscription: str
    credits: int
    is_admin: bool = False
    role: str = UserRole.CUSTOMER_ORG_BUYER.value
    org_id: Optional[str] = None
    org_status: Optional[str] = None
    zone_entitlements: List[str] = []
    selected_zone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
