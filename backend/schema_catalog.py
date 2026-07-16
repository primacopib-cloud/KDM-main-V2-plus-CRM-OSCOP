"""
KDMARCHE × O'SCOP - Catalogue Produits Schema
Multi-zones, pricing dynamique, ABAC integration

Découpé en modules : schema_catalog_enums, schema_catalog_cart (ré-exportés ici).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from schema_catalog_enums import *  # noqa: F401,F403
from schema_catalog_cart import *  # noqa: F401,F403

# ============== CATEGORIES ==============

class CategoryCreate(BaseModel):
    """Create category"""
    code: str = Field(..., min_length=2, max_length=50)
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None  # For hierarchy
    image_url: Optional[str] = None
    sort_order: int = 0


class CategoryResponse(BaseModel):
    """Category response"""
    id: str
    code: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int
    product_count: int = 0
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryInDB(BaseModel):
    """Category in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    product_count: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== SUPPLIERS (Internal) ==============

class SupplierInDB(BaseModel):
    """Supplier in database (not exposed to clients)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    country: str = "FR"
    zones_served: List[str] = []  # Zone codes
    lead_time_days: int = 7
    min_order_value: int = 0  # cents
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PRODUCTS ==============

class ProductCreate(BaseModel):
    """Create product"""
    sku: str = Field(..., min_length=3, max_length=50)
    name: str
    description: Optional[str] = None
    category_id: str
    unit: UnitType = UnitType.PIECE
    unit_quantity: float = 1.0  # e.g., 1 for piece, 0.5 for 500g
    min_order_qty: int = 1
    max_order_qty: Optional[int] = None
    weight_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    image_url: Optional[str] = None
    tags: List[str] = []


class ProductResponse(BaseModel):
    """Product response (public)"""
    id: str
    sku: str
    name: str
    description: Optional[str] = None
    category_id: str
    category_name: Optional[str] = None
    unit: str
    unit_quantity: float
    min_order_qty: int
    max_order_qty: Optional[int] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    status: str
    # Price (only if authorized)
    price_visible: bool = False
    price_ht_cents: Optional[int] = None
    price_type: Optional[str] = None
    original_price_ht_cents: Optional[int] = None  # For promos
    savings_percent: Optional[float] = None
    # Stock
    in_stock: bool = True
    stock_quantity: Optional[int] = None

    class Config:
        from_attributes = True


class ProductInDB(BaseModel):
    """Product in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str
    name: str
    description: Optional[str] = None
    category_id: str
    supplier_id: Optional[str] = None  # Internal only
    unit: str = UnitType.PIECE.value
    unit_quantity: float = 1.0
    min_order_qty: int = 1
    max_order_qty: Optional[int] = None
    weight_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    status: str = ProductStatus.ACTIVE.value
    is_featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== ZONE PRICING ==============

class ZonePriceCreate(BaseModel):
    """Create/update zone price"""
    zone_code: str
    price_ht_cents: int = Field(..., gt=0)
    price_type: PriceType = PriceType.STANDARD
    original_price_ht_cents: Optional[int] = None  # Reference price for savings calc
    promo_start: Optional[datetime] = None
    promo_end: Optional[datetime] = None


class ZonePriceResponse(BaseModel):
    """Zone price response"""
    id: str
    product_id: str
    zone_code: str
    price_ht_cents: int
    price_type: str
    original_price_ht_cents: Optional[int] = None
    savings_percent: Optional[float] = None
    promo_start: Optional[datetime] = None
    promo_end: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class ZonePriceInDB(BaseModel):
    """Zone price in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    zone_code: str
    price_ht_cents: int
    price_type: str = PriceType.STANDARD.value
    original_price_ht_cents: Optional[int] = None  # "Prix public" reference
    promo_start: Optional[datetime] = None
    promo_end: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== ZONE STOCK ==============

class ZoneStockInDB(BaseModel):
    """Stock per zone"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    zone_code: str
    quantity_available: int = 0
    quantity_reserved: int = 0
    reorder_point: int = 10
    last_restock_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


