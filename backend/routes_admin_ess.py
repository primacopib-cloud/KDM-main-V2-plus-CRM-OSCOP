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


# ============== PRIORITY RULES ENDPOINTS ==============

@admin_ess_router.get("/rules", response_model=List[RoutePriorityRuleResponse])
async def list_priority_rules(
    zone_code: Optional[str] = Query(None, description="Filter by zone code"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """
    GET /api/admin/v1/routes/rules
    
    Liste des règles de priorisation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = {}
    if zone_code:
        query["zone_code"] = zone_code.upper()
    if is_active is not None:
        query["is_active"] = is_active
    
    rules = await db.kdm_route_priority_rules.find(query, {"_id": 0}).sort([("zone_code", 1), ("sort_order", 1), ("code", 1)]).to_list(500)
    
    return [
        RoutePriorityRuleResponse(
            id=r.get("id", generate_id()),
            route_policy_id=r.get("route_policy_id"),
            zone_code=r.get("zone_code", ""),
            code=r.get("code", ""),
            weight=r.get("weight", 0),
            is_active=r.get("is_active", True),
            sort_order=r.get("sort_order", 100),
            created_at=r.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(r.get("created_at"), datetime) else str(r.get("created_at", "")),
            updated_at=r.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(r.get("updated_at"), datetime) else str(r.get("updated_at", ""))
        )
        for r in rules
    ]


@admin_ess_router.post("/rules", response_model=RoutePriorityRuleResponse, status_code=201)
async def create_priority_rule(request: RoutePriorityRuleCreate):
    """
    POST /api/admin/v1/routes/rules
    
    Créer une règle de priorisation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zone_code = request.zone_code.upper() if request.zone_code else None
    
    if not zone_code:
        raise HTTPException(status_code=400, detail="zone_code is required")
    
    # Check policy exists for zone
    policy = await db.kdm_route_policy.find_one({"zone_code": zone_code})
    if not policy:
        raise HTTPException(status_code=400, detail=f"No route policy exists for zone {zone_code}")
    
    # Check rule doesn't already exist
    existing = await db.kdm_route_priority_rules.find_one({
        "zone_code": zone_code,
        "code": request.code
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": "RULE_EXISTS", "message": f"Rule {request.code} already exists for zone {zone_code}"}
        )
    
    now = datetime.now(timezone.utc)
    rule_id = generate_id()
    
    doc = {
        "id": rule_id,
        "zone_code": zone_code,
        "route_policy_id": policy.get("id"),
        "code": request.code,
        "weight": request.weight,
        "is_active": request.is_active,
        "sort_order": request.sort_order,
        "created_at": now,
        "updated_at": now
    }
    
    await db.kdm_route_priority_rules.insert_one(doc)
    logger.info(f"Created priority rule {request.code} for zone {zone_code}")
    
    return RoutePriorityRuleResponse(
        id=rule_id,
        route_policy_id=policy.get("id"),
        zone_code=zone_code,
        code=request.code,
        weight=request.weight,
        is_active=request.is_active,
        sort_order=request.sort_order,
        created_at=now.isoformat(),
        updated_at=now.isoformat()
    )


@admin_ess_router.post("/rules/bulk", response_model=List[RoutePriorityRuleResponse], status_code=201)
async def bulk_create_priority_rules(request: BulkRulesCreate):
    """
    POST /api/admin/v1/routes/rules/bulk
    
    Créer plusieurs règles de priorisation en une fois.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zone_code = request.zone_code.upper()
    
    # Check policy exists
    policy = await db.kdm_route_policy.find_one({"zone_code": zone_code})
    if not policy:
        raise HTTPException(status_code=400, detail=f"No route policy exists for zone {zone_code}")
    
    now = datetime.now(timezone.utc)
    results = []
    
    for rule in request.rules:
        rule_id = generate_id()
        
        doc = {
            "id": rule_id,
            "zone_code": zone_code,
            "route_policy_id": policy.get("id"),
            "code": rule.code,
            "weight": rule.weight,
            "is_active": rule.is_active,
            "sort_order": rule.sort_order,
            "created_at": now,
            "updated_at": now
        }
        
        # Upsert to handle duplicates
        await db.kdm_route_priority_rules.update_one(
            {"zone_code": zone_code, "code": rule.code},
            {"$set": doc},
            upsert=True
        )
        
        results.append(RoutePriorityRuleResponse(
            id=rule_id,
            route_policy_id=policy.get("id"),
            zone_code=zone_code,
            code=rule.code,
            weight=rule.weight,
            is_active=rule.is_active,
            sort_order=rule.sort_order,
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        ))
    
    logger.info(f"Bulk created {len(results)} priority rules for zone {zone_code}")
    return results


@admin_ess_router.get("/rules/{rule_id}", response_model=RoutePriorityRuleResponse)
async def get_priority_rule(rule_id: str):
    """
    GET /api/admin/v1/routes/rules/{rule_id}
    
    Détail d'une règle de priorisation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    rule = await db.kdm_route_priority_rules.find_one({"id": rule_id}, {"_id": 0})
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return RoutePriorityRuleResponse(
        id=rule.get("id", rule_id),
        route_policy_id=rule.get("route_policy_id"),
        zone_code=rule.get("zone_code", ""),
        code=rule.get("code", ""),
        weight=rule.get("weight", 0),
        is_active=rule.get("is_active", True),
        sort_order=rule.get("sort_order", 100),
        created_at=rule.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(rule.get("created_at"), datetime) else str(rule.get("created_at", "")),
        updated_at=rule.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(rule.get("updated_at"), datetime) else str(rule.get("updated_at", ""))
    )


@admin_ess_router.patch("/rules/{rule_id}", response_model=RoutePriorityRuleResponse)
async def update_priority_rule(rule_id: str, request: RoutePriorityRuleUpdate):
    """
    PATCH /api/admin/v1/routes/rules/{rule_id}
    
    Mettre à jour une règle de priorisation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    rule = await db.kdm_route_priority_rules.find_one({"id": rule_id}, {"_id": 0})
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if request.code is not None:
        update_data["code"] = request.code
    if request.weight is not None:
        update_data["weight"] = request.weight
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    if request.sort_order is not None:
        update_data["sort_order"] = request.sort_order
    
    await db.kdm_route_priority_rules.update_one({"id": rule_id}, {"$set": update_data})
    
    logger.info(f"Updated priority rule {rule_id}")
    
    return await get_priority_rule(rule_id)


@admin_ess_router.delete("/rules/{rule_id}", status_code=204)
async def delete_priority_rule(rule_id: str):
    """
    DELETE /api/admin/v1/routes/rules/{rule_id}
    
    Supprimer une règle de priorisation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    result = await db.kdm_route_priority_rules.delete_one({"id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    logger.info(f"Deleted priority rule {rule_id}")
    return None


# ============== ROUTE CAPACITY ENDPOINTS ==============

@admin_ess_router.get("/capacity", response_model=List[RouteCapacityResponse])
async def list_route_capacity(
    zone_code: Optional[str] = Query(None, description="Filter by zone code"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    tour_id: Optional[str] = Query(None, description="Filter by tour ID")
):
    """
    GET /api/admin/v1/routes/capacity
    
    Liste des capacités de tournée.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = {}
    if zone_code:
        query["zone_code"] = zone_code.upper()
    if is_active is not None:
        query["is_active"] = is_active
    if tour_id:
        query["tour_id"] = tour_id
    
    capacities = await db.kdm_route_capacity.find(query, {"_id": 0}).sort([("zone_code", 1), ("tour_id", 1)]).to_list(1000)
    
    result = []
    zone_cache = {}
    
    for c in capacities:
        zone_code = c.get("zone_code", "")
        
        if zone_code not in zone_cache:
            zone_cache[zone_code] = await get_zone_ref(zone_code)
        
        zone_ref = zone_cache[zone_code]
        capacity = c.get("capacity", 0)
        booked = c.get("booked", 0)
        available = max(0, capacity - booked)
        fill_rate = (booked / capacity * 100) if capacity > 0 else 0
        
        result.append(RouteCapacityResponse(
            id=c.get("id", generate_id()),
            zone=zone_ref or ZoneRef(id="", code=zone_code, label=zone_code),
            tour_id=c.get("tour_id", ""),
            capacity=capacity,
            booked=booked,
            available=available,
            fill_rate=round(fill_rate, 1),
            window_start=c.get("window_start"),
            window_end=c.get("window_end"),
            is_active=c.get("is_active", True),
            updated_at=c.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(c.get("updated_at"), datetime) else str(c.get("updated_at", ""))
        ))
    
    return result


@admin_ess_router.post("/capacity", response_model=RouteCapacityResponse, status_code=201)
async def create_route_capacity(request: RouteCapacityCreate):
    """
    POST /api/admin/v1/routes/capacity
    
    Créer une capacité de tournée.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zone_code = request.zone_code.upper() if request.zone_code else None
    
    if not zone_code:
        raise HTTPException(status_code=400, detail="zone_code is required")
    
    # Check capacity doesn't already exist
    existing = await db.kdm_route_capacity.find_one({
        "zone_code": zone_code,
        "tour_id": request.tour_id
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": "CAPACITY_EXISTS", "message": f"Capacity already exists for tour {request.tour_id} in zone {zone_code}"}
        )
    
    now = datetime.now(timezone.utc)
    capacity_id = generate_id()
    
    doc = {
        "id": capacity_id,
        "zone_code": zone_code,
        "tour_id": request.tour_id,
        "capacity": request.capacity,
        "booked": request.booked,
        "window_start": request.window_start,
        "window_end": request.window_end,
        "is_active": request.is_active,
        "created_at": now,
        "updated_at": now
    }
    
    await db.kdm_route_capacity.insert_one(doc)
    logger.info(f"Created route capacity {request.tour_id} for zone {zone_code}")
    
    zone_ref = await get_zone_ref(zone_code)
    available = max(0, request.capacity - request.booked)
    fill_rate = (request.booked / request.capacity * 100) if request.capacity > 0 else 0
    
    return RouteCapacityResponse(
        id=capacity_id,
        zone=zone_ref or ZoneRef(id="", code=zone_code, label=zone_code),
        tour_id=request.tour_id,
        capacity=request.capacity,
        booked=request.booked,
        available=available,
        fill_rate=round(fill_rate, 1),
        window_start=request.window_start,
        window_end=request.window_end,
        is_active=request.is_active,
        updated_at=now.isoformat()
    )


@admin_ess_router.post("/capacity/bulk", response_model=List[RouteCapacityResponse], status_code=201)
async def bulk_create_route_capacity(request: BulkCapacityCreate):
    """
    POST /api/admin/v1/routes/capacity/bulk
    
    Créer plusieurs capacités de tournée en une fois.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    zone_code = request.zone_code.upper()
    zone_ref = await get_zone_ref(zone_code)
    
    now = datetime.now(timezone.utc)
    results = []
    
    for tour in request.tours:
        capacity_id = generate_id()
        
        doc = {
            "id": capacity_id,
            "zone_code": zone_code,
            "tour_id": tour.tour_id,
            "capacity": tour.capacity,
            "booked": tour.booked,
            "window_start": tour.window_start,
            "window_end": tour.window_end,
            "is_active": tour.is_active,
            "created_at": now,
            "updated_at": now
        }
        
        # Upsert to handle duplicates
        await db.kdm_route_capacity.update_one(
            {"zone_code": zone_code, "tour_id": tour.tour_id},
            {"$set": doc},
            upsert=True
        )
        
        available = max(0, tour.capacity - tour.booked)
        fill_rate = (tour.booked / tour.capacity * 100) if tour.capacity > 0 else 0
        
        results.append(RouteCapacityResponse(
            id=capacity_id,
            zone=zone_ref or ZoneRef(id="", code=zone_code, label=zone_code),
            tour_id=tour.tour_id,
            capacity=tour.capacity,
            booked=tour.booked,
            available=available,
            fill_rate=round(fill_rate, 1),
            window_start=tour.window_start,
            window_end=tour.window_end,
            is_active=tour.is_active,
            updated_at=now.isoformat()
        ))
    
    logger.info(f"Bulk created {len(results)} route capacities for zone {zone_code}")
    return results


@admin_ess_router.get("/capacity/{capacity_id}", response_model=RouteCapacityResponse)
async def get_route_capacity(capacity_id: str):
    """
    GET /api/admin/v1/routes/capacity/{capacity_id}
    
    Détail d'une capacité de tournée.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    capacity = await db.kdm_route_capacity.find_one({"id": capacity_id}, {"_id": 0})
    
    if not capacity:
        raise HTTPException(status_code=404, detail="Capacity not found")
    
    zone_ref = await get_zone_ref(capacity.get("zone_code", ""))
    cap_val = capacity.get("capacity", 0)
    booked = capacity.get("booked", 0)
    available = max(0, cap_val - booked)
    fill_rate = (booked / cap_val * 100) if cap_val > 0 else 0
    
    return RouteCapacityResponse(
        id=capacity.get("id", capacity_id),
        zone=zone_ref or ZoneRef(id="", code=capacity.get("zone_code", ""), label=capacity.get("zone_code", "")),
        tour_id=capacity.get("tour_id", ""),
        capacity=cap_val,
        booked=booked,
        available=available,
        fill_rate=round(fill_rate, 1),
        window_start=capacity.get("window_start"),
        window_end=capacity.get("window_end"),
        is_active=capacity.get("is_active", True),
        updated_at=capacity.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(capacity.get("updated_at"), datetime) else str(capacity.get("updated_at", ""))
    )


@admin_ess_router.patch("/capacity/{capacity_id}", response_model=RouteCapacityResponse)
async def update_route_capacity(capacity_id: str, request: RouteCapacityUpdate):
    """
    PATCH /api/admin/v1/routes/capacity/{capacity_id}
    
    Mettre à jour une capacité de tournée.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    capacity = await db.kdm_route_capacity.find_one({"id": capacity_id}, {"_id": 0})
    
    if not capacity:
        raise HTTPException(status_code=404, detail="Capacity not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if request.tour_id is not None:
        update_data["tour_id"] = request.tour_id
    if request.capacity is not None:
        update_data["capacity"] = request.capacity
    if request.booked is not None:
        update_data["booked"] = request.booked
    if request.window_start is not None:
        update_data["window_start"] = request.window_start
    if request.window_end is not None:
        update_data["window_end"] = request.window_end
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    await db.kdm_route_capacity.update_one({"id": capacity_id}, {"$set": update_data})
    
    logger.info(f"Updated route capacity {capacity_id}")
    
    return await get_route_capacity(capacity_id)


@admin_ess_router.delete("/capacity/{capacity_id}", status_code=204)
async def delete_route_capacity(capacity_id: str):
    """
    DELETE /api/admin/v1/routes/capacity/{capacity_id}
    
    Supprimer une capacité de tournée.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    result = await db.kdm_route_capacity.delete_one({"id": capacity_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Capacity not found")
    
    logger.info(f"Deleted route capacity {capacity_id}")
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
