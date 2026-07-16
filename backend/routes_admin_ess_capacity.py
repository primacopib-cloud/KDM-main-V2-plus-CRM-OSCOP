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

admin_ess_capacity_router = APIRouter(prefix="/api/admin/v1/routes", tags=["Admin ESS Routes"])

db = None

def set_admin_ess_capacity_database(database):
    global db
    db = database

from routes_admin_ess import (
    ZoneRef, RouteCapacityBase, RouteCapacityCreate, RouteCapacityUpdate,
    RouteCapacityResponse, BulkCapacityCreate, get_zone_by_code, get_zone_ref,
)

# ============== ROUTE CAPACITY ENDPOINTS ==============

@admin_ess_capacity_router.get("/capacity", response_model=List[RouteCapacityResponse])
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


@admin_ess_capacity_router.post("/capacity", response_model=RouteCapacityResponse, status_code=201)
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


@admin_ess_capacity_router.post("/capacity/bulk", response_model=List[RouteCapacityResponse], status_code=201)
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


@admin_ess_capacity_router.get("/capacity/{capacity_id}", response_model=RouteCapacityResponse)
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


@admin_ess_capacity_router.patch("/capacity/{capacity_id}", response_model=RouteCapacityResponse)
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


@admin_ess_capacity_router.delete("/capacity/{capacity_id}", status_code=204)
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


