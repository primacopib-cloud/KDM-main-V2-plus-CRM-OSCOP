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

admin_ess_rules_router = APIRouter(prefix="/api/admin/v1/routes", tags=["Admin ESS Routes"])

db = None

def set_admin_ess_rules_database(database):
    global db
    db = database

from routes_admin_ess import (
    ZoneRef, RoutePriorityRuleBase, RoutePriorityRuleCreate, RoutePriorityRuleUpdate,
    RoutePriorityRuleResponse, BulkRulesCreate, get_zone_by_code, get_zone_ref,
)

# ============== PRIORITY RULES ENDPOINTS ==============

@admin_ess_rules_router.get("/rules", response_model=List[RoutePriorityRuleResponse])
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


@admin_ess_rules_router.post("/rules", response_model=RoutePriorityRuleResponse, status_code=201)
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


@admin_ess_rules_router.post("/rules/bulk", response_model=List[RoutePriorityRuleResponse], status_code=201)
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


@admin_ess_rules_router.get("/rules/{rule_id}", response_model=RoutePriorityRuleResponse)
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


@admin_ess_rules_router.patch("/rules/{rule_id}", response_model=RoutePriorityRuleResponse)
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


@admin_ess_rules_router.delete("/rules/{rule_id}", status_code=204)
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


