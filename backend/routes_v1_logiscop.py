"""
KDMARCHE × LOGI'SCOP - V1 API Endpoints
Endpoints OpenAPI v1 pour le workflow LOGI'SCOP (livraison ESS)

Découpé en modules : logiscop_v1_models, logiscop_v1_pricing, routes_v1_logiscop_orders.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import math

from routes_logistics_shared import DELIVERY_POLICY
from logiscop_v1_models import (
    PREPARATION_FEES, SLOT_SUPPLEMENTS,
    DeliveryAddress, LogiscopQuoteRequest, LogiscopQuoteLineItem, LogiscopQuoteResponse,
    CheckoutQuoteResponse,
)
from logiscop_v1_pricing import (
    calculate_transport_cost, calculate_preparation_fees, evaluate_delivery_policy,
)
from routes_v1_logiscop_orders import set_v1_logiscop_orders_database

logger = logging.getLogger(__name__)

# Router with v1 prefix
v1_logiscop_router = APIRouter(prefix="/api/v1/b2b")

db = None

def set_v1_logiscop_database(database):
    global db
    db = database
    set_v1_logiscop_orders_database(database)

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


