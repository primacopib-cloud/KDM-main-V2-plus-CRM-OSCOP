"""KDMARCHE OPA — Bundle generation from DB (split from routes_opa_bundle.py)."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import tarfile
import io
import json
import os
import logging
from pathlib import Path

from opa_defaults import (
    ZonePrepOption, ZoneConfig, ZonePolicy, OPABundleData,
    get_default_zones_config, get_default_zones_policy, get_default_delivery_policy,
    get_default_route_policy, get_default_route_capacity,
)

logger = logging.getLogger(__name__)

db = None

def set_opa_gen_database(database):
    global db
    db = database

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


