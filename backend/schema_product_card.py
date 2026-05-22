"""
KDMARCHE × O'SCOP - Modèle de Fiche Produit Professionnelle Multi-Catégories
Adapté pour : Alimentaire, Matériaux, Biens d'équipement, Matières premières, etc.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, date


# ============== ENUMS ==============

class ProductCategory(str, Enum):
    """Catégories principales de produits"""
    ALIMENTAIRE = "alimentaire"
    BOISSONS = "boissons"
    MATERIAUX = "materiaux"
    EQUIPEMENTS = "equipements"
    MATIERES_PREMIERES = "matieres_premieres"
    HYGIENE = "hygiene"
    CHIMIE = "chimie"
    TEXTILE = "textile"
    ELECTRONIQUE = "electronique"
    AUTRE = "autre"


class ProductStatus(str, Enum):
    """Statuts du produit"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"


class UnitType(str, Enum):
    """Unités de mesure"""
    PIECE = "piece"
    KG = "kg"
    GRAMME = "g"
    LITRE = "L"
    ML = "mL"
    METRE = "m"
    CM = "cm"
    M2 = "m²"
    M3 = "m³"
    TONNE = "T"
    PALETTE = "palette"
    CARTON = "carton"
    LOT = "lot"


class TemperatureRange(str, Enum):
    """Plages de température de conservation"""
    AMBIENT = "ambient"           # Température ambiante (15-25°C)
    REFRIGERATED = "refrigerated" # Réfrigéré (0-4°C)
    FROZEN = "frozen"             # Surgelé (-18°C)
    DEEP_FROZEN = "deep_frozen"   # Surgélation profonde (-25°C)
    CONTROLLED = "controlled"     # Température contrôlée spécifique


class HazardClass(str, Enum):
    """Classes de danger (pour produits chimiques/dangereux)"""
    NONE = "none"
    FLAMMABLE = "flammable"
    CORROSIVE = "corrosive"
    TOXIC = "toxic"
    OXIDIZING = "oxidizing"
    EXPLOSIVE = "explosive"
    IRRITANT = "irritant"
    ENVIRONMENTAL = "environmental"


# ============== SUB-MODELS ==============

class Dimensions(BaseModel):
    """Dimensions physiques"""
    length_cm: Optional[float] = Field(None, description="Longueur en cm")
    width_cm: Optional[float] = Field(None, description="Largeur en cm")
    height_cm: Optional[float] = Field(None, description="Hauteur en cm")
    diameter_cm: Optional[float] = Field(None, description="Diamètre en cm")
    volume_l: Optional[float] = Field(None, description="Volume en litres")
    volume_m3: Optional[float] = Field(None, description="Volume en m³")


class Weight(BaseModel):
    """Poids et masse"""
    net_weight_kg: Optional[float] = Field(None, description="Poids net en kg")
    gross_weight_kg: Optional[float] = Field(None, description="Poids brut en kg")
    drained_weight_kg: Optional[float] = Field(None, description="Poids égoutté en kg")
    unit_weight_kg: Optional[float] = Field(None, description="Poids unitaire en kg")


class Pricing(BaseModel):
    """Structure tarifaire"""
    price_ht_cents: int = Field(..., description="Prix HT en centimes")
    currency: str = Field("EUR", description="Devise")
    tva_rate: float = Field(20.0, description="Taux TVA (%)")
    price_ttc_cents: Optional[int] = Field(None, description="Prix TTC calculé")
    
    # Tarification dégressif
    tier_pricing: Optional[List[Dict[str, Any]]] = Field(None, description="Tarifs dégressifs [{'min_qty': 10, 'price_ht_cents': 900}, ...]")
    
    # Prix par zone
    zone_pricing: Optional[Dict[str, int]] = Field(None, description="Prix HT par zone {'GUADELOUPE': 1000, ...}")
    
    # Remises
    discount_percent: Optional[float] = Field(None, description="Remise en %")
    promo_price_ht_cents: Optional[int] = Field(None, description="Prix promo HT")
    promo_start: Optional[datetime] = None
    promo_end: Optional[datetime] = None


class Stock(BaseModel):
    """Gestion des stocks"""
    quantity_available: int = Field(0, description="Quantité disponible")
    quantity_reserved: int = Field(0, description="Quantité réservée")
    quantity_incoming: int = Field(0, description="Quantité en commande")
    reorder_threshold: int = Field(10, description="Seuil de réapprovisionnement")
    max_stock: Optional[int] = Field(None, description="Stock maximum")
    
    # Stock par zone/entrepôt
    stock_by_location: Optional[Dict[str, int]] = Field(None, description="Stock par emplacement")
    
    # Dates
    last_restock_date: Optional[datetime] = None
    next_restock_date: Optional[datetime] = None


class Packaging(BaseModel):
    """Conditionnement et emballage"""
    unit_per_pack: int = Field(1, description="Unités par conditionnement")
    pack_per_carton: Optional[int] = Field(None, description="Conditionnements par carton")
    carton_per_pallet: Optional[int] = Field(None, description="Cartons par palette")
    units_per_pallet: Optional[int] = Field(None, description="Unités par palette")
    
    # Dimensions conditionnement
    pack_dimensions: Optional[Dimensions] = None
    carton_dimensions: Optional[Dimensions] = None
    pallet_dimensions: Optional[Dimensions] = None
    
    # Type d'emballage
    packaging_type: Optional[str] = Field(None, description="Type: bouteille, sachet, carton, vrac, etc.")
    packaging_material: Optional[str] = Field(None, description="Matériau: plastique, verre, carton, etc.")
    is_recyclable: bool = Field(False, description="Emballage recyclable")
    eco_contribution_cents: Optional[int] = Field(None, description="Éco-contribution en centimes")


class Origin(BaseModel):
    """Origine et traçabilité"""
    country_code: str = Field(..., description="Code pays ISO (FR, ES, etc.)")
    country_name: str = Field(..., description="Nom du pays")
    region: Optional[str] = Field(None, description="Région/Province")
    city: Optional[str] = Field(None, description="Ville")
    
    # Labels d'origine
    aoc_aop: Optional[str] = Field(None, description="AOC/AOP")
    igp: Optional[str] = Field(None, description="IGP")
    label_rouge: bool = Field(False)
    
    # Traçabilité
    producer_name: Optional[str] = Field(None, description="Nom du producteur")
    producer_code: Optional[str] = Field(None, description="Code producteur")
    batch_tracking: bool = Field(False, description="Suivi par lot")


class NutritionInfo(BaseModel):
    """Informations nutritionnelles (pour alimentaire)"""
    serving_size_g: Optional[float] = Field(None, description="Portion de référence en g")
    energy_kcal: Optional[float] = Field(None, description="Énergie en kcal/100g")
    energy_kj: Optional[float] = Field(None, description="Énergie en kJ/100g")
    fat_g: Optional[float] = Field(None, description="Matières grasses en g/100g")
    saturated_fat_g: Optional[float] = Field(None, description="Acides gras saturés en g/100g")
    carbohydrates_g: Optional[float] = Field(None, description="Glucides en g/100g")
    sugars_g: Optional[float] = Field(None, description="Sucres en g/100g")
    fiber_g: Optional[float] = Field(None, description="Fibres en g/100g")
    protein_g: Optional[float] = Field(None, description="Protéines en g/100g")
    salt_g: Optional[float] = Field(None, description="Sel en g/100g")
    
    # Nutri-Score
    nutri_score: Optional[str] = Field(None, description="Nutri-Score (A-E)")
    
    # Suppléments
    vitamins: Optional[Dict[str, str]] = Field(None, description="Vitamines et minéraux")


class Allergens(BaseModel):
    """Allergènes (pour alimentaire)"""
    contains: List[str] = Field(default_factory=list, description="Contient")
    may_contain: List[str] = Field(default_factory=list, description="Peut contenir (traces)")
    free_from: List[str] = Field(default_factory=list, description="Sans (garanti)")
    
    # Liste standardisée des allergènes
    STANDARD_ALLERGENS = [
        "gluten", "crustaces", "oeufs", "poissons", "arachides",
        "soja", "lait", "fruits_a_coque", "celeri", "moutarde",
        "sesame", "sulfites", "lupin", "mollusques"
    ]


class Conservation(BaseModel):
    """Conservation et durée de vie"""
    temperature_range: TemperatureRange = Field(TemperatureRange.AMBIENT)
    temperature_min_c: Optional[float] = Field(None, description="Température min °C")
    temperature_max_c: Optional[float] = Field(None, description="Température max °C")
    humidity_percent: Optional[float] = Field(None, description="Humidité relative %")
    
    # Durée de vie
    shelf_life_days: Optional[int] = Field(None, description="Durée de conservation en jours")
    dlc_type: Optional[str] = Field(None, description="DLC ou DDM")
    opened_shelf_life_days: Optional[int] = Field(None, description="Conservation après ouverture")
    
    # Instructions
    storage_instructions: Optional[str] = Field(None, description="Instructions de stockage")
    handling_instructions: Optional[str] = Field(None, description="Instructions de manipulation")


class TechnicalSpecs(BaseModel):
    """Spécifications techniques (pour équipements/matériaux)"""
    # Caractéristiques générales
    material: Optional[str] = Field(None, description="Matériau principal")
    composition: Optional[str] = Field(None, description="Composition détaillée")
    color: Optional[str] = Field(None, description="Couleur")
    finish: Optional[str] = Field(None, description="Finition")
    
    # Performance
    capacity: Optional[str] = Field(None, description="Capacité")
    power_watts: Optional[float] = Field(None, description="Puissance en watts")
    voltage: Optional[str] = Field(None, description="Tension (ex: 220-240V)")
    frequency_hz: Optional[float] = Field(None, description="Fréquence Hz")
    
    # Résistance
    load_capacity_kg: Optional[float] = Field(None, description="Charge max en kg")
    pressure_bar: Optional[float] = Field(None, description="Pression en bar")
    temperature_resistance_c: Optional[float] = Field(None, description="Résistance température °C")
    
    # Normes et certifications
    norms: List[str] = Field(default_factory=list, description="Normes (CE, NF, ISO, etc.)")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    
    # Spécifications libres
    custom_specs: Optional[Dict[str, str]] = Field(None, description="Spécifications personnalisées")


class Warranty(BaseModel):
    """Garantie (pour équipements)"""
    duration_months: int = Field(12, description="Durée en mois")
    warranty_type: str = Field("standard", description="Type: standard, étendue, pièces, main_oeuvre")
    coverage: Optional[str] = Field(None, description="Couverture de la garantie")
    exclusions: Optional[str] = Field(None, description="Exclusions")
    manufacturer_warranty: bool = Field(True, description="Garantie fabricant")


class Compliance(BaseModel):
    """Conformité réglementaire"""
    # Marquages obligatoires
    ce_marking: bool = Field(False, description="Marquage CE")
    nf_marking: bool = Field(False, description="Marque NF")
    
    # Alimentaire
    haccp_compliant: bool = Field(False, description="Conformité HACCP")
    organic_certified: bool = Field(False, description="Certifié Bio")
    organic_label: Optional[str] = Field(None, description="Label bio (AB, Eurofeuille, etc.)")
    halal_certified: bool = Field(False)
    kosher_certified: bool = Field(False)
    
    # Environnement
    reach_compliant: bool = Field(False, description="Conformité REACH")
    rohs_compliant: bool = Field(False, description="Conformité RoHS")
    fsc_certified: bool = Field(False, description="Certifié FSC")
    
    # Sécurité
    hazard_class: HazardClass = Field(HazardClass.NONE)
    safety_data_sheet_url: Optional[str] = Field(None, description="Fiche de données sécurité")
    
    # Documents
    compliance_documents: List[str] = Field(default_factory=list, description="URLs documents conformité")


class Media(BaseModel):
    """Médias et documents"""
    # Images
    main_image_url: Optional[str] = Field(None, description="Image principale")
    gallery_urls: List[str] = Field(default_factory=list, description="Galerie d'images")
    thumbnail_url: Optional[str] = Field(None, description="Miniature")
    
    # Documents
    technical_sheet_url: Optional[str] = Field(None, description="Fiche technique PDF")
    user_manual_url: Optional[str] = Field(None, description="Manuel utilisateur PDF")
    safety_sheet_url: Optional[str] = Field(None, description="Fiche sécurité PDF")
    
    # Vidéos
    video_url: Optional[str] = Field(None, description="Vidéo produit")
    
    # 3D
    model_3d_url: Optional[str] = Field(None, description="Modèle 3D")


class Logistics(BaseModel):
    """Logistique et transport"""
    # Codes
    customs_code: Optional[str] = Field(None, description="Code douanier (HS)")
    intrastat_code: Optional[str] = Field(None, description="Code Intrastat")
    
    # Conditionnement transport
    is_stackable: bool = Field(True, description="Gerbage autorisé")
    max_stack_height: Optional[int] = Field(None, description="Hauteur max gerbage")
    is_fragile: bool = Field(False)
    requires_adr: bool = Field(False, description="Transport ADR requis")
    
    # Délais
    lead_time_days: int = Field(3, description="Délai de livraison standard")
    min_order_quantity: int = Field(1, description="Quantité min de commande")
    order_multiple: int = Field(1, description="Multiple de commande")
    
    # Zones de livraison
    available_zones: List[str] = Field(default_factory=list, description="Zones de disponibilité")
    excluded_zones: List[str] = Field(default_factory=list, description="Zones exclues")


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
