"""
KDMARCHE × LOGI'SCOP - Contrat de Transport API
Génération et gestion des contrats de transport LOGI'SCOP

Routes:
- POST /api/contracts/transport/generate - Génère un contrat de transport
- GET /api/contracts/transport/{contract_id} - Récupère un contrat
- POST /api/contracts/transport/{contract_id}/sign - Signe un contrat
- GET /api/contracts/transport/{contract_id}/pdf - Télécharge le PDF
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import io
import logging
import re

logger = logging.getLogger(__name__)

# Router
contracts_router = APIRouter(prefix="/api/contracts")

# Database reference
db = None


def set_contracts_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== MODELS ==============

class TransportContractClient(BaseModel):
    """Client info for transport contract"""
    legal_name: str
    address: str
    siret: str
    tva_number: Optional[str] = None
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None


class TransportContractRequest(BaseModel):
    """Request to generate a transport contract"""
    order_id: Optional[str] = None
    zone_code: str
    client: TransportContractClient
    delivery_address: str
    delivery_slot: str = "AM"
    weight_kg: float
    volume_m3: Optional[float] = None
    goods_value_cents: int
    transport_quote_id: Optional[str] = None


class TransportContractSignRequest(BaseModel):
    """Request to sign a transport contract"""
    signer_name: str
    signer_title: str
    signature_method: str = "OTP"  # OTP, eIDAS, manual
    otp_code: Optional[str] = None
    ip_address: Optional[str] = None


class TransportContractResponse(BaseModel):
    """Transport contract response"""
    id: str
    reference: str
    status: str  # draft, pending_signature, signed, cancelled
    zone_code: str
    client_legal_name: str
    delivery_address: str
    transport_quote_cents: int
    created_at: str
    signed_at: Optional[str] = None
    doc_hash: Optional[str] = None


# ============== LOGI'SCOP INFO ==============

LOGISCOP_INFO = {
    "legal_name": "LOGI'SCOP",
    "form": "Établissement secondaire de la SCIC O'SCOP",
    "address": "387 Rue de l'Industrie, Parc d'Activité de la Jaille, 97122 Baie-Mahault, Guadeloupe",
    "siret": "XXX XXX XXX XXXXX",
    "tva": "FR XX XXX XXX XXX",
    "email": "logistique@oscop.fr",
    "phone": "+590 590 XX XX XX",
    "sign_name": "Direction LOGI'SCOP",
    "sign_title": "Responsable Logistique"
}

# Zone names mapping
ZONE_NAMES = {
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
    "GUADELOUPE": "Guadeloupe",
    "MARTINIQUE": "Martinique",
    "GUYANE": "Guyane",
    "REUNION": "La Réunion",
    "MAYOTTE": "Mayotte"
}


# ============== HELPER FUNCTIONS ==============

def generate_contract_reference() -> str:
    """Generate a unique contract reference"""
    now = datetime.now()
    random_part = uuid.uuid4().hex[:6].upper()
    return f"CTR-LSC-{now.strftime('%Y%m%d')}-{random_part}"


def generate_verification_code() -> str:
    """Generate a verification code for signature"""
    now = datetime.now()
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    import random
    random_part = ''.join(random.choices(chars, k=6))
    return f"LSC-{now.strftime('%Y%m%d')}-{random_part}"


def compute_document_hash(contract_data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of contract data"""
    import json
    payload = json.dumps(contract_data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def calculate_transport_cost(zone_code: str, weight_kg: float, volume_m3: float = 0) -> int:
    """Calculate transport cost in cents"""
    # Rate configuration per zone
    rates = {
        "971": {"base": 250, "per_kg": 45, "per_m3": 8500},
        "972": {"base": 280, "per_kg": 50, "per_m3": 9000},
        "973": {"base": 450, "per_kg": 75, "per_m3": 15000},
        "974": {"base": 320, "per_kg": 55, "per_m3": 11000},
        "976": {"base": 380, "per_kg": 65, "per_m3": 12000},
    }
    
    # Map text codes to numeric
    code_map = {
        "GUADELOUPE": "971", "MARTINIQUE": "972", "GUYANE": "973",
        "REUNION": "974", "MAYOTTE": "976"
    }
    numeric_code = code_map.get(zone_code.upper(), zone_code)
    
    rate = rates.get(numeric_code, rates["971"])
    
    # Calculate weight-based and volume-based costs
    weight_cost = rate["base"] + int(weight_kg * rate["per_kg"])
    volume_cost = rate["base"] + int(volume_m3 * rate["per_m3"]) if volume_m3 else 0
    
    # Return the higher of the two (payant pour rule)
    return max(weight_cost, volume_cost)


def render_contract_html(contract: Dict[str, Any], variables: Dict[str, str]) -> str:
    """Render contract HTML with variables replaced"""
    # Read template
    template_path = "/app/frontend/public/contracts/transport-logiscop.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        logger.warning("Template contrat non trouvé, utilisation du fallback HTML intégré")
        html = """<!doctype html><html><head><meta charset='utf-8'><title>Contrat Transport LOGI'SCOP</title>
        <style>body{font-family:Arial,sans-serif;padding:24px;color:#111827}.muted{color:#6b7280}h1{color:#1d4ed8}.box{border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:12px 0}</style></head><body>
        <h1>Contrat de transport LOGI'SCOP</h1><div class='box'><b>Référence :</b> {{contract_reference}}</div><div class='box'><b>Client :</b> {{client_name}}</div>
        <div class='box'><b>Zone :</b> {{zone_code}}</div><p class='muted'>Document fallback généré automatiquement lorsque le template n'est pas disponible.</p></body></html>"""
    
    # Replace all variables
    for key, value in variables.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    
    return html


# Phrase courte pour le checkout (MUST be before {contract_id} routes)
TRANSPORT_CONTRACT_DISCLAIMER = "La livraison LOGI'SCOP est une prestation de transport indépendante, distincte de la vente des marchandises, exécutée par un opérateur logistique ESS."


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
