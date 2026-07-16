"""KDMARCHE × LOGI'SCOP V1 — Policy data & Pydantic models (split from routes_v1_logiscop.py)."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# ============== DELIVERY POLICY DATA ==============
# DELIVERY_POLICY moved to routes_logistics_shared.py to break the circular
# import between routes_ess and routes_v1_logiscop.
# It is re-exported via the `from routes_logistics_shared import DELIVERY_POLICY`
# at the top of this file for backwards compatibility with other modules.

# Frais de préparation LOGI'SCOP
PREPARATION_FEES = {
    "picking_per_line": 150,        # 1.50€ par ligne
    "packaging_small": 200,         # 2€ pour colis < 5kg
    "packaging_medium": 350,        # 3.50€ pour colis 5-20kg
    "packaging_large": 500,         # 5€ pour colis > 20kg
    "palettization": 1500,          # 15€ par palette
    "labeling": 50,                 # 0.50€ par étiquette
}

# Suppléments créneaux
SLOT_SUPPLEMENTS = {
    "AM": {"label": "Matin (8h-12h)", "cents": 0},
    "PM": {"label": "Après-midi (14h-18h)", "cents": 0},
    "EXPRESS": {"label": "Express (< 4h)", "cents": 2500},
    "RDV": {"label": "Sur rendez-vous", "cents": 500},
}


# ============== PYDANTIC MODELS ==============

class DeliveryAddress(BaseModel):
    street: str
    complement: Optional[str] = None
    city: str
    postal_code: str
    country: str = "FR"
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class LogiscopQuoteRequest(BaseModel):
    """POST /v1/b2b/logiscop/quote"""
    zone_code: str
    fulfillment_mode: str = "LOGISCOP_DELIVERY"  # EXW_PICKUP, LOGISCOP_DELIVERY
    delivery_mode: str = "DIRECT"  # DIRECT, ESS_ROUTE
    weight_kg: float = Field(..., gt=0)
    volume_m3: Optional[float] = Field(None, ge=0)
    items_count: int = Field(1, ge=1)
    cartons: Optional[int] = Field(None, ge=1)
    pallets: Optional[int] = Field(None, ge=0)
    delivery_slot: str = "AM"
    delivery_type: str = "standard"  # standard, express
    tour_id: Optional[str] = None  # For ESS_ROUTE mode
    delivery_address: Optional[DeliveryAddress] = None
    delivery_window: Optional[Dict[str, str]] = None  # {"start": "08:00", "end": "12:00"}


class LogiscopQuoteLineItem(BaseModel):
    code: str
    label: str
    amount_ht_cents: int
    quantity: int = 1


class LogiscopQuoteResponse(BaseModel):
    zone_code: str
    zone_name: str
    fulfillment_mode: str
    delivery_mode: str  # DIRECT or ESS_ROUTE
    
    # Weight/Volume
    weight_kg: float
    volume_m3: Optional[float]
    billing_mode: str  # "weight" ou "volume" (le plus élevé)
    
    # Line items
    lines: List[LogiscopQuoteLineItem]
    
    # Totals
    subtotal_ht_cents: int
    transport_total_ht: float  # En euros pour compatibilité OpenAPI
    vat_rate: float
    vat_cents: int
    vat_amount: float  # En euros
    total_ttc_cents: int
    transport_total_ttc: float  # En euros
    
    # Delivery info
    slot: str
    slot_label: str
    estimated_delivery: str
    
    # Route info (for ESS_ROUTE mode)
    route: Optional[Dict[str, Any]] = None
    
    # Breakdown (for OpenAPI compliance)
    breakdown: Optional[List[Dict[str, Any]]] = None
    
    # Quote metadata
    quote_id: str
    valid_until: str
    expires_at: str
    billing_entity: str = "LOGI'SCOP"
    currency: str = "EUR"


class CheckoutQuoteRequest(BaseModel):
    """POST /v1/b2b/checkout/quote"""
    zone_code: str
    
    # Goods (KDMARCHE)
    goods_subtotal_ht_cents: int
    goods_items_count: int = 1
    
    # Delivery options
    fulfillment_mode: str = "EXW"  # "EXW" ou "DELIVERY"
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_slot: str = "AM"
    
    # Weight/Volume for delivery calculation
    weight_kg: float = 0
    volume_m3: float = 0
    
    # Preparation options (from cart)
    prep_options: List[Dict[str, Any]] = []


class CheckoutQuoteLine(BaseModel):
    entity: str  # "KDMARCHE" ou "LOGI'SCOP"
    category: str  # "goods", "preparation", "transport", "slot_supplement"
    label: str
    amount_ht_cents: int


class CheckoutQuoteResponse(BaseModel):
    zone_code: str
    zone_name: str
    fulfillment_mode: str
    
    # Lines by entity
    lines: List[CheckoutQuoteLine]
    
    # KDMARCHE totals (goods + prep)
    kdmarche_subtotal_ht_cents: int
    kdmarche_vat_rate: float
    kdmarche_vat_cents: int
    kdmarche_total_ttc_cents: int
    
    # LOGI'SCOP totals (transport only, if DELIVERY mode)
    logiscop_subtotal_ht_cents: int
    logiscop_vat_rate: float
    logiscop_vat_cents: int
    logiscop_total_ttc_cents: int
    
    # Grand total
    grand_total_ht_cents: int
    grand_total_ttc_cents: int
    
    # Quote metadata
    quote_id: str
    valid_until: str


class OrderDeliveryInfo(BaseModel):
    fulfillment_mode: str
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_slot: Optional[str] = None
    logistics_quote_id: Optional[str] = None


class CreateOrderV1Request(BaseModel):
    """POST /v1/b2b/orders"""
    cart_id: str
    zone_code: str
    
    # Delivery
    delivery: OrderDeliveryInfo
    
    # Preparation options
    prep_options: List[Dict[str, Any]] = []
    
    # Payment
    use_installment: bool = False
    payment_method: str = "card"  # card, sepa
    
    # Notes
    notes: Optional[str] = None
    
    # Signature reference (if already signed)
    signature_id: Optional[str] = None


class OrderV1Response(BaseModel):
    id: str
    order_number: str
    status: str
    
    # Amounts
    goods_total_ht_cents: int
    prep_fees_ht_cents: int
    transport_ht_cents: int
    vat_cents: int
    total_ttc_cents: int
    
    # Delivery
    fulfillment_mode: str
    pickup_location_id: Optional[str]
    delivery_address: Optional[Dict]
    
    # Metadata
    created_at: str
    estimated_delivery: Optional[str]


