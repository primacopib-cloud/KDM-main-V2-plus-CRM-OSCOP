"""LOLODRIVE by O'SCOP — Constants, enums & Pydantic models (split from routes_lolodrive_oscoop.py)."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# =======================
# Constants / business rules
# =======================

PASS_PRICE_CENTS = 6000
PASS_UC = 600
PASS_DAYS = 30

RECHARGE_PACKS = {
    "MINI": {"amount_cents": 2000, "uc": 200},
    "STANDARD": {"amount_cents": 4000, "uc": 400},
    "MAXI": {"amount_cents": 7000, "uc": 720},
}

DEFAULT_LOGISTICS_CONFIG = {
    "id": "default",
    "drive_open_time": "08:00",
    "drive_close_time": "21:30",
    "drive_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
    "drive_fee_min_cents": 200,
    "drive_fee_min_uc": 20,
    "drive_fee_max_cents": 300,
    "drive_fee_max_uc": 30,
    "delivery_fee_min_cents": 500,
    "delivery_fee_max_cents": 1000,
    "delivery_fee_min_uc": 50,
    "delivery_fee_max_uc": 100,
    "allow_uc_for_normal_if_pass_active": True,
}

# =======================
# Schemas
# =======================

class CatalogType(str, Enum):
    ESSENTIAL = "ESSENTIAL"
    NORMAL = "NORMAL"

class FulfillmentType(str, Enum):
    DRIVE = "DRIVE"
    DELIVERY = "DELIVERY"
    LOLO_POINT = "LOLO_POINT"

class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PREPARING = "PREPARING"
    READY = "READY"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class EventType(str, Enum):
    LOLO_HOUR = "LOLO_HOUR"
    FLASH_PASS = "FLASH_PASS"
    FLASH_PUBLIC = "FLASH_PUBLIC"
    LOLO_BIG_DEAL = "LOLO_BIG_DEAL"
    PARTNER = "PARTNER"

class RegisterProduct(BaseModel):
    sku: str
    name: str
    category: str = "Épicerie"
    brand: Optional[str] = None
    size_label: Optional[str] = None
    catalog_type: CatalogType = CatalogType.NORMAL
    price_public_cents: int
    price_pass_cents: Optional[int] = None
    image_url: Optional[str] = None
    stock_qty: Optional[int] = None

class QuoteLine(BaseModel):
    sku: str
    qty: int = Field(..., ge=1)

class QuoteRequest(BaseModel):
    items: List[QuoteLine]

class OrderCreate(BaseModel):
    fulfillment_type: FulfillmentType
    items: List[QuoteLine]
    lolo_point_code: Optional[str] = None
    delivery_zone: Optional[str] = None
    delivery_slot_id: Optional[str] = None

class RechargeIntentRequest(BaseModel):
    pack: str = Field(..., description="MINI | STANDARD | MAXI")

class OrderIntentRequest(BaseModel):
    order_id: str

class LoloPointCreate(BaseModel):
    name: str
    code: str
    city: Optional[str] = None
    address: Optional[str] = None
    zone_name: Optional[str] = None
    territory: Optional[str] = None  # GP / MQ / GF / RE
    lat: Optional[float] = None
    lng: Optional[float] = None
    manager_user_id: Optional[str] = None
    payout_cap_cents_monthly: int = 120000
    payout_cap_percent_bps: int = 600

class EventCreate(BaseModel):
    type: EventType
    title: str
    starts_at: datetime
    ends_at: datetime
    is_pass_only: bool = True
    partner_id: Optional[str] = None
    sponsor_pack: Optional[str] = None
    stock_limit: Optional[int] = None
    per_user_limit: int = 1
    drive_only: bool = True

class PartnerCreate(BaseModel):
    name: str
    type: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

class CoopContributionCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    estimated_value_cents: Optional[int] = None
    user_id: Optional[str] = None

class StatusUpdate(BaseModel):
    status: OrderStatus

class PayoutPreviewRequest(BaseModel):
    from_date: datetime
    to_date: datetime

