"""
KDMARCHE × O'SCOP - Préparation de Commande Schema
Options de préparation conditionnelles par zone géographique
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============== ENUMS ==============

class PreparationType(str, Enum):
    """Type d'option de préparation"""
    PREP_PALLET = "PREP_PALLET"       # Palette complète
    PREP_CARTON = "PREP_CARTON"       # Cartons individuels
    PREP_CONTAINER = "PREP_CONTAINER" # Container
    PALETTE = "PALETTE"               # Alias pour compatibilité
    CARTON = "CARTON"                 # Alias pour compatibilité
    PICKING = "PICKING"               # Picking à l'unité
    MANUTENTION = "MANUTENTION"       # Frais de manutention
    STOCKAGE = "STOCKAGE"             # Frais de stockage temporaire
    EXPRESS = "EXPRESS"               # Préparation express


class PricingMode(str, Enum):
    """Mode de tarification"""
    FIXED = "FIXED"               # Prix fixe
    ORDER = "ORDER"               # Prix par commande
    PER_UNIT = "PER_UNIT"         # Prix par unité/carton
    PALLET = "PALLET"             # Prix par palette
    CARTON = "CARTON"             # Prix par carton
    CONTAINER = "CONTAINER"       # Prix par container
    PER_KG = "PER_KG"             # Prix au kilo
    PERCENTAGE = "PERCENTAGE"     # Pourcentage du total


class ZoneKind(str, Enum):
    """Type de zone géographique"""
    OM = "OM"           # Outre-Mer
    EXPORT = "EXPORT"   # Export international


# ============== MODELS ==============

class ZonePreparationOptionBase(BaseModel):
    """Base model for zone preparation option"""
    zone_code: str
    code: str  # Code unique: PREP_PALLET, PREP_CARTON, PREP_CONTAINER
    preparation_type: PreparationType
    name: str
    unit_label: str = "unité"  # Ex: "palette", "carton", "container"
    description: Optional[str] = None
    pricing_mode: PricingMode = PricingMode.FIXED
    price_ht_cents: int = Field(..., ge=0, description="Prix HT en centimes")
    tva_rate: float = Field(default=8.5, ge=0, le=100)  # TVA DOM par défaut
    tva_exonerated: bool = False  # Exonération TVA (0%)
    min_qty: int = Field(default=1, ge=0)
    max_qty: int = Field(default=999999, ge=1)
    includes: List[str] = []  # Ce qui est inclus dans l'option
    excludes: List[str] = []  # Ce qui est exclu
    sla_lead_time_hours: int = 0  # Délai de préparation en heures
    is_required: bool = False  # Option obligatoire
    is_default: bool = False   # Option par défaut
    enabled: bool = True       # Option activée pour la zone
    sort_order: int = 0


class ZonePreparationOptionCreate(ZonePreparationOptionBase):
    """Create zone preparation option"""
    pass


class ZonePreparationOptionUpdate(BaseModel):
    """Update zone preparation option"""
    name: Optional[str] = None
    unit_label: Optional[str] = None
    description: Optional[str] = None
    pricing_mode: Optional[PricingMode] = None
    price_ht_cents: Optional[int] = None
    tva_rate: Optional[float] = None
    tva_exonerated: Optional[bool] = None
    min_qty: Optional[int] = None
    max_qty: Optional[int] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    sla_lead_time_hours: Optional[int] = None
    is_required: Optional[bool] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ZonePreparationOptionResponse(ZonePreparationOptionBase):
    """Response model for zone preparation option"""
    id: str
    price_ttc_cents: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ZonePreparationOptionInDB(ZonePreparationOptionBase):
    """Zone preparation option in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    price_ttc_cents: int = 0  # Calculated field
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate TTC (0 if exonerated)
        if self.tva_exonerated:
            self.price_ttc_cents = self.price_ht_cents
        elif self.price_ht_cents:
            self.price_ttc_cents = int(self.price_ht_cents * (1 + self.tva_rate / 100))


# ============== ZONE MODEL ==============

class ZoneBase(BaseModel):
    """Base model for geographic zone"""
    code: str  # GUADELOUPE, MARTINIQUE, etc.
    label: str
    kind: ZoneKind = ZoneKind.OM
    currency: str = "EUR"
    vat_rate: float = Field(default=8.5, ge=0, le=100)  # Taux TVA par défaut
    vat_exoneration_allowed: bool = True  # Possibilité d'exonération
    exw_only: bool = True
    pickup_required: bool = True
    is_active: bool = True


class ZoneCreate(ZoneBase):
    """Create zone"""
    pass


class ZoneUpdate(BaseModel):
    """Update zone"""
    label: Optional[str] = None
    kind: Optional[ZoneKind] = None
    currency: Optional[str] = None
    vat_rate: Optional[float] = None
    vat_exoneration_allowed: Optional[bool] = None
    exw_only: Optional[bool] = None
    pickup_required: Optional[bool] = None
    is_active: Optional[bool] = None


class ZoneResponse(ZoneBase):
    """Response model for zone"""
    id: str
    created_at: datetime
    updated_at: datetime
    prep_options_count: int = 0
    
    class Config:
        from_attributes = True


class ZoneInDB(ZoneBase):
    """Zone in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== ORDER PREPARATION SELECTION ==============

class PreparationSelectionItem(BaseModel):
    """Single preparation option selection in an order"""
    option_id: str
    option_name: str
    preparation_type: str
    pricing_mode: str
    quantity: int = 1
    unit_price_ht_cents: int
    total_ht_cents: int
    tva_rate: float
    total_tva_cents: int
    total_ttc_cents: int


class OrderPreparationSelection(BaseModel):
    """All preparation selections for an order"""
    items: List[PreparationSelectionItem] = []
    subtotal_ht_cents: int = 0
    total_tva_cents: int = 0
    total_ttc_cents: int = 0


# ============== ORDER CALCULATION ==============

class OrderCalculationRequest(BaseModel):
    """Request for order total calculation with preparation options"""
    products_subtotal_ht_cents: int = Field(..., ge=0)
    products_tva_cents: int = Field(..., ge=0)
    zone_code: str
    preparation_selections: List[Dict[str, Any]] = []  # [{option_id, quantity}]


class OrderCalculationResponse(BaseModel):
    """Response with calculated order totals"""
    # Products
    products_subtotal_ht_cents: int
    products_tva_cents: int
    products_total_ttc_cents: int
    
    # Preparation fees
    preparation_subtotal_ht_cents: int
    preparation_tva_cents: int
    preparation_total_ttc_cents: int
    preparation_details: List[PreparationSelectionItem]
    
    # Grand totals
    grand_total_ht_cents: int
    grand_total_tva_cents: int
    grand_total_ttc_cents: int
    
    # Summary
    zone_code: str
    calculation_timestamp: datetime



from schema_preparation_defaults import DEFAULT_ZONES, DEFAULT_ZONE_PREPARATION_OPTIONS  # noqa: E402,F401
