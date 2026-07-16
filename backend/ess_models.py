"""KDMARCHE ESS Route — Policy data, modèles & helpers (split from routes_ess.py)."""
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import secrets

from routes_logistics_shared import (
    DEFAULT_ROUTE_POLICY,
    ESS_ROUTE_TARIFFS,
    DELIVERY_POLICY,
)

logger = logging.getLogger(__name__)

db = None

def set_ess_models_database(database):
    global db
    db = database

# ============== ROUTE POLICY DATA ==============
# Constants moved to routes_logistics_shared.py to break the circular
# import between routes_ess and routes_v1_logiscop.


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


