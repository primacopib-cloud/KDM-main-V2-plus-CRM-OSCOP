"""
KDMARCHE ESS Route — API endpoints (quote, tours, booking, annexe).

Découpé : données & helpers dans ess_models.py.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import os
import secrets
from pathlib import Path

from routes_logistics_shared import (
    DEFAULT_ROUTE_POLICY,
    ESS_ROUTE_TARIFFS,
    DELIVERY_POLICY,
)
from ess_models import (
    DeliveryWindow, DeliveryAddress, ESSRouteQuoteRequest, ESSRouteQuoteLineItem,
    RouteReference, ESSRouteQuoteResponse, TourInfo, TourListResponse,
    BookTourRequest, BookTourResponse,
    get_route_policy, get_zone_name, calculate_ess_route_cost, calculate_standard_cost,
    evaluate_ess_route_policy, generate_tour_id,
    set_ess_models_database,
)

logger = logging.getLogger(__name__)

ess_router = APIRouter(prefix="/api/ess", tags=["ESS Route"])

db = None

def set_ess_database(database):
    global db
    db = database
    set_ess_models_database(database)

# ============== API ENDPOINTS ==============

@ess_router.post("/quote", response_model=ESSRouteQuoteResponse)
async def create_ess_route_quote(request: ESSRouteQuoteRequest):
    """
    POST /api/ess/quote
    
    Get a quote for ESS Route (Tournées Mutualisées) delivery.
    Returns pricing with ESS benefits and savings vs standard delivery.
    """
    zone_code = request.zone_code.upper()
    
    # Check policy
    policy_result = await evaluate_ess_route_policy(zone_code, {
        "delivery_window": request.delivery_window.model_dump() if request.delivery_window else None,
        "tour_id": request.tour_id
    })
    
    if not policy_result["allow"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ESS_ROUTE_POLICY_DENIED",
                "deny_reasons": policy_result["deny"],
                "message": "Le mode Tournées ESS n'est pas disponible pour cette configuration"
            }
        )
    
    # Calculate costs
    cost = calculate_ess_route_cost(zone_code, request.weight_kg, request.cartons)
    if "error" in cost:
        raise HTTPException(status_code=400, detail={"error": cost["error"]})
    
    # Build line items
    lines = []
    
    # Base transport
    lines.append(ESSRouteQuoteLineItem(
        code="ESS_TRANSPORT",
        label=f"Transport Tournée ESS {get_zone_name(zone_code)} ({cost['billing_mode']})",
        amount_ht_cents=cost["transport_ht_cents"],
        quantity=1
    ))
    
    # Calculate totals
    subtotal_ht = sum(line.amount_ht_cents for line in lines)
    vat_rate = cost["vat_rate"]
    vat_cents = int(subtotal_ht * vat_rate / 100) if vat_rate > 0 else 0
    total_ttc = subtotal_ht + vat_cents
    
    # Calculate savings vs standard
    standard_cost = calculate_standard_cost(zone_code, request.weight_kg)
    savings = max(0, standard_cost - subtotal_ht)
    
    # Generate quote ID
    quote_id = f"ESS-{zone_code[:2]}-{uuid.uuid4().hex[:8].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    
    # Route reference
    route = RouteReference(
        tour_id=request.tour_id,
        route_window=request.delivery_window,
        priority_reason_code=policy_result.get("priority_reason_code")
    )
    
    return ESSRouteQuoteResponse(
        zone_code=zone_code,
        zone_name=get_zone_name(zone_code),
        delivery_mode="ESS_ROUTE",
        weight_kg=request.weight_kg,
        cartons=request.cartons,
        lines=lines,
        subtotal_ht_cents=subtotal_ht,
        vat_rate=vat_rate,
        vat_cents=vat_cents,
        total_ttc_cents=total_ttc,
        route=route,
        estimated_delivery=f"{cost['estimated_days']} jours ouvrés",
        quote_id=quote_id,
        valid_until=valid_until,
        savings_vs_standard_cents=savings,
        eco_benefit="Réduction empreinte carbone via mutualisation"
    )


@ess_router.get("/tours", response_model=TourListResponse)
async def list_available_tours(zone_code: str, days_ahead: int = 14):
    """
    GET /api/ess/tours
    
    List available ESS Route tours for a zone.
    """
    zone_code = zone_code.upper()
    policy = await get_route_policy(zone_code)
    
    if not policy or not policy.get("ess_route_enabled", False):
        raise HTTPException(
            status_code=400,
            detail={"error": "ESS_ROUTE_NOT_AVAILABLE", "zone": zone_code}
        )
    
    tours = []
    
    # Try to get tours from database
    if db is not None:
        db_tours = await db.kdm_route_capacity.find(
            {"zone_code": zone_code, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        for tour in db_tours:
            status = "full" if tour.get("booked", 0) >= tour.get("capacity", 0) else "open"
            tours.append(TourInfo(
                tour_id=tour.get("tour_id", ""),
                zone_code=zone_code,
                date=tour.get("window_start", "")[:10] if tour.get("window_start") else "",
                window_start=tour.get("window_start", "08:00")[-8:-3] if tour.get("window_start") else "08:00",
                window_end=tour.get("window_end", "12:00")[-8:-3] if tour.get("window_end") else "12:00",
                capacity=tour.get("capacity", 0),
                booked=tour.get("booked", 0),
                available=max(0, tour.get("capacity", 0) - tour.get("booked", 0)),
                status=status
            ))
    
    # If no tours in DB, generate mock tours
    if not tours:
        today = datetime.now(timezone.utc).date()
        windows = [("AM", "08:00", "12:00"), ("PM", "14:00", "18:00")]
        max_capacity = policy.get("max_daily_capacity", 100)
        
        for day_offset in range(1, days_ahead + 1):
            tour_date = today + timedelta(days=day_offset)
            if tour_date.weekday() >= 5:
                continue
            
            for window_code, start, end in windows:
                tour_id = generate_tour_id(zone_code, tour_date, window_code)
                # Mock booked count for demo data — uses cryptographic randomness
                upper_bound = max(1, int(max_capacity * 0.7) - 10 + 1)
                booked = 10 + secrets.randbelow(upper_bound)
                available = max_capacity - booked
                
                tours.append(TourInfo(
                    tour_id=tour_id,
                    zone_code=zone_code,
                    date=tour_date.isoformat(),
                    window_start=start,
                    window_end=end,
                    capacity=max_capacity,
                    booked=booked,
                    available=available,
                    status="open" if available > 0 else "full"
                ))
    
    return TourListResponse(tours=tours, zone_code=zone_code, total=len(tours))


@ess_router.get("/tours/{tour_id}", response_model=TourInfo)
async def get_tour_details(tour_id: str):
    """
    GET /api/ess/tours/{tour_id}
    
    Get details of a specific tour.
    """
    # Parse tour ID to get zone and date info
    # Format: TOUR-GP-2026W03-THU-AM
    parts = tour_id.split("-")
    if len(parts) < 5:
        raise HTTPException(status_code=400, detail="Invalid tour_id format")
    
    zone_prefix = parts[1]
    zone_map = {"GP": "GUADELOUPE", "MQ": "MARTINIQUE", "GF": "GUYANE", "RE": "REUNION", "YT": "MAYOTTE"}
    zone_code = zone_map.get(zone_prefix, "GUADELOUPE")
    
    window_code = parts[4]
    windows = {"AM": ("08:00", "12:00"), "PM": ("14:00", "18:00")}
    start, end = windows.get(window_code, ("08:00", "12:00"))
    
    policy = DEFAULT_ROUTE_POLICY.get(zone_code, {})
    max_capacity = policy.get("max_daily_capacity", 100)
    
    # Check if tour exists in DB (for now, generate mock data)
    upper_bound = max(1, int(max_capacity * 0.8) - 10 + 1)
    booked = 10 + secrets.randbelow(upper_bound)
    
    return TourInfo(
        tour_id=tour_id,
        zone_code=zone_code,
        date=datetime.now(timezone.utc).date().isoformat(),
        window_start=start,
        window_end=end,
        capacity=max_capacity,
        booked=booked,
        available=max_capacity - booked,
        status="open" if (max_capacity - booked) > 0 else "full"
    )


@ess_router.post("/book", response_model=BookTourResponse)
async def book_tour_spot(request: BookTourRequest):
    """
    POST /api/ess/book
    
    Book a spot on an ESS Route tour.
    """
    # Verify tour exists and has capacity
    try:
        tour = await get_tour_details(request.tour_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    if tour.status == "full":
        raise HTTPException(
            status_code=400,
            detail={"error": "ESS_ROUTE_TOUR_CAPACITY_FULL", "tour_id": request.tour_id}
        )
    
    # Create booking
    booking_id = f"BOOK-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)
    
    booking_doc = {
        "id": booking_id,
        "tour_id": request.tour_id,
        "order_id": request.order_id,
        "org_id": request.org_id,
        "delivery_address": request.delivery_address.model_dump(),
        "cartons": request.cartons,
        "weight_kg": request.weight_kg,
        "notes": request.notes,
        "status": "confirmed",
        "position": tour.booked + 1,
        "created_at": now,
        "updated_at": now
    }
    
    # Store in DB
    if db is not None:
        await db.ess_route_bookings.insert_one(booking_doc)
        
        # Update tour capacity
        await db.ess_tours.update_one(
            {"tour_id": request.tour_id},
            {"$inc": {"booked": 1}, "$set": {"updated_at": now}},
            upsert=True
        )
    
    logger.info(f"ESS Route booking created: {booking_id} for tour {request.tour_id}")
    
    return BookTourResponse(
        booking_id=booking_id,
        tour_id=request.tour_id,
        status="confirmed",
        window_start=tour.window_start,
        window_end=tour.window_end,
        estimated_position=tour.booked + 1,
        created_at=now.isoformat()
    )


@ess_router.get("/annex/{order_id}/html")
async def get_ess_annex_html(order_id: str):
    """
    GET /api/ess/annex/{order_id}/html
    
    Get the populated HTML for the ESS Route annex document.
    """
    # Get order data
    order = None
    if db is not None:
        order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order uses ESS_ROUTE delivery mode
    delivery_mode = order.get("delivery_mode", "DIRECT")
    if delivery_mode != "ESS_ROUTE":
        raise HTTPException(
            status_code=400,
            detail="Order does not use ESS_ROUTE delivery mode"
        )
    
    # Get client info
    org_id = order.get("org_id")
    org = None
    if db is not None and org_id:
        org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    
    # Load HTML template
    template_path = Path(__file__).parent.parent / "frontend" / "public" / "contracts" / "annex-ess-route.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=500, detail="Template not found")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace variables
    zone_code = order.get("zone_code", "GUADELOUPE")
    tour_id = order.get("tour_id", "N/A")
    delivery_address = order.get("delivery_address", {})
    
    replacements = {
        "{{LOGO_SRC}}": "/kdmarche-logo.svg",
        "{{REF_ANNEXE_TOURNEES}}": f"ANX-ESS-{order_id[:8].upper()}",
        "{{VERSION}}": "1.0",
        "{{DATE_EFFET}}": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "{{ZONE_CODE}}": zone_code,
        "{{LOGISCOP_FORM}}": "Établissement secondaire de la SCIC O'SCOP",
        "{{LOGISCOP_ADDRESS}}": "387 Rue de l'Industrie, 97122 Baie-Mahault",
        "{{LOGISCOP_SIRET}}": "XXX XXX XXX XXXXX",
        "{{LOGISCOP_TVA}}": "FR XX XXX XXX XXX",
        "{{LOGISCOP_EMAIL}}": "logistique@oscop.fr",
        "{{LOGISCOP_PHONE}}": "+590 590 XX XX XX",
        "{{CLIENT_LEGAL_NAME}}": org.get("legal_name", "Client B2B") if org else "Client B2B",
        "{{CLIENT_ADDRESS}}": f"{delivery_address.get('street', '')}, {delivery_address.get('postal_code', '')} {delivery_address.get('city', '')}",
        "{{CLIENT_SIRET}}": org.get("registration_id", "N/A") if org else "N/A",
        "{{CLIENT_TVA}}": org.get("tva_number", "N/A") if org else "N/A",
        "{{CLIENT_CONTACT}}": delivery_address.get("contact_name", ""),
        "{{CLIENT_SIGN_NAME}}": org.get("contact_name", "") if org else "",
        "{{CLIENT_SIGN_TITLE}}": "Représentant légal",
        "{{LOGISCOP_SIGN_NAME}}": "[Responsable LOGI'SCOP]",
        "{{LOGISCOP_SIGN_TITLE}}": "Directeur Logistique",
        "{{LIEU_SIGNATURE}}": delivery_address.get("city", "Baie-Mahault"),
        "{{DATE_SIGNATURE}}": datetime.now(timezone.utc).strftime("%d/%m/%Y")
    }
    
    for key, value in replacements.items():
        html_content = html_content.replace(key, str(value))
    
    return {"html": html_content, "order_id": order_id, "tour_id": tour_id}


@ess_router.get("/disclaimer")
async def get_ess_route_disclaimer():
    """
    GET /api/ess/disclaimer
    
    Get the legal disclaimer text for ESS Route delivery (for checkout).
    """
    return {
        "short": "La livraison en Tournées ESS est une tournée mutualisée planifiée, destinée à réduire les coûts et l'empreinte carbone. Elle implique une fenêtre de livraison et des règles d'accès équitables et traçables.",
        "long": """La livraison en Tournées ESS est une tournée mutualisée planifiée, organisée par LOGI'SCOP 
dans une logique d'intérêt collectif, de réduction des coûts et d'optimisation environnementale.

Cette prestation implique :
- Une fenêtre de livraison (et non une heure fixe)
- Des règles de priorisation équitables et traçables
- Un POD (preuve de livraison) probant avec signature et horodatage

En choisissant ce mode, vous acceptez les conditions de l'Annexe Tournées ESS.""",
        "legal_reference": "ANNEXE-ESS-ROUTE-2026-001",
        "document_url": "/legal/annexe-ess-route"
    }


@ess_router.get("/policy/{zone_code}")
async def get_ess_route_policy_endpoint(zone_code: str):
    """
    GET /api/ess/policy/{zone_code}
    
    Get ESS Route policy for a zone (for OPA bundle generation).
    """
    zone_code = zone_code.upper()
    policy = await get_route_policy(zone_code)
    
    if not policy:
        raise HTTPException(status_code=404, detail=f"No ESS Route policy for zone {zone_code}")
    
    tariff = ESS_ROUTE_TARIFFS.get(zone_code, {})
    
    return {
        "zone_code": zone_code,
        "zone_name": get_zone_name(zone_code),
        "policy": policy,
        "tariff": tariff,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
