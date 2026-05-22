"""
KDMARCHE × O'SCOP - Admin API Routes for Zones & Preparation Options
CRUD complet conforme au schéma OpenAPI 3.0
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

logger = logging.getLogger(__name__)

# Router
admin_zones_router = APIRouter(prefix="/api/admin/v1")

# Database reference
db = None

# OPA cache regeneration function reference
_regen_opa_cache = None


def set_admin_zones_database(database):
    """Set database reference from main server"""
    global db
    db = database


def set_opa_cache_regen_callback(callback):
    """Set callback for OPA cache regeneration"""
    global _regen_opa_cache
    _regen_opa_cache = callback


async def trigger_opa_cache_regen():
    """Trigger OPA cache regeneration after zone/option changes"""
    global _regen_opa_cache
    if _regen_opa_cache:
        await _regen_opa_cache()
    else:
        # Fallback: regenerate directly
        from routes_b2b import regenerate_opa_cache
        await regenerate_opa_cache()


# ============== INITIALIZATION ==============

async def init_zones_and_options():
    """Initialize zones and options if not exist"""
    # Initialize zones
    zones_count = await db.kdm_zones.count_documents({})
    if zones_count == 0:
        logger.info("Initializing default zones...")
        for zone_data in DEFAULT_ZONES:
            zone = ZoneInDB(**zone_data)
            await db.kdm_zones.insert_one(zone.dict())
        logger.info(f"Initialized {len(DEFAULT_ZONES)} zones")
    
    # Initialize options
    options_count = await db.zone_preparation_options.count_documents({})
    if options_count == 0:
        logger.info("Initializing default preparation options...")
        for opt_data in DEFAULT_ZONE_PREPARATION_OPTIONS:
            opt = ZonePreparationOptionInDB(**opt_data)
            if opt.tva_exonerated:
                opt.price_ttc_cents = opt.price_ht_cents
            else:
                opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
            await db.zone_preparation_options.insert_one(opt.dict())
        logger.info(f"Initialized {len(DEFAULT_ZONE_PREPARATION_OPTIONS)} preparation options")


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


# ============== PUBLIC B2B ENDPOINTS ==============

@admin_zones_router.get(
    "/b2b/zones/{zone_code}/prep-options",
    response_model=List[ZonePreparationOptionResponse],
    tags=["B2B Public"]
)
async def public_get_zone_prep_options(zone_code: str):
    """
    [PUBLIC B2B] Options de préparation disponibles pour une zone.
    
    Renvoie uniquement les options enabled=true avec contraintes et prix.
    """
    await init_zones_and_options()
    
    options = await db.zone_preparation_options.find(
        {
            "zone_code": zone_code,
            "is_active": True,
            "enabled": True
        },
        {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    
    if not options:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune option de préparation pour la zone {zone_code}"
        )
    
    return [ZonePreparationOptionResponse(**opt) for opt in options]


@admin_zones_router.post("/b2b/cart/prep-options/apply", tags=["B2B Public"])
async def apply_cart_prep_options(request: dict):
    """
    [PUBLIC B2B] Appliquer les options de préparation au panier.
    
    Contrôlé par ABAC policy: kdm.prep_options.apply
    
    Body:
    {
        "zone_code": "GUADELOUPE",
        "selections": [{"code": "PREP_PALLET", "qty": 2}],
        "org_id": "org-123",
        "roles": ["CUSTOMER_ORG_BUYER"]
    }
    """
    await init_zones_and_options()
    
    zone_code = request.get("zone_code")
    selections = request.get("selections", [])
    org_id = request.get("org_id")
    roles = request.get("roles", [])
    
    # Build zones config from DB
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    options = await db.zone_preparation_options.find(
        {"is_active": True},
        {"_id": 0}
    ).to_list(500)
    
    zones_config = build_zones_config_from_db(zones, options)
    
    # Evaluate policy
    policy = KDMarcheAccessPolicyV2(zones_config)
    result = policy.evaluate(
        action="kdm.prep_options.apply",
        resource={
            "org_id": org_id,
            "zone_id": zone_code,
            "selections": selections
        },
        subject={
            "org_id": org_id,
            "roles": roles
        }
    )
    
    if not result.get("allow"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "POLICY_DENIED",
                "deny_reasons": result.get("deny_reasons", [])
            }
        )
    
    # Calculate totals for valid selections
    calculated_selections = []
    total_ht = 0
    total_tva = 0
    
    for selection in selections:
        code = selection.get("code")
        qty = selection.get("qty", 1)
        
        # Get option details
        option = await db.zone_preparation_options.find_one({
            "zone_code": zone_code,
            "code": code,
            "enabled": True
        }, {"_id": 0})
        
        if option:
            line_ht = option["price_ht_cents"] * qty
            if option.get("tva_exonerated"):
                line_tva = 0
            else:
                line_tva = int(line_ht * option["tva_rate"] / 100)
            
            calculated_selections.append({
                "code": code,
                "label": option["name"],
                "qty": qty,
                "unit_price_ht_cents": option["price_ht_cents"],
                "total_ht_cents": line_ht,
                "tva_rate": option["tva_rate"],
                "tva_exonerated": option.get("tva_exonerated", False),
                "total_tva_cents": line_tva,
                "total_ttc_cents": line_ht + line_tva
            })
            
            total_ht += line_ht
            total_tva += line_tva
    
    return {
        "allowed": True,
        "zone_code": zone_code,
        "selections": calculated_selections,
        "total_ht_cents": total_ht,
        "total_tva_cents": total_tva,
        "total_ttc_cents": total_ht + total_tva,
        "policy_result": result
    }


# ============== CONFIG EXPORT ==============

@admin_zones_router.get("/zones/export/config", tags=["Zones"])
async def export_zones_config():
    """
    Exporter la configuration zones/options au format JSON standardisé.
    
    Utile pour la synchronisation OPA ou export.
    """
    await init_zones_and_options()
    
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    options = await db.zone_preparation_options.find(
        {"is_active": True},
        {"_id": 0}
    ).to_list(500)
    
    zones_config = build_zones_config_from_db(zones, options)
    
    return export_zones_config_to_json(zones_config)


@admin_zones_router.post("/zones/reinit-defaults", tags=["Zones"])
async def reinit_zones_defaults():
    """
    Réinitialiser toutes les zones et options par défaut.
    
    ATTENTION: Supprime toutes les données existantes!
    """
    # Delete all
    await db.kdm_zones.delete_many({})
    await db.zone_preparation_options.delete_many({})
    
    # Reinit
    for zone_data in DEFAULT_ZONES:
        zone = ZoneInDB(**zone_data)
        await db.kdm_zones.insert_one(zone.dict())
    
    for opt_data in DEFAULT_ZONE_PREPARATION_OPTIONS:
        opt = ZonePreparationOptionInDB(**opt_data)
        if opt.tva_exonerated:
            opt.price_ttc_cents = opt.price_ht_cents
        else:
            opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
        await db.zone_preparation_options.insert_one(opt.dict())
    
    # Trigger OPA cache regeneration
    await trigger_opa_cache_regen()
    
    return {
        "message": "Zones et options réinitialisées",
        "zones_count": len(DEFAULT_ZONES),
        "options_count": len(DEFAULT_ZONE_PREPARATION_OPTIONS)
    }
