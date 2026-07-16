"""KDMARCHE × LOGI'SCOP V1 — Pricing & policy helpers (split from routes_v1_logiscop.py)."""
from typing import Dict, Any
import math
import logging

from routes_logistics_shared import DELIVERY_POLICY
from logiscop_v1_models import PREPARATION_FEES, SLOT_SUPPLEMENTS

logger = logging.getLogger(__name__)

# ============== HELPER FUNCTIONS ==============

def calculate_transport_cost(zone_code: str, weight_kg: float, volume_m3: float = 0) -> Dict[str, Any]:
    """Calculate transport cost using weight/volume rule (payant pour)"""
    policy = DELIVERY_POLICY.get(zone_code)
    if not policy:
        return {"error": "ZONE_NOT_FOUND"}
    
    # Weight-based cost
    weight_cost = policy["base_rate_cents"] + int(weight_kg * policy["rate_per_kg_cents"])
    
    # Volume-based cost (if volume provided)
    volume_cost = 0
    if volume_m3 and volume_m3 > 0:
        volume_cost = policy["base_rate_cents"] + int(volume_m3 * policy["rate_per_m3_cents"])
    
    # Apply "payant pour" rule (higher of the two)
    if volume_cost > weight_cost:
        billing_mode = "volume"
        transport_ht_cents = volume_cost
    else:
        billing_mode = "weight"
        transport_ht_cents = weight_cost
    
    return {
        "transport_ht_cents": transport_ht_cents,
        "billing_mode": billing_mode,
        "weight_cost_cents": weight_cost,
        "volume_cost_cents": volume_cost
    }


def calculate_preparation_fees(weight_kg: float, items_count: int) -> Dict[str, Any]:
    """Calculate preparation fees"""
    fees = 0
    lines = []
    
    # Picking per line
    picking_fee = items_count * PREPARATION_FEES["picking_per_line"]
    fees += picking_fee
    lines.append({"code": "PICKING", "label": f"Picking ({items_count} ligne(s))", "cents": picking_fee})
    
    # Packaging based on weight
    if weight_kg <= 5:
        pkg_fee = PREPARATION_FEES["packaging_small"]
        pkg_label = "Emballage colis < 5kg"
    elif weight_kg <= 20:
        pkg_fee = PREPARATION_FEES["packaging_medium"]
        pkg_label = "Emballage colis 5-20kg"
    else:
        pkg_fee = PREPARATION_FEES["packaging_large"]
        pkg_label = "Emballage colis > 20kg"
        
        # Add palletization for heavy shipments
        if weight_kg > 100:
            palettes = math.ceil(weight_kg / 500)
            pallet_fee = palettes * PREPARATION_FEES["palettization"]
            fees += pallet_fee
            lines.append({"code": "PALLET", "label": f"Palettisation ({palettes} palette(s))", "cents": pallet_fee})
    
    fees += pkg_fee
    lines.append({"code": "PACKAGING", "label": pkg_label, "cents": pkg_fee})
    
    # Labeling
    label_fee = items_count * PREPARATION_FEES["labeling"]
    fees += label_fee
    lines.append({"code": "LABELING", "label": f"Étiquetage ({items_count})", "cents": label_fee})
    
    return {
        "total_cents": fees,
        "lines": lines
    }


def evaluate_delivery_policy(zone_code: str, fulfillment_mode: str, request_data: Dict) -> Dict[str, Any]:
    """Evaluate OPA-style delivery policy in Python"""
    policy = DELIVERY_POLICY.get(zone_code)
    deny_reasons = []
    
    if not policy:
        return {"allow": False, "deny": ["ZONE_UNKNOWN"]}
    
    if fulfillment_mode == "DELIVERY":
        # Check if delivery is enabled
        if not policy.get("delivery_enabled", False):
            deny_reasons.append("DELIVERY_NOT_AVAILABLE_FOR_ZONE")
        
        # Check weight limits
        weight_kg = request_data.get("weight_kg", 0)
        if weight_kg < policy.get("min_weight_kg", 0):
            deny_reasons.append("DELIVERY_MIN_WEIGHT_NOT_MET")
        if weight_kg > policy.get("max_weight_kg", 9999):
            deny_reasons.append("DELIVERY_MAX_WEIGHT_EXCEEDED")
        
        # Check minimum value
        min_value = policy.get("min_value_cents", 0)
        if min_value > 0 and request_data.get("goods_value_cents", 0) < min_value:
            deny_reasons.append("DELIVERY_MIN_VALUE_NOT_MET")
        
        # Check delivery address
        address = request_data.get("delivery_address")
        if not address:
            deny_reasons.append("DELIVERY_ADDRESS_REQUIRED")
        elif not address.get("street") or not address.get("city") or not address.get("postal_code"):
            deny_reasons.append("DELIVERY_ADDRESS_INCOMPLETE")
        
        # Check delivery slot
        slot = request_data.get("delivery_slot", "AM").upper()
        if slot == "EXPRESS" and not policy.get("express_enabled", False):
            deny_reasons.append("EXPRESS_DELIVERY_NOT_AVAILABLE")
    
    elif fulfillment_mode == "EXW":
        # Check pickup location
        if policy.get("pickup_required", True) and not request_data.get("pickup_location_id"):
            deny_reasons.append("PICKUP_LOCATION_REQUIRED_FOR_EXW")
    
    return {
        "allow": len(deny_reasons) == 0,
        "deny": deny_reasons
    }


