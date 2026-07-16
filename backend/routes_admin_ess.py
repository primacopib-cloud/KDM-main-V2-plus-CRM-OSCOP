"""
KDMARCHE × LOGI'SCOP - Admin API: ESS Routes Management
CRUD complet pour la gestion des tournées ESS (policies, rules, capacity)

Endpoints:
- /api/admin/v1/routes/policies - CRUD Route Policy
- /api/admin/v1/routes/rules - CRUD Priority Rules  
- /api/admin/v1/routes/capacity - CRUD Route Capacity
- /api/admin/v1/zones - Liste des zones (référence)
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
import uuid
import logging

logger = logging.getLogger(__name__)

# Router
admin_ess_router = APIRouter(prefix="/api/admin/v1/routes", tags=["Admin ESS Routes"])

# Database reference
db = None


def set_admin_ess_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== PYDANTIC MODELS ==============

# --- Zone Reference ---
class ZoneRef(BaseModel):
    id: str
    code: str
    label: str


# --- Route Policy ---
class RoutePolicyBase(BaseModel):
    ess_route_enabled: bool = False
    window_required: bool = True
    min_reliability_score: int = Field(0, ge=0, le=100)
    max_daily_capacity: int = Field(0, ge=0)


class RoutePolicyCreate(RoutePolicyBase):
    zone_id: Optional[str] = None  # Can use zone_code instead
    zone_code: Optional[str] = None


class RoutePolicyUpdate(BaseModel):
    ess_route_enabled: Optional[bool] = None
    window_required: Optional[bool] = None
    min_reliability_score: Optional[int] = Field(None, ge=0, le=100)
    max_daily_capacity: Optional[int] = Field(None, ge=0)


class RoutePolicyResponse(RoutePolicyBase):
    id: str
    zone: ZoneRef
    created_at: str
    updated_at: str
    
    # Include associated rules count
    rules_count: int = 0


# --- Priority Rules ---
class RoutePriorityRuleBase(BaseModel):
    code: str
    weight: int = 0
    is_active: bool = True
    sort_order: int = 100


class RoutePriorityRuleCreate(RoutePriorityRuleBase):
    route_policy_id: Optional[str] = None  # Can use zone_code instead
    zone_code: Optional[str] = None


class RoutePriorityRuleUpdate(BaseModel):
    code: Optional[str] = None
    weight: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class RoutePriorityRuleResponse(RoutePriorityRuleBase):
    id: str
    route_policy_id: Optional[str] = None
    zone_code: str
    created_at: str
    updated_at: str


# --- Route Capacity ---
class RouteCapacityBase(BaseModel):
    tour_id: str
    capacity: int = Field(0, ge=0)
    booked: int = Field(0, ge=0)
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    is_active: bool = True


class RouteCapacityCreate(RouteCapacityBase):
    zone_id: Optional[str] = None  # Can use zone_code instead
    zone_code: Optional[str] = None


class RouteCapacityUpdate(BaseModel):
    tour_id: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=0)
    booked: Optional[int] = Field(None, ge=0)
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    is_active: Optional[bool] = None


class RouteCapacityResponse(RouteCapacityBase):
    id: str
    zone: ZoneRef
    available: int = 0
    fill_rate: float = 0.0
    updated_at: str


# --- Bulk Operations ---
class BulkRulesCreate(BaseModel):
    zone_code: str
    rules: List[RoutePriorityRuleBase]


class BulkCapacityCreate(BaseModel):
    zone_code: str
    tours: List[RouteCapacityBase]


# ============== HELPER FUNCTIONS ==============

def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())


async def get_zone_by_code(zone_code: str) -> Optional[dict]:
    """Get zone document by code"""
    if db is None:
        return None
    return await db.kdm_zones.find_one(
        {"code": zone_code.upper(), "is_active": True},
        {"_id": 0}
    )


async def get_zone_ref(zone_code: str) -> Optional[ZoneRef]:
    """Get ZoneRef by code"""
    zone = await get_zone_by_code(zone_code)
    if zone:
        return ZoneRef(
            id=zone.get("id", zone_code),
            code=zone.get("code", zone_code),
            label=zone.get("name", zone_code)
        )
    return None


# ============== ZONES ENDPOINTS ==============

@admin_ess_router.get("/zones", response_model=List[ZoneRef], tags=["Admin Zones"])
async def list_zones():
    """
    GET /api/admin/v1/routes/zones
    
    Liste des zones disponibles (référence pour les policies).
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zones = await db.kdm_zones.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "code": 1, "name": 1}
    ).sort("code", 1).to_list(100)
    
    return [
        ZoneRef(
            id=z.get("id", z.get("code", "")),
            code=z.get("code", ""),
            label=z.get("name", z.get("code", ""))
        )
        for z in zones
    ]


# ============== ROUTE POLICY ENDPOINTS ==============

@admin_ess_router.get("/policies", response_model=List[RoutePolicyResponse])
async def list_route_policies(
    zone_code: Optional[str] = Query(None, description="Filter by zone code")
):
    """
    GET /api/admin/v1/routes/policies
    
    Liste des route policies (1 par zone).
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = {}
    if zone_code:
        query["zone_code"] = zone_code.upper()
    
    policies = await db.kdm_route_policy.find(query, {"_id": 0}).sort("zone_code", 1).to_list(100)
    
    result = []
    for p in policies:
        zone_ref = await get_zone_ref(p.get("zone_code", ""))
        if not zone_ref:
            zone_ref = ZoneRef(id="", code=p.get("zone_code", ""), label=p.get("zone_code", ""))
        
        # Count rules for this policy
        rules_count = await db.kdm_route_priority_rules.count_documents({
            "zone_code": p.get("zone_code", ""),
            "is_active": True
        })
        
        result.append(RoutePolicyResponse(
            id=p.get("id", generate_id()),
            zone=zone_ref,
            ess_route_enabled=p.get("ess_route_enabled", False),
            window_required=p.get("window_required", True),
            min_reliability_score=p.get("min_reliability_score", 0),
            max_daily_capacity=p.get("max_daily_capacity", 0),
            rules_count=rules_count,
            created_at=p.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(p.get("created_at"), datetime) else str(p.get("created_at", "")),
            updated_at=p.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(p.get("updated_at"), datetime) else str(p.get("updated_at", ""))
        ))
    
    return result


@admin_ess_router.post("/policies", response_model=RoutePolicyResponse, status_code=201)
async def create_route_policy(request: RoutePolicyCreate):
    """
    POST /api/admin/v1/routes/policies
    
    Créer une route policy (1 par zone).
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zone_code = request.zone_code.upper() if request.zone_code else None
    
    if not zone_code:
        raise HTTPException(status_code=400, detail="zone_code is required")
    
    # Check zone exists
    zone = await get_zone_by_code(zone_code)
    if not zone:
        raise HTTPException(status_code=400, detail=f"Zone {zone_code} not found")
    
    # Check policy doesn't already exist
    existing = await db.kdm_route_policy.find_one({"zone_code": zone_code})
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": "POLICY_EXISTS", "message": f"Policy already exists for zone {zone_code}"}
        )
    
    now = datetime.now(timezone.utc)
    policy_id = generate_id()
    
    doc = {
        "id": policy_id,
        "zone_code": zone_code,
        "ess_route_enabled": request.ess_route_enabled,
        "window_required": request.window_required,
        "min_reliability_score": request.min_reliability_score,
        "max_daily_capacity": request.max_daily_capacity,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    
    await db.kdm_route_policy.insert_one(doc)
    logger.info(f"Created route policy for zone {zone_code}: {policy_id}")
    
    zone_ref = await get_zone_ref(zone_code)
    
    return RoutePolicyResponse(
        id=policy_id,
        zone=zone_ref or ZoneRef(id="", code=zone_code, label=zone_code),
        ess_route_enabled=request.ess_route_enabled,
        window_required=request.window_required,
        min_reliability_score=request.min_reliability_score,
        max_daily_capacity=request.max_daily_capacity,
        rules_count=0,
        created_at=now.isoformat(),
        updated_at=now.isoformat()
    )


@admin_ess_router.get("/policies/{policy_id}", response_model=RoutePolicyResponse)
async def get_route_policy(policy_id: str):
    """
    GET /api/admin/v1/routes/policies/{policy_id}
    
    Détail d'une route policy.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Try to find by id or zone_code
    policy = await db.kdm_route_policy.find_one(
        {"$or": [{"id": policy_id}, {"zone_code": policy_id.upper()}]},
        {"_id": 0}
    )
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    zone_ref = await get_zone_ref(policy.get("zone_code", ""))
    rules_count = await db.kdm_route_priority_rules.count_documents({
        "zone_code": policy.get("zone_code", ""),
        "is_active": True
    })
    
    return RoutePolicyResponse(
        id=policy.get("id", policy_id),
        zone=zone_ref or ZoneRef(id="", code=policy.get("zone_code", ""), label=policy.get("zone_code", "")),
        ess_route_enabled=policy.get("ess_route_enabled", False),
        window_required=policy.get("window_required", True),
        min_reliability_score=policy.get("min_reliability_score", 0),
        max_daily_capacity=policy.get("max_daily_capacity", 0),
        rules_count=rules_count,
        created_at=policy.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(policy.get("created_at"), datetime) else str(policy.get("created_at", "")),
        updated_at=policy.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(policy.get("updated_at"), datetime) else str(policy.get("updated_at", ""))
    )


@admin_ess_router.patch("/policies/{policy_id}", response_model=RoutePolicyResponse)
async def update_route_policy(policy_id: str, request: RoutePolicyUpdate):
    """
    PATCH /api/admin/v1/routes/policies/{policy_id}
    
    Mettre à jour une route policy.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Find existing
    policy = await db.kdm_route_policy.find_one(
        {"$or": [{"id": policy_id}, {"zone_code": policy_id.upper()}]},
        {"_id": 0}
    )
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Build update
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if request.ess_route_enabled is not None:
        update_data["ess_route_enabled"] = request.ess_route_enabled
    if request.window_required is not None:
        update_data["window_required"] = request.window_required
    if request.min_reliability_score is not None:
        update_data["min_reliability_score"] = request.min_reliability_score
    if request.max_daily_capacity is not None:
        update_data["max_daily_capacity"] = request.max_daily_capacity
    
    await db.kdm_route_policy.update_one(
        {"$or": [{"id": policy_id}, {"zone_code": policy_id.upper()}]},
        {"$set": update_data}
    )
    
    logger.info(f"Updated route policy {policy_id}")
    
    return await get_route_policy(policy_id)


@admin_ess_router.delete("/policies/{policy_id}", status_code=204)
async def delete_route_policy(policy_id: str):
    """
    DELETE /api/admin/v1/routes/policies/{policy_id}
    
    Supprimer une route policy (et ses rules associées).
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Find existing
    policy = await db.kdm_route_policy.find_one(
        {"$or": [{"id": policy_id}, {"zone_code": policy_id.upper()}]},
        {"_id": 0}
    )
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    zone_code = policy.get("zone_code", "")
    
    # Delete policy
    await db.kdm_route_policy.delete_one(
        {"$or": [{"id": policy_id}, {"zone_code": policy_id.upper()}]}
    )
    
    # Delete associated rules
    deleted_rules = await db.kdm_route_priority_rules.delete_many({"zone_code": zone_code})
    
    logger.info(f"Deleted route policy {policy_id} and {deleted_rules.deleted_count} rules")
    
    return None



# ============== STATISTICS ENDPOINTS ==============

@admin_ess_router.get("/stats")
async def get_ess_route_stats():
    """
    GET /api/admin/v1/routes/stats
    
    Statistiques globales des tournées ESS.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Count policies
    policies_count = await db.kdm_route_policy.count_documents({})
    enabled_count = await db.kdm_route_policy.count_documents({"ess_route_enabled": True})
    
    # Count rules
    rules_count = await db.kdm_route_priority_rules.count_documents({"is_active": True})
    
    # Count capacities
    capacities_count = await db.kdm_route_capacity.count_documents({"is_active": True})
    
    # Aggregate capacity stats
    pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {
            "_id": "$zone_code",
            "total_capacity": {"$sum": "$capacity"},
            "total_booked": {"$sum": "$booked"},
            "tours_count": {"$sum": 1}
        }}
    ]
    
    capacity_by_zone = await db.kdm_route_capacity.aggregate(pipeline).to_list(100)
    
    zone_stats = {}
    for stat in capacity_by_zone:
        zone_code = stat["_id"]
        total_cap = stat["total_capacity"]
        total_booked = stat["total_booked"]
        fill_rate = (total_booked / total_cap * 100) if total_cap > 0 else 0
        
        zone_stats[zone_code] = {
            "tours_count": stat["tours_count"],
            "total_capacity": total_cap,
            "total_booked": total_booked,
            "total_available": total_cap - total_booked,
            "fill_rate_percent": round(fill_rate, 1)
        }
    
    return {
        "policies": {
            "total": policies_count,
            "enabled": enabled_count,
            "disabled": policies_count - enabled_count
        },
        "rules": {
            "total_active": rules_count
        },
        "capacity": {
            "total_tours": capacities_count,
            "by_zone": zone_stats
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
