"""Vendor enums & Pydantic models (split from routes_vendor.py)."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from enum import Enum

# ============== ENUMS ==============

class VendorStatus(str, Enum):
    PENDING = "pending"           # Waiting for admin approval
    APPROVED = "approved"         # Can submit products
    SUSPENDED = "suspended"       # Temporarily suspended
    REJECTED = "rejected"         # Application rejected


class ProductStatus(str, Enum):
    DRAFT = "draft"               # Not yet submitted
    PENDING_APPROVAL = "pending_approval"  # Submitted, waiting for review
    APPROVED = "approved"         # Active and visible
    REJECTED = "rejected"         # Not approved
    INACTIVE = "inactive"         # Deactivated by vendor


class DocumentType(str, Enum):
    TECHNICAL = "technical"       # Technical datasheet
    REGULATORY = "regulatory"     # Regulatory compliance
    CERTIFICATE = "certificate"   # Quality certificate
    OTHER = "other"


# ============== MODELS ==============

class VendorRegistration(BaseModel):
    """Vendor registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=2)
    siret: str = Field(..., pattern=r'^[0-9]{14}$')
    tva_intra: Optional[str] = None
    address: str
    city: str
    postal_code: str
    country: str = "FR"
    phone: str
    contact_name: str
    contact_title: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class VendorProfile(BaseModel):
    """Vendor profile update"""
    company_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    bank_iban: Optional[str] = None
    bank_bic: Optional[str] = None


class ProductSubmission(BaseModel):
    """Product submission by vendor"""
    name: str = Field(..., min_length=2, max_length=200)
    sku: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=10)
    category: str
    subcategory: Optional[str] = None
    
    # Pricing
    price_ht: float = Field(..., gt=0)
    tva_rate: float = Field(default=20.0, ge=0, le=100)
    
    # Stock & Volume
    stock_quantity: int = Field(..., ge=0)
    min_order_quantity: int = Field(default=1, ge=1)
    unit_type: str = Field(default="unit")  # unit, kg, liter, box, pallet
    volume_per_unit: Optional[float] = None
    weight_per_unit: Optional[float] = None
    
    # Product Format
    format_type: str = Field(default="standard")  # standard, lot, palette, container
    units_per_lot: Optional[int] = None
    lots_per_palette: Optional[int] = None
    
    # Origin
    country_of_origin: str = Field(default="FR")
    region_of_origin: Optional[str] = None
    
    # Dates
    dlc_days: Optional[int] = None  # Days until expiration
    production_date: Optional[str] = None
    
    # Logistics
    ean13: Optional[str] = None
    dimensions: Optional[Dict] = None  # {length, width, height}
    storage_conditions: Optional[str] = None
    
    # Zones availability
    available_zones: List[str] = Field(default=["GUADELOUPE"])
    
    # Additional info
    brand: Optional[str] = None
    certifications: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    ingredients: Optional[str] = None


class ProductUpdate(BaseModel):
    """Product update by vendor"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_ht: Optional[float] = None
    stock_quantity: Optional[int] = None
    min_order_quantity: Optional[int] = None
    available_zones: Optional[List[str]] = None
    dlc_days: Optional[int] = None


class ProductDocument(BaseModel):
    """Document attached to product"""
    document_type: DocumentType
    name: str
    url: str
    description: Optional[str] = None



COUNTRIES = {
    "FR": {"name": "France", "flag": "🇫🇷"},
    "GP": {"name": "Guadeloupe", "flag": "🇬🇵"},
    "MQ": {"name": "Martinique", "flag": "🇲🇶"},
    "GF": {"name": "Guyane", "flag": "🇬🇫"},
    "RE": {"name": "La Réunion", "flag": "🇷🇪"},
    "YT": {"name": "Mayotte", "flag": "🇾🇹"},
    "NC": {"name": "Nouvelle-Calédonie", "flag": "🇳🇨"},
    "PF": {"name": "Polynésie française", "flag": "🇵🇫"},
    "BE": {"name": "Belgique", "flag": "🇧🇪"},
    "DE": {"name": "Allemagne", "flag": "🇩🇪"},
    "ES": {"name": "Espagne", "flag": "🇪🇸"},
    "IT": {"name": "Italie", "flag": "🇮🇹"},
    "NL": {"name": "Pays-Bas", "flag": "🇳🇱"},
    "PT": {"name": "Portugal", "flag": "🇵🇹"},
    "MA": {"name": "Maroc", "flag": "🇲🇦"},
    "SN": {"name": "Sénégal", "flag": "🇸🇳"},
    "CI": {"name": "Côte d'Ivoire", "flag": "🇨🇮"},
    "CN": {"name": "Chine", "flag": "🇨🇳"},
    "TH": {"name": "Thaïlande", "flag": "🇹🇭"},
    "BR": {"name": "Brésil", "flag": "🇧🇷"},
    "US": {"name": "États-Unis", "flag": "🇺🇸"},
}
