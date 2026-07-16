"""KDMARCHE × LOGI'SCOP — Tarifs transport, schémas & points de retrait (split from routes_logiscop.py)."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import logging
import math

logger = logging.getLogger(__name__)

# ============== CONFIGURATION TARIFS TRANSPORT ==============

# Tarifs au kg par zone (en centimes)
TRANSPORT_RATES_PER_KG = {
    "971": {"base": 250, "per_kg": 45},    # Guadeloupe
    "972": {"base": 280, "per_kg": 50},    # Martinique  
    "973": {"base": 450, "per_kg": 75},    # Guyane
    "974": {"base": 320, "per_kg": 55},    # La Réunion
    "976": {"base": 380, "per_kg": 65},    # Mayotte
}

# Tarifs au m³ par zone (en centimes)
TRANSPORT_RATES_PER_M3 = {
    "971": {"base": 1500, "per_m3": 8500},   # Guadeloupe
    "972": {"base": 1800, "per_m3": 9000},   # Martinique
    "973": {"base": 3000, "per_m3": 15000},  # Guyane
    "974": {"base": 2200, "per_m3": 11000},  # La Réunion
    "976": {"base": 2500, "per_m3": 12000},  # Mayotte
}

# Frais de préparation/dégroupage (en centimes)
PREPARATION_FEES = {
    "picking_per_line": 150,        # 1.50€ par ligne de commande
    "packaging_small": 200,         # 2€ pour colis < 5kg
    "packaging_medium": 350,        # 3.50€ pour colis 5-20kg
    "packaging_large": 500,         # 5€ pour colis > 20kg
    "palettization": 1500,          # 15€ par palette
    "labeling": 50,                 # 0.50€ par étiquette
}

# Créneaux de livraison disponibles
DELIVERY_SLOTS = [
    {"id": "AM", "label": "Matin (8h-12h)", "supplement_cents": 0},
    {"id": "PM", "label": "Après-midi (14h-18h)", "supplement_cents": 0},
    {"id": "EXPRESS", "label": "Express (< 4h)", "supplement_cents": 2500},
    {"id": "RDV", "label": "Sur rendez-vous", "supplement_cents": 500},
]


# ============== SCHEMAS ==============

class PickupLocation(BaseModel):
    id: str
    zone_code: str
    name: str
    address: str
    city: str
    postal_code: str
    phone: Optional[str] = None
    opening_hours: str
    coordinates: Optional[dict] = None
    is_active: bool = True


class DeliveryQuoteRequest(BaseModel):
    zone_code: str
    weight_kg: float
    volume_m3: Optional[float] = None
    items_count: int = 1
    delivery_type: str = "standard"  # standard, express
    slot: str = "AM"


class DeliveryQuoteResponse(BaseModel):
    zone_code: str
    zone_name: str
    weight_kg: float
    volume_m3: Optional[float]
    
    # Détail tarification
    transport_base_cents: int
    transport_weight_cents: int
    transport_volume_cents: int
    slot_supplement_cents: int
    preparation_fees_cents: int
    
    # Totaux
    subtotal_ht_cents: int
    tva_cents: int
    tva_rate: float = 8.5
    total_ttc_cents: int
    
    # Info
    estimated_delivery: str
    slot_label: str
    billing_entity: str = "LOGI'SCOP"


class DeliveryOption(BaseModel):
    type: str  # "EXW" ou "DELIVERY"
    label: str
    description: str
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[dict] = None
    slot: Optional[str] = None
    quote: Optional[DeliveryQuoteResponse] = None
    terms_accepted: bool = False


class InboundRequest(BaseModel):
    """Réception palette fournisseur"""
    supplier_name: str
    bl_number: str  # Bon de livraison
    items: List[dict]  # [{product_id, sku, quantity, lot, dlc}]
    pallet_count: int
    total_weight_kg: float
    received_by: str


class PreparationRequest(BaseModel):
    """Demande de préparation/dégroupage"""
    order_id: str
    items: List[dict]  # [{product_id, quantity}]
    packaging_type: str = "carton"  # carton, palette
    special_instructions: Optional[str] = None


class DeliveryRequest(BaseModel):
    """Demande de livraison"""
    order_id: str
    delivery_type: str  # EXW ou DELIVERY
    pickup_location_id: Optional[str] = None
    delivery_address: Optional[dict] = None
    slot: str = "AM"
    contact_name: str
    contact_phone: str
    special_instructions: Optional[str] = None


class ProofOfDelivery(BaseModel):
    """Preuve de livraison/retrait"""
    order_id: str
    delivery_type: str
    recipient_name: str
    recipient_signature: str  # Base64
    photos: Optional[List[str]] = None  # URLs
    notes: Optional[str] = None


# ============== POINTS DE RETRAIT ==============

# Points de retrait par défaut par zone
DEFAULT_PICKUP_LOCATIONS = [
    # Guadeloupe
    {
        "id": "PU-971-01",
        "zone_code": "971",
        "name": "LOGI'SCOP Jarry",
        "address": "Zone Industrielle de Jarry, Bâtiment C4",
        "city": "Baie-Mahault",
        "postal_code": "97122",
        "phone": "0590 123 456",
        "opening_hours": "Lun-Ven: 7h-17h, Sam: 8h-12h",
        "coordinates": {"lat": 16.2650, "lng": -61.5500},
        "is_active": True
    },
    {
        "id": "PU-971-02",
        "zone_code": "971",
        "name": "LOGI'SCOP Pointe-à-Pitre",
        "address": "Rue Achille René Boisneuf",
        "city": "Pointe-à-Pitre",
        "postal_code": "97110",
        "phone": "0590 234 567",
        "opening_hours": "Lun-Ven: 8h-16h",
        "coordinates": {"lat": 16.2411, "lng": -61.5331},
        "is_active": True
    },
    # Martinique
    {
        "id": "PU-972-01",
        "zone_code": "972",
        "name": "LOGI'SCOP La Lézarde",
        "address": "Zone La Lézarde, Lot 15",
        "city": "Le Lamentin",
        "postal_code": "97232",
        "phone": "0596 123 456",
        "opening_hours": "Lun-Ven: 7h-17h, Sam: 8h-12h",
        "coordinates": {"lat": 14.6167, "lng": -61.0000},
        "is_active": True
    },
    {
        "id": "PU-972-02",
        "zone_code": "972",
        "name": "LOGI'SCOP Fort-de-France",
        "address": "Boulevard du Général de Gaulle",
        "city": "Fort-de-France",
        "postal_code": "97200",
        "phone": "0596 234 567",
        "opening_hours": "Lun-Ven: 8h-16h",
        "coordinates": {"lat": 14.6037, "lng": -61.0742},
        "is_active": True
    },
    # Guyane
    {
        "id": "PU-973-01",
        "zone_code": "973",
        "name": "LOGI'SCOP Dégrad des Cannes",
        "address": "Port de Dégrad des Cannes",
        "city": "Rémire-Montjoly",
        "postal_code": "97354",
        "phone": "0594 123 456",
        "opening_hours": "Lun-Ven: 7h-16h",
        "coordinates": {"lat": 4.8500, "lng": -52.3000},
        "is_active": True
    },
    # La Réunion
    {
        "id": "PU-974-01",
        "zone_code": "974",
        "name": "LOGI'SCOP Port Réunion",
        "address": "Zone Portuaire Est",
        "city": "Le Port",
        "postal_code": "97420",
        "phone": "0262 123 456",
        "opening_hours": "Lun-Ven: 7h-17h, Sam: 8h-12h",
        "coordinates": {"lat": -20.9333, "lng": 55.2833},
        "is_active": True
    },
    {
        "id": "PU-974-02",
        "zone_code": "974",
        "name": "LOGI'SCOP Saint-Pierre",
        "address": "Zone Industrielle Les Sables",
        "city": "Saint-Pierre",
        "postal_code": "97410",
        "phone": "0262 234 567",
        "opening_hours": "Lun-Ven: 8h-16h",
        "coordinates": {"lat": -21.3393, "lng": 55.4781},
        "is_active": True
    },
    # Mayotte
    {
        "id": "PU-976-01",
        "zone_code": "976",
        "name": "LOGI'SCOP Longoni",
        "address": "Port de Longoni",
        "city": "Koungou",
        "postal_code": "97690",
        "phone": "0269 123 456",
        "opening_hours": "Lun-Ven: 7h-15h",
        "coordinates": {"lat": -12.7167, "lng": 45.1833},
        "is_active": True
    },
]

ZONE_NAMES = {
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
}


