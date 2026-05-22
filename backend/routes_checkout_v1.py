"""
KDMARCHE × LOGI'SCOP - Checkout B2B API V1
Endpoints OpenAPI conformes avec support fulfillment EXW/LOGISCOP_DELIVERY
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

# Router
checkout_v1_router = APIRouter(prefix="/api/v1/b2b", tags=["CheckoutB2B"])

# Database reference
db = None

def set_checkout_v1_database(database):
    global db
    db = database


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


# ============== ENDPOINTS ==============

@checkout_v1_router.post("/logiscop/quote", response_model=LogiScopQuoteResponse)
async def create_logiscop_quote(request: LogiScopQuoteRequest):
    """
    POST /v1/b2b/logiscop/quote
    Calcule un devis transport LOGI'SCOP (option livraison)
    Contrôle OPA: kdm.delivery.quote
    """
    # OPA check
    policy_result = evaluate_delivery_policy(
        request.zone_code, 
        request.fulfillment_mode,
        request.goods_metrics.cartons if request.goods_metrics else 0
    )
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "OPA_DENY",
                "violations": policy_result["deny"],
                "message": f"Livraison LOGI'SCOP non autorisée: {', '.join(policy_result['deny'])}"
            }
        )
    
    # If EXW_PICKUP, return zero cost quote
    if request.fulfillment_mode == FulfillmentMode.EXW_PICKUP:
        return LogiScopQuoteResponse(
            zone_code=request.zone_code,
            fulfillment_mode=request.fulfillment_mode,
            transport_total_ht=0,
            vat_rate=0,
            vat_amount=0,
            transport_total_ttc=0,
            quote_id=f"QUOTE-EXW-{uuid.uuid4().hex[:8].upper()}",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            breakdown=[]
        )
    
    # Calculate transport costs
    zone_upper = request.zone_code.upper()
    rates = TRANSPORT_RATES.get(zone_upper, TRANSPORT_RATES.get("971"))
    vat_rate = ZONE_TVA_RATES.get(zone_upper, 8.5)
    
    breakdown = []
    total_ht_cents = rates["base_ht"]
    breakdown.append(QuoteBreakdownItem(label="Base transport", amount_ht=rates["base_ht"] / 100))
    
    if request.goods_metrics:
        if request.goods_metrics.total_weight_kg:
            weight_cost = int(request.goods_metrics.total_weight_kg * rates["per_kg_ht"])
            total_ht_cents += weight_cost
            breakdown.append(QuoteBreakdownItem(
                label=f"Transport poids ({request.goods_metrics.total_weight_kg}kg)",
                amount_ht=weight_cost / 100
            ))
        
        if request.goods_metrics.total_volume_m3:
            volume_cost = int(request.goods_metrics.total_volume_m3 * rates["per_m3_ht"])
            # Règle du payant pour: prend le max
            if volume_cost > (total_ht_cents - rates["base_ht"]):
                # Replace weight with volume
                total_ht_cents = rates["base_ht"] + volume_cost
                breakdown = [
                    QuoteBreakdownItem(label="Base transport", amount_ht=rates["base_ht"] / 100),
                    QuoteBreakdownItem(
                        label=f"Transport volume ({request.goods_metrics.total_volume_m3}m³)",
                        amount_ht=volume_cost / 100
                    )
                ]
    
    total_ht = total_ht_cents / 100
    vat_amount = round(total_ht * vat_rate / 100, 2)
    total_ttc = total_ht + vat_amount
    
    quote_id = f"QUOTE-LOGI-{uuid.uuid4().hex[:8].upper()}"
    
    # Store quote in DB
    if db is not None:
        await db.logistics_quotes.insert_one({
            "quote_id": quote_id,
            "zone_code": request.zone_code,
            "fulfillment_mode": request.fulfillment_mode.value,
            "goods_metrics": request.goods_metrics.dict() if request.goods_metrics else None,
            "transport_total_ht": total_ht,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "transport_total_ttc": total_ttc,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return LogiScopQuoteResponse(
        zone_code=request.zone_code,
        fulfillment_mode=request.fulfillment_mode,
        transport_total_ht=total_ht,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        transport_total_ttc=total_ttc,
        quote_id=quote_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        breakdown=breakdown
    )


@checkout_v1_router.post("/checkout/quote", response_model=CheckoutQuoteResponse)
async def create_checkout_quote(request: CheckoutQuoteRequest):
    """
    POST /v1/b2b/checkout/quote
    Calcule HT/TVA/TTC avec fulfillment (marchandises + préparation + transport optionnel)
    Contrôles OPA: kdm.prep_options.apply + kdm.delivery.quote (si livraison)
    """
    zone_upper = request.zone_code.upper()
    vat_rate = ZONE_TVA_RATES.get(zone_upper, 8.5)
    
    # Calculate goods + fees
    goods_ht = request.goods_subtotal_ht
    fees_ht = request.fees_subtotal_ht or 0
    
    # Add prep lines
    for prep in (request.prep_lines or []):
        fees_ht += prep.total_ht
    
    # Transport costs
    transport_ht = 0
    transport_ttc = 0
    
    if request.fulfillment_mode == FulfillmentMode.LOGISCOP_DELIVERY:
        if request.logistics_quote_id and db is not None:
            # Fetch quote from DB
            quote = await db.logistics_quotes.find_one({"quote_id": request.logistics_quote_id})
            if quote:
                transport_ht = quote.get("transport_total_ht", 0)
                transport_ttc = quote.get("transport_total_ttc", 0)
    
    # Totals (excluding transport - billed separately by LOGI'SCOP)
    total_ht = goods_ht + fees_ht
    vat_amount = round(total_ht * vat_rate / 100, 2)
    total_ttc = total_ht + vat_amount
    
    return CheckoutQuoteResponse(
        zone_code=request.zone_code,
        vat_rate=vat_rate,
        goods_subtotal_ht=goods_ht,
        fees_subtotal_ht=fees_ht,
        total_ht=total_ht,
        vat_amount=vat_amount,
        total_ttc=total_ttc,
        fulfillment=FulfillmentInfo(
            mode=request.fulfillment_mode,
            pickup_location_id=request.pickup_location_id,
            delivery_address=request.delivery_address,
            delivery_window=request.delivery_window,
            transport_total_ht=transport_ht if transport_ht > 0 else None,
            transport_total_ttc=transport_ttc if transport_ttc > 0 else None,
            logistics_quote_id=request.logistics_quote_id
        )
    )


@checkout_v1_router.post("/orders", response_model=OrderCreateResponse)
async def create_order(request: OrderCreateRequest):
    """
    POST /v1/b2b/orders
    Crée une commande B2B avec fulfillment EXW ou LOGISCOP_DELIVERY
    Contrôles OPA: kdm.order.create (incoterm + prep + delivery)
    """
    # OPA evaluation
    policy_result = evaluate_order_create(request)
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "OPA_DENY",
                "violations": policy_result["deny"],
                "message": f"Création commande refusée: {', '.join(policy_result['deny'])}"
            }
        )
    
    # Idempotency check
    if request.idempotency_key and db is not None:
        existing = await db.orders_v1.find_one({"idempotency_key": request.idempotency_key})
        if existing:
            return OrderCreateResponse(
                order_id=existing["order_id"],
                order_number=existing["order_number"],
                status=existing["status"],
                incoterm=existing["incoterm"],
                fulfillment_mode=FulfillmentMode(existing["fulfillment_mode"]),
                zone_code=existing["zone_code"],
                total_ttc=existing["total_ttc"],
                created_at=datetime.fromisoformat(existing["created_at"]),
                pickup_location_id=existing.get("pickup_location_id"),
                delivery_address=DeliveryAddress(**existing["delivery_address"]) if existing.get("delivery_address") else None,
                logistics_quote_id=existing.get("logistics_quote_id")
            )
    
    # Generate IDs
    order_id = str(uuid.uuid4())
    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Create order document
    order = {
        "order_id": order_id,
        "order_number": order_number,
        "idempotency_key": request.idempotency_key,
        "status": "PENDING",
        "zone_code": request.zone_code,
        "incoterm": request.incoterm,
        "fulfillment_mode": request.fulfillment_mode.value,
        
        "pickup_location_id": request.pickup_location_id,
        "delivery_address": request.delivery_address.dict() if request.delivery_address else None,
        "delivery_window": {
            "start": request.delivery_window.start.isoformat(),
            "end": request.delivery_window.end.isoformat()
        } if request.delivery_window else None,
        "logistics_quote_id": request.logistics_quote_id,
        
        "goods_lines": [line.dict() for line in request.goods_lines],
        "prep_selections": [prep.dict() for prep in (request.prep_selections or [])],
        
        "currency": request.totals_currency,
        "goods_subtotal_ht": request.goods_subtotal_ht,
        "fees_subtotal_ht": request.fees_subtotal_ht,
        "total_ht": request.total_ht,
        "vat_rate": request.vat_rate,
        "vat_amount": request.vat_amount,
        "total_ttc": request.total_ttc,
        
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.orders_v1.insert_one(order)
    
    logger.info(f"Order created: {order_number}, mode={request.fulfillment_mode.value}, zone={request.zone_code}")
    
    return OrderCreateResponse(
        order_id=order_id,
        order_number=order_number,
        status="PENDING",
        incoterm=request.incoterm,
        fulfillment_mode=request.fulfillment_mode,
        zone_code=request.zone_code,
        total_ttc=request.total_ttc,
        created_at=datetime.now(timezone.utc),
        pickup_location_id=request.pickup_location_id,
        delivery_address=request.delivery_address,
        logistics_quote_id=request.logistics_quote_id
    )


@checkout_v1_router.get("/delivery-policy")
async def get_delivery_policy():
    """Get delivery policy data (for OPA bundle)"""
    return {
        "delivery_policy": {
            k: v for k, v in DELIVERY_POLICY.items() 
            if k in ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "MAYOTTE"]
        }
    }


@checkout_v1_router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order by ID"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    order = await db.orders_v1.find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Remove MongoDB _id
    order.pop("_id", None)
    return order
