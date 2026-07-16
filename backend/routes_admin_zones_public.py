"""KDMARCHE Admin Zones — Endpoints publics B2B & export de config (split from routes_admin_zones.py)."""
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
    init_zones_and_options, trigger_opa_cache_regen, set_admin_zones_common_database,
)

logger = logging.getLogger(__name__)

admin_zones_public_router = APIRouter(prefix="/api/admin/v1")

db = None

def set_admin_zones_public_database(database):
    global db
    db = database

# ============== PUBLIC B2B ENDPOINTS ==============

@admin_zones_public_router.get(
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


@admin_zones_public_router.post("/b2b/cart/prep-options/apply", tags=["B2B Public"])
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

@admin_zones_public_router.get("/zones/export/config", tags=["Zones"])
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


@admin_zones_public_router.post("/zones/reinit-defaults", tags=["Zones"])
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
