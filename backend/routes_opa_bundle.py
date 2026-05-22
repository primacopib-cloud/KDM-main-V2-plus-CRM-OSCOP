"""
KDMARCHE × O'SCOP - OPA Bundle Generator
Génère un bundle OPA standard (data.json + policies) depuis MongoDB

Structure du bundle:
  bundle/
    data.json           <- zones_config + zones_policy (généré depuis DB)
    policy/
      kdm_incoterm.rego
      kdm_prep_options.rego
      kdm_order_create.rego
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import tarfile
import io
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Router
opa_bundle_router = APIRouter(prefix="/api/opa")

# Database reference
db = None

def set_opa_bundle_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== MODELS ==============

class ZonePrepOption(BaseModel):
    enabled: bool
    min_qty: int = 1
    max_qty: int = 100
    pricing_mode: str  # PALLET, CARTON, CONTAINER, FIXED, PER_UNIT, PER_KG, PERCENTAGE

class ZoneConfig(BaseModel):
    prep_options: Dict[str, ZonePrepOption]

class ZonePolicy(BaseModel):
    exw_only: bool = True
    pickup_required: bool = True
    vat_rate: Optional[float] = 8.5
    vat_exonerated: Optional[bool] = False

class OPABundleData(BaseModel):
    zones_config: Dict[str, ZoneConfig]
    zones_policy: Dict[str, ZonePolicy]
    generated_at: str
    version: str = "1.0.0"

class OPAInputResource(BaseModel):
    zone_code: str
    incoterm: str = "EXW"
    pickup_location_id: Optional[str] = None
    prep_selections: Optional[List[Dict[str, Any]]] = []

class OPAInput(BaseModel):
    action: str = "kdm.order.create"
    resource: OPAInputResource
    subject: Optional[Dict[str, Any]] = {}


# ============== BUNDLE GENERATION ==============

async def generate_zones_config_from_db() -> Dict[str, Any]:
    """
    Génère zones_config depuis MongoDB (kdm_zones + zone_preparation_options)
    
    Format de sortie:
    {
      "GUADELOUPE": {
        "prep_options": {
          "PREP_PALLET": { "enabled": true, "min_qty": 1, "max_qty": 50, "pricing_mode": "PALLET" },
          ...
        }
      },
      ...
    }
    """
    zones_config = {}
    
    try:
        # Récupérer toutes les zones
        zones = await db.kdm_zones.find({}).to_list(100)
        
        for zone in zones:
            zone_code = zone.get("code", "").upper()
            if not zone_code:
                continue
            
            # Récupérer les options de préparation pour cette zone
            options = await db.zone_preparation_options.find(
                {"zone_code": zone_code}
            ).to_list(50)
            
            prep_options = {}
            for opt in options:
                opt_code = opt.get("code", "")
                if opt_code:
                    # Déterminer le pricing_mode
                    pricing_mode = opt.get("pricing_mode", "FIXED")
                    if "PALLET" in opt_code.upper():
                        pricing_mode = "PALLET"
                    elif "CARTON" in opt_code.upper():
                        pricing_mode = "CARTON"
                    elif "CONTAINER" in opt_code.upper():
                        pricing_mode = "CONTAINER"
                    
                    prep_options[opt_code] = {
                        "enabled": opt.get("enabled", True),
                        "min_qty": opt.get("min_qty", 1),
                        "max_qty": opt.get("max_qty", 100),
                        "pricing_mode": pricing_mode,
                        "price_ht_cents": opt.get("price_ht_cents", 0),
                        "tva_rate": opt.get("tva_rate", zone.get("vat_rate", 8.5))
                    }
            
            zones_config[zone_code] = {
                "prep_options": prep_options
            }
        
        # Si pas de données en DB, utiliser les defaults
        if not zones_config:
            zones_config = get_default_zones_config()
        
        return zones_config
        
    except Exception as e:
        logger.error(f"Error generating zones_config from DB: {e}")
        return get_default_zones_config()


async def generate_zones_policy_from_db() -> Dict[str, Any]:
    """
    Génère zones_policy depuis MongoDB (kdm_zones)
    
    Format de sortie:
    {
      "GUADELOUPE": { "exw_only": true, "pickup_required": true },
      ...
    }
    """
    zones_policy = {}
    
    try:
        zones = await db.kdm_zones.find({}).to_list(100)
        
        for zone in zones:
            zone_code = zone.get("code", "").upper()
            if not zone_code:
                continue
            
            zones_policy[zone_code] = {
                "exw_only": zone.get("exw_only", True),
                "pickup_required": zone.get("pickup_required", True),
                "vat_rate": zone.get("vat_rate", 8.5),
                "vat_exonerated": zone.get("vat_exoneration_allowed", False),
                "kind": zone.get("kind", "OM"),
                "currency": zone.get("currency", "EUR")
            }
        
        # Si pas de données en DB, utiliser les defaults
        if not zones_policy:
            zones_policy = get_default_zones_policy()
        
        return zones_policy
        
    except Exception as e:
        logger.error(f"Error generating zones_policy from DB: {e}")
        return get_default_zones_policy()


def get_default_zones_config() -> Dict[str, Any]:
    """Configuration par défaut des zones DOM-TOM"""
    return {
        "GUADELOUPE": {
            "prep_options": {
                "PREP_PALLET": {"enabled": True, "min_qty": 1, "max_qty": 50, "pricing_mode": "PALLET", "price_ht_cents": 1800},
                "PREP_CARTON": {"enabled": True, "min_qty": 1, "max_qty": 500, "pricing_mode": "CARTON", "price_ht_cents": 250},
                "PREP_CONTAINER": {"enabled": False, "min_qty": 1, "max_qty": 5, "pricing_mode": "CONTAINER", "price_ht_cents": 45000}
            }
        },
        "MARTINIQUE": {
            "prep_options": {
                "PREP_PALLET": {"enabled": True, "min_qty": 1, "max_qty": 50, "pricing_mode": "PALLET", "price_ht_cents": 1800},
                "PREP_CARTON": {"enabled": True, "min_qty": 1, "max_qty": 500, "pricing_mode": "CARTON", "price_ht_cents": 250},
                "PREP_CONTAINER": {"enabled": False, "min_qty": 1, "max_qty": 5, "pricing_mode": "CONTAINER", "price_ht_cents": 45000}
            }
        },
        "GUYANE": {
            "prep_options": {
                "PREP_PALLET": {"enabled": True, "min_qty": 1, "max_qty": 30, "pricing_mode": "PALLET", "price_ht_cents": 2200},
                "PREP_CARTON": {"enabled": True, "min_qty": 1, "max_qty": 300, "pricing_mode": "CARTON", "price_ht_cents": 300},
                "PREP_CONTAINER": {"enabled": True, "min_qty": 1, "max_qty": 10, "pricing_mode": "CONTAINER", "price_ht_cents": 55000}
            }
        },
        "REUNION": {
            "prep_options": {
                "PREP_PALLET": {"enabled": True, "min_qty": 1, "max_qty": 60, "pricing_mode": "PALLET", "price_ht_cents": 2000},
                "PREP_CARTON": {"enabled": True, "min_qty": 1, "max_qty": 600, "pricing_mode": "CARTON", "price_ht_cents": 280},
                "PREP_CONTAINER": {"enabled": True, "min_qty": 1, "max_qty": 8, "pricing_mode": "CONTAINER", "price_ht_cents": 50000}
            }
        },
        "MAYOTTE": {
            "prep_options": {
                "PREP_PALLET": {"enabled": True, "min_qty": 1, "max_qty": 20, "pricing_mode": "PALLET", "price_ht_cents": 2500},
                "PREP_CARTON": {"enabled": True, "min_qty": 1, "max_qty": 200, "pricing_mode": "CARTON", "price_ht_cents": 350},
                "PREP_CONTAINER": {"enabled": False, "min_qty": 1, "max_qty": 3, "pricing_mode": "CONTAINER", "price_ht_cents": 60000}
            }
        }
    }


def get_default_zones_policy() -> Dict[str, Any]:
    """Politiques par défaut des zones DOM-TOM"""
    return {
        "GUADELOUPE": {"exw_only": True, "pickup_required": True, "vat_rate": 8.5, "vat_exonerated": False, "kind": "OM", "currency": "EUR"},
        "MARTINIQUE": {"exw_only": True, "pickup_required": True, "vat_rate": 8.5, "vat_exonerated": False, "kind": "OM", "currency": "EUR"},
        "GUYANE": {"exw_only": True, "pickup_required": True, "vat_rate": 0, "vat_exonerated": True, "kind": "OM", "currency": "EUR"},
        "REUNION": {"exw_only": True, "pickup_required": True, "vat_rate": 8.5, "vat_exonerated": False, "kind": "OM", "currency": "EUR"},
        "MAYOTTE": {"exw_only": True, "pickup_required": True, "vat_rate": 0, "vat_exonerated": True, "kind": "OM", "currency": "EUR"}
    }


def get_default_delivery_policy() -> Dict[str, Any]:
    """Policy de livraison par défaut pour les zones DOM-TOM"""
    return {
        "971": {
            "zone_name": "Guadeloupe",
            "delivery_enabled": True,
            "pickup_required": True,
            "min_weight_kg": 0,
            "max_weight_kg": 1000,
            "min_value_cents": 0,
            "express_enabled": True,
            "vat_rate": 8.5
        },
        "972": {
            "zone_name": "Martinique",
            "delivery_enabled": True,
            "pickup_required": True,
            "min_weight_kg": 0,
            "max_weight_kg": 1000,
            "min_value_cents": 0,
            "express_enabled": True,
            "vat_rate": 8.5
        },
        "973": {
            "zone_name": "Guyane",
            "delivery_enabled": True,
            "pickup_required": True,
            "min_weight_kg": 5,
            "max_weight_kg": 500,
            "min_value_cents": 10000,
            "express_enabled": False,
            "vat_rate": 0
        },
        "974": {
            "zone_name": "La Réunion",
            "delivery_enabled": True,
            "pickup_required": True,
            "min_weight_kg": 0,
            "max_weight_kg": 800,
            "min_value_cents": 0,
            "express_enabled": True,
            "vat_rate": 8.5
        },
        "976": {
            "zone_name": "Mayotte",
            "delivery_enabled": True,
            "pickup_required": True,
            "min_weight_kg": 2,
            "max_weight_kg": 300,
            "min_value_cents": 5000,
            "express_enabled": False,
            "vat_rate": 0
        }
    }


def get_default_route_policy() -> Dict[str, Any]:
    """Policy ESS Route par défaut pour les zones DOM-TOM (Tournées Mutualisées)"""
    return {
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
            "ess_route_enabled": False,
            "window_required": True,
            "min_reliability_score": 50,
            "max_daily_capacity": 40,
            "priority_rules": []
        }
    }


def get_default_route_capacity() -> Dict[str, Any]:
    """Capacité route par défaut (tournées planifiées)"""
    return {
        "GUADELOUPE": {},
        "MARTINIQUE": {},
        "GUYANE": {},
        "REUNION": {},
        "MAYOTTE": {}
    }


async def generate_delivery_policy_from_db() -> Dict[str, Any]:
    """Génère delivery_policy depuis MongoDB kdm_zones"""
    delivery_policy = {}
    
    if db is None:
        logger.warning("Database not initialized, using default delivery policy")
        return get_default_delivery_policy()
    
    try:
        zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        # Mapping code texte -> code numérique DOM
        code_mapping = {
            "GUADELOUPE": "971",
            "MARTINIQUE": "972", 
            "GUYANE": "973",
            "REUNION": "974",
            "MAYOTTE": "976"
        }
        
        for zone in zones:
            zone_code = zone.get("code", "")
            numeric_code = code_mapping.get(zone_code.upper(), zone_code)
            
            delivery_policy[numeric_code] = {
                "zone_name": zone.get("name", zone_code),
                "logiscop_delivery_enabled": zone.get("logiscop_delivery_enabled", False),
                "delivery_enabled": zone.get("logiscop_delivery_enabled", False),
                "pickup_required": zone.get("pickup_required", True),
                "min_cartons": zone.get("delivery_min_cartons", 1),
                "max_cartons": zone.get("delivery_max_cartons", 100),
                "vat_rate": zone.get("vat_rate", 8.5),
                "vat_exonerated": zone.get("vat_exonerated", False)
            }
        
        if not delivery_policy:
            return get_default_delivery_policy()
        
        return delivery_policy
        
    except Exception as e:
        logger.error(f"Error generating delivery_policy from DB: {e}")
        return get_default_delivery_policy()


async def generate_route_policy_from_db() -> Dict[str, Any]:
    """
    Génère route_policy depuis MongoDB (kdm_route_policy + kdm_route_priority_rules)
    
    Format de sortie:
    {
      "GUADELOUPE": {
        "ess_route_enabled": true,
        "window_required": true,
        "min_reliability_score": 60,
        "max_daily_capacity": 120,
        "priority_rules": [
          {"code": "COMPLIANCE_OK", "weight": 40},
          ...
        ]
      },
      ...
    }
    """
    route_policy = {}
    
    if db is None:
        logger.warning("Database not initialized, using default route policy")
        return get_default_route_policy()
    
    try:
        # Récupérer les zones
        zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        # Récupérer toutes les route_policy
        policies = await db.kdm_route_policy.find({}, {"_id": 0}).to_list(100)
        policies_by_zone = {p.get("zone_code", ""): p for p in policies}
        
        # Récupérer toutes les priority_rules
        rules = await db.kdm_route_priority_rules.find({"is_active": True}, {"_id": 0}).to_list(500)
        rules_by_zone = {}
        for rule in rules:
            zone_code = rule.get("zone_code", "")
            if zone_code not in rules_by_zone:
                rules_by_zone[zone_code] = []
            rules_by_zone[zone_code].append({
                "code": rule.get("code", ""),
                "weight": rule.get("weight", 0)
            })
        
        for zone in zones:
            zone_code = zone.get("code", "").upper()
            if not zone_code:
                continue
            
            policy = policies_by_zone.get(zone_code, {})
            zone_rules = rules_by_zone.get(zone_code, [])
            
            # Sort rules by weight descending
            zone_rules.sort(key=lambda x: x.get("weight", 0), reverse=True)
            
            route_policy[zone_code] = {
                "ess_route_enabled": policy.get("ess_route_enabled", False),
                "window_required": policy.get("window_required", True),
                "min_reliability_score": policy.get("min_reliability_score", 0),
                "max_daily_capacity": policy.get("max_daily_capacity", 0),
                "priority_rules": zone_rules
            }
        
        if not route_policy:
            return get_default_route_policy()
        
        return route_policy
        
    except Exception as e:
        logger.error(f"Error generating route_policy from DB: {e}")
        return get_default_route_policy()


async def generate_route_capacity_from_db() -> Dict[str, Any]:
    """
    Génère route_capacity depuis MongoDB (kdm_route_capacity)
    
    Format de sortie:
    {
      "GUADELOUPE": {
        "TOUR-GP-2026W03-THU-AM": {"capacity": 60, "booked": 42, "window_start": "...", "window_end": "..."},
        ...
      },
      ...
    }
    """
    route_capacity = {}
    
    if db is None:
        logger.warning("Database not initialized, using default route capacity")
        return get_default_route_capacity()
    
    try:
        # Récupérer les zones
        zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        # Récupérer toutes les capacités
        capacities = await db.kdm_route_capacity.find({"is_active": True}, {"_id": 0}).to_list(1000)
        
        # Group by zone
        capacity_by_zone = {}
        for cap in capacities:
            zone_code = cap.get("zone_code", "").upper()
            if zone_code not in capacity_by_zone:
                capacity_by_zone[zone_code] = {}
            
            tour_id = cap.get("tour_id", "")
            if tour_id:
                capacity_by_zone[zone_code][tour_id] = {
                    "capacity": cap.get("capacity", 0),
                    "booked": cap.get("booked", 0),
                    "window_start": cap.get("window_start"),
                    "window_end": cap.get("window_end")
                }
        
        for zone in zones:
            zone_code = zone.get("code", "").upper()
            if not zone_code:
                continue
            route_capacity[zone_code] = capacity_by_zone.get(zone_code, {})
        
        if not route_capacity:
            return get_default_route_capacity()
        
        return route_capacity
        
    except Exception as e:
        logger.error(f"Error generating route_capacity from DB: {e}")
        return get_default_route_capacity()


async def generate_data_json() -> Dict[str, Any]:
    """Génère le data.json complet pour le bundle OPA"""
    zones_config = await generate_zones_config_from_db()
    zones_policy = await generate_zones_policy_from_db()
    delivery_policy = await generate_delivery_policy_from_db()
    route_policy = await generate_route_policy_from_db()
    route_capacity = await generate_route_capacity_from_db()
    
    return {
        "zones_config": zones_config,
        "zones_policy": zones_policy,
        "delivery_policy": delivery_policy,
        "route_policy": route_policy,
        "route_capacity": route_capacity,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.3.0"
    }


def get_policy_files() -> Dict[str, str]:
    """Récupère le contenu des fichiers policy Rego"""
    policy_dir = Path(__file__).parent / "opa_bundle" / "policy"
    policies = {}
    
    policy_files = [
        "kdm_incoterm.rego",
        "kdm_prep_options.rego", 
        "kdm_order_create.rego",
        "kdm_delivery.rego",
        "kdm_delivery_route.rego"
    ]
    
    for filename in policy_files:
        filepath = policy_dir / filename
        if filepath.exists():
            policies[filename] = filepath.read_text(encoding="utf-8")
        else:
            logger.warning(f"Policy file not found: {filepath}")
    
    return policies


async def create_bundle_tarball() -> bytes:
    """
    Crée le bundle.tar.gz au format standard OPA
    
    Structure:
      bundle/
        data.json
        policy/
          kdm_incoterm.rego
          kdm_prep_options.rego
          kdm_order_create.rego
    """
    # Générer data.json
    data_json = await generate_data_json()
    data_json_bytes = json.dumps(data_json, indent=2, ensure_ascii=False).encode("utf-8")
    
    # Récupérer les policies
    policies = get_policy_files()
    
    # Créer le tarball en mémoire
    buffer = io.BytesIO()
    
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        # Ajouter data.json
        data_info = tarfile.TarInfo(name="data.json")
        data_info.size = len(data_json_bytes)
        data_info.mtime = int(datetime.now(timezone.utc).timestamp())
        tar.addfile(data_info, io.BytesIO(data_json_bytes))
        
        # Ajouter les fichiers policy
        for filename, content in policies.items():
            content_bytes = content.encode("utf-8")
            policy_info = tarfile.TarInfo(name=f"policy/{filename}")
            policy_info.size = len(content_bytes)
            policy_info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(policy_info, io.BytesIO(content_bytes))
    
    buffer.seek(0)
    return buffer.read()


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
