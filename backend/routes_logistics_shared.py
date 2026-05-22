"""
Shared logistics constants used by both routes_ess.py and routes_v1_logiscop.py.

Extracted into this module to break the circular import between:
- routes_ess.py (ESS Route / Tournées Mutualisées API)
- routes_v1_logiscop.py (LOGI'SCOP V1 delivery API)

Both modules now depend only on this shared module (unidirectional DAG):
    routes_logistics_shared  ←─  routes_ess
                            ←─  routes_v1_logiscop  ←─  (uses routes_ess functions)
"""

# ============== DELIVERY POLICY (LOGI'SCOP) ==============
# Per-zone postal-code policy used by routes_v1_logiscop for standard delivery.
DELIVERY_POLICY = {
    "971": {  # Guadeloupe
        "zone_name": "Guadeloupe",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 1000,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 250,
        "rate_per_kg_cents": 45,
        "rate_per_m3_cents": 8500,
        "vat_rate": 8.5,
        "estimated_days": "3-5",
    },
    "972": {  # Martinique
        "zone_name": "Martinique",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 1000,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 280,
        "rate_per_kg_cents": 50,
        "rate_per_m3_cents": 9000,
        "vat_rate": 8.5,
        "estimated_days": "3-5",
    },
    "973": {  # Guyane
        "zone_name": "Guyane",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 5,
        "max_weight_kg": 500,
        "min_value_cents": 10000,
        "express_enabled": False,
        "base_rate_cents": 450,
        "rate_per_kg_cents": 75,
        "rate_per_m3_cents": 15000,
        "vat_rate": 0,
        "estimated_days": "5-7",
    },
    "974": {  # La Réunion
        "zone_name": "La Réunion",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 0,
        "max_weight_kg": 800,
        "min_value_cents": 0,
        "express_enabled": True,
        "base_rate_cents": 320,
        "rate_per_kg_cents": 55,
        "rate_per_m3_cents": 11000,
        "vat_rate": 8.5,
        "estimated_days": "4-6",
    },
    "976": {  # Mayotte
        "zone_name": "Mayotte",
        "delivery_enabled": True,
        "pickup_required": True,
        "min_weight_kg": 2,
        "max_weight_kg": 300,
        "min_value_cents": 5000,
        "express_enabled": False,
        "base_rate_cents": 380,
        "rate_per_kg_cents": 65,
        "rate_per_m3_cents": 12000,
        "vat_rate": 0,
        "estimated_days": "5-7",
    },
}


# ============== ROUTE POLICY (ESS Route Tournées) ==============
# Default route policy fallback (used when DB is empty).
DEFAULT_ROUTE_POLICY = {
    "GUADELOUPE": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 120,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20},
            {"code": "RECENT_LATE_CANCEL", "weight": -30},
        ],
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
            {"code": "RECENT_LATE_CANCEL", "weight": -30},
        ],
    },
    "GUYANE": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 60,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20},
        ],
    },
    "REUNION": {
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 80,
        "priority_rules": [
            {"code": "COMPLIANCE_OK", "weight": 40},
            {"code": "RELIABLE_PICKUPS", "weight": 30},
            {"code": "LOW_INCIDENTS", "weight": 20},
        ],
    },
    "MAYOTTE": {
        "ess_route_enabled": False,
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 40,
        "priority_rules": [],
    },
}


# ESS Route Tariffs (reduced due to mutualization)
ESS_ROUTE_TARIFFS = {
    "GUADELOUPE": {
        "base_rate_cents": 180,
        "rate_per_kg_cents": 35,
        "rate_per_carton_cents": 120,
        "vat_rate": 8.5,
        "estimated_days": "2-4",
    },
    "MARTINIQUE": {
        "base_rate_cents": 200,
        "rate_per_kg_cents": 38,
        "rate_per_carton_cents": 130,
        "vat_rate": 8.5,
        "estimated_days": "2-4",
    },
    "GUYANE": {
        "base_rate_cents": 350,
        "rate_per_kg_cents": 60,
        "rate_per_carton_cents": 200,
        "vat_rate": 0,
        "estimated_days": "4-6",
    },
    "REUNION": {
        "base_rate_cents": 250,
        "rate_per_kg_cents": 45,
        "rate_per_carton_cents": 150,
        "vat_rate": 8.5,
        "estimated_days": "3-5",
    },
    "MAYOTTE": {
        "base_rate_cents": 300,
        "rate_per_kg_cents": 55,
        "rate_per_carton_cents": 180,
        "vat_rate": 0,
        "estimated_days": "5-7",
    },
}
