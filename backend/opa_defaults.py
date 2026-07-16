"""KDMARCHE OPA — Models & default policies (split from routes_opa_bundle.py)."""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

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


