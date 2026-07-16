"""
KDMARCHE × LOGI'SCOP - Proof of Delivery (POD) API
Génération et gestion des bons de livraison LOGI'SCOP

Découpé en modules : pod_models, routes_pod_sign.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import io
import logging

from pod_models import (
    PODItem, DeliveryInfo, RecipientInfo, GeneratePODRequest, SignPODRequest,
    CarrierSignPODRequest, PODResponse, LOGISCOP_INFO,
    generate_bl_number, generate_pod_verification_code, compute_pod_hash, render_pod_html,
)
from routes_pod_sign import set_pod_sign_database

logger = logging.getLogger(__name__)

pod_router = APIRouter(prefix="/api/delivery")

db = None


def set_pod_database(database):
    """Set database reference from main server"""
    global db
    db = database
    set_pod_sign_database(database)

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


