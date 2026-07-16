"""
KDMARCHE Admin Zones — CRUD zones & options de préparation.

Découpé en modules : admin_zones_common, routes_admin_zones_public.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from schema_preparation import (
    ZoneKind, PreparationType, PricingMode,
    ZoneCreate, ZoneUpdate, ZoneResponse, ZoneInDB,
    ZonePreparationOptionCreate, ZonePreparationOptionUpdate,
    ZonePreparationOptionResponse, ZonePreparationOptionInDB,
    DEFAULT_ZONES, DEFAULT_ZONE_PREPARATION_OPTIONS
)
from abac_policy import (
    PrepOptionsPolicy, KDMarcheAccessPolicyV2,
    build_zones_config_from_db, export_zones_config_to_json
)
from admin_zones_common import (
    init_zones_and_options, trigger_opa_cache_regen, set_opa_cache_regen_callback,
    set_admin_zones_common_database,
)
from routes_admin_zones_public import set_admin_zones_public_database

logger = logging.getLogger(__name__)

admin_zones_router = APIRouter(prefix="/api/admin/v1")

db = None

def set_admin_zones_database(database):
    global db
    db = database
    set_admin_zones_common_database(database)
    set_admin_zones_public_database(database)

# ============== ZONES ENDPOINTS ==============

@admin_zones_router.get("/zones", response_model=List[ZoneResponse], tags=["Zones"])
async def list_zones(
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    kind: Optional[ZoneKind] = Query(None, description="Filtrer par type (OM/EXPORT)")
):
    """
    Liste des zones géographiques.
    
    Permissions: KDM_B2B_ADMIN, KDM_FINANCE, SUPER_ADMIN
    """
    await init_zones_and_options()
    
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if kind:
        query["kind"] = kind.value
    
    zones = await db.kdm_zones.find(query, {"_id": 0}).sort("code", 1).to_list(100)
    
    # Add prep_options_count
    result = []
    for zone in zones:
        options_count = await db.zone_preparation_options.count_documents({
            "zone_code": zone["code"],
            "is_active": True
        })
        zone["prep_options_count"] = options_count
        result.append(ZoneResponse(**zone))
    
    return result


@admin_zones_router.post("/zones", response_model=ZoneResponse, status_code=201, tags=["Zones"])
async def create_zone(zone: ZoneCreate):
    """
    Créer une nouvelle zone géographique.
    
    Permissions: KDM_B2B_ADMIN, SUPER_ADMIN
    """
    # Check if code already exists
    existing = await db.kdm_zones.find_one({"code": zone.code})
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"error": "ZONE_CODE_EXISTS", "details": [f"Zone {zone.code} existe déjà"]}
        )
    
    new_zone = ZoneInDB(**zone.dict())
    await db.kdm_zones.insert_one(new_zone.dict())
    
    logger.info(f"Created zone: {new_zone.code}")
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return ZoneResponse(**new_zone.dict(), prep_options_count=0)


@admin_zones_router.get("/zones/{zone_id}", response_model=ZoneResponse, tags=["Zones"])
async def get_zone(zone_id: str):
    """
    Détail d'une zone par ID ou code.
    """
    await init_zones_and_options()
    
    # Try by ID first, then by code
    zone = await db.kdm_zones.find_one({"id": zone_id}, {"_id": 0})
    if not zone:
        zone = await db.kdm_zones.find_one({"code": zone_id}, {"_id": 0})
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    options_count = await db.zone_preparation_options.count_documents({
        "zone_code": zone["code"],
        "is_active": True
    })
    
    return ZoneResponse(**zone, prep_options_count=options_count)


@admin_zones_router.patch("/zones/{zone_id}", response_model=ZoneResponse, tags=["Zones"])
async def update_zone(zone_id: str, update: ZoneUpdate):
    """
    Mettre à jour une zone.
    """
    # Find zone
    zone = await db.kdm_zones.find_one({"id": zone_id})
    if not zone:
        zone = await db.kdm_zones.find_one({"code": zone_id})
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.kdm_zones.update_one(
            {"id": zone["id"]},
            {"$set": update_data}
        )
    
    updated = await db.kdm_zones.find_one({"id": zone["id"]}, {"_id": 0})
    options_count = await db.zone_preparation_options.count_documents({
        "zone_code": updated["code"],
        "is_active": True
    })
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return ZoneResponse(**updated, prep_options_count=options_count)


@admin_zones_router.delete("/zones/{zone_id}", status_code=204, tags=["Zones"])
async def delete_zone(zone_id: str):
    """
    Désactiver une zone (soft delete via is_active=false).
    """
    result = await db.kdm_zones.update_one(
        {"$or": [{"id": zone_id}, {"code": zone_id}]},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return None


# ============== PREP OPTIONS ENDPOINTS ==============

@admin_zones_router.get(
    "/zones/{zone_id}/prep-options",
    response_model=List[ZonePreparationOptionResponse],
    tags=["PrepOptions"]
)
async def list_zone_prep_options(zone_id: str):
    """
    Liste des options de préparation d'une zone.
    """
    await init_zones_and_options()
    
    # Get zone code
    zone = await db.kdm_zones.find_one({"$or": [{"id": zone_id}, {"code": zone_id}]}, {"_id": 0})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    zone_code = zone["code"]
    
    options = await db.zone_preparation_options.find(
        {"zone_code": zone_code},
        {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    
    return [ZonePreparationOptionResponse(**opt) for opt in options]


@admin_zones_router.post(
    "/zones/{zone_id}/prep-options",
    response_model=ZonePreparationOptionResponse,
    status_code=201,
    tags=["PrepOptions"]
)
async def create_prep_option(zone_id: str, option: ZonePreparationOptionCreate):
    """
    Créer une option de préparation pour une zone.
    """
    # Get zone
    zone = await db.kdm_zones.find_one({"$or": [{"id": zone_id}, {"code": zone_id}]}, {"_id": 0})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    zone_code = zone["code"]
    
    # Check if option code already exists for this zone
    existing = await db.zone_preparation_options.find_one({
        "zone_code": zone_code,
        "code": option.code
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "OPTION_CODE_EXISTS",
                "details": [f"Option {option.code} existe déjà pour la zone {zone_code}"]
            }
        )
    
    # Create option
    opt_data = option.dict()
    opt_data["zone_code"] = zone_code
    new_opt = ZonePreparationOptionInDB(**opt_data)
    
    # Calculate TTC
    if new_opt.tva_exonerated:
        new_opt.price_ttc_cents = new_opt.price_ht_cents
    else:
        new_opt.price_ttc_cents = int(new_opt.price_ht_cents * (1 + new_opt.tva_rate / 100))
    
    await db.zone_preparation_options.insert_one(new_opt.dict())
    
    logger.info(f"Created prep option: {new_opt.code} for zone {zone_code}")
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return ZonePreparationOptionResponse(**new_opt.dict())


@admin_zones_router.patch(
    "/zones/{zone_id}/prep-options/{option_id}",
    response_model=ZonePreparationOptionResponse,
    tags=["PrepOptions"]
)
async def update_prep_option(zone_id: str, option_id: str, update: ZonePreparationOptionUpdate):
    """
    Mettre à jour une option de préparation.
    """
    # Find option
    option = await db.zone_preparation_options.find_one({"id": option_id})
    if not option:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    # Recalculate TTC if needed
    if "price_ht_cents" in update_data or "tva_rate" in update_data or "tva_exonerated" in update_data:
        price_ht = update_data.get("price_ht_cents", option["price_ht_cents"])
        tva_rate = update_data.get("tva_rate", option["tva_rate"])
        tva_exonerated = update_data.get("tva_exonerated", option.get("tva_exonerated", False))
        
        if tva_exonerated:
            update_data["price_ttc_cents"] = price_ht
        else:
            update_data["price_ttc_cents"] = int(price_ht * (1 + tva_rate / 100))
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.zone_preparation_options.update_one(
        {"id": option_id},
        {"$set": update_data}
    )
    
    updated = await db.zone_preparation_options.find_one({"id": option_id}, {"_id": 0})
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return ZonePreparationOptionResponse(**updated)


@admin_zones_router.delete(
    "/zones/{zone_id}/prep-options/{option_id}",
    status_code=204,
    tags=["PrepOptions"]
)
async def delete_prep_option(zone_id: str, option_id: str):
    """
    Désactiver une option de préparation.
    """
    result = await db.zone_preparation_options.update_one(
        {"id": option_id},
        {"$set": {"is_active": False, "enabled": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return None


