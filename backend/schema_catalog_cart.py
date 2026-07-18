"""KDMARCHE × O'SCOP — Schema Catalogue : panier & commandes (split from schema_catalog.py)."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from schema_catalog_enums import CartStatus, OrderStatus  # noqa: F401 — aussi ré-exportés

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
    unavailable: bool = False

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
    alerts: List[Dict[str, Any]] = []
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
