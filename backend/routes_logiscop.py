"""
KDMARCHE × LOGI'SCOP - Logistics API
Gestion des points de retrait, tarification transport et workflow logistique
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import uuid
import logging
import math

logger = logging.getLogger(__name__)

# Router
logiscop_router = APIRouter(prefix="/api/logiscop")

# Database reference
db = None

def set_logiscop_database(database):
    global db
    db = database


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


# ============== ENDPOINTS ==============

@logiscop_router.get("/pickup-locations", response_model=List[PickupLocation])
async def get_pickup_locations(zone_code: Optional[str] = None):
    """
    Récupérer les points de retrait EXW LOGI'SCOP
    """
    # Try to get from DB first
    query = {"is_active": True}
    if zone_code:
        query["zone_code"] = zone_code
    
    locations = []
    if db is not None:
        cursor = db.pickup_locations.find(query)
        locations = await cursor.to_list(100)
    
    # If no DB locations, use defaults
    if not locations:
        locations = DEFAULT_PICKUP_LOCATIONS
        if zone_code:
            locations = [loc for loc in locations if loc["zone_code"] == zone_code]
    
    return [PickupLocation(**loc) for loc in locations]


@logiscop_router.get("/pickup-locations/{location_id}", response_model=PickupLocation)
async def get_pickup_location(location_id: str):
    """Récupérer un point de retrait spécifique"""
    location = None
    
    if db is not None:
        location = await db.pickup_locations.find_one({"id": location_id})
    
    if not location:
        # Check defaults
        for loc in DEFAULT_PICKUP_LOCATIONS:
            if loc["id"] == location_id:
                location = loc
                break
    
    if not location:
        raise HTTPException(status_code=404, detail="Point de retrait non trouvé")
    
    return PickupLocation(**location)


@logiscop_router.get("/delivery-slots")
async def get_delivery_slots(zone_code: Optional[str] = None):
    """Récupérer les créneaux de livraison disponibles"""
    return {
        "slots": DELIVERY_SLOTS,
        "zone_code": zone_code,
        "next_available_date": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    }


@logiscop_router.post("/quote", response_model=DeliveryQuoteResponse)
async def calculate_delivery_quote(request: DeliveryQuoteRequest):
    """
    Calculer un devis de livraison LOGI'SCOP
    Tarification au poids ou au volume (le plus avantageux pour LOGI'SCOP)
    """
    zone_code = request.zone_code
    
    if zone_code not in TRANSPORT_RATES_PER_KG:
        raise HTTPException(status_code=400, detail=f"Zone non couverte: {zone_code}")
    
    weight_rates = TRANSPORT_RATES_PER_KG[zone_code]
    volume_rates = TRANSPORT_RATES_PER_M3[zone_code]
    
    # Calcul transport au poids
    transport_weight_cents = weight_rates["base"] + int(request.weight_kg * weight_rates["per_kg"])
    
    # Calcul transport au volume (si fourni)
    transport_volume_cents = 0
    if request.volume_m3 and request.volume_m3 > 0:
        transport_volume_cents = volume_rates["base"] + int(request.volume_m3 * volume_rates["per_m3"])
    
    # On prend le max (règle du "payant pour")
    transport_base_cents = weight_rates["base"]
    if transport_volume_cents > transport_weight_cents:
        transport_total = transport_volume_cents
    else:
        transport_total = transport_weight_cents
    
    # Frais de préparation
    preparation_fees_cents = 0
    preparation_fees_cents += request.items_count * PREPARATION_FEES["picking_per_line"]
    
    # Packaging selon poids
    if request.weight_kg <= 5:
        preparation_fees_cents += PREPARATION_FEES["packaging_small"]
    elif request.weight_kg <= 20:
        preparation_fees_cents += PREPARATION_FEES["packaging_medium"]
    else:
        preparation_fees_cents += PREPARATION_FEES["packaging_large"]
        # Palettisation si > 100kg
        if request.weight_kg > 100:
            palettes = math.ceil(request.weight_kg / 500)
            preparation_fees_cents += palettes * PREPARATION_FEES["palettization"]
    
    # Étiquetage
    preparation_fees_cents += request.items_count * PREPARATION_FEES["labeling"]
    
    # Supplément créneau
    slot_supplement_cents = 0
    slot_label = "Standard"
    for slot in DELIVERY_SLOTS:
        if slot["id"] == request.slot:
            slot_supplement_cents = slot["supplement_cents"]
            slot_label = slot["label"]
            break
    
    # Totaux
    subtotal_ht_cents = transport_total + preparation_fees_cents + slot_supplement_cents
    tva_rate = 8.5  # DOM
    tva_cents = int(subtotal_ht_cents * tva_rate / 100)
    total_ttc_cents = subtotal_ht_cents + tva_cents
    
    # Estimation livraison
    if request.delivery_type == "express":
        estimated_delivery = "Sous 24-48h"
    else:
        estimated_delivery = "3-5 jours ouvrés"
    
    return DeliveryQuoteResponse(
        zone_code=zone_code,
        zone_name=ZONE_NAMES.get(zone_code, zone_code),
        weight_kg=request.weight_kg,
        volume_m3=request.volume_m3,
        transport_base_cents=transport_base_cents,
        transport_weight_cents=transport_weight_cents - transport_base_cents,
        transport_volume_cents=max(0, transport_volume_cents - volume_rates["base"]) if transport_volume_cents > 0 else 0,
        slot_supplement_cents=slot_supplement_cents,
        preparation_fees_cents=preparation_fees_cents,
        subtotal_ht_cents=subtotal_ht_cents,
        tva_cents=tva_cents,
        tva_rate=tva_rate,
        total_ttc_cents=total_ttc_cents,
        estimated_delivery=estimated_delivery,
        slot_label=slot_label,
        billing_entity="LOGI'SCOP"
    )


@logiscop_router.get("/rates")
async def get_transport_rates():
    """Récupérer la grille tarifaire LOGI'SCOP"""
    return {
        "rates_per_kg": TRANSPORT_RATES_PER_KG,
        "rates_per_m3": TRANSPORT_RATES_PER_M3,
        "preparation_fees": PREPARATION_FEES,
        "delivery_slots": DELIVERY_SLOTS,
        "tva_rate": 8.5,
        "billing_entity": "LOGI'SCOP",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


# ============== WORKFLOW LOGISTIQUE ==============

@logiscop_router.post("/inbound")
async def register_inbound(request: InboundRequest):
    """
    Enregistrer une réception de marchandise (palette fournisseur)
    """
    inbound = {
        "id": str(uuid.uuid4()),
        "type": "INBOUND",
        "status": "RECEIVED",
        "supplier_name": request.supplier_name,
        "bl_number": request.bl_number,
        "items": request.items,
        "pallet_count": request.pallet_count,
        "total_weight_kg": request.total_weight_kg,
        "received_by": request.received_by,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.logistics_events.insert_one(inbound)
    
    logger.info(f"Inbound registered: BL {request.bl_number} from {request.supplier_name}")
    
    return {
        "success": True,
        "inbound_id": inbound["id"],
        "bl_number": request.bl_number,
        "status": "RECEIVED",
        "message": f"Réception enregistrée: {request.pallet_count} palette(s), {request.total_weight_kg}kg"
    }


@logiscop_router.post("/preparation")
async def create_preparation(request: PreparationRequest):
    """
    Créer une demande de préparation/dégroupage
    """
    preparation = {
        "id": str(uuid.uuid4()),
        "type": "PREPARATION",
        "status": "PENDING",
        "order_id": request.order_id,
        "items": request.items,
        "packaging_type": request.packaging_type,
        "special_instructions": request.special_instructions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.logistics_events.insert_one(preparation)
        
        # Update order status
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {
                "logistics_status": "PREPARATION_PENDING",
                "preparation_id": preparation["id"],
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    
    logger.info(f"Preparation created for order {request.order_id}")
    
    return {
        "success": True,
        "preparation_id": preparation["id"],
        "order_id": request.order_id,
        "status": "PENDING",
        "message": "Demande de préparation créée"
    }


@logiscop_router.post("/delivery-request")
async def create_delivery_request(request: DeliveryRequest):
    """
    Créer une demande de livraison ou retrait EXW
    """
    delivery = {
        "id": str(uuid.uuid4()),
        "type": "DELIVERY_REQUEST",
        "delivery_type": request.delivery_type,  # EXW ou DELIVERY
        "status": "PENDING",
        "order_id": request.order_id,
        "pickup_location_id": request.pickup_location_id,
        "delivery_address": request.delivery_address,
        "slot": request.slot,
        "contact_name": request.contact_name,
        "contact_phone": request.contact_phone,
        "special_instructions": request.special_instructions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.logistics_events.insert_one(delivery)
        
        # Update order
        logistics_status = "READY_FOR_PICKUP" if request.delivery_type == "EXW" else "DELIVERY_SCHEDULED"
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {
                "logistics_status": logistics_status,
                "delivery_request_id": delivery["id"],
                "delivery_type": request.delivery_type,
                "pickup_location_id": request.pickup_location_id,
                "delivery_slot": request.slot,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    
    if request.delivery_type == "EXW":
        message = f"Commande prête pour retrait au point LOGI'SCOP"
    else:
        slot_label = next((s["label"] for s in DELIVERY_SLOTS if s["id"] == request.slot), request.slot)
        message = f"Livraison programmée - Créneau: {slot_label}"
    
    logger.info(f"Delivery request created for order {request.order_id}: {request.delivery_type}")
    
    return {
        "success": True,
        "delivery_request_id": delivery["id"],
        "order_id": request.order_id,
        "delivery_type": request.delivery_type,
        "status": "PENDING",
        "message": message
    }


@logiscop_router.post("/proof-of-delivery")
async def submit_proof_of_delivery(request: ProofOfDelivery):
    """
    Enregistrer la preuve de livraison/retrait avec signature
    """
    pod = {
        "id": str(uuid.uuid4()),
        "type": "PROOF_OF_DELIVERY",
        "order_id": request.order_id,
        "delivery_type": request.delivery_type,
        "recipient_name": request.recipient_name,
        "recipient_signature": request.recipient_signature,
        "photos": request.photos,
        "notes": request.notes,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.logistics_events.insert_one(pod)
        
        # Update order
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {
                "logistics_status": "DELIVERED",
                "proof_of_delivery_id": pod["id"],
                "delivered_at": datetime.now(timezone.utc),
                "delivered_to": request.recipient_name,
                "status": "DELIVERED",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    
    logger.info(f"Proof of delivery submitted for order {request.order_id}")
    
    return {
        "success": True,
        "pod_id": pod["id"],
        "order_id": request.order_id,
        "completed_at": pod["completed_at"],
        "message": f"{'Retrait' if request.delivery_type == 'EXW' else 'Livraison'} confirmé(e) - Signataire: {request.recipient_name}"
    }


@logiscop_router.get("/order/{order_id}/tracking")
async def get_order_tracking(order_id: str):
    """
    Récupérer le suivi logistique d'une commande
    """
    events = []
    order = None
    
    if db is not None:
        # Get order
        order = await db.orders.find_one({"id": order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Commande non trouvée")
        
        # Get logistics events
        cursor = db.logistics_events.find({"order_id": order_id}).sort("created_at", 1)
        events = await cursor.to_list(100)
    
    # Build timeline
    timeline = []
    for event in events:
        timeline.append({
            "id": event["id"],
            "type": event["type"],
            "status": event["status"],
            "timestamp": event.get("created_at") or event.get("completed_at"),
            "details": {
                k: v for k, v in event.items() 
                if k not in ["_id", "id", "type", "status", "created_at", "order_id"]
            }
        })
    
    return {
        "order_id": order_id,
        "order_number": order.get("order_number") if order else None,
        "logistics_status": order.get("logistics_status") if order else None,
        "delivery_type": order.get("delivery_type") if order else None,
        "timeline": timeline
    }


# ============== INITIALISATION DB ==============

@logiscop_router.post("/init-pickup-locations")
async def init_pickup_locations():
    """Initialiser les points de retrait par défaut dans la DB"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Clear existing
    await db.pickup_locations.delete_many({})
    
    # Insert defaults
    await db.pickup_locations.insert_many(DEFAULT_PICKUP_LOCATIONS)
    
    return {
        "success": True,
        "count": len(DEFAULT_PICKUP_LOCATIONS),
        "message": f"{len(DEFAULT_PICKUP_LOCATIONS)} points de retrait initialisés"
    }
