"""KDMARCHE × O'SCOP — Schema V2 billing & wallet models (split from schema_v2.py)."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from schema_v2_enums import *  # noqa: F401,F403

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


