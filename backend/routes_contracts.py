"""
KDMARCHE × LOGI'SCOP - Contrats de transport électroniques.

Découpé : modèles & helpers dans contracts_models.py.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import io
import logging
import re

from contracts_models import (
    TransportContractClient, TransportContractRequest, TransportContractSignRequest,
    TransportContractResponse, LOGISCOP_INFO, TRANSPORT_CONTRACT_DISCLAIMER, ZONE_NAMES,
    generate_contract_reference, generate_verification_code, compute_document_hash,
    calculate_transport_cost, render_contract_html,
)

logger = logging.getLogger(__name__)

contracts_router = APIRouter(prefix="/api/contracts")

db = None

def set_contracts_database(database):
    global db
    db = database


@contracts_router.get("/transport/disclaimer", tags=["Contracts"])
async def get_transport_disclaimer():
    """
    GET /api/contracts/transport/disclaimer
    
    Retourne la phrase courte pour afficher au checkout.
    """
    return {
        "disclaimer": TRANSPORT_CONTRACT_DISCLAIMER,
        "link_text": "Consulter le contrat de transport LOGI'SCOP",
        "link_url": "/legal/contrat-transport"
    }


# ============== API ENDPOINTS ==============

@contracts_router.post("/transport/generate", response_model=TransportContractResponse, tags=["Contracts"])
async def generate_transport_contract(request: TransportContractRequest):
    """
    POST /api/contracts/transport/generate
    
    Génère un nouveau contrat de transport LOGI'SCOP.
    Le contrat est créé en statut "draft" et doit être signé pour être valide.
    """
    # Generate contract reference
    contract_ref = generate_contract_reference()
    contract_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Calculate transport cost if not provided
    transport_cost = calculate_transport_cost(
        request.zone_code, 
        request.weight_kg, 
        request.volume_m3 or 0
    )
    
    # Get zone name
    zone_name = ZONE_NAMES.get(request.zone_code.upper(), request.zone_code)
    
    # Create contract document
    contract_doc = {
        "id": contract_id,
        "reference": contract_ref,
        "type": "TRANSPORT_LOGISCOP",
        "status": "draft",
        "version": "1.0",
        
        # Zone info
        "zone_code": request.zone_code,
        "zone_name": zone_name,
        
        # Client info
        "client": {
            "legal_name": request.client.legal_name,
            "address": request.client.address,
            "siret": request.client.siret,
            "tva_number": request.client.tva_number,
            "contact_name": request.client.contact_name,
            "contact_email": request.client.contact_email,
            "contact_phone": request.client.contact_phone
        },
        
        # Delivery info
        "delivery_address": request.delivery_address,
        "delivery_slot": request.delivery_slot,
        "weight_kg": request.weight_kg,
        "volume_m3": request.volume_m3,
        "goods_value_cents": request.goods_value_cents,
        "transport_quote_cents": transport_cost,
        "transport_quote_id": request.transport_quote_id,
        
        # Related order
        "order_id": request.order_id,
        
        # LOGI'SCOP info
        "logiscop": LOGISCOP_INFO,
        
        # Timestamps
        "created_at": now,
        "updated_at": now,
        "signed_at": None,
        "expires_at": now + timedelta(days=7),  # Contract valid for 7 days
        
        # Signature info (to be filled on signing)
        "signature": None,
        "doc_hash": None,
        "verification_code": None
    }
    
    # Store in database
    await db.transport_contracts.insert_one(contract_doc)
    
    logger.info(f"Transport contract generated: {contract_ref} for {request.client.legal_name}")
    
    return TransportContractResponse(
        id=contract_id,
        reference=contract_ref,
        status="draft",
        zone_code=request.zone_code,
        client_legal_name=request.client.legal_name,
        delivery_address=request.delivery_address,
        transport_quote_cents=transport_cost,
        created_at=now.isoformat()
    )


@contracts_router.get("/transport/{contract_id}", tags=["Contracts"])
async def get_transport_contract(contract_id: str):
    """
    GET /api/contracts/transport/{contract_id}
    
    Récupère les détails d'un contrat de transport.
    """
    contract = await db.transport_contracts.find_one(
        {"id": contract_id}, 
        {"_id": 0}
    )
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat non trouvé")
    
    return contract


@contracts_router.get("/transport/{contract_id}/html", response_class=HTMLResponse, tags=["Contracts"])
async def get_transport_contract_html(contract_id: str):
    """
    GET /api/contracts/transport/{contract_id}/html
    
    Récupère le contrat de transport au format HTML.
    """
    contract = await db.transport_contracts.find_one(
        {"id": contract_id}, 
        {"_id": 0}
    )
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat non trouvé")
    
    # Prepare variables for template
    client = contract.get("client") or {}
    logiscop = contract.get("logiscop") or LOGISCOP_INFO
    signature = contract.get("signature") or {}
    
    variables = {
        # Document info
        "VERSION": contract.get("version", "1.0"),
        "CONTRAT_REF": contract.get("reference", ""),
        "DATE_EMISSION": contract.get("created_at", datetime.now()).strftime("%Y-%m-%dT%H:%M:%S") if isinstance(contract.get("created_at"), datetime) else str(contract.get("created_at", "")),
        "ZONE_CODE": contract.get("zone_code", ""),
        
        # Logo
        "LOGO_SRC": "/kdmarche-logo.svg",
        
        # LOGI'SCOP info
        "LOGISCOP_FORM": logiscop.get("form", ""),
        "LOGISCOP_ADDRESS": logiscop.get("address", ""),
        "LOGISCOP_SIRET": logiscop.get("siret", ""),
        "LOGISCOP_TVA": logiscop.get("tva", ""),
        "LOGISCOP_EMAIL": logiscop.get("email", ""),
        "LOGISCOP_PHONE": logiscop.get("phone", ""),
        "LOGISCOP_SIGN_NAME": logiscop.get("sign_name", ""),
        "LOGISCOP_SIGN_TITLE": logiscop.get("sign_title", ""),
        
        # Client info
        "CLIENT_LEGAL_NAME": client.get("legal_name", ""),
        "CLIENT_ADDRESS": client.get("address", ""),
        "CLIENT_SIRET": client.get("siret", ""),
        "CLIENT_TVA": client.get("tva_number", "N/A"),
        "CLIENT_CONTACT": f"{client.get('contact_name', '')} · {client.get('contact_email', '')}",
        "CLIENT_SIGN_NAME": signature.get("signer_name") or client.get("contact_name", ""),
        "CLIENT_SIGN_TITLE": signature.get("signer_title") or "Représentant légal",
        
        # Legal
        "DROIT_APPLICABLE": "Droit français",
        "JURIDICTION": "Tribunaux de Pointe-à-Pitre",
        
        # Signature info
        "HORODATAGE_SIGNATURE": signature.get("signed_at", ""),
        "CODE_VERIFICATION": contract.get("verification_code", ""),
        "DOC_HASH": contract.get("doc_hash", ""),
        "VERIFY_URL": f"https://kdmarche.fr/verify/{contract.get('verification_code', '')}",
        "SERVICE_REF": contract.get("transport_quote_id") or contract.get("reference", ""),
        "HORODATAGE_SIGNATURE_LOGISCOP": signature.get("logiscop_signed_at", ""),
    }
    
    html = render_contract_html(contract, variables)
    return HTMLResponse(content=html)


@contracts_router.post("/transport/{contract_id}/sign", tags=["Contracts"])
async def sign_transport_contract(contract_id: str, request: TransportContractSignRequest):
    """
    POST /api/contracts/transport/{contract_id}/sign
    
    Signe un contrat de transport.
    """
    contract = await db.transport_contracts.find_one({"id": contract_id}, {"_id": 0})
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat non trouvé")
    
    if contract.get("status") == "signed":
        raise HTTPException(status_code=400, detail="Contrat déjà signé")
    
    if contract.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Contrat annulé")
    
    # Check expiration
    expires_at = contract.get("expires_at")
    if expires_at and isinstance(expires_at, datetime):
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            raise HTTPException(status_code=400, detail="Contrat expiré")
    
    now = datetime.now(timezone.utc)
    
    # Generate verification code and hash
    verification_code = generate_verification_code()
    
    # Compute document hash
    hash_data = {
        "reference": contract.get("reference"),
        "client_siret": contract.get("client", {}).get("siret"),
        "zone_code": contract.get("zone_code"),
        "transport_quote_cents": contract.get("transport_quote_cents"),
        "signed_at": now.isoformat(),
        "signer_name": request.signer_name,
        "verification_code": verification_code
    }
    doc_hash = compute_document_hash(hash_data)
    
    # Signature record
    signature = {
        "signer_name": request.signer_name,
        "signer_title": request.signer_title,
        "method": request.signature_method,
        "signed_at": now.isoformat(),
        "ip_address": request.ip_address,
        "logiscop_signed_at": now.isoformat(),  # Auto-sign by LOGI'SCOP
    }
    
    # Update contract
    update_result = await db.transport_contracts.update_one(
        {"id": contract_id},
        {
            "$set": {
                "status": "signed",
                "signed_at": now,
                "updated_at": now,
                "signature": signature,
                "verification_code": verification_code,
                "doc_hash": doc_hash
            }
        }
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Erreur lors de la signature")
    
    logger.info(f"Transport contract signed: {contract.get('reference')} by {request.signer_name}")
    
    return {
        "status": "signed",
        "contract_id": contract_id,
        "reference": contract.get("reference"),
        "verification_code": verification_code,
        "doc_hash": doc_hash,
        "signed_at": now.isoformat(),
        "message": "Contrat de transport signé avec succès"
    }


@contracts_router.get("/transport/{contract_id}/pdf", tags=["Contracts"])
async def download_transport_contract_pdf(contract_id: str):
    """
    GET /api/contracts/transport/{contract_id}/pdf
    
    Télécharge le contrat de transport au format PDF.
    Note: Utilise une conversion HTML vers PDF simple.
    """
    # Get HTML first
    contract = await db.transport_contracts.find_one({"id": contract_id}, {"_id": 0})
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat non trouvé")
    
    # For now, return HTML with print-friendly headers
    # In production, use weasyprint or similar for PDF conversion
    
    # Get HTML content
    html_response = await get_transport_contract_html(contract_id)
    html_content = html_response.body.decode() if hasattr(html_response, 'body') else str(html_response)
    
    # Return as downloadable HTML (can be printed to PDF)
    filename = f"contrat-transport-{contract.get('reference', contract_id)}.html"
    
    return StreamingResponse(
        io.BytesIO(html_content.encode('utf-8')),
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/html; charset=utf-8"
        }
    )


@contracts_router.get("/transport/verify/{verification_code}", tags=["Contracts"])
async def verify_transport_contract(verification_code: str):
    """
    GET /api/contracts/transport/verify/{verification_code}
    
    Vérifie l'authenticité d'un contrat de transport signé.
    """
    contract = await db.transport_contracts.find_one(
        {"verification_code": verification_code},
        {"_id": 0}
    )
    
    if not contract:
        return {
            "valid": False,
            "message": "Code de vérification invalide ou contrat non trouvé"
        }
    
    return {
        "valid": True,
        "reference": contract.get("reference"),
        "status": contract.get("status"),
        "zone_code": contract.get("zone_code"),
        "client_legal_name": contract.get("client", {}).get("legal_name"),
        "signed_at": contract.get("signed_at"),
        "doc_hash": contract.get("doc_hash"),
        "message": "Contrat de transport vérifié avec succès"
    }


@contracts_router.get("/transport/by-order/{order_id}", tags=["Contracts"])
async def get_contracts_by_order(order_id: str):
    """
    GET /api/contracts/transport/by-order/{order_id}
    
    Récupère les contrats de transport liés à une commande.
    """
    contracts = await db.transport_contracts.find(
        {"order_id": order_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "order_id": order_id,
        "contracts": contracts,
        "count": len(contracts)
    }
