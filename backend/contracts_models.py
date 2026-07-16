"""KDMARCHE × LOGI'SCOP Contrats — Modèles, infos & helpers (split from routes_contracts.py)."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

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
    """Generate a verification code for signature using cryptographic randomness"""
    now = datetime.now()
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    import secrets as _secrets
    random_part = ''.join(_secrets.choice(chars) for _ in range(6))
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
