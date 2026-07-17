"""KDMARCHE × O'SCOP - SMS Signature: status, certificate & admin endpoints (split from routes_signature.py)."""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone
import logging

from signature_models import (
    SignatureStatus, DocumentType, SignatureStatusResponse, mask_phone, add_audit_entry,
)

logger = logging.getLogger(__name__)

signature_admin_router = APIRouter(prefix="/api/signatures")

db = None

def set_signature_admin_database(database):
    global db
    db = database

@signature_admin_router.get("/status/{signature_id}", response_model=SignatureStatusResponse)
async def get_signature_status(signature_id: str):
    """Get signature status and details"""
    
    signature = await db.signatures.find_one({"id": signature_id}, {"_id": 0, "otp": 0})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    return SignatureStatusResponse(
        signature_id=signature["id"],
        status=SignatureStatus(signature["status"]),
        document_type=DocumentType(signature["document_type"]),
        document_ref=signature.get("document_ref"),
        signer=signature["signer"],
        signed_at=datetime.fromisoformat(signature["signed_at"]) if signature.get("signed_at") else None,
        signature_hash=signature.get("signature_hash"),
        audit_trail=signature.get("audit_trail", [])
    )


@signature_admin_router.post("/decline/{signature_id}")
async def decline_signature(request: Request, signature_id: str, reason: str = ""):
    """Decline/refuse to sign the document"""
    
    signature = await db.signatures.find_one({"id": signature_id})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    if signature["status"] == SignatureStatus.SIGNED.value:
        raise HTTPException(status_code=400, detail="Document déjà signé")
    
    client_ip = request.client.host if request.client else None
    now = datetime.now(timezone.utc)
    
    await db.signatures.update_one(
        {"id": signature_id},
        {
            "$set": {
                "status": SignatureStatus.DECLINED.value,
                "declined_reason": reason,
                "updated_at": now.isoformat()
            },
            "$push": {
                "audit_trail": {
                    "action": "DECLINED",
                    "timestamp": now.isoformat(),
                    "ip_address": client_ip,
                    "details": {"reason": reason}
                }
            }
        }
    )
    
    logger.info(f"Signature declined: {signature_id}")
    
    return {"success": True, "message": "Signature refusée", "signature_id": signature_id}


@signature_admin_router.get("/certificate/{signature_id}")
async def get_signature_certificate(signature_id: str):
    """
    Generate signature certificate/proof document
    Returns a structured certificate with all audit information
    """
    
    signature = await db.signatures.find_one({"id": signature_id}, {"_id": 0, "otp": 0})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    if signature["status"] != SignatureStatus.SIGNED.value:
        raise HTTPException(status_code=400, detail="Document non signé")
    
    signer = signature["signer"]
    
    certificate = {
        "certificate_id": f"cert_{signature_id}",
        "title": "Certificat de Signature Électronique",
        "signature_level": "AES (Advanced Electronic Signature)",
        "regulation": "Conforme eIDAS (Règlement UE 910/2014)",
        "document": {
            "type": signature["document_type"],
            "reference": signature.get("document_ref"),
        },
        "signer": {
            "name": f"{signer['first_name']} {signer['last_name']}",
            "email": signer["email"],
            "phone_masked": mask_phone(signer["phone"]),
            "company": signer.get("company"),
            "title": signer.get("title"),
        },
        "signature": {
            "hash": signature["signature_hash"],
            "algorithm": "SHA-256",
            "consent_text": signature.get("consent_text"),
            "signed_at": signature["signed_at"],
        },
        "authentication": {
            "method": "SMS OTP",
            "phone_verified": True,
        },
        "audit_trail": signature.get("audit_trail", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issuer": "KDMARCHE × O'SCOP - Communityplace B2B ESS"
    }
    
    return certificate


# ============== ADMIN ENDPOINTS ==============

@signature_admin_router.get("/admin/list")
async def admin_list_signatures(
    request: Request,
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 50
):
    """Admin: List all signatures with optional filters"""
    
    # TODO: Add proper admin authentication
    
    query = {}
    if status:
        query["status"] = status
    if document_type:
        query["document_type"] = document_type
    
    signatures = await db.signatures.find(
        query,
        {"_id": 0, "otp": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "signatures": signatures,
        "count": len(signatures)
    }


@signature_admin_router.get("/admin/stats")
async def admin_signature_stats():
    """Admin: Get signature statistics"""
    
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    
    stats = await db.signatures.aggregate(pipeline).to_list(100)
    
    stats_dict = {s["_id"]: s["count"] for s in stats}
    
    return {
        "total": sum(stats_dict.values()),
        "by_status": stats_dict,
        "signed": stats_dict.get(SignatureStatus.SIGNED.value, 0),
        "pending": stats_dict.get(SignatureStatus.PENDING_OTP.value, 0),
        "declined": stats_dict.get(SignatureStatus.DECLINED.value, 0),
        "expired": stats_dict.get(SignatureStatus.EXPIRED.value, 0),
    }
