"""KDMARCHE — Schéma préparation : données par défaut (split from schema_preparation.py)."""
# ============== DEFAULT DATA ==============

DEFAULT_ZONES = [
    {
        "code": "GUADELOUPE",
        "label": "Guadeloupe (971)",
        "kind": "OM",
        "currency": "EUR",
        "vat_rate": 8.5,
        "vat_exoneration_allowed": True,
        "exw_only": True,
        "pickup_required": True
    },
    {
        "code": "MARTINIQUE",
        "label": "Martinique (972)",
        "kind": "OM",
        "currency": "EUR",
        "vat_rate": 8.5,
        "vat_exoneration_allowed": True,
        "exw_only": True,
        "pickup_required": True
    },
    {
        "code": "GUYANE",
        "label": "Guyane (973)",
        "kind": "OM",
        "currency": "EUR",
        "vat_rate": 0,  # Exonéré TVA
        "vat_exoneration_allowed": True,
        "exw_only": True,
        "pickup_required": True
    },
    {
        "code": "REUNION",
        "label": "La Réunion (974)",
        "kind": "OM",
        "currency": "EUR",
        "vat_rate": 8.5,
        "vat_exoneration_allowed": True,
        "exw_only": True,
        "pickup_required": True
    },
    {
        "code": "MAYOTTE",
        "label": "Mayotte (976)",
        "kind": "OM",
        "currency": "EUR",
        "vat_rate": 0,  # Exonéré TVA
        "vat_exoneration_allowed": True,
        "exw_only": True,
        "pickup_required": True
    },
]

DEFAULT_ZONE_PREPARATION_OPTIONS = [
    # Zone GUADELOUPE
    {
        "zone_code": "GUADELOUPE",
        "code": "PREP_PALLET",
        "preparation_type": "PREP_PALLET",
        "name": "Préparation palette",
        "unit_label": "palette",
        "description": "Préparation et palettisation complète",
        "pricing_mode": "PALLET",
        "price_ht_cents": 1800,  # 18€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 50,
        "includes": ["filmage", "étiquetage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 24,
        "enabled": True,
        "is_default": True,
        "sort_order": 1
    },
    {
        "zone_code": "GUADELOUPE",
        "code": "PREP_CARTON",
        "preparation_type": "PREP_CARTON",
        "name": "Préparation cartons",
        "unit_label": "carton",
        "description": "Prix par carton préparé",
        "pricing_mode": "CARTON",
        "price_ht_cents": 350,  # 3.50€/carton
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 500,
        "includes": ["emballage"],
        "excludes": [],
        "sla_lead_time_hours": 48,
        "enabled": True,
        "sort_order": 2
    },
    {
        "zone_code": "GUADELOUPE",
        "code": "PREP_CONTAINER",
        "preparation_type": "PREP_CONTAINER",
        "name": "Préparation container",
        "unit_label": "container",
        "description": "Empotage container complet",
        "pricing_mode": "CONTAINER",
        "price_ht_cents": 25000,  # 250€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 5,
        "includes": ["calage", "arrimage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 72,
        "enabled": False,  # Désactivé par défaut
        "sort_order": 3
    },
    {
        "zone_code": "GUADELOUPE",
        "code": "MANUTENTION",
        "preparation_type": "MANUTENTION",
        "name": "Manutention EXW",
        "unit_label": "forfait",
        "description": "Chargement sur véhicule",
        "pricing_mode": "FIXED",
        "price_ht_cents": 2500,  # 25€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 1,
        "includes": ["chargement"],
        "excludes": [],
        "sla_lead_time_hours": 2,
        "enabled": True,
        "sort_order": 4
    },
    
    # Zone MARTINIQUE
    {
        "zone_code": "MARTINIQUE",
        "code": "PREP_PALLET",
        "preparation_type": "PREP_PALLET",
        "name": "Préparation palette",
        "unit_label": "palette",
        "description": "Préparation et palettisation complète",
        "pricing_mode": "PALLET",
        "price_ht_cents": 2000,  # 20€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 50,
        "includes": ["filmage", "étiquetage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 24,
        "enabled": True,
        "is_default": True,
        "sort_order": 1
    },
    {
        "zone_code": "MARTINIQUE",
        "code": "PREP_CARTON",
        "preparation_type": "PREP_CARTON",
        "name": "Préparation cartons",
        "unit_label": "carton",
        "description": "Prix par carton préparé",
        "pricing_mode": "CARTON",
        "price_ht_cents": 400,  # 4€/carton
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 500,
        "includes": ["emballage"],
        "excludes": [],
        "sla_lead_time_hours": 48,
        "enabled": True,
        "sort_order": 2
    },
    {
        "zone_code": "MARTINIQUE",
        "code": "PREP_CONTAINER",
        "preparation_type": "PREP_CONTAINER",
        "name": "Préparation container",
        "unit_label": "container",
        "description": "Empotage container complet",
        "pricing_mode": "CONTAINER",
        "price_ht_cents": 28000,  # 280€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 5,
        "includes": ["calage", "arrimage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 72,
        "enabled": False,
        "sort_order": 3
    },
    
    # Zone GUYANE (TVA 0%)
    {
        "zone_code": "GUYANE",
        "code": "PREP_PALLET",
        "preparation_type": "PREP_PALLET",
        "name": "Préparation palette",
        "unit_label": "palette",
        "description": "Préparation et palettisation complète",
        "pricing_mode": "PALLET",
        "price_ht_cents": 2200,  # 22€
        "tva_rate": 0,
        "tva_exonerated": True,  # Guyane = exonéré TVA
        "min_qty": 1,
        "max_qty": 50,
        "includes": ["filmage", "étiquetage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 48,
        "enabled": True,
        "is_default": True,
        "sort_order": 1
    },
    {
        "zone_code": "GUYANE",
        "code": "PREP_CARTON",
        "preparation_type": "PREP_CARTON",
        "name": "Préparation cartons",
        "unit_label": "carton",
        "description": "Prix par carton préparé",
        "pricing_mode": "CARTON",
        "price_ht_cents": 450,  # 4.50€/carton
        "tva_rate": 0,
        "tva_exonerated": True,
        "min_qty": 1,
        "max_qty": 500,
        "includes": ["emballage"],
        "excludes": [],
        "sla_lead_time_hours": 72,
        "enabled": True,
        "sort_order": 2
    },
    {
        "zone_code": "GUYANE",
        "code": "PREP_CONTAINER",
        "preparation_type": "PREP_CONTAINER",
        "name": "Préparation container",
        "unit_label": "container",
        "description": "Empotage container complet",
        "pricing_mode": "CONTAINER",
        "price_ht_cents": 30000,  # 300€
        "tva_rate": 0,
        "tva_exonerated": True,
        "min_qty": 1,
        "max_qty": 5,
        "includes": ["calage", "arrimage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 96,
        "enabled": True,
        "sort_order": 3
    },
    
    # Zone REUNION
    {
        "zone_code": "REUNION",
        "code": "PREP_PALLET",
        "preparation_type": "PREP_PALLET",
        "name": "Préparation palette",
        "unit_label": "palette",
        "description": "Préparation et palettisation complète",
        "pricing_mode": "PALLET",
        "price_ht_cents": 2500,  # 25€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 50,
        "includes": ["filmage", "étiquetage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 24,
        "enabled": True,
        "is_default": True,
        "sort_order": 1
    },
    {
        "zone_code": "REUNION",
        "code": "PREP_CARTON",
        "preparation_type": "PREP_CARTON",
        "name": "Préparation cartons",
        "unit_label": "carton",
        "description": "Prix par carton préparé",
        "pricing_mode": "CARTON",
        "price_ht_cents": 500,  # 5€/carton
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 500,
        "includes": ["emballage"],
        "excludes": [],
        "sla_lead_time_hours": 48,
        "enabled": True,
        "sort_order": 2
    },
    {
        "zone_code": "REUNION",
        "code": "PREP_CONTAINER",
        "preparation_type": "PREP_CONTAINER",
        "name": "Préparation container",
        "unit_label": "container",
        "description": "Empotage container complet",
        "pricing_mode": "CONTAINER",
        "price_ht_cents": 35000,  # 350€
        "tva_rate": 8.5,
        "tva_exonerated": False,
        "min_qty": 1,
        "max_qty": 5,
        "includes": ["calage", "arrimage"],
        "excludes": ["transport"],
        "sla_lead_time_hours": 72,
        "enabled": False,
        "sort_order": 3
    },
]
