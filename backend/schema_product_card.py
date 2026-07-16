"""
KDMARCHE × O'SCOP - Modèle de Fiche Produit Professionnelle Multi-Catégories
Adapté pour : Alimentaire, Matériaux, Biens d'équipement, Matières premières, etc.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, date

from schema_product_card_parts import *  # noqa: F401,F403
from schema_product_card_parts import (
    ProductCategory, ProductStatus, UnitType, TemperatureRange, HazardClass,
    Dimensions, Weight, Pricing, Stock, Packaging, Origin, NutritionInfo,
    Allergens, Conservation, TechnicalSpecs, Warranty, Compliance, Media, Logistics,
)

# ============== MAIN PRODUCT MODEL ==============

class ProductCard(BaseModel):
    """
    Fiche Produit Professionnelle Multi-Catégories
    Modèle complet et polyvalent pour tous types de produits B2B
    """
    
    # === IDENTIFICATION ===
    id: Optional[str] = Field(None, description="ID unique")
    sku: str = Field(..., description="Référence interne (SKU)")
    ean: Optional[str] = Field(None, description="Code-barres EAN-13")
    upc: Optional[str] = Field(None, description="Code UPC")
    manufacturer_ref: Optional[str] = Field(None, description="Référence fabricant")
    
    # === INFORMATIONS DE BASE ===
    name: str = Field(..., description="Nom du produit")
    short_description: Optional[str] = Field(None, max_length=200, description="Description courte")
    description: Optional[str] = Field(None, description="Description complète")
    
    # === CLASSIFICATION ===
    category: ProductCategory = Field(..., description="Catégorie principale")
    subcategory: Optional[str] = Field(None, description="Sous-catégorie")
    tags: List[str] = Field(default_factory=list, description="Tags/mots-clés")
    brand: Optional[str] = Field(None, description="Marque")
    manufacturer: Optional[str] = Field(None, description="Fabricant")
    
    # === STATUT ===
    status: ProductStatus = Field(ProductStatus.DRAFT)
    is_active: bool = Field(True)
    is_new: bool = Field(False, description="Nouveauté")
    is_featured: bool = Field(False, description="Mis en avant")
    
    # === UNITÉ DE VENTE ===
    unit_type: UnitType = Field(UnitType.PIECE)
    unit_label: str = Field("unité", description="Libellé unité (ex: bouteille, sac, etc.)")
    
    # === SECTIONS DÉTAILLÉES ===
    dimensions: Optional[Dimensions] = None
    weight: Optional[Weight] = None
    pricing: Pricing
    stock: Optional[Stock] = None
    packaging: Optional[Packaging] = None
    origin: Optional[Origin] = None
    
    # === SECTIONS SPÉCIFIQUES PAR CATÉGORIE ===
    # Alimentaire
    nutrition: Optional[NutritionInfo] = None
    allergens: Optional[Allergens] = None
    conservation: Optional[Conservation] = None
    ingredients: Optional[str] = Field(None, description="Liste des ingrédients")
    
    # Équipements / Matériaux
    technical_specs: Optional[TechnicalSpecs] = None
    warranty: Optional[Warranty] = None
    
    # Conformité (tous produits)
    compliance: Optional[Compliance] = None
    
    # === MÉDIAS ET DOCUMENTS ===
    media: Optional[Media] = None
    
    # === LOGISTIQUE ===
    logistics: Optional[Logistics] = None
    
    # === VENDOR ===
    vendor_id: Optional[str] = Field(None, description="ID vendeur")
    vendor_name: Optional[str] = Field(None, description="Nom vendeur")
    
    # === MÉTADONNÉES ===
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # === CHAMPS PERSONNALISÉS ===
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Champs personnalisés")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('price_ttc_cents', pre=True, always=True)
    def calculate_ttc(cls, v, values):
        if 'pricing' in values and values['pricing']:
            pricing = values['pricing']
            if isinstance(pricing, dict):
                ht = pricing.get('price_ht_cents', 0)
                tva = pricing.get('tva_rate', 20.0)
            else:
                ht = pricing.price_ht_cents
                tva = pricing.tva_rate
            return int(ht * (1 + tva / 100))
        return v


# ============== TEMPLATES PAR CATÉGORIE ==============

def get_product_template(category: ProductCategory) -> Dict[str, Any]:
    """
    Retourne un template de fiche produit pré-rempli selon la catégorie
    """
    
    base_template = {
        "sku": "",
        "name": "",
        "category": category.value,
        "status": "draft",
        "unit_type": "piece",
        "pricing": {
            "price_ht_cents": 0,
            "currency": "EUR",
            "tva_rate": 20.0
        }
    }
    
    if category == ProductCategory.ALIMENTAIRE:
        return {
            **base_template,
            "unit_type": "kg",
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 5.5},
            "nutrition": {
                "serving_size_g": 100,
                "energy_kcal": None,
                "fat_g": None,
                "carbohydrates_g": None,
                "protein_g": None,
                "salt_g": None
            },
            "allergens": {"contains": [], "may_contain": [], "free_from": []},
            "conservation": {
                "temperature_range": "ambient",
                "shelf_life_days": None,
                "dlc_type": "DDM"
            },
            "origin": {"country_code": "FR", "country_name": "France"},
            "compliance": {"haccp_compliant": True}
        }
    
    elif category == ProductCategory.BOISSONS:
        return {
            **base_template,
            "unit_type": "L",
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 5.5},
            "packaging": {"unit_per_pack": 6, "packaging_type": "bouteille"},
            "conservation": {"temperature_range": "ambient"},
            "origin": {"country_code": "FR", "country_name": "France"}
        }
    
    elif category == ProductCategory.MATERIAUX:
        return {
            **base_template,
            "unit_type": "m²",
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20.0},
            "dimensions": {"length_cm": None, "width_cm": None, "height_cm": None},
            "weight": {"net_weight_kg": None},
            "technical_specs": {
                "material": "",
                "norms": [],
                "certifications": []
            },
            "compliance": {"ce_marking": True},
            "logistics": {"is_stackable": True, "is_fragile": False}
        }
    
    elif category == ProductCategory.EQUIPEMENTS:
        return {
            **base_template,
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20.0},
            "technical_specs": {
                "power_watts": None,
                "voltage": "220-240V",
                "norms": ["CE"],
                "certifications": []
            },
            "warranty": {
                "duration_months": 24,
                "warranty_type": "standard",
                "manufacturer_warranty": True
            },
            "compliance": {"ce_marking": True},
            "media": {"user_manual_url": None}
        }
    
    elif category == ProductCategory.MATIERES_PREMIERES:
        return {
            **base_template,
            "unit_type": "kg",
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20.0},
            "technical_specs": {
                "composition": "",
                "custom_specs": {"pureté": "", "grade": ""}
            },
            "origin": {"country_code": "", "country_name": ""},
            "compliance": {"reach_compliant": True},
            "logistics": {"min_order_quantity": 100}
        }
    
    elif category == ProductCategory.CHIMIE:
        return {
            **base_template,
            "unit_type": "L",
            "pricing": {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20.0},
            "technical_specs": {"composition": ""},
            "compliance": {
                "reach_compliant": True,
                "hazard_class": "none",
                "safety_data_sheet_url": None
            },
            "logistics": {"requires_adr": False}
        }
    
    else:
        return base_template


# ============== EXPORT ==============

__all__ = [
    "ProductCategory",
    "ProductStatus", 
    "UnitType",
    "TemperatureRange",
    "HazardClass",
    "Dimensions",
    "Weight",
    "Pricing",
    "Stock",
    "Packaging",
    "Origin",
    "NutritionInfo",
    "Allergens",
    "Conservation",
    "TechnicalSpecs",
    "Warranty",
    "Compliance",
    "Media",
    "Logistics",
    "ProductCard",
    "get_product_template"
]
