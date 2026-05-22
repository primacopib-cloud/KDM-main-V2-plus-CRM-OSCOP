"""
KDMARCHE × O'SCOP - Catalogue Produits Schema
Multi-zones, pricing dynamique, ABAC integration

Structure:
- Categories (hiérarchie)
- Products (catalogue)
- Zone Pricing (prix par zone)
- Suppliers (fournisseurs - non visible client)
- Stock (disponibilité par zone)
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============== ENUMS ==============

class ProductStatus(str, Enum):
    """Product availability status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    DISCONTINUED = "DISCONTINUED"


class PriceType(str, Enum):
    """Price type"""
    STANDARD = "STANDARD"
    PROMO = "PROMO"
    FLASH = "FLASH"


class UnitType(str, Enum):
    """Unit of measurement"""
    PIECE = "PIECE"
    KG = "KG"
    LITRE = "LITRE"
    CARTON = "CARTON"
    PALETTE = "PALETTE"


class OrderStatus(str, Enum):
    """Order status"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    INVOICED = "INVOICED"
    PAID = "PAID"
    CANCELED = "CANCELED"


class CartStatus(str, Enum):
    """Cart status"""
    ACTIVE = "ACTIVE"
    CONVERTED = "CONVERTED"
    ABANDONED = "ABANDONED"


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


# ============== CART ==============

class CartItemCreate(BaseModel):
    """Add item to cart"""
    product_id: str
    quantity: int = Field(..., gt=0)


class CartItemResponse(BaseModel):
    """Cart item response"""
    id: str
    product_id: str
    product_name: str
    product_sku: str
    product_image: Optional[str] = None
    unit: str
    quantity: int
    price_ht_cents: int
    line_total_ht_cents: int

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Cart response"""
    id: str
    org_id: str
    zone_code: str
    status: str
    items: List[CartItemResponse] = []
    items_count: int = 0
    subtotal_ht_cents: int = 0
    tax_cents: int = 0
    total_ttc_cents: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartInDB(BaseModel):
    """Cart in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    zone_code: str
    status: str = CartStatus.ACTIVE.value
    items: List[dict] = []  # [{product_id, quantity, price_ht_cents, ...}]
    subtotal_ht_cents: int = 0
    tax_cents: int = 0
    total_ttc_cents: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== ORDERS ==============

class OrderCreate(BaseModel):
    """Create order from cart"""
    cart_id: str
    pickup_location_id: str
    notes: Optional[str] = None
    use_installment: bool = False  # Request installment payment (4x)


class OrderItemResponse(BaseModel):
    """Order item"""
    product_id: str
    product_name: str
    product_sku: str
    unit: str
    quantity: int
    price_ht_cents: int
    line_total_ht_cents: int


class OrderResponse(BaseModel):
    """Order response"""
    id: str
    order_number: str
    org_id: str
    zone_code: str
    status: str
    incoterm: str = "EXW"
    pickup_location_id: str
    pickup_location_name: Optional[str] = None
    items: List[OrderItemResponse] = []
    items_count: int = 0
    subtotal_ht_cents: int = 0
    tax_cents: int = 0
    total_ttc_cents: int = 0
    credits_used: int = 0
    notes: Optional[str] = None
    # Installment payment
    is_installment: bool = False
    installment_plan: Optional[Dict[str, Any]] = None
    installment_eligible: bool = False  # Computed: subtotal >= 5500€
    confirmed_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderInDB(BaseModel):
    """Order in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default_factory=lambda: f"KDM-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}")
    org_id: str
    zone_code: str
    status: str = OrderStatus.PENDING.value
    incoterm: str = "EXW"
    pickup_location_id: str
    items: List[dict] = []
    items_count: int = 0
    subtotal_ht_cents: int = 0
    tax_cents: int = 0
    total_ttc_cents: int = 0
    credits_used: int = 0
    notes: Optional[str] = None
    created_by_user_id: str
    confirmed_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    # Installment payment fields
    is_installment: bool = False
    installment_plan: Optional[Dict[str, Any]] = None  # {total, fees, installments: [...]}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== INSTALLMENT PAYMENT ==============

class InstallmentPlanCreate(BaseModel):
    """Request installment payment for an order"""
    order_id: str


class InstallmentSchedule(BaseModel):
    """Single installment in the plan"""
    number: int  # 1, 2, 3, 4
    amount_cents: int
    due_date: datetime
    status: str = "PENDING"  # PENDING, PAID, OVERDUE
    paid_at: Optional[datetime] = None


class InstallmentPlanResponse(BaseModel):
    """Installment plan response"""
    eligible: bool
    min_amount_ht_cents: int = 550000  # 5500€ in cents
    subtotal_ht_cents: int
    # Fee calculation: HT × 20% + TVA 8.50%
    fee_rate: float = 0.20  # 20%
    fee_tva_rate: float = 0.085  # 8.50%
    fees_ht_cents: int
    fees_tva_cents: int
    total_fees_cents: int
    total_with_fees_cents: int
    installment_count: int = 4
    installments: List[InstallmentSchedule] = []
    message: Optional[str] = None


class InstallmentPlanInDB(BaseModel):
    """Installment plan stored in order"""
    subtotal_ht_cents: int
    fees_ht_cents: int
    fees_tva_cents: int
    total_fees_cents: int
    total_with_fees_cents: int
    installments: List[dict]  # List of InstallmentSchedule as dict
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== PICKUP LOCATIONS ==============

class PickupLocationResponse(BaseModel):
    """Pickup location response"""
    id: str
    zone_code: str
    name: str
    address: str
    city: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class PickupLocationInDB(BaseModel):
    """Pickup location in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    zone_code: str
    name: str
    address: str
    city: str
    postal_code: str
    country: str = "FR"
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # {lat, lng}
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== DEFAULT DATA ==============

DEFAULT_CATEGORIES = [
    {"code": "ALIMENTAIRE", "name": "Alimentaire", "description": "Produits alimentaires", "sort_order": 1},
    {"code": "BOISSONS", "name": "Boissons", "description": "Boissons et liquides", "sort_order": 2},
    {"code": "HYGIENE", "name": "Hygiène", "description": "Produits d'hygiène et entretien", "sort_order": 3},
    {"code": "EPICERIE", "name": "Épicerie", "description": "Épicerie sèche", "sort_order": 4},
    {"code": "FRAIS", "name": "Produits frais", "description": "Produits frais et réfrigérés", "sort_order": 5},
    {"code": "SURGELES", "name": "Surgelés", "description": "Produits surgelés", "sort_order": 6},
]

DEFAULT_PICKUP_LOCATIONS = [
    {
        "zone_code": "MARTINIQUE",
        "name": "Entrepôt Fort-de-France",
        "address": "Zone Industrielle de la Lézarde",
        "city": "Fort-de-France",
        "postal_code": "97232",
        "country": "FR",
        "phone": "0596 60 00 00",
        "opening_hours": "Lun-Ven 8h-17h, Sam 8h-12h",
    },
    {
        "zone_code": "GUADELOUPE",
        "name": "Entrepôt Jarry",
        "address": "Zone Industrielle de Jarry",
        "city": "Baie-Mahault",
        "postal_code": "97122",
        "country": "FR",
        "phone": "0590 26 00 00",
        "opening_hours": "Lun-Ven 8h-17h, Sam 8h-12h",
    },
    {
        "zone_code": "GUYANE",
        "name": "Entrepôt Cayenne",
        "address": "Zone Industrielle de Dégrad des Cannes",
        "city": "Rémire-Montjoly",
        "postal_code": "97354",
        "country": "FR",
        "phone": "0594 30 00 00",
        "opening_hours": "Lun-Ven 8h-17h",
    },
    {
        "zone_code": "REUNION",
        "name": "Entrepôt Le Port",
        "address": "Zone Industrielle n°2",
        "city": "Le Port",
        "postal_code": "97420",
        "country": "FR",
        "phone": "0262 42 00 00",
        "opening_hours": "Lun-Ven 8h-17h, Sam 8h-12h",
    },
]

# Sample products for demo
SAMPLE_PRODUCTS = [
    {
        "sku": "ALI-RIZ-001",
        "name": "Riz long grain 5kg",
        "category_code": "ALIMENTAIRE",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 5,
        "tags": ["riz", "base", "économique"],
        "prices": {"MARTINIQUE": 1250, "GUADELOUPE": 1280, "GUYANE": 1350, "REUNION": 1400},
        "original_price": 2500,  # Prix public reference
    },
    {
        "sku": "ALI-HUI-001",
        "name": "Huile de tournesol 5L",
        "category_code": "ALIMENTAIRE",
        "unit": "PIECE",
        "unit_quantity": 1,
        "min_order_qty": 4,
        "tags": ["huile", "cuisine"],
        "prices": {"MARTINIQUE": 890, "GUADELOUPE": 920, "GUYANE": 980, "REUNION": 1050},
        "original_price": 1800,
    },
    {
        "sku": "BOI-EAU-001",
        "name": "Eau minérale 1.5L (pack 6)",
        "category_code": "BOISSONS",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 10,
        "tags": ["eau", "boisson"],
        "prices": {"MARTINIQUE": 320, "GUADELOUPE": 340, "GUYANE": 380, "REUNION": 420},
        "original_price": 650,
    },
    {
        "sku": "BOI-JUS-001",
        "name": "Jus d'orange 1L (pack 12)",
        "category_code": "BOISSONS",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 5,
        "tags": ["jus", "fruit", "orange"],
        "prices": {"MARTINIQUE": 1450, "GUADELOUPE": 1500, "GUYANE": 1600, "REUNION": 1700},
        "original_price": 2900,
    },
    {
        "sku": "HYG-SAV-001",
        "name": "Savon liquide 5L",
        "category_code": "HYGIENE",
        "unit": "PIECE",
        "unit_quantity": 1,
        "min_order_qty": 4,
        "tags": ["savon", "hygiène"],
        "prices": {"MARTINIQUE": 780, "GUADELOUPE": 800, "GUYANE": 850, "REUNION": 900},
        "original_price": 1560,
    },
    {
        "sku": "EPI-PAT-001",
        "name": "Pâtes alimentaires 500g (carton 24)",
        "category_code": "EPICERIE",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 3,
        "tags": ["pâtes", "épicerie"],
        "prices": {"MARTINIQUE": 1850, "GUADELOUPE": 1900, "GUYANE": 2000, "REUNION": 2100},
        "original_price": 3700,
    },
    {
        "sku": "EPI-SUC-001",
        "name": "Sucre en poudre 1kg (pack 10)",
        "category_code": "EPICERIE",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 5,
        "tags": ["sucre", "base"],
        "prices": {"MARTINIQUE": 950, "GUADELOUPE": 980, "GUYANE": 1050, "REUNION": 1100},
        "original_price": 1900,
    },
    {
        "sku": "FRA-LAI-001",
        "name": "Lait UHT 1L (pack 12)",
        "category_code": "FRAIS",
        "unit": "CARTON",
        "unit_quantity": 1,
        "min_order_qty": 5,
        "tags": ["lait", "frais"],
        "prices": {"MARTINIQUE": 1150, "GUADELOUPE": 1200, "GUYANE": 1280, "REUNION": 1350},
        "original_price": 2300,
    },
]
