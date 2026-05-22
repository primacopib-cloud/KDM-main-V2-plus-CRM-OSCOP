"""
KDMARCHE × LOGI'SCOP - V1 API Endpoints
Endpoints OpenAPI v1 pour le workflow LOGI'SCOP (livraison ESS)

Routes:
- POST /v1/b2b/logiscop/quote - Calcul devis livraison LOGI'SCOP
- POST /v1/b2b/checkout/quote - Devis checkout complet (marchandises + transport)
- POST /v1/b2b/orders - Création commande avec mode de livraison
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import math

logger = logging.getLogger(__name__)

# Router with v1 prefix
v1_logiscop_router = APIRouter(prefix="/api/v1/b2b")

# Database reference
db = None


def set_v1_logiscop_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== DELIVERY POLICY DATA ==============
# Configuration des zones pour la politique de livraison LOGI'SCOP

DELIVERY_POLICY = {
    "971": {  # Guadeloupe
        "zone_name": "Guadeloupe",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 1000,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 250,
        "rate_per_kg_cents": 45,
        "rate_per_m3_cents": 8500,
        "vat_rate": 8.5,
        "estimated_days": "3-5"
    },
    "972": {  # Martinique
        "zone_name": "Martinique",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 1000,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 280,
        "rate_per_kg_cents": 50,
        "rate_per_m3_cents": 9000,
        "vat_rate": 8.5,
        "estimated_days": "3-5"
    },
    "973": {  # Guyane
        "zone_name": "Guyane",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 5,  # Minimum pour Guyane
        "max_weight_kg": 500,
        "min_value_cents": 10000,  # Minimum 100€
        "express_enabled": False,
        "base_rate_cents": 450,
        "rate_per_kg_cents": 75,
        "rate_per_m3_cents": 15000,
        "vat_rate": 0,  # Exonéré
        "estimated_days": "5-7"
    },
    "974": {  # La Réunion
        "zone_name": "La Réunion",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 800,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 320,
        "rate_per_kg_cents": 55,
        "rate_per_m3_cents": 11000,
        "vat_rate": 8.5,
        "estimated_days": "4-6"
    },
    "976": {  # Mayotte
        "zone_name": "Mayotte",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 2,
        "max_weight_kg": 300,
        "min_value_cents": 5000,  # Minimum 50€
        "express_enabled": False,
        "base_rate_cents": 380,
        "rate_per_kg_cents": 65,
        "rate_per_m3_cents": 12000,
        "vat_rate": 0,  # Exonéré
        "estimated_days": "5-7"
    },
}

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


# ============== HELPER FUNCTIONS ==============

def calculate_transport_cost(zone_code: str, weight_kg: float, volume_m3: float = 0) -> Dict[str, Any]:
    """Calculate transport cost using weight/volume rule (payant pour)"""
    policy = DELIVERY_POLICY.get(zone_code)
    if not policy:
        return {"error": "ZONE_NOT_FOUND"}
    
    # Weight-based cost
    weight_cost = policy["base_rate_cents"] + int(weight_kg * policy["rate_per_kg_cents"])
    
    # Volume-based cost (if volume provided)
    volume_cost = 0
    if volume_m3 and volume_m3 > 0:
        volume_cost = policy["base_rate_cents"] + int(volume_m3 * policy["rate_per_m3_cents"])
    
    # Apply "payant pour" rule (higher of the two)
    if volume_cost > weight_cost:
        billing_mode = "volume"
        transport_ht_cents = volume_cost
    else:
        billing_mode = "weight"
        transport_ht_cents = weight_cost
    
    return {
        "transport_ht_cents": transport_ht_cents,
        "billing_mode": billing_mode,
        "weight_cost_cents": weight_cost,
        "volume_cost_cents": volume_cost
    }


def calculate_preparation_fees(weight_kg: float, items_count: int) -> Dict[str, Any]:
    """Calculate preparation fees"""
    fees = 0
    lines = []
    
    # Picking per line
    picking_fee = items_count * PREPARATION_FEES["picking_per_line"]
    fees += picking_fee
    lines.append({"code": "PICKING", "label": f"Picking ({items_count} ligne(s))", "cents": picking_fee})
    
    # Packaging based on weight
    if weight_kg <= 5:
        pkg_fee = PREPARATION_FEES["packaging_small"]
        pkg_label = "Emballage colis < 5kg"
    elif weight_kg <= 20:
        pkg_fee = PREPARATION_FEES["packaging_medium"]
        pkg_label = "Emballage colis 5-20kg"
    else:
        pkg_fee = PREPARATION_FEES["packaging_large"]
        pkg_label = "Emballage colis > 20kg"
        
        # Add palletization for heavy shipments
        if weight_kg > 100:
            palettes = math.ceil(weight_kg / 500)
            pallet_fee = palettes * PREPARATION_FEES["palettization"]
            fees += pallet_fee
            lines.append({"code": "PALLET", "label": f"Palettisation ({palettes} palette(s))", "cents": pallet_fee})
    
    fees += pkg_fee
    lines.append({"code": "PACKAGING", "label": pkg_label, "cents": pkg_fee})
    
    # Labeling
    label_fee = items_count * PREPARATION_FEES["labeling"]
    fees += label_fee
    lines.append({"code": "LABELING", "label": f"Étiquetage ({items_count})", "cents": label_fee})
    
    return {
        "total_cents": fees,
        "lines": lines
    }


def evaluate_delivery_policy(zone_code: str, fulfillment_mode: str, request_data: Dict) -> Dict[str, Any]:
    """Evaluate OPA-style delivery policy in Python"""
    policy = DELIVERY_POLICY.get(zone_code)
    deny_reasons = []
    
    if not policy:
        return {"allow": False, "deny": ["ZONE_UNKNOWN"]}
    
    if fulfillment_mode == "DELIVERY":
        # Check if delivery is enabled
        if not policy.get("delivery_enabled", False):
            deny_reasons.append("DELIVERY_NOT_AVAILABLE_FOR_ZONE")
        
        # Check weight limits
        weight_kg = request_data.get("weight_kg", 0)
        if weight_kg < policy.get("min_weight_kg", 0):
            deny_reasons.append("DELIVERY_MIN_WEIGHT_NOT_MET")
        if weight_kg > policy.get("max_weight_kg", 9999):
            deny_reasons.append("DELIVERY_MAX_WEIGHT_EXCEEDED")
        
        # Check minimum value
        min_value = policy.get("min_value_cents", 0)
        if min_value > 0 and request_data.get("goods_value_cents", 0) < min_value:
            deny_reasons.append("DELIVERY_MIN_VALUE_NOT_MET")
        
        # Check delivery address
        address = request_data.get("delivery_address")
        if not address:
            deny_reasons.append("DELIVERY_ADDRESS_REQUIRED")
        elif not address.get("street") or not address.get("city") or not address.get("postal_code"):
            deny_reasons.append("DELIVERY_ADDRESS_INCOMPLETE")
        
        # Check delivery slot
        slot = request_data.get("delivery_slot", "AM").upper()
        if slot == "EXPRESS" and not policy.get("express_enabled", False):
            deny_reasons.append("EXPRESS_DELIVERY_NOT_AVAILABLE")
    
    elif fulfillment_mode == "EXW":
        # Check pickup location
        if policy.get("pickup_required", True) and not request_data.get("pickup_location_id"):
            deny_reasons.append("PICKUP_LOCATION_REQUIRED_FOR_EXW")
    
    return {
        "allow": len(deny_reasons) == 0,
        "deny": deny_reasons
    }


# ============== API ENDPOINTS ==============

# Zone code mapping (text to numeric)
ZONE_CODE_MAPPING = {
    "GUADELOUPE": "971",
    "MARTINIQUE": "972",
    "GUYANE": "973",
    "REUNION": "974",
    "MAYOTTE": "976"
}

# Reverse mapping (numeric to text)
ZONE_CODE_REVERSE = {v: k for k, v in ZONE_CODE_MAPPING.items()}


@v1_logiscop_router.post("/logiscop/quote", response_model=LogiscopQuoteResponse, tags=["LOGISCOP"])
async def create_logiscop_quote(request: LogiscopQuoteRequest):
    """
    POST /v1/b2b/logiscop/quote
    
    Calcule un devis de livraison LOGI'SCOP (transport uniquement).
    Supporte deux modes de livraison:
    - DIRECT: Livraison classique à la demande
    - ESS_ROUTE: Livraison par tournée mutualisée ESS
    
    OPA check: kdm.delivery.quote
    
    Response: Devis détaillé avec lignes, TVA et totaux.
    """
    raw_zone_code = request.zone_code.upper()
    
    # Convert text zone codes to numeric
    zone_code_numeric = ZONE_CODE_MAPPING.get(raw_zone_code, raw_zone_code)
    zone_code_text = ZONE_CODE_REVERSE.get(raw_zone_code, raw_zone_code)
    
    # If we got a text code, use it as-is for ESS; otherwise convert
    if raw_zone_code in ZONE_CODE_MAPPING:
        zone_code_text = raw_zone_code
        zone_code_numeric = ZONE_CODE_MAPPING[raw_zone_code]
    elif raw_zone_code in ZONE_CODE_REVERSE:
        zone_code_text = ZONE_CODE_REVERSE[raw_zone_code]
        zone_code_numeric = raw_zone_code
    else:
        zone_code_text = raw_zone_code
        zone_code_numeric = raw_zone_code
    
    delivery_mode = request.delivery_mode.upper() if request.delivery_mode else "DIRECT"
    fulfillment_mode = request.fulfillment_mode.upper() if request.fulfillment_mode else "LOGISCOP_DELIVERY"
    
    policy = DELIVERY_POLICY.get(zone_code_numeric)
    
    if not policy:
        raise HTTPException(
            status_code=400,
            detail={"error": "ZONE_NOT_FOUND", "message": f"Zone {raw_zone_code} non couverte par LOGI'SCOP"}
        )
    
    # For ESS_ROUTE mode, delegate to ESS router logic (uses text zone code)
    if delivery_mode == "ESS_ROUTE":
        return await _create_ess_route_quote(request, zone_code_text, policy)
    
    # DIRECT mode - standard delivery calculation
    transport = calculate_transport_cost(zone_code_numeric, request.weight_kg, request.volume_m3)
    
    # Calculate preparation fees
    prep = calculate_preparation_fees(request.weight_kg, request.items_count)
    
    # Slot supplement
    slot = request.delivery_slot.upper()
    slot_info = SLOT_SUPPLEMENTS.get(slot, SLOT_SUPPLEMENTS["AM"])
    slot_supplement = slot_info["cents"]
    
    # Build lines
    lines = []
    breakdown = []
    
    # Transport line
    lines.append(LogiscopQuoteLineItem(
        code="TRANSPORT",
        label=f"Transport {policy['zone_name']} ({transport['billing_mode']})",
        amount_ht_cents=transport["transport_ht_cents"],
        quantity=1
    ))
    breakdown.append({"label": f"Transport {policy['zone_name']}", "amount_ht": transport["transport_ht_cents"] / 100})
    
    # Preparation lines
    for prep_line in prep["lines"]:
        lines.append(LogiscopQuoteLineItem(
            code=prep_line["code"],
            label=prep_line["label"],
            amount_ht_cents=prep_line["cents"],
            quantity=1
        ))
        breakdown.append({"label": prep_line["label"], "amount_ht": prep_line["cents"] / 100})
    
    # Slot supplement (if any)
    if slot_supplement > 0:
        lines.append(LogiscopQuoteLineItem(
            code="SLOT_SUPPLEMENT",
            label=f"Supplément créneau: {slot_info['label']}",
            amount_ht_cents=slot_supplement,
            quantity=1
        ))
        breakdown.append({"label": f"Supplément {slot_info['label']}", "amount_ht": slot_supplement / 100})
    
    # Calculate totals
    subtotal_ht_cents = sum(line.amount_ht_cents for line in lines)
    vat_rate = policy["vat_rate"]
    vat_cents = int(subtotal_ht_cents * vat_rate / 100) if vat_rate > 0 else 0
    total_ttc_cents = subtotal_ht_cents + vat_cents
    
    # Generate quote ID and validity
    quote_id = f"LQ-{zone_code_numeric}-{uuid.uuid4().hex[:8].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    # Estimated delivery
    if request.delivery_type == "express" and policy.get("express_enabled"):
        estimated_delivery = "Sous 24-48h"
    else:
        estimated_delivery = f"{policy['estimated_days']} jours ouvrés"
    
    return LogiscopQuoteResponse(
        zone_code=zone_code_numeric,
        zone_name=policy["zone_name"],
        fulfillment_mode=fulfillment_mode,
        delivery_mode="DIRECT",
        weight_kg=request.weight_kg,
        volume_m3=request.volume_m3,
        billing_mode=transport["billing_mode"],
        lines=lines,
        subtotal_ht_cents=subtotal_ht_cents,
        transport_total_ht=subtotal_ht_cents / 100,
        vat_rate=vat_rate,
        vat_cents=vat_cents,
        vat_amount=vat_cents / 100,
        total_ttc_cents=total_ttc_cents,
        transport_total_ttc=total_ttc_cents / 100,
        slot=slot,
        slot_label=slot_info["label"],
        estimated_delivery=estimated_delivery,
        route=None,
        breakdown=breakdown,
        quote_id=quote_id,
        valid_until=valid_until,
        expires_at=valid_until,
        currency="EUR"
    )


async def _create_ess_route_quote(request: LogiscopQuoteRequest, zone_code: str, policy: dict) -> LogiscopQuoteResponse:
    """
    Create quote for ESS_ROUTE (Tournées Mutualisées) delivery mode.
    """
    from routes_ess import ESS_ROUTE_TARIFFS, get_route_policy, evaluate_ess_route_policy
    
    # Get ESS Route policy
    ess_policy = await get_route_policy(zone_code)
    
    if not ess_policy or not ess_policy.get("ess_route_enabled", False):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ESS_ROUTE_DISABLED_FOR_ZONE",
                "deny": ["ESS_ROUTE_DISABLED_FOR_ZONE"],
                "message": f"Les tournées ESS ne sont pas disponibles pour la zone {zone_code}"
            }
        )
    
    # Check policy
    policy_result = await evaluate_ess_route_policy(zone_code, {
        "delivery_window": request.delivery_window,
        "tour_id": request.tour_id
    })
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ESS_ROUTE_POLICY_DENIED",
                "deny": policy_result["deny"],
                "message": "Le mode Tournées ESS n'est pas autorisé pour cette configuration"
            }
        )
    
    # Get ESS tariffs
    ess_tariff = ESS_ROUTE_TARIFFS.get(zone_code, {})
    if not ess_tariff:
        raise HTTPException(status_code=400, detail={"error": "ESS_ROUTE_TARIFF_NOT_FOUND"})
    
    # Calculate ESS Route cost (mutualized pricing)
    cartons = request.cartons or request.items_count or 1
    
    # Weight-based or carton-based (whichever is higher)
    weight_cost = ess_tariff["base_rate_cents"] + int(request.weight_kg * ess_tariff["rate_per_kg_cents"])
    carton_cost = ess_tariff["base_rate_cents"] + int(cartons * ess_tariff["rate_per_carton_cents"])
    
    if carton_cost > weight_cost:
        billing_mode = "cartons"
        transport_ht_cents = carton_cost
    else:
        billing_mode = "weight"
        transport_ht_cents = weight_cost
    
    # Build lines
    lines = []
    breakdown = []
    
    lines.append(LogiscopQuoteLineItem(
        code="ESS_TRANSPORT",
        label=f"Transport Tournée ESS {policy['zone_name']} ({billing_mode})",
        amount_ht_cents=transport_ht_cents,
        quantity=1
    ))
    breakdown.append({"label": f"Transport ESS {policy['zone_name']}", "amount_ht": transport_ht_cents / 100})
    
    # Calculate totals
    subtotal_ht_cents = transport_ht_cents
    vat_rate = ess_tariff.get("vat_rate", policy.get("vat_rate", 8.5))
    vat_cents = int(subtotal_ht_cents * vat_rate / 100) if vat_rate > 0 else 0
    total_ttc_cents = subtotal_ht_cents + vat_cents
    
    # Generate quote ID
    quote_id = f"ESS-{zone_code[:2]}-{uuid.uuid4().hex[:8].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    
    # Route reference
    route = {
        "tour_id": request.tour_id,
        "route_window": request.delivery_window,
        "priority_reason_code": policy_result.get("priority_reason_code")
    }
    
    # Slot info (use delivery window if provided)
    slot = "ESS"
    slot_label = "Tournée ESS Mutualisée"
    if request.delivery_window:
        slot_label = f"Tournée ESS ({request.delivery_window.get('start', '08:00')}-{request.delivery_window.get('end', '12:00')})"
    
    return LogiscopQuoteResponse(
        zone_code=zone_code,
        zone_name=policy["zone_name"],
        fulfillment_mode=request.fulfillment_mode or "LOGISCOP_DELIVERY",
        delivery_mode="ESS_ROUTE",
        weight_kg=request.weight_kg,
        volume_m3=request.volume_m3,
        billing_mode=billing_mode,
        lines=lines,
        subtotal_ht_cents=subtotal_ht_cents,
        transport_total_ht=subtotal_ht_cents / 100,
        vat_rate=vat_rate,
        vat_cents=vat_cents,
        vat_amount=vat_cents / 100,
        total_ttc_cents=total_ttc_cents,
        transport_total_ttc=total_ttc_cents / 100,
        slot=slot,
        slot_label=slot_label,
        estimated_delivery=f"{ess_tariff.get('estimated_days', '2-4')} jours ouvrés",
        route=route,
        breakdown=breakdown,
        quote_id=quote_id,
        valid_until=valid_until,
        expires_at=valid_until,
        currency="EUR"
    )


@v1_logiscop_router.post("/checkout/quote-full", response_model=CheckoutQuoteResponse, tags=["Checkout"])
async def create_checkout_quote(request: CheckoutQuoteRequest):
    """
    POST /v1/b2b/checkout/quote
    
    Calcule un devis checkout complet avec séparation KDMARCHE / LOGI'SCOP.
    
    - Mode EXW: Uniquement les montants KDMARCHE (marchandises + préparation)
    - Mode DELIVERY: KDMARCHE (marchandises) + LOGI'SCOP (transport)
    
    Response: Devis détaillé avec totaux par entité et grand total.
    """
    zone_code = request.zone_code.upper() if request.zone_code.isalpha() else request.zone_code
    fulfillment_mode = request.fulfillment_mode.upper()
    
    # Get zone policy
    policy = DELIVERY_POLICY.get(zone_code)
    if not policy:
        raise HTTPException(
            status_code=400,
            detail={"error": "ZONE_NOT_FOUND", "message": f"Zone {zone_code} inconnue"}
        )
    
    # Evaluate OPA policy
    policy_result = evaluate_delivery_policy(zone_code, fulfillment_mode, {
        "weight_kg": request.weight_kg,
        "goods_value_cents": request.goods_subtotal_ht_cents,
        "delivery_address": request.delivery_address.model_dump() if request.delivery_address else None,
        "delivery_slot": request.delivery_slot,
        "pickup_location_id": request.pickup_location_id
    })
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "POLICY_DENIED",
                "deny_reasons": policy_result["deny"],
                "message": "La politique de livraison n'est pas respectée"
            }
        )
    
    lines = []
    kdmarche_total_ht = 0
    logiscop_total_ht = 0
    
    # KDMARCHE: Goods
    lines.append(CheckoutQuoteLine(
        entity="KDMARCHE",
        category="goods",
        label="Marchandises B2B",
        amount_ht_cents=request.goods_subtotal_ht_cents
    ))
    kdmarche_total_ht += request.goods_subtotal_ht_cents
    
    # KDMARCHE: Preparation options (if any)
    for opt in request.prep_options:
        opt_amount = opt.get("total_ht_cents", 0)
        if opt_amount > 0:
            lines.append(CheckoutQuoteLine(
                entity="KDMARCHE",
                category="preparation",
                label=opt.get("label", opt.get("code", "Préparation")),
                amount_ht_cents=opt_amount
            ))
            kdmarche_total_ht += opt_amount
    
    # LOGI'SCOP: Transport (only if DELIVERY mode)
    if fulfillment_mode == "DELIVERY":
        transport = calculate_transport_cost(zone_code, request.weight_kg, request.volume_m3)
        prep = calculate_preparation_fees(request.weight_kg, request.goods_items_count)
        
        # Transport line
        lines.append(CheckoutQuoteLine(
            entity="LOGI'SCOP",
            category="transport",
            label=f"Transport {policy['zone_name']}",
            amount_ht_cents=transport["transport_ht_cents"]
        ))
        logiscop_total_ht += transport["transport_ht_cents"]
        
        # Preparation lines
        for prep_line in prep["lines"]:
            lines.append(CheckoutQuoteLine(
                entity="LOGI'SCOP",
                category="preparation",
                label=prep_line["label"],
                amount_ht_cents=prep_line["cents"]
            ))
            logiscop_total_ht += prep_line["cents"]
        
        # Slot supplement
        slot = request.delivery_slot.upper()
        slot_info = SLOT_SUPPLEMENTS.get(slot, SLOT_SUPPLEMENTS["AM"])
        if slot_info["cents"] > 0:
            lines.append(CheckoutQuoteLine(
                entity="LOGI'SCOP",
                category="slot_supplement",
                label=f"Supplément: {slot_info['label']}",
                amount_ht_cents=slot_info["cents"]
            ))
            logiscop_total_ht += slot_info["cents"]
    
    # Calculate VAT
    kdmarche_vat_rate = policy["vat_rate"]
    logiscop_vat_rate = policy["vat_rate"]
    
    kdmarche_vat = int(kdmarche_total_ht * kdmarche_vat_rate / 100) if kdmarche_vat_rate > 0 else 0
    logiscop_vat = int(logiscop_total_ht * logiscop_vat_rate / 100) if logiscop_vat_rate > 0 else 0
    
    kdmarche_ttc = kdmarche_total_ht + kdmarche_vat
    logiscop_ttc = logiscop_total_ht + logiscop_vat
    
    # Grand totals
    grand_total_ht = kdmarche_total_ht + logiscop_total_ht
    grand_total_ttc = kdmarche_ttc + logiscop_ttc
    
    # Generate quote
    quote_id = f"CQ-{zone_code}-{uuid.uuid4().hex[:8].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    return CheckoutQuoteResponse(
        zone_code=zone_code,
        zone_name=policy["zone_name"],
        fulfillment_mode=fulfillment_mode,
        lines=lines,
        kdmarche_subtotal_ht_cents=kdmarche_total_ht,
        kdmarche_vat_rate=kdmarche_vat_rate,
        kdmarche_vat_cents=kdmarche_vat,
        kdmarche_total_ttc_cents=kdmarche_ttc,
        logiscop_subtotal_ht_cents=logiscop_total_ht,
        logiscop_vat_rate=logiscop_vat_rate,
        logiscop_vat_cents=logiscop_vat,
        logiscop_total_ttc_cents=logiscop_ttc,
        grand_total_ht_cents=grand_total_ht,
        grand_total_ttc_cents=grand_total_ttc,
        quote_id=quote_id,
        valid_until=valid_until
    )


@v1_logiscop_router.post("/orders", response_model=OrderV1Response, tags=["Orders"])
async def create_order_v1(request: CreateOrderV1Request):
    """
    POST /v1/b2b/orders
    
    Crée une commande B2B avec le mode de livraison sélectionné.
    
    - Valide la politique de livraison via OPA
    - Calcule les totaux (KDMARCHE + LOGI'SCOP si DELIVERY)
    - Crée l'ordre dans la DB
    
    Response: Détails de la commande créée
    """
    zone_code = request.zone_code.upper() if request.zone_code.isalpha() else request.zone_code
    fulfillment_mode = request.delivery.fulfillment_mode.upper()
    
    # Get cart
    cart = await db.carts.find_one({"id": request.cart_id}, {"_id": 0})
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    
    if cart.get("status") != "active":
        raise HTTPException(status_code=400, detail="Ce panier n'est plus actif")
    
    # Get zone policy
    policy = DELIVERY_POLICY.get(zone_code)
    if not policy:
        raise HTTPException(status_code=400, detail=f"Zone {zone_code} inconnue")
    
    # Calculate weights
    total_weight = sum(item.get("weight_kg", 0) * item.get("quantity", 1) for item in cart.get("items", []))
    total_volume = sum(item.get("volume_m3", 0) * item.get("quantity", 1) for item in cart.get("items", []))
    
    # Evaluate OPA policy
    policy_result = evaluate_delivery_policy(zone_code, fulfillment_mode, {
        "weight_kg": total_weight,
        "goods_value_cents": cart.get("subtotal_ht_cents", 0),
        "delivery_address": request.delivery.delivery_address.model_dump() if request.delivery.delivery_address else None,
        "delivery_slot": request.delivery.delivery_slot,
        "pickup_location_id": request.delivery.pickup_location_id
    })
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "POLICY_DENIED",
                "deny_reasons": policy_result["deny"],
                "message": "La politique de livraison n'est pas respectée"
            }
        )
    
    # Calculate totals
    goods_ht = cart.get("subtotal_ht_cents", 0)
    
    # Prep fees from cart options
    prep_fees_ht = sum(opt.get("total_ht_cents", 0) for opt in request.prep_options)
    
    # Transport (if DELIVERY)
    transport_ht = 0
    logiscop_prep_ht = 0
    if fulfillment_mode == "DELIVERY":
        transport = calculate_transport_cost(zone_code, total_weight, total_volume)
        transport_ht = transport["transport_ht_cents"]
        
        prep = calculate_preparation_fees(total_weight, len(cart.get("items", [])))
        logiscop_prep_ht = prep["total_cents"]
        
        # Add slot supplement
        slot = (request.delivery.delivery_slot or "AM").upper()
        slot_info = SLOT_SUPPLEMENTS.get(slot, SLOT_SUPPLEMENTS["AM"])
        transport_ht += slot_info["cents"]
    
    # Total transport includes prep
    total_transport_ht = transport_ht + logiscop_prep_ht
    
    # VAT
    vat_rate = policy["vat_rate"]
    kdmarche_vat = int((goods_ht + prep_fees_ht) * vat_rate / 100) if vat_rate > 0 else 0
    logiscop_vat = int(total_transport_ht * vat_rate / 100) if vat_rate > 0 else 0
    total_vat = kdmarche_vat + logiscop_vat
    
    # Total TTC
    total_ttc = goods_ht + prep_fees_ht + total_transport_ht + total_vat
    
    # Generate order number
    order_count = await db.orders.count_documents({}) + 1
    order_number = f"KDM-{datetime.now().strftime('%Y%m')}-{order_count:05d}"
    
    # Create order document
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    order_doc = {
        "id": order_id,
        "order_number": order_number,
        "cart_id": request.cart_id,
        "zone_code": zone_code,
        "status": "pending_payment",
        
        # Delivery info
        "fulfillment_mode": fulfillment_mode,
        "pickup_location_id": request.delivery.pickup_location_id,
        "delivery_address": request.delivery.delivery_address.model_dump() if request.delivery.delivery_address else None,
        "delivery_slot": request.delivery.delivery_slot,
        "logistics_quote_id": request.delivery.logistics_quote_id,
        
        # Items from cart
        "items": cart.get("items", []),
        
        # Preparation options
        "prep_options": request.prep_options,
        
        # Amounts
        "goods_total_ht_cents": goods_ht,
        "prep_fees_ht_cents": prep_fees_ht,
        "transport_ht_cents": total_transport_ht,
        "vat_cents": total_vat,
        "total_ttc_cents": total_ttc,
        
        # Payment
        "use_installment": request.use_installment,
        "payment_method": request.payment_method,
        
        # Notes
        "notes": request.notes,
        
        # Signature
        "signature_id": request.signature_id,
        
        # Metadata
        "created_at": now,
        "updated_at": now
    }
    
    # Insert order
    await db.orders.insert_one(order_doc)
    
    # Update cart status
    await db.carts.update_one(
        {"id": request.cart_id},
        {"$set": {"status": "ordered", "order_id": order_id, "updated_at": now}}
    )
    
    # Estimated delivery
    if fulfillment_mode == "DELIVERY":
        estimated_delivery = f"{policy['estimated_days']} jours ouvrés"
    else:
        estimated_delivery = "Retrait disponible sous 24-48h"
    
    logger.info(f"Order created: {order_number} ({fulfillment_mode}) - Total: {total_ttc/100:.2f}€")
    
    return OrderV1Response(
        id=order_id,
        order_number=order_number,
        status="pending_payment",
        goods_total_ht_cents=goods_ht,
        prep_fees_ht_cents=prep_fees_ht,
        transport_ht_cents=total_transport_ht,
        vat_cents=total_vat,
        total_ttc_cents=total_ttc,
        fulfillment_mode=fulfillment_mode,
        pickup_location_id=request.delivery.pickup_location_id,
        delivery_address=request.delivery.delivery_address.model_dump() if request.delivery.delivery_address else None,
        created_at=now.isoformat(),
        estimated_delivery=estimated_delivery
    )


@v1_logiscop_router.get("/delivery-policy", tags=["LOGISCOP"])
async def get_delivery_policy():
    """
    GET /v1/b2b/delivery-policy
    
    Retourne la configuration de la politique de livraison pour OPA.
    Utilisé pour générer le bundle OPA data.json.
    """
    return {
        "delivery_policy": DELIVERY_POLICY,
        "slot_supplements": SLOT_SUPPLEMENTS,
        "preparation_fees": PREPARATION_FEES,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
