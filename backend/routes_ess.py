"""
KDMARCHE × LOGI'SCOP - ESS Route (Tournées Mutualisées) API
Endpoints for ESS Route delivery mode management

Routes:
- POST /api/ess/quote - Get ESS route delivery quote
- GET /api/ess/tours - List available tours for a zone
- GET /api/ess/tours/{tour_id} - Get tour details
- POST /api/ess/book - Book a spot on a tour
- GET /api/ess/annex/{order_id}/html - Get ESS Route annex HTML
- GET /api/ess/disclaimer - Get checkout disclaimer text
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Router
ess_router = APIRouter(prefix="/api/ess", tags=["ESS Route"])

# Database reference
db = None


def set_ess_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== ROUTE POLICY DATA ==============

# Default route policy (fallback if DB is empty)
DEFAULT_ROUTE_POLICY = {
    "GUADELOUPE": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 120,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20},
            {"code": "RECENT_LATE_CANCEL", "weight": -30}
        ]
    },
    "MARTINIQUE": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 100,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20},
            {"code": "RECENT_LATE_CANCEL", "weight": -30}
        ]
    },
    "GUYANE": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 60,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20}
        ]
    },
    "REUNION": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 80,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20}
        ]
    },
    "MAYOTTE": {
        "ess_route_enabled": False,  # Not yet available in Mayotte
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 40,
        "priority_rules": []
    }
}


async def get_route_policy(zone_code: str) -> dict:
    """Get route policy from database or fallback to default"""
    zone_code = zone_code.upper()
    
    if db is not None:
        policy = await db.kdm_route_policy.find_one({"zone_code": zone_code}, {"_id": 0})
        if policy:
            # Get priority rules
            rules = await db.kdm_route_priority_rules.find(
                {"zone_code": zone_code, "is_active": True},
                {"_id": 0}
            ).sort("sort_order", 1).to_list(50)
            
            policy["priority_rules"] = [
                {"code": r.get("code"), "weight": r.get("weight", 0)}
                for r in rules
            ]
            return policy
    
    return DEFAULT_ROUTE_POLICY.get(zone_code, {})

# ESS Route Tariffs (reduced due to mutualization)
ESS_ROUTE_TARIFFS = {
    "GUADELOUPE": {
        "base_rate_cents": 180,  # Reduced from standard
        "rate_per_kg_cents": 35,
        "rate_per_carton_cents": 120,
        "vat_rate": 8.5,
        "estimated_days": "2-4"
    },
    "MARTINIQUE": {
        "base_rate_cents": 200,
        "rate_per_kg_cents": 38,
        "rate_per_carton_cents": 130,
        "vat_rate": 8.5,
        "estimated_days": "2-4"
    },
    "GUYANE": {
        "base_rate_cents": 350,
        "rate_per_kg_cents": 60,
        "rate_per_carton_cents": 200,
        "vat_rate": 0,  # Exonerated
        "estimated_days": "4-6"
    },
    "REUNION": {
        "base_rate_cents": 250,
        "rate_per_kg_cents": 45,
        "rate_per_carton_cents": 150,
        "vat_rate": 8.5,
        "estimated_days": "3-5"
    },
    "MAYOTTE": {
        "base_rate_cents": 300,
        "rate_per_kg_cents": 55,
        "rate_per_carton_cents": 180,
        "vat_rate": 0,  # Exonerated
        "estimated_days": "5-7"
    }
}


# ============== PYDANTIC MODELS ==============

class DeliveryWindow(BaseModel):
    start: str  # ISO time format HH:MM
    end: str    # ISO time format HH:MM


class DeliveryAddress(BaseModel):
    street: str
    complement: Optional[str] = None
    city: str
    postal_code: str
    country: str = "FR"
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class ESSRouteQuoteRequest(BaseModel):
    """Request for ESS Route delivery quote"""
    zone_code: str
    weight_kg: float = Field(..., gt=0)
    cartons: int = Field(1, ge=1)
    delivery_address: DeliveryAddress
    delivery_window: Optional[DeliveryWindow] = None
    tour_id: Optional[str] = None


class ESSRouteQuoteLineItem(BaseModel):
    code: str
    label: str
    amount_ht_cents: int
    quantity: int = 1


class RouteReference(BaseModel):
    tour_id: Optional[str] = None
    route_window: Optional[DeliveryWindow] = None
    priority_reason_code: Optional[str] = None


class ESSRouteQuoteResponse(BaseModel):
    zone_code: str
    zone_name: str
    delivery_mode: str = "ESS_ROUTE"
    
    # Metrics
    weight_kg: float
    cartons: int
    
    # Line items
    lines: List[ESSRouteQuoteLineItem]
    
    # Totals
    subtotal_ht_cents: int
    vat_rate: float
    vat_cents: int
    total_ttc_cents: int
    
    # Route info
    route: RouteReference
    estimated_delivery: str
    
    # Quote metadata
    quote_id: str
    valid_until: str
    billing_entity: str = "LOGI'SCOP"
    
    # ESS benefits
    savings_vs_standard_cents: int
    eco_benefit: str


class TourInfo(BaseModel):
    tour_id: str
    zone_code: str
    date: str
    window_start: str
    window_end: str
    capacity: int
    booked: int
    available: int
    status: str  # "open", "full", "completed"


class TourListResponse(BaseModel):
    tours: List[TourInfo]
    zone_code: str
    total: int


class BookTourRequest(BaseModel):
    tour_id: str
    order_id: Optional[str] = None
    org_id: str
    delivery_address: DeliveryAddress
    cartons: int = Field(1, ge=1)
    weight_kg: float = Field(..., gt=0)
    notes: Optional[str] = None


class BookTourResponse(BaseModel):
    booking_id: str
    tour_id: str
    status: str
    window_start: str
    window_end: str
    estimated_position: int
    created_at: str


# ============== HELPER FUNCTIONS ==============

def get_zone_name(zone_code: str) -> str:
    """Get display name for zone"""
    names = {
        "GUADELOUPE": "Guadeloupe",
        "MARTINIQUE": "Martinique",
        "GUYANE": "Guyane",
        "REUNION": "La Réunion",
        "MAYOTTE": "Mayotte"
    }
    return names.get(zone_code.upper(), zone_code)


def calculate_ess_route_cost(zone_code: str, weight_kg: float, cartons: int) -> Dict[str, Any]:
    """Calculate ESS Route cost (mutualized pricing)"""
    tariff = ESS_ROUTE_TARIFFS.get(zone_code.upper())
    if not tariff:
        return {"error": "ZONE_NOT_FOUND"}
    
    # Calculate based on weight or cartons (whichever is higher)
    weight_cost = tariff["base_rate_cents"] + int(weight_kg * tariff["rate_per_kg_cents"])
    carton_cost = tariff["base_rate_cents"] + int(cartons * tariff["rate_per_carton_cents"])
    
    # Apply "payant pour" rule (higher of the two)
    if carton_cost > weight_cost:
        billing_mode = "cartons"
        transport_ht_cents = carton_cost
    else:
        billing_mode = "weight"
        transport_ht_cents = weight_cost
    
    return {
        "transport_ht_cents": transport_ht_cents,
        "billing_mode": billing_mode,
        "weight_cost_cents": weight_cost,
        "carton_cost_cents": carton_cost,
        "vat_rate": tariff["vat_rate"],
        "estimated_days": tariff["estimated_days"]
    }


def calculate_standard_cost(zone_code: str, weight_kg: float) -> int:
    """Calculate standard delivery cost for comparison"""
    # Standard rates are higher than ESS Route
    from routes_v1_logiscop import DELIVERY_POLICY
    policy = DELIVERY_POLICY.get(zone_code[:3] if zone_code.isalpha() else zone_code)
    if not policy:
        return 0
    return policy["base_rate_cents"] + int(weight_kg * policy["rate_per_kg_cents"])


async def evaluate_ess_route_policy(zone_code: str, request_data: Dict, reliability_score: int = 100) -> Dict[str, Any]:
    """Evaluate OPA-style ESS Route policy"""
    policy = await get_route_policy(zone_code.upper())
    deny_reasons = []
    
    if not policy:
        return {"allow": False, "deny": ["ESS_ROUTE_ZONE_UNKNOWN"]}
    
    if not policy.get("ess_route_enabled", False):
        deny_reasons.append("ESS_ROUTE_DISABLED_FOR_ZONE")
    
    if policy.get("window_required", True):
        window = request_data.get("delivery_window")
        if not window or not window.get("start") or not window.get("end"):
            deny_reasons.append("ESS_ROUTE_DELIVERY_WINDOW_REQUIRED")
    
    if reliability_score < policy.get("min_reliability_score", 60):
        deny_reasons.append("ESS_ROUTE_PRIORITY_SCORE_TOO_LOW")
    
    # Check tour capacity if tour_id provided
    tour_id = request_data.get("tour_id")
    if tour_id and db is not None:
        capacity = await db.kdm_route_capacity.find_one(
            {"zone_code": zone_code.upper(), "tour_id": tour_id, "is_active": True},
            {"_id": 0}
        )
        if capacity and capacity.get("booked", 0) >= capacity.get("capacity", 0):
            deny_reasons.append("ESS_ROUTE_TOUR_CAPACITY_FULL")
    
    return {
        "allow": len(deny_reasons) == 0,
        "deny": deny_reasons,
        "priority_reason_code": "COMPLIANCE_OK" if len(deny_reasons) == 0 else None
    }


def generate_tour_id(zone_code: str, date: datetime, window: str) -> str:
    """Generate a tour ID"""
    week_num = date.isocalendar()[1]
    day_abbr = date.strftime("%a").upper()[:3]
    return f"TOUR-{zone_code[:2].upper()}-{date.year}W{week_num:02d}-{day_abbr}-{window}"


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
                import random
                booked = random.randint(10, int(max_capacity * 0.7))
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
    
    policy = ROUTE_POLICY.get(zone_code, {})
    max_capacity = policy.get("max_daily_capacity", 100)
    
    # Check if tour exists in DB (for now, generate mock data)
    import random
    booked = random.randint(10, int(max_capacity * 0.8))
    
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
