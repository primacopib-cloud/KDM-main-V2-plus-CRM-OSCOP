"""KDMARCHE × LOGI'SCOP POD — Signature, vérification & auto-génération (split from routes_pod.py)."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import logging

from pod_models import (
    PODItem, DeliveryInfo, RecipientInfo, GeneratePODRequest, SignPODRequest,
    CarrierSignPODRequest, PODResponse, LOGISCOP_INFO,
    generate_bl_number, generate_pod_verification_code, compute_pod_hash, render_pod_html,
)

logger = logging.getLogger(__name__)

pod_sign_router = APIRouter(prefix="/api/delivery")

db = None

def set_pod_sign_database(database):
    global db
    db = database

@pod_sign_router.post("/pod/{pod_id}/sign", tags=["Delivery POD"])
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


@pod_sign_router.post("/pod/{pod_id}/carrier-sign", tags=["Delivery POD"])
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


@pod_sign_router.get("/pod/verify/{verification_code}", tags=["Delivery POD"])
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


@pod_sign_router.get("/pod/by-order/{order_id}", tags=["Delivery POD"])
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


@pod_sign_router.post("/pod/auto-generate/{order_id}", tags=["Delivery POD"])
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
    from routes_pod import generate_pod
    return await generate_pod(request)
