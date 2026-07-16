"""KDMARCHE × O'SCOP — Schema V2 zones, entitlements, partner & defaults (split from schema_v2.py)."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from schema_v2_enums import *  # noqa: F401,F403

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
