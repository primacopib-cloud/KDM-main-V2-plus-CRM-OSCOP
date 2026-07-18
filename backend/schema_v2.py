"""
KDMARCHE × O'SCOP B2B Platform - Core Schema (MongoDB Adaptation)
Based on PostgreSQL production schema, adapted for MongoDB with references

Phase 1: Core (orgs, users, memberships, applications)
Découpé en modules : schema_v2_enums, schema_v2_billing, schema_v2_zones (ré-exportés ici).
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from schema_v2_enums import (  # noqa: F401 — ré-exports
    OrgStatus, ApplicationStatus, SubscriptionStatus, PartnerProvisionStatus,
    LedgerStatus, LedgerDirection, WalletStatus, DocType, DocStatus,
    ZoneKind, BillingPeriod, InvoiceType, InvoiceStatus,
    DeliveryMode, FulfillmentMode, TourStatus, ESSBookingStatus,
    EntitlementSource, EntitlementStatus, OscopRole, KdmRole, CustomerRole,
)
from schema_v2_billing import (  # noqa: F401 — ré-exports
    PlanResponse, PlanInDB, SubscriptionCreate, SubscriptionResponse, SubscriptionInDB,
    InvoiceResponse, InvoiceInDB, WalletResponse, WalletInDB,
    LedgerEntryCreate, LedgerEntryResponse, LedgerEntryInDB,
)
from schema_v2_zones import (  # noqa: F401 — ré-exports
    ZoneResponse, ZoneInDB, EntitlementResponse, EntitlementInDB,
    RuntimePreferencesInDB, PartnerAccountResponse, PartnerAccountInDB,
    AuditLogEntry, OutboxEventStatus, OutboxEvent,
    DEFAULT_ZONES, DEFAULT_PLANS,
)

# ============== PHASE 1: CORE MODELS ==============

# --- Organizations ---

class OrgCreate(BaseModel):
    """Create organization request"""
    legal_name: str = Field(..., min_length=2, max_length=255)
    registration_country: str = Field(default="FR", max_length=2)
    registration_id: str = Field(..., min_length=9, max_length=20)  # SIRET
    territory: str = Field(...)  # Primary zone code
    member_type: str = Field(default="BUYER_PRO")  # BUYER_PRO | VENDOR_PRO
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


