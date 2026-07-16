"""KDMARCHE × LOGI'SCOP POD — Models, info & helpers (split from routes_pod.py)."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)

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
    """Generate a verification code for POD using cryptographic randomness"""
    now = datetime.now()
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    import secrets as _secrets
    random_part = ''.join(_secrets.choice(chars) for _ in range(6))
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


