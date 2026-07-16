"""KDMARCHE OPA — Policy evaluation & API endpoints (split from routes_opa_bundle.py)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import io
import json
import logging

from opa_defaults import OPAInput, OPAInputResource
from opa_bundle_gen import (
    generate_zones_config_from_db, generate_zones_policy_from_db,
    generate_delivery_policy_from_db, generate_route_policy_from_db,
    generate_route_capacity_from_db, generate_data_json,
    get_policy_files, create_bundle_tarball,
    set_opa_gen_database,
)

logger = logging.getLogger(__name__)

opa_bundle_router = APIRouter(prefix="/api/opa")

db = None

def set_opa_bundle_database(database):
    global db
    db = database
    set_opa_gen_database(database)

# ============== POLICY EVALUATION (Python-based) ==============

def evaluate_incoterm_policy(zones_policy: Dict, resource: Dict) -> Dict[str, Any]:
    """Évalue la policy incoterm en Python (équivalent kdm_incoterm.rego)"""
    zone_code = resource.get("zone_code", "").upper()
    policy = zones_policy.get(zone_code)
    
    deny = []
    
    # Zone inconnue ?
    if policy is None:
        deny.append("ZONE_UNKNOWN")
        return {"allow": False, "deny": deny}
    
    # EXW requis mais pas fourni ?
    exw_required = policy.get("exw_only", True)
    incoterm = resource.get("incoterm", "").upper()
    
    if exw_required and incoterm != "EXW":
        deny.append("INCOTERM_NOT_ALLOWED_EXW_ONLY")
    
    # Pickup requis mais pas fourni ?
    pickup_required = policy.get("pickup_required", True)
    pickup_location_id = resource.get("pickup_location_id", "")
    
    if pickup_required and not pickup_location_id:
        deny.append("PICKUP_LOCATION_REQUIRED_FOR_EXW")
    
    return {
        "allow": len(deny) == 0,
        "deny": deny
    }


def evaluate_prep_options_policy(zones_config: Dict, resource: Dict) -> Dict[str, Any]:
    """Évalue la policy prep_options en Python (équivalent kdm_prep_options.rego)"""
    zone_code = resource.get("zone_code", "").upper()
    zone = zones_config.get(zone_code)
    
    deny = []
    
    # Zone inconnue ?
    if zone is None:
        deny.append("ZONE_UNKNOWN_FOR_PREP_OPTIONS")
        return {"allow": False, "deny": deny}
    
    prep_options = zone.get("prep_options", {})
    prep_selections = resource.get("prep_selections", [])
    
    for sel in prep_selections:
        code = sel.get("code", "")
        qty = sel.get("qty", 0)
        
        opt_cfg = prep_options.get(code)
        
        # Option inconnue ?
        if opt_cfg is None:
            deny.append(f"PREP_OPTION_UNKNOWN:{code}")
            continue
        
        # Option désactivée ?
        if not opt_cfg.get("enabled", False):
            deny.append(f"PREP_OPTION_DISABLED_FOR_ZONE:{code}")
            continue
        
        # Quantité hors limites ?
        min_qty = opt_cfg.get("min_qty", 1)
        max_qty = opt_cfg.get("max_qty", 100)
        
        if qty < min_qty or qty > max_qty:
            deny.append(f"PREP_OPTION_QTY_OUT_OF_RANGE:{code}")
    
    return {
        "allow": len(deny) == 0,
        "deny": deny
    }


async def evaluate_order_create_policy(input_data: Dict) -> Dict[str, Any]:
    """
    Évalue la policy complète kdm.order.create en Python
    (équivalent kdm_order_create.rego qui combine incoterm + prep)
    """
    # Charger les données
    data_json = await generate_data_json()
    zones_config = data_json.get("zones_config", {})
    zones_policy = data_json.get("zones_policy", {})
    
    resource = input_data.get("resource", {})
    
    # Évaluer les sous-policies
    incoterm_result = evaluate_incoterm_policy(zones_policy, resource)
    prep_result = evaluate_prep_options_policy(zones_config, resource)
    
    # Combiner les résultats
    all_deny = incoterm_result.get("deny", []) + prep_result.get("deny", [])
    
    return {
        "allow": len(all_deny) == 0,
        "deny": all_deny,
        "details": {
            "incoterm": incoterm_result,
            "prep_options": prep_result
        }
    }


# ============== API ENDPOINTS ==============

@opa_bundle_router.get("/bundle/data.json")
async def get_bundle_data():
    """
    GET /api/opa/bundle/data.json
    Retourne le data.json généré depuis MongoDB
    """
    try:
        data = await generate_data_json()
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error generating data.json: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@opa_bundle_router.get("/bundle/download")
async def download_bundle():
    """
    GET /api/opa/bundle/download
    Télécharge le bundle.tar.gz complet (data.json + policies)
    """
    try:
        tarball = await create_bundle_tarball()
        
        return StreamingResponse(
            io.BytesIO(tarball),
            media_type="application/gzip",
            headers={
                "Content-Disposition": "attachment; filename=opa-bundle.tar.gz",
                "Content-Length": str(len(tarball))
            }
        )
    except Exception as e:
        logger.error(f"Error creating bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@opa_bundle_router.get("/policies")
async def list_policies():
    """
    GET /api/opa/policies
    Liste les fichiers policy Rego disponibles
    """
    policies = get_policy_files()
    return {
        "policies": list(policies.keys()),
        "count": len(policies)
    }


@opa_bundle_router.get("/policies/{filename}")
async def get_policy(filename: str):
    """
    GET /api/opa/policies/{filename}
    Retourne le contenu d'un fichier policy Rego
    """
    policies = get_policy_files()
    
    if filename not in policies:
        raise HTTPException(status_code=404, detail=f"Policy not found: {filename}")
    
    return {
        "filename": filename,
        "content": policies[filename]
    }


@opa_bundle_router.post("/evaluate")
async def evaluate_policy(input_data: OPAInput):
    """
    POST /api/opa/evaluate
    Évalue une action contre les policies (évaluation Python native)
    
    Body:
    {
      "action": "kdm.order.create",
      "resource": {
        "zone_code": "GUADELOUPE",
        "incoterm": "EXW",
        "pickup_location_id": "pickup_971",
        "prep_selections": [{"code": "PREP_PALLET", "qty": 2}]
      },
      "subject": {"org_id": "o1", "roles": ["CUSTOMER_ORG_BUYER"]}
    }
    
    Response:
    {
      "allow": true/false,
      "deny": ["REASON1", "REASON2"],
      "details": { ... }
    }
    """
    try:
        if input_data.action == "kdm.order.create":
            result = await evaluate_order_create_policy(input_data.model_dump())
            return result
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown action: {input_data.action}. Supported: kdm.order.create"
            )
    except Exception as e:
        logger.error(f"Policy evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@opa_bundle_router.get("/zones")
async def list_zones_for_opa():
    """
    GET /api/opa/zones
    Liste les zones avec leurs configs et policies (format OPA-ready)
    """
    data = await generate_data_json()
    
    zones_summary = []
    for zone_code in data["zones_config"].keys():
        config = data["zones_config"].get(zone_code, {})
        policy = data["zones_policy"].get(zone_code, {})
        
        zones_summary.append({
            "code": zone_code,
            "prep_options_count": len(config.get("prep_options", {})),
            "prep_options_enabled": [
                k for k, v in config.get("prep_options", {}).items() 
                if v.get("enabled", False)
            ],
            "exw_only": policy.get("exw_only", True),
            "pickup_required": policy.get("pickup_required", True),
            "vat_rate": policy.get("vat_rate", 8.5),
            "vat_exonerated": policy.get("vat_exonerated", False)
        })
    
    return {
        "zones": zones_summary,
        "total": len(zones_summary),
        "generated_at": data.get("generated_at")
    }


@opa_bundle_router.post("/bundle/regenerate")
async def regenerate_bundle():
    """
    POST /api/opa/bundle/regenerate
    Force la régénération du bundle depuis la DB
    et met à jour le cache OPA
    """
    try:
        # Générer les nouvelles données
        data = await generate_data_json()
        
        # Mettre à jour le cache MongoDB
        await db.kdm_opa_cache.update_one(
            {"key": "opa_bundle_data"},
            {
                "$set": {
                    "key": "opa_bundle_data",
                    "data": data,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Bundle regenerated successfully",
            "zones_count": len(data.get("zones_config", {})),
            "generated_at": data.get("generated_at")
        }
    except Exception as e:
        logger.error(f"Error regenerating bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))
