"""KDMARCHE Checkout V1 — Enums, schémas, policy & évaluation OPA native (split from routes_checkout_v1.py)."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ============== ENUMS & SCHEMAS ==============

class FulfillmentMode(str, Enum):
    EXW_PICKUP = "EXW_PICKUP"
    LOGISCOP_DELIVERY = "LOGISCOP_DELIVERY"


class DeliveryAddress(BaseModel):
    company: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    postal_code: str
    country: str = "FR"
    territory: Optional[str] = None


class DeliveryWindow(BaseModel):
    start: datetime
    end: datetime


class GoodsMetrics(BaseModel):
    total_weight_kg: Optional[float] = None
    total_volume_m3: Optional[float] = None
    pallets: Optional[int] = None
    cartons: Optional[int] = None


class LogiScopQuoteRequest(BaseModel):
    zone_code: str
    fulfillment_mode: FulfillmentMode
    goods_metrics: Optional[GoodsMetrics] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_window: Optional[DeliveryWindow] = None


class QuoteBreakdownItem(BaseModel):
    label: str
    amount_ht: float


class LogiScopQuoteResponse(BaseModel):
    zone_code: str
    fulfillment_mode: FulfillmentMode
    currency: str = "EUR"
    transport_total_ht: float
    vat_rate: float
    vat_amount: float
    transport_total_ttc: float
    quote_id: str
    expires_at: datetime
    breakdown: List[QuoteBreakdownItem] = []


class AppliedPrepLine(BaseModel):
    option_code: str
    quantity: int
    unit_price_ht: float
    total_ht: float


class FulfillmentInfo(BaseModel):
    mode: FulfillmentMode
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_window: Optional[DeliveryWindow] = None
    transport_total_ht: Optional[float] = None
    transport_total_ttc: Optional[float] = None
    logistics_quote_id: Optional[str] = None


class CheckoutQuoteRequest(BaseModel):
    zone_code: str
    fulfillment_mode: FulfillmentMode
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_window: Optional[DeliveryWindow] = None
    logistics_quote_id: Optional[str] = None
    goods_subtotal_ht: float
    fees_subtotal_ht: Optional[float] = 0
    prep_lines: Optional[List[AppliedPrepLine]] = []


class CheckoutQuoteResponse(BaseModel):
    zone_code: str
    vat_rate: float
    goods_subtotal_ht: float
    fees_subtotal_ht: float
    total_ht: float
    vat_amount: float
    total_ttc: float
    fulfillment: FulfillmentInfo


class OrderLine(BaseModel):
    product_id: str
    product_sku: str
    product_name: str
    quantity: int
    unit_price_ht: float
    total_ht: float
    lot_number: Optional[str] = None
    dlc: Optional[str] = None


class PrepSelection(BaseModel):
    option_code: str
    quantity: int


class OrderCreateRequest(BaseModel):
    idempotency_key: Optional[str] = None
    zone_code: str
    incoterm: str = "EXW"
    fulfillment_mode: FulfillmentMode
    
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    delivery_window: Optional[DeliveryWindow] = None
    logistics_quote_id: Optional[str] = None
    
    goods_lines: List[OrderLine]
    prep_selections: Optional[List[PrepSelection]] = []
    
    totals_currency: str = "EUR"
    goods_subtotal_ht: float
    fees_subtotal_ht: float = 0
    total_ht: float
    vat_rate: float
    vat_amount: float
    total_ttc: float


class OrderCreateResponse(BaseModel):
    order_id: str
    order_number: str
    status: str
    incoterm: str
    fulfillment_mode: FulfillmentMode
    zone_code: str
    total_ttc: float
    created_at: datetime
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddress] = None
    logistics_quote_id: Optional[str] = None


# ============== DELIVERY POLICY (OPA Data) ==============

DELIVERY_POLICY = {
    "GUADELOUPE": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 600, "zone_code": "971"},
    "MARTINIQUE": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 600, "zone_code": "972"},
    "GUYANE": {"logiscop_delivery_enabled": False, "zone_code": "973"},
    "REUNION": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 800, "zone_code": "974"},
    "MAYOTTE": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 400, "zone_code": "976"},
    # Also support zone codes directly
    "971": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 600},
    "972": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 600},
    "973": {"logiscop_delivery_enabled": False},
    "974": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 800},
    "976": {"logiscop_delivery_enabled": True, "min_cartons": 1, "max_cartons": 400},
}

# Transport rates (cents)
TRANSPORT_RATES = {
    "971": {"base_ht": 250, "per_kg_ht": 45, "per_m3_ht": 8500},
    "972": {"base_ht": 280, "per_kg_ht": 50, "per_m3_ht": 9000},
    "973": {"base_ht": 450, "per_kg_ht": 75, "per_m3_ht": 15000},
    "974": {"base_ht": 320, "per_kg_ht": 55, "per_m3_ht": 11000},
    "976": {"base_ht": 380, "per_kg_ht": 65, "per_m3_ht": 12000},
    "GUADELOUPE": {"base_ht": 250, "per_kg_ht": 45, "per_m3_ht": 8500},
    "MARTINIQUE": {"base_ht": 280, "per_kg_ht": 50, "per_m3_ht": 9000},
    "GUYANE": {"base_ht": 450, "per_kg_ht": 75, "per_m3_ht": 15000},
    "REUNION": {"base_ht": 320, "per_kg_ht": 55, "per_m3_ht": 11000},
    "MAYOTTE": {"base_ht": 380, "per_kg_ht": 65, "per_m3_ht": 12000},
}

ZONE_TVA_RATES = {
    "971": 8.5, "972": 8.5, "973": 0, "974": 8.5, "976": 0,
    "GUADELOUPE": 8.5, "MARTINIQUE": 8.5, "GUYANE": 0, "REUNION": 8.5, "MAYOTTE": 0,
}


# ============== OPA EVALUATION (Python native) ==============

def evaluate_delivery_policy(zone_code: str, fulfillment_mode: FulfillmentMode, cartons: int = 0) -> dict:
    """Evaluate delivery policy (OPA-style)"""
    errors = []
    zone_upper = zone_code.upper()
    policy = DELIVERY_POLICY.get(zone_upper)
    
    if not policy:
        errors.append("DELIVERY_ZONE_UNKNOWN")
        return {"allow": False, "deny": errors}
    
    if fulfillment_mode == FulfillmentMode.LOGISCOP_DELIVERY:
        if not policy.get("logiscop_delivery_enabled"):
            errors.append("LOGISCOP_DELIVERY_DISABLED_FOR_ZONE")
        
        if cartons > 0:
            min_cartons = policy.get("min_cartons", 1)
            max_cartons = policy.get("max_cartons", 9999)
            if cartons < min_cartons:
                errors.append(f"CARTONS_BELOW_MINIMUM_{min_cartons}")
            if cartons > max_cartons:
                errors.append(f"CARTONS_ABOVE_MAXIMUM_{max_cartons}")
    
    return {"allow": len(errors) == 0, "deny": errors}


def evaluate_order_create(request: OrderCreateRequest) -> dict:
    """Evaluate order create policy (OPA-style)"""
    errors = []
    
    # Check delivery policy if LOGISCOP_DELIVERY
    if request.fulfillment_mode == FulfillmentMode.LOGISCOP_DELIVERY:
        cartons = sum(line.quantity for line in request.goods_lines)
        delivery_check = evaluate_delivery_policy(request.zone_code, request.fulfillment_mode, cartons)
        errors.extend(delivery_check["deny"])
        
        # Require logistics_quote_id
        if not request.logistics_quote_id:
            errors.append("LOGISCOP_QUOTE_ID_REQUIRED")
        
        # Require delivery_address
        if not request.delivery_address or not request.delivery_address.line1:
            errors.append("DELIVERY_ADDRESS_REQUIRED")
    
    # Check EXW_PICKUP requires pickup_location_id
    if request.fulfillment_mode == FulfillmentMode.EXW_PICKUP:
        if not request.pickup_location_id:
            errors.append("PICKUP_LOCATION_REQUIRED")
    
    return {"allow": len(errors) == 0, "deny": errors}


