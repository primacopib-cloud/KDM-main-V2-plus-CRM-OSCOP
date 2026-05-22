"""
KDMARCHE × LOGI'SCOP - Proof of Delivery (POD) API
Génération et gestion des bons de livraison LOGI'SCOP

Routes:
- POST /api/delivery/pod/generate - Génère un POD pour une commande
- GET /api/delivery/pod/{pod_id} - Récupère un POD
- GET /api/delivery/pod/{pod_id}/html - Récupère le POD au format HTML
- POST /api/delivery/pod/{pod_id}/sign - Signe un POD (destinataire)
- POST /api/delivery/pod/{pod_id}/carrier-sign - Signature transporteur
- GET /api/delivery/pod/verify/{verification_code} - Vérifie l'authenticité d'un POD
- GET /api/delivery/pod/by-order/{order_id} - Récupère les POD d'une commande
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import io
import logging

logger = logging.getLogger(__name__)

# Router
pod_router = APIRouter(prefix="/api/delivery")

# Database reference
db = None


def set_pod_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== MODELS ==============

class PODItem(BaseModel):
    """Item in the delivery"""
    sku: str
    label: str
    quantity: int
    lot_number: Optional[str] = None
    dlc_ddm: Optional[str] = None  # Date Limite Consommation / Date Durabilité Minimale
    observations: Optional[str] = None


class DeliveryInfo(BaseModel):
    """Delivery information"""
    pickup_location_address: str
    delivery_window: str  # e.g., "AM (8h-12h)", "PM (14h-18h)"
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None


class RecipientInfo(BaseModel):
    """Recipient/client information"""
    legal_name: str
    address_line1: str
    address_line2: Optional[str] = ""
    postal_code: str
    city: str
    country: str = "France"
    contact_name: str
    phone: Optional[str] = None


class GeneratePODRequest(BaseModel):
    """Request to generate a POD"""
    order_id: str
    order_reference: str
    zone_code: str
    recipient: RecipientInfo
    delivery: DeliveryInfo
    items: List[PODItem]


class SignPODRequest(BaseModel):
    """Request to sign a POD (recipient)"""
    signer_name: str
    signer_title: str = "Représentant"
    reserves: Optional[str] = None  # Any reservations/issues noted
    signature_method: str = "manual"  # manual, OTP, eIDAS
    ip_address: Optional[str] = None


class CarrierSignPODRequest(BaseModel):
    """Request to sign a POD (carrier/driver)"""
    agent_name: str
    agent_title: str = "Chauffeur"
    reserves: Optional[str] = None
    ip_address: Optional[str] = None


class PODResponse(BaseModel):
    """POD response"""
    id: str
    bl_number: str
    order_id: str
    order_reference: str
    status: str  # draft, pending_signature, signed, delivered
    zone_code: str
    recipient_name: str
    created_at: str
    delivered_at: Optional[str] = None
    verification_code: Optional[str] = None
    doc_hash: Optional[str] = None


# ============== LOGI'SCOP INFO ==============

LOGISCOP_INFO = {
    "legal_name": "LOGI'SCOP",
    "form": "Établissement secondaire de la SCIC O'SCOP",
    "address": "387 Rue de l'Industrie, Parc d'Activité de la Jaille, 97122 Baie-Mahault, Guadeloupe",
    "siret": "XXX XXX XXX XXXXX",
    "tva": "FR XX XXX XXX XXX",
    "email": "logistique@oscop.fr",
    "phone": "+590 590 XX XX XX"
}


# ============== HELPER FUNCTIONS ==============

def generate_bl_number() -> str:
    """Generate a unique BL (Bon de Livraison) number"""
    now = datetime.now()
    random_part = uuid.uuid4().hex[:6].upper()
    return f"BL-LSC-{now.strftime('%Y%m%d')}-{random_part}"


def generate_pod_verification_code() -> str:
    """Generate a verification code for POD"""
    now = datetime.now()
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    import random
    random_part = ''.join(random.choices(chars, k=6))
    return f"POD-{now.strftime('%Y%m%d')}-{random_part}"


def compute_pod_hash(pod_data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of POD data"""
    import json
    payload = json.dumps(pod_data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def render_pod_html(pod: Dict[str, Any], variables: Dict[str, str]) -> str:
    """Render POD HTML with variables replaced"""
    template_path = "/app/frontend/public/contracts/pod-logiscop.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        logger.warning("Template POD non trouvé, utilisation du fallback HTML intégré")
        html = """<!doctype html><html><head><meta charset='utf-8'><title>POD LOGI'SCOP</title>
        <style>body{font-family:Arial,sans-serif;padding:24px;color:#111827}.muted{color:#6b7280}.small{font-size:12px}.right{text-align:right}table{width:100%;border-collapse:collapse;margin-top:18px}td,th{border:1px solid #e5e7eb;padding:8px}h1{color:#1d4ed8}</style></head><body>
        <h1>Bon de livraison LOGI'SCOP</h1><p><b>N° BL :</b> {{bl_number}}</p><p><b>Commande :</b> {{order_reference}}</p><p><b>Destinataire :</b> {{recipient_name}}</p>
        <table><thead><tr><th>Article</th><th>Qté</th><th>Lot</th><th>Observations</th></tr></thead><tbody><!-- Items will be inserted here --></tbody></table>
        <p class='muted small'>Document généré automatiquement.</p></body></html>"""
    
    # Replace all variables
    for key, value in variables.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    
    # Generate items table rows
    items = pod.get("items", [])
    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
            <td>
                <b>{item.get('label', '')}</b><br/>
                <span class="muted small">SKU: {item.get('sku', '')} · DLC/DDM: {item.get('dlc_ddm', 'N/A')}</span>
            </td>
            <td class="right">{item.get('quantity', 0)}</td>
            <td>{item.get('lot_number', 'N/A')}</td>
            <td class="right">{item.get('observations', '')}</td>
        </tr>
        """
    
    # Replace items placeholder
    html = html.replace("<!-- Items will be inserted here -->", items_html)
    
    return html


# ============== API ENDPOINTS ==============

@pod_router.post("/pod/generate", response_model=PODResponse, tags=["Delivery POD"])
async def generate_pod(request: GeneratePODRequest):
    """
    POST /api/delivery/pod/generate
    
    Génère un nouveau Bon de Livraison (POD) pour une commande.
    Le POD est créé en statut "draft" et doit être signé à la livraison.
    """
    # Generate BL number
    bl_number = generate_bl_number()
    pod_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Create POD document
    pod_doc = {
        "id": pod_id,
        "bl_number": bl_number,
        "type": "POD_LOGISCOP",
        "status": "draft",
        "version": "1.0",
        
        # Order reference
        "order_id": request.order_id,
        "order_reference": request.order_reference,
        "zone_code": request.zone_code,
        
        # Recipient info
        "recipient": {
            "legal_name": request.recipient.legal_name,
            "address_line1": request.recipient.address_line1,
            "address_line2": request.recipient.address_line2,
            "postal_code": request.recipient.postal_code,
            "city": request.recipient.city,
            "country": request.recipient.country,
            "contact_name": request.recipient.contact_name,
            "phone": request.recipient.phone
        },
        
        # Delivery info
        "delivery": {
            "pickup_location_address": request.delivery.pickup_location_address,
            "delivery_window": request.delivery.delivery_window,
            "vehicle_id": request.delivery.vehicle_id,
            "driver_name": request.delivery.driver_name,
            "driver_phone": request.delivery.driver_phone
        },
        
        # Items
        "items": [item.model_dump() for item in request.items],
        
        # LOGI'SCOP info
        "logiscop": LOGISCOP_INFO,
        
        # Timestamps
        "created_at": now,
        "updated_at": now,
        "delivered_at": None,
        
        # Signatures
        "recipient_signature": None,
        "carrier_signature": None,
        "verification_code": None,
        "doc_hash": None
    }
    
    # Store in database
    await db.delivery_pods.insert_one(pod_doc)
    
    logger.info(f"POD generated: {bl_number} for order {request.order_reference}")
    
    return PODResponse(
        id=pod_id,
        bl_number=bl_number,
        order_id=request.order_id,
        order_reference=request.order_reference,
        status="draft",
        zone_code=request.zone_code,
        recipient_name=request.recipient.legal_name,
        created_at=now.isoformat()
    )


@pod_router.get("/pod/{pod_id}", tags=["Delivery POD"])
async def get_pod(pod_id: str):
    """
    GET /api/delivery/pod/{pod_id}
    
    Récupère les détails d'un POD.
    """
    pod = await db.delivery_pods.find_one({"id": pod_id}, {"_id": 0})
    
    if not pod:
        raise HTTPException(status_code=404, detail="POD non trouvé")
    
    return pod


@pod_router.get("/pod/{pod_id}/html", response_class=HTMLResponse, tags=["Delivery POD"])
async def get_pod_html(pod_id: str):
    """
    GET /api/delivery/pod/{pod_id}/html
    
    Récupère le POD au format HTML.
    """
    pod = await db.delivery_pods.find_one({"id": pod_id}, {"_id": 0})
    
    if not pod:
        raise HTTPException(status_code=404, detail="POD non trouvé")
    
    # Prepare variables
    recipient = pod.get("recipient") or {}
    delivery = pod.get("delivery") or {}
    logiscop = pod.get("logiscop") or LOGISCOP_INFO
    recipient_sig = pod.get("recipient_signature") or {}
    carrier_sig = pod.get("carrier_signature") or {}
    
    variables = {
        # Document info
        "BL_NUM": pod.get("bl_number", ""),
        "DATE_EMISSION": pod.get("created_at", datetime.now()).strftime("%Y-%m-%dT%H:%M:%S") if isinstance(pod.get("created_at"), datetime) else str(pod.get("created_at", "")),
        "ORDER_REF": pod.get("order_reference", ""),
        "ZONE_CODE": pod.get("zone_code", ""),
        
        # Logo
        "LOGO_SRC": "/kdmarche-logo.svg",
        
        # LOGI'SCOP info
        "LOGISCOP_FORM": logiscop.get("form", ""),
        "LOGISCOP_ADDRESS": logiscop.get("address", ""),
        "LOGISCOP_SIRET": logiscop.get("siret", ""),
        "LOGISCOP_TVA": logiscop.get("tva", ""),
        "LOGISCOP_EMAIL": logiscop.get("email", ""),
        "LOGISCOP_PHONE": logiscop.get("phone", ""),
        
        # Recipient info
        "CLIENT_LEGAL_NAME": recipient.get("legal_name", ""),
        "DELIVERY_ADDRESS_LINE1": recipient.get("address_line1", ""),
        "DELIVERY_ADDRESS_LINE2": recipient.get("address_line2", ""),
        "DELIVERY_POSTAL_CODE": recipient.get("postal_code", ""),
        "DELIVERY_CITY": recipient.get("city", ""),
        "DELIVERY_COUNTRY": recipient.get("country", "France"),
        "DELIVERY_CONTACT_NAME": recipient.get("contact_name", ""),
        "DELIVERY_PHONE": recipient.get("phone", ""),
        
        # Delivery info
        "PICKUP_LOCATION_ADDRESS": delivery.get("pickup_location_address", ""),
        "DELIVERY_WINDOW": delivery.get("delivery_window", ""),
        "VEHICLE_ID": delivery.get("vehicle_id", "N/A"),
        "DRIVER_NAME": delivery.get("driver_name", "N/A"),
        "DRIVER_PHONE": delivery.get("driver_phone", "N/A"),
        
        # Recipient signature
        "RECIPIENT_SIGN_NAME": recipient_sig.get("signer_name") or recipient.get("contact_name", ""),
        "RECIPIENT_SIGN_TITLE": recipient_sig.get("signer_title", "Représentant"),
        "HORODATAGE_REMISE": recipient_sig.get("signed_at", ""),
        
        # Carrier signature
        "LOGISCOP_AGENT_NAME": carrier_sig.get("agent_name") or delivery.get("driver_name", ""),
        "LOGISCOP_AGENT_TITLE": carrier_sig.get("agent_title", "Chauffeur"),
        "HORODATAGE_TRANSPORTEUR": carrier_sig.get("signed_at", ""),
        
        # Verification
        "CODE_VERIFICATION": pod.get("verification_code", ""),
        "DOC_HASH": pod.get("doc_hash", ""),
        "VERIFY_URL": f"https://kdmarche.fr/verify-pod/{pod.get('verification_code', '')}",
        "SERVICE_REF": pod.get("order_reference", ""),
        
        # Reserves
        "RESERVES_TEXTE": recipient_sig.get("reserves") or carrier_sig.get("reserves") or "Aucune réserve"
    }
    
    html = render_pod_html(pod, variables)
    return HTMLResponse(content=html)


@pod_router.post("/pod/{pod_id}/sign", tags=["Delivery POD"])
async def sign_pod_recipient(pod_id: str, request: SignPODRequest):
    """
    POST /api/delivery/pod/{pod_id}/sign
    
    Signature du POD par le destinataire (client).
    """
    pod = await db.delivery_pods.find_one({"id": pod_id}, {"_id": 0})
    
    if not pod:
        raise HTTPException(status_code=404, detail="POD non trouvé")
    
    if pod.get("status") == "delivered":
        raise HTTPException(status_code=400, detail="POD déjà signé et livré")
    
    now = datetime.now(timezone.utc)
    
    # Recipient signature
    recipient_signature = {
        "signer_name": request.signer_name,
        "signer_title": request.signer_title,
        "reserves": request.reserves,
        "method": request.signature_method,
        "signed_at": now.isoformat(),
        "ip_address": request.ip_address
    }
    
    # Update status based on whether carrier has signed
    carrier_sig = pod.get("carrier_signature")
    new_status = "delivered" if carrier_sig else "pending_carrier_signature"
    
    # Generate verification code and hash if both signatures present
    verification_code = None
    doc_hash = None
    delivered_at = None
    
    if carrier_sig:
        verification_code = generate_pod_verification_code()
        hash_data = {
            "bl_number": pod.get("bl_number"),
            "order_reference": pod.get("order_reference"),
            "recipient_signed_at": now.isoformat(),
            "carrier_signed_at": carrier_sig.get("signed_at"),
            "verification_code": verification_code
        }
        doc_hash = compute_pod_hash(hash_data)
        delivered_at = now
    
    # Update POD
    update_data = {
        "recipient_signature": recipient_signature,
        "status": new_status,
        "updated_at": now
    }
    
    if verification_code:
        update_data["verification_code"] = verification_code
        update_data["doc_hash"] = doc_hash
        update_data["delivered_at"] = delivered_at
    
    await db.delivery_pods.update_one(
        {"id": pod_id},
        {"$set": update_data}
    )
    
    # If fully signed, update order status
    if new_status == "delivered":
        await db.orders.update_one(
            {"id": pod.get("order_id")},
            {"$set": {"status": "delivered", "delivered_at": now, "updated_at": now}}
        )
        logger.info(f"Order {pod.get('order_reference')} marked as delivered")
    
    logger.info(f"POD {pod.get('bl_number')} signed by recipient: {request.signer_name}")
    
    return {
        "status": new_status,
        "pod_id": pod_id,
        "bl_number": pod.get("bl_number"),
        "recipient_signed_at": now.isoformat(),
        "verification_code": verification_code,
        "doc_hash": doc_hash,
        "message": "Signature destinataire enregistrée" if not carrier_sig else "POD complètement signé - Livraison confirmée"
    }


@pod_router.post("/pod/{pod_id}/carrier-sign", tags=["Delivery POD"])
async def sign_pod_carrier(pod_id: str, request: CarrierSignPODRequest):
    """
    POST /api/delivery/pod/{pod_id}/carrier-sign
    
    Signature du POD par le transporteur (chauffeur LOGI'SCOP).
    """
    pod = await db.delivery_pods.find_one({"id": pod_id}, {"_id": 0})
    
    if not pod:
        raise HTTPException(status_code=404, detail="POD non trouvé")
    
    if pod.get("status") == "delivered":
        raise HTTPException(status_code=400, detail="POD déjà signé et livré")
    
    now = datetime.now(timezone.utc)
    
    # Carrier signature
    carrier_signature = {
        "agent_name": request.agent_name,
        "agent_title": request.agent_title,
        "reserves": request.reserves,
        "signed_at": now.isoformat(),
        "ip_address": request.ip_address
    }
    
    # Update status based on whether recipient has signed
    recipient_sig = pod.get("recipient_signature")
    new_status = "delivered" if recipient_sig else "pending_recipient_signature"
    
    # Generate verification code and hash if both signatures present
    verification_code = None
    doc_hash = None
    delivered_at = None
    
    if recipient_sig:
        verification_code = generate_pod_verification_code()
        hash_data = {
            "bl_number": pod.get("bl_number"),
            "order_reference": pod.get("order_reference"),
            "recipient_signed_at": recipient_sig.get("signed_at"),
            "carrier_signed_at": now.isoformat(),
            "verification_code": verification_code
        }
        doc_hash = compute_pod_hash(hash_data)
        delivered_at = now
    
    # Update POD
    update_data = {
        "carrier_signature": carrier_signature,
        "status": new_status,
        "updated_at": now
    }
    
    if verification_code:
        update_data["verification_code"] = verification_code
        update_data["doc_hash"] = doc_hash
        update_data["delivered_at"] = delivered_at
    
    await db.delivery_pods.update_one(
        {"id": pod_id},
        {"$set": update_data}
    )
    
    # If fully signed, update order status
    if new_status == "delivered":
        await db.orders.update_one(
            {"id": pod.get("order_id")},
            {"$set": {"status": "delivered", "delivered_at": now, "updated_at": now}}
        )
        logger.info(f"Order {pod.get('order_reference')} marked as delivered")
    
    logger.info(f"POD {pod.get('bl_number')} signed by carrier: {request.agent_name}")
    
    return {
        "status": new_status,
        "pod_id": pod_id,
        "bl_number": pod.get("bl_number"),
        "carrier_signed_at": now.isoformat(),
        "verification_code": verification_code,
        "doc_hash": doc_hash,
        "message": "Signature transporteur enregistrée" if not recipient_sig else "POD complètement signé - Livraison confirmée"
    }


@pod_router.get("/pod/verify/{verification_code}", tags=["Delivery POD"])
async def verify_pod(verification_code: str):
    """
    GET /api/delivery/pod/verify/{verification_code}
    
    Vérifie l'authenticité d'un POD signé.
    """
    pod = await db.delivery_pods.find_one(
        {"verification_code": verification_code},
        {"_id": 0}
    )
    
    if not pod:
        return {
            "valid": False,
            "message": "Code de vérification invalide ou POD non trouvé"
        }
    
    return {
        "valid": True,
        "bl_number": pod.get("bl_number"),
        "order_reference": pod.get("order_reference"),
        "status": pod.get("status"),
        "zone_code": pod.get("zone_code"),
        "recipient_name": pod.get("recipient", {}).get("legal_name"),
        "delivered_at": pod.get("delivered_at"),
        "doc_hash": pod.get("doc_hash"),
        "has_reserves": bool(pod.get("recipient_signature", {}).get("reserves") or pod.get("carrier_signature", {}).get("reserves")),
        "message": "POD vérifié avec succès"
    }


@pod_router.get("/pod/by-order/{order_id}", tags=["Delivery POD"])
async def get_pods_by_order(order_id: str):
    """
    GET /api/delivery/pod/by-order/{order_id}
    
    Récupère tous les POD liés à une commande.
    """
    pods = await db.delivery_pods.find(
        {"order_id": order_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "order_id": order_id,
        "pods": pods,
        "count": len(pods)
    }


@pod_router.post("/pod/auto-generate/{order_id}", tags=["Delivery POD"])
async def auto_generate_pod_for_order(order_id: str):
    """
    POST /api/delivery/pod/auto-generate/{order_id}
    
    Génère automatiquement un POD pour une commande existante.
    Utilisé quand le statut de commande passe à "shipped" ou "out_for_delivery".
    """
    # Get order
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Check if POD already exists
    existing_pod = await db.delivery_pods.find_one({"order_id": order_id})
    if existing_pod:
        return {
            "status": "already_exists",
            "pod_id": existing_pod.get("id"),
            "bl_number": existing_pod.get("bl_number"),
            "message": "Un POD existe déjà pour cette commande"
        }
    
    # Only generate for DELIVERY mode
    if order.get("fulfillment_mode") != "DELIVERY":
        raise HTTPException(
            status_code=400, 
            detail="POD uniquement pour les commandes en mode livraison LOGI'SCOP"
        )
    
    # Build POD request from order
    delivery_address = order.get("delivery_address") or {}
    items = order.get("items", [])
    
    # Get pickup point from zone
    zone_code = order.get("zone_code", "971")
    pickup_points = {
        "971": "Point EXW LOGI'SCOP Baie-Mahault, 97122 Guadeloupe",
        "972": "Point EXW LOGI'SCOP Fort-de-France, 97200 Martinique",
        "973": "Point EXW LOGI'SCOP Cayenne, 97300 Guyane",
        "974": "Point EXW LOGI'SCOP Saint-Denis, 97400 La Réunion",
        "976": "Point EXW LOGI'SCOP Mamoudzou, 97600 Mayotte"
    }
    
    # Map delivery slot
    slot_labels = {
        "AM": "Matin (8h-12h)",
        "PM": "Après-midi (14h-18h)",
        "EXPRESS": "Express (< 4h)",
        "RDV": "Sur rendez-vous"
    }
    
    request = GeneratePODRequest(
        order_id=order_id,
        order_reference=order.get("order_number", order_id),
        zone_code=zone_code,
        recipient=RecipientInfo(
            legal_name=delivery_address.get("contact_name") or order.get("customer_name", "Client"),
            address_line1=delivery_address.get("street", ""),
            address_line2=delivery_address.get("complement", ""),
            postal_code=delivery_address.get("postal_code", ""),
            city=delivery_address.get("city", ""),
            country=delivery_address.get("country", "France"),
            contact_name=delivery_address.get("contact_name", ""),
            phone=delivery_address.get("contact_phone")
        ),
        delivery=DeliveryInfo(
            pickup_location_address=pickup_points.get(zone_code, pickup_points["971"]),
            delivery_window=slot_labels.get(order.get("delivery_slot", "AM"), "Matin (8h-12h)")
        ),
        items=[
            PODItem(
                sku=item.get("sku", item.get("product_id", "")),
                label=item.get("name", item.get("label", "Produit")),
                quantity=item.get("quantity", 1),
                lot_number=item.get("lot_number"),
                dlc_ddm=item.get("dlc_ddm")
            )
            for item in items
        ]
    )
    
    # Generate POD
    return await generate_pod(request)
