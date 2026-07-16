"""KDMARCHE × LOGI'SCOP V1 — Checkout quote & orders endpoints (split from routes_v1_logiscop.py)."""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import math

from routes_logistics_shared import DELIVERY_POLICY
from logiscop_v1_models import (
    PREPARATION_FEES, SLOT_SUPPLEMENTS,
    DeliveryAddress, CheckoutQuoteRequest, CheckoutQuoteLine, CheckoutQuoteResponse,
    OrderDeliveryInfo, CreateOrderV1Request, OrderV1Response,
)
from logiscop_v1_pricing import (
    calculate_transport_cost, calculate_preparation_fees, evaluate_delivery_policy,
)

logger = logging.getLogger(__name__)

v1_logiscop_orders_router = APIRouter(prefix="/api/v1/b2b")

db = None

def set_v1_logiscop_orders_database(database):
    global db
    db = database

@v1_logiscop_orders_router.post("/checkout/quote-full", response_model=CheckoutQuoteResponse, tags=["Checkout"])
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


@v1_logiscop_orders_router.post("/orders", response_model=OrderV1Response, tags=["Orders"])
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


@v1_logiscop_orders_router.get("/delivery-policy", tags=["LOGISCOP"])
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
