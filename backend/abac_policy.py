"""
KDMARCHE ABAC — Policies préparation, accès V2 & builders de config zones.

Découpé : dataclasses & ABACPolicyEngine dans abac_engine.py (ré-exportés ici).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from schema_v2 import (
    OrgStatus, SubscriptionStatus, PartnerProvisionStatus,
    WalletStatus, CustomerRole, OscopRole, KdmRole, ZoneKind
)
from abac_engine import (
    PolicySubject, PolicyResource, PolicyContext, PolicyInput, PolicyData,
    PolicyResult, ABACPolicyEngine,
)

logger = logging.getLogger(__name__)

# ============== CONVENIENCE FUNCTIONS ==============
#
# NOTE: The previous helpers `check_pricing_access`, `check_order_access` and
# `check_wallet_consume` were removed in 2026-02 — they were never called from
# anywhere in the codebase (verified via grep). Routes call
# `ABACPolicyEngine().evaluate(input, data)` directly with the typed
# `PolicyInput` / `PolicyData` dataclasses, which keeps callsites explicit
# and avoids long positional argument lists (the previous helpers had 9–13
# positional args, which the code review flagged as error-prone).
#
# If a future caller needs a thin wrapper, prefer building a small
# `OrderAccessContext` / `PricingAccessContext` dataclass at the call site
# rather than reintroducing a wide-signature function.


# ============== PREP OPTIONS POLICY (OPA/REGO STYLE) ==============

class PrepOptionsPolicy:
    """
    OPA/Rego-style policy for preparation options
    
    Rule: Option préparation autorisée uniquement si enabled=true pour la zone
    
    Example input:
    {
      "action": "kdm.prep_options.apply",
      "resource": {
        "org_id": "o1",
        "zone_id": "GUADELOUPE",
        "selections": [
          {"code":"PREP_PALLET","qty":2},
          {"code":"PREP_CONTAINER","qty":1}
        ]
      },
      "subject": {"org_id":"o1","roles":["CUSTOMER_ORG_BUYER"]}
    }
    """
    
    def __init__(self, zones_config: Dict[str, Any]):
        self.zones_config = zones_config
    
    def evaluate(self, action: str, resource: Dict, subject: Dict) -> Dict:
        """Evaluate policy for given input"""
        deny_reasons = []
        warnings = []
        
        if action != "kdm.prep_options.apply":
            return {"allow": True, "warnings": ["Action non concernée"]}
        
        zone_id = resource.get("zone_id")
        selections = resource.get("selections", [])
        
        # Rule 1: Zone must exist
        if not self._zone_exists(zone_id):
            return {"allow": False, "deny_reasons": ["ZONE_UNKNOWN_FOR_PREP_OPTIONS"]}
        
        zone_config = self.zones_config.get(zone_id, {})
        prep_options = zone_config.get("prep_options", {})
        
        # Evaluate each selection
        for selection in selections:
            code = selection.get("code")
            qty = selection.get("qty", 0)
            
            if code not in prep_options:
                deny_reasons.append(f"PREP_OPTION_UNKNOWN:{code}")
                continue
            
            option_config = prep_options.get(code, {})
            
            if not option_config.get("enabled", False):
                deny_reasons.append(f"PREP_OPTION_DISABLED_FOR_ZONE:{code}")
                continue
            
            min_qty = option_config.get("min_qty", 0)
            max_qty = option_config.get("max_qty", 999999)
            if not (min_qty <= qty <= max_qty):
                deny_reasons.append(f"PREP_OPTION_QTY_OUT_OF_RANGE:{code}")
        
        return {
            "allow": len(deny_reasons) == 0,
            "deny_reasons": deny_reasons,
            "warnings": warnings
        }
    
    def _zone_exists(self, zone_id: str) -> bool:
        if not zone_id:
            return False
        zone = self.zones_config.get(zone_id)
        return zone is not None and zone.get("prep_options") is not None


class KDMarcheAccessPolicyV2:
    """
    Policy principale KDMARCHE V2 avec intégration des sous-policies
    """
    
    ALLOWED_ROLES = [
        "CUSTOMER_ORG_BUYER", "CUSTOMER_ORG_ADMIN",
        "KDM_B2B_ADMIN", "KDM_FINANCE", "KDM_WAREHOUSE", "SUPER_ADMIN"
    ]
    
    def __init__(self, zones_config: Dict[str, Any], allowed_zones: Optional[List[str]] = None):
        self.zones_config = zones_config
        self.allowed_zones = allowed_zones
        self.prep_policy = PrepOptionsPolicy(zones_config)
    
    def evaluate(self, action: str, resource: Dict, subject: Dict) -> Dict:
        deny_reasons = []
        
        # Check base access
        roles = subject.get("roles", [])
        if not any(r in self.ALLOWED_ROLES for r in roles):
            deny_reasons.append("BASE_ACCESS_DENIED")
        
        # Check zone is allowed
        zone_id = resource.get("zone_id")
        if zone_id and self.allowed_zones and zone_id not in self.allowed_zones:
            deny_reasons.append(f"ZONE_NOT_ALLOWED:{zone_id}")
        
        # For prep_options.apply action, delegate to prep policy
        if action == "kdm.prep_options.apply":
            prep_result = self.prep_policy.evaluate(action, resource, subject)
            deny_reasons.extend(prep_result.get("deny_reasons", []))
        
        return {
            "allow": len(deny_reasons) == 0,
            "deny_reasons": deny_reasons
        }


def build_zones_config_from_db(zones: List[Dict], options: List[Dict]) -> Dict[str, Any]:
    """Build zones_config JSON from database records"""
    config = {}
    
    options_by_zone = {}
    for opt in options:
        zone_code = opt.get("zone_code")
        if zone_code not in options_by_zone:
            options_by_zone[zone_code] = {}
        
        code = opt.get("code")
        options_by_zone[zone_code][code] = {
            "enabled": opt.get("enabled", False),
            "min_qty": opt.get("min_qty", 1),
            "max_qty": opt.get("max_qty", 999999),
            "pricing_mode": opt.get("pricing_mode"),
            "unit_price_ht_cents": opt.get("price_ht_cents"),
            "tva_rate": opt.get("tva_rate"),
            "tva_exonerated": opt.get("tva_exonerated", False),
        }
    
    for zone in zones:
        code = zone.get("code")
        config[code] = {
            "label": zone.get("label"),
            "kind": zone.get("kind"),
            "vat_rate": zone.get("vat_rate"),
            "is_active": zone.get("is_active", True),
            "prep_options": options_by_zone.get(code, {})
        }
    
    return config


def export_zones_config_to_json(zones_config: Dict) -> Dict:
    """Export zones_config to standardized JSON format"""
    return {
        "version": "1.0",
        "default_zone": list(zones_config.keys())[0] if zones_config else None,
        "zones": zones_config,
        "exported_at": datetime.utcnow().isoformat()
    }

