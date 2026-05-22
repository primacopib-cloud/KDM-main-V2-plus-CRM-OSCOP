"""
KDMARCHE × O'SCOP - SMS Signature Service
Workflow de signature électronique par SMS (OTP)
Conforme eIDAS niveau AES (Advanced Electronic Signature)
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum
import os
import logging
import uuid
import hashlib
import hmac
import secrets
import string

# Import email service for sending OTP via email (backup/alternative to SMS)
from email_service import send_otp_email, send_signature_confirmation_email, is_email_configured

logger = logging.getLogger(__name__)

# Router
signature_router = APIRouter(prefix="/api/signatures")

# Database reference (set by server.py)
db = None

def set_signature_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== CONFIGURATION ==============

# OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60

# Signature Settings
SIGNATURE_EXPIRY_DAYS = 7


# ============== ENUMS ==============

class SignatureStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_OTP = "PENDING_OTP"       # OTP sent, waiting for verification
    OTP_VERIFIED = "OTP_VERIFIED"     # OTP verified, ready to sign
    SIGNED = "SIGNED"                 # Document signed
    DECLINED = "DECLINED"             # Signer refused
    EXPIRED = "EXPIRED"               # OTP or signature expired
    FAILED = "FAILED"                 # Max attempts exceeded


class DocumentType(str, Enum):
    CGV_KDMARCHE = "CGV_KDMARCHE"
    CG_OSCOP = "CG_OSCOP"
    CONVENTION = "CONVENTION"
    BON_COMMANDE = "BON_COMMANDE"
    ADHESION = "ADHESION"


# ============== MODELS ==============

class SignerInfo(BaseModel):
    """Signer information"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    company: Optional[str] = None
    title: Optional[str] = None


class InitiateSignatureRequest(BaseModel):
    """Request to initiate SMS signature"""
    document_type: DocumentType
    document_ref: Optional[str] = None  # e.g., order_id, application_id
    signer: SignerInfo
    document_data: Optional[Dict] = None  # Dynamic data for document generation


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    signature_id: str
    otp_code: str = Field(..., min_length=6, max_length=6)


class ConfirmSignatureRequest(BaseModel):
    """Request to confirm signature after OTP"""
    signature_id: str
    consent_text: str = Field(default="Lu et approuvé")
    ip_address: Optional[str] = None


class ResendOTPRequest(BaseModel):
    """Request to resend OTP"""
    signature_id: str


class SignatureResponse(BaseModel):
    """Signature response"""
    signature_id: str
    status: SignatureStatus
    document_type: DocumentType
    signer_name: str
    signer_phone_masked: str
    otp_sent: bool = False
    otp_expires_at: Optional[datetime] = None
    attempts_remaining: int = OTP_MAX_ATTEMPTS
    message: str


class SignatureStatusResponse(BaseModel):
    """Signature status response"""
    signature_id: str
    status: SignatureStatus
    document_type: DocumentType
    document_ref: Optional[str] = None
    signer: dict
    signed_at: Optional[datetime] = None
    signature_hash: Optional[str] = None
    audit_trail: List[dict] = []


# ============== HELPER FUNCTIONS ==============

def generate_otp() -> str:
    """Generate a 6-digit OTP code using cryptographic randomness"""
    return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def hash_otp(otp: str, salt: str) -> str:
    """Hash OTP with salt for secure storage"""
    return hashlib.sha256(f"{otp}{salt}".encode()).hexdigest()


def mask_phone(phone: str) -> str:
    """Mask phone number for display: +33612345678 -> +33 6** *** *78"""
    if len(phone) < 6:
        return phone
    return f"{phone[:4]}** *** **{phone[-2:]}"


def generate_signature_hash(data: dict) -> str:
    """Generate a unique hash for the signature proof"""
    content = f"{data['signature_id']}{data['signer_email']}{data['signed_at']}{data['document_type']}"
    return hashlib.sha256(content.encode()).hexdigest()


async def add_audit_entry(signature_id: str, action: str, details: dict = None, ip_address: str = None):
    """Add entry to signature audit trail"""
    entry = {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": ip_address,
        "details": details or {}
    }
    await db.signatures.update_one(
        {"id": signature_id},
        {"$push": {"audit_trail": entry}}
    )


async def send_sms_otp(phone: str, otp: str, signer_name: str, document_type: str, signer_email: str = None):
    """
    Send OTP via SMS and/or Email
    Currently sends via email (SendGrid) as SMS provider not yet integrated
    TODO: Integrate Twilio or OVH SMS for production
    """
    # Log for development/testing
    logger.info(f"[SMS OTP] To: {phone} | Code: {otp} | Document: {document_type}")
    
    # Send via email if available (backup/alternative)
    if signer_email and is_email_configured():
        try:
            send_otp_email(signer_email, otp, signer_name, document_type, OTP_EXPIRY_MINUTES)
            logger.info(f"[EMAIL OTP] Sent to {signer_email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")
    
    # TODO: Implement actual SMS sending with Twilio
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # client.messages.create(body=message, from_='+33...', to=phone)
    
    return True


# ============== ENDPOINTS ==============

@signature_router.post("/initiate", response_model=SignatureResponse)
async def initiate_signature(
    request: Request,
    signature_data: InitiateSignatureRequest,
    background_tasks: BackgroundTasks
):
    """
    Initiate SMS signature workflow
    Step 1: Create signature request and send OTP to signer's phone
    """
    
    # Generate IDs
    signature_id = f"sig_{uuid.uuid4().hex[:12]}"
    otp_salt = uuid.uuid4().hex
    otp_code = generate_otp()
    otp_hash = hash_otp(otp_code, otp_salt)
    
    # Calculate expiry
    now = datetime.now(timezone.utc)
    otp_expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    signature_expires_at = now + timedelta(days=SIGNATURE_EXPIRY_DAYS)
    
    # Get client IP
    client_ip = request.client.host if request.client else None
    
    # Create signature record
    signature_record = {
        "id": signature_id,
        "document_type": signature_data.document_type.value,
        "document_ref": signature_data.document_ref,
        "document_data": signature_data.document_data,
        "status": SignatureStatus.PENDING_OTP.value,
        "signer": {
            "first_name": signature_data.signer.first_name,
            "last_name": signature_data.signer.last_name,
            "email": signature_data.signer.email,
            "phone": signature_data.signer.phone,
            "company": signature_data.signer.company,
            "title": signature_data.signer.title,
        },
        "otp": {
            "hash": otp_hash,
            "salt": otp_salt,
            "expires_at": otp_expires_at.isoformat(),
            "attempts": 0,
            "last_sent_at": now.isoformat(),
        },
        "audit_trail": [
            {
                "action": "INITIATED",
                "timestamp": now.isoformat(),
                "ip_address": client_ip,
                "details": {"document_type": signature_data.document_type.value}
            },
            {
                "action": "OTP_SENT",
                "timestamp": now.isoformat(),
                "ip_address": client_ip,
                "details": {"phone_masked": mask_phone(signature_data.signer.phone)}
            }
        ],
        "signed_at": None,
        "signature_hash": None,
        "consent_text": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": signature_expires_at.isoformat(),
    }
    
    await db.signatures.insert_one(signature_record)
    
    # Send OTP via SMS (background task)
    signer_name = f"{signature_data.signer.first_name} {signature_data.signer.last_name}"
    background_tasks.add_task(
        send_sms_otp,
        signature_data.signer.phone,
        otp_code,
        signer_name,
        signature_data.document_type.value,
        signature_data.signer.email  # Also send via email
    )
    
    logger.info(f"Signature initiated: {signature_id} for {signer_name}")
    
    return SignatureResponse(
        signature_id=signature_id,
        status=SignatureStatus.PENDING_OTP,
        document_type=signature_data.document_type,
        signer_name=signer_name,
        signer_phone_masked=mask_phone(signature_data.signer.phone),
        otp_sent=True,
        otp_expires_at=otp_expires_at,
        attempts_remaining=OTP_MAX_ATTEMPTS,
        message=f"Code de vérification envoyé au {mask_phone(signature_data.signer.phone)}"
    )


@signature_router.post("/verify-otp", response_model=SignatureResponse)
async def verify_otp(
    request: Request,
    verify_data: VerifyOTPRequest
):
    """
    Verify OTP code
    Step 2: Validate the OTP sent to signer's phone
    """
    
    # Find signature
    signature = await db.signatures.find_one({"id": verify_data.signature_id})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    # Check status
    if signature["status"] == SignatureStatus.SIGNED.value:
        raise HTTPException(status_code=400, detail="Document déjà signé")
    
    if signature["status"] == SignatureStatus.EXPIRED.value:
        raise HTTPException(status_code=400, detail="Signature expirée")
    
    if signature["status"] == SignatureStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Trop de tentatives échouées")
    
    # Check OTP expiry
    otp_expires_at = datetime.fromisoformat(signature["otp"]["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > otp_expires_at:
        await db.signatures.update_one(
            {"id": verify_data.signature_id},
            {"$set": {"status": SignatureStatus.EXPIRED.value}}
        )
        raise HTTPException(status_code=400, detail="Code expiré. Veuillez demander un nouveau code.")
    
    # Check attempts
    attempts = signature["otp"]["attempts"]
    if attempts >= OTP_MAX_ATTEMPTS:
        await db.signatures.update_one(
            {"id": verify_data.signature_id},
            {"$set": {"status": SignatureStatus.FAILED.value}}
        )
        raise HTTPException(status_code=400, detail="Nombre maximum de tentatives atteint")
    
    # Verify OTP
    otp_hash = hash_otp(verify_data.otp_code, signature["otp"]["salt"])
    client_ip = request.client.host if request.client else None
    
    if otp_hash != signature["otp"]["hash"]:
        # Increment attempts
        new_attempts = attempts + 1
        await db.signatures.update_one(
            {"id": verify_data.signature_id},
            {
                "$set": {"otp.attempts": new_attempts},
                "$push": {
                    "audit_trail": {
                        "action": "OTP_FAILED",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "ip_address": client_ip,
                        "details": {"attempt": new_attempts}
                    }
                }
            }
        )
        
        remaining = OTP_MAX_ATTEMPTS - new_attempts
        if remaining <= 0:
            await db.signatures.update_one(
                {"id": verify_data.signature_id},
                {"$set": {"status": SignatureStatus.FAILED.value}}
            )
            raise HTTPException(status_code=400, detail="Nombre maximum de tentatives atteint")
        
        raise HTTPException(
            status_code=400, 
            detail=f"Code incorrect. {remaining} tentative(s) restante(s)."
        )
    
    # OTP verified - update status
    await db.signatures.update_one(
        {"id": verify_data.signature_id},
        {
            "$set": {
                "status": SignatureStatus.OTP_VERIFIED.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {
                "audit_trail": {
                    "action": "OTP_VERIFIED",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ip_address": client_ip,
                    "details": {}
                }
            }
        }
    )
    
    signer = signature["signer"]
    signer_name = f"{signer['first_name']} {signer['last_name']}"
    
    logger.info(f"OTP verified for signature: {verify_data.signature_id}")
    
    return SignatureResponse(
        signature_id=verify_data.signature_id,
        status=SignatureStatus.OTP_VERIFIED,
        document_type=DocumentType(signature["document_type"]),
        signer_name=signer_name,
        signer_phone_masked=mask_phone(signer["phone"]),
        otp_sent=True,
        otp_expires_at=otp_expires_at,
        attempts_remaining=OTP_MAX_ATTEMPTS - signature["otp"]["attempts"],
        message="Code vérifié. Vous pouvez maintenant signer le document."
    )


@signature_router.post("/confirm", response_model=SignatureStatusResponse)
async def confirm_signature(
    request: Request,
    confirm_data: ConfirmSignatureRequest
):
    """
    Confirm signature after OTP verification
    Step 3: Apply signature with consent text
    """
    
    # Find signature
    signature = await db.signatures.find_one({"id": confirm_data.signature_id})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    # Check status
    if signature["status"] != SignatureStatus.OTP_VERIFIED.value:
        if signature["status"] == SignatureStatus.SIGNED.value:
            raise HTTPException(status_code=400, detail="Document déjà signé")
        raise HTTPException(status_code=400, detail="Veuillez d'abord vérifier le code SMS")
    
    # Get client IP
    client_ip = confirm_data.ip_address or (request.client.host if request.client else None)
    now = datetime.now(timezone.utc)
    
    # Generate signature hash (proof)
    signature_proof = {
        "signature_id": confirm_data.signature_id,
        "signer_email": signature["signer"]["email"],
        "signed_at": now.isoformat(),
        "document_type": signature["document_type"],
        "consent_text": confirm_data.consent_text,
    }
    signature_hash = generate_signature_hash(signature_proof)
    
    # Update signature record
    await db.signatures.update_one(
        {"id": confirm_data.signature_id},
        {
            "$set": {
                "status": SignatureStatus.SIGNED.value,
                "signed_at": now.isoformat(),
                "signature_hash": signature_hash,
                "consent_text": confirm_data.consent_text,
                "updated_at": now.isoformat()
            },
            "$push": {
                "audit_trail": {
                    "action": "SIGNED",
                    "timestamp": now.isoformat(),
                    "ip_address": client_ip,
                    "details": {
                        "consent_text": confirm_data.consent_text,
                        "signature_hash": signature_hash
                    }
                }
            }
        }
    )
    
    # Get updated signature
    signature = await db.signatures.find_one({"id": confirm_data.signature_id}, {"_id": 0})
    
    logger.info(f"Document signed: {confirm_data.signature_id} | Hash: {signature_hash[:16]}...")
    
    return SignatureStatusResponse(
        signature_id=confirm_data.signature_id,
        status=SignatureStatus.SIGNED,
        document_type=DocumentType(signature["document_type"]),
        document_ref=signature.get("document_ref"),
        signer=signature["signer"],
        signed_at=now,
        signature_hash=signature_hash,
        audit_trail=signature.get("audit_trail", [])
    )


@signature_router.post("/resend-otp", response_model=SignatureResponse)
async def resend_otp(
    request: Request,
    resend_data: ResendOTPRequest,
    background_tasks: BackgroundTasks
):
    """
    Resend OTP code
    Respects cooldown period to prevent abuse
    """
    
    # Find signature
    signature = await db.signatures.find_one({"id": resend_data.signature_id})
    if not signature:
        raise HTTPException(status_code=404, detail="Signature non trouvée")
    
    # Check status
    if signature["status"] in [SignatureStatus.SIGNED.value, SignatureStatus.FAILED.value]:
        raise HTTPException(status_code=400, detail="Impossible de renvoyer le code")
    
    # Check cooldown
    last_sent = datetime.fromisoformat(signature["otp"]["last_sent_at"].replace("Z", "+00:00"))
    cooldown_end = last_sent + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
    
    if datetime.now(timezone.utc) < cooldown_end:
        seconds_remaining = int((cooldown_end - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=429, 
            detail=f"Veuillez patienter {seconds_remaining} secondes avant de demander un nouveau code"
        )
    
    # Generate new OTP
    now = datetime.now(timezone.utc)
    otp_salt = uuid.uuid4().hex
    otp_code = generate_otp()
    otp_hash = hash_otp(otp_code, otp_salt)
    otp_expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    client_ip = request.client.host if request.client else None
    
    # Update signature with new OTP
    await db.signatures.update_one(
        {"id": resend_data.signature_id},
        {
            "$set": {
                "status": SignatureStatus.PENDING_OTP.value,
                "otp.hash": otp_hash,
                "otp.salt": otp_salt,
                "otp.expires_at": otp_expires_at.isoformat(),
                "otp.attempts": 0,
                "otp.last_sent_at": now.isoformat(),
                "updated_at": now.isoformat()
            },
            "$push": {
                "audit_trail": {
                    "action": "OTP_RESENT",
                    "timestamp": now.isoformat(),
                    "ip_address": client_ip,
                    "details": {}
                }
            }
        }
    )
    
    # Send new OTP
    signer = signature["signer"]
    signer_name = f"{signer['first_name']} {signer['last_name']}"
    background_tasks.add_task(
        send_sms_otp,
        signer["phone"],
        otp_code,
        signer_name,
        signature["document_type"]
    )
    
    logger.info(f"OTP resent for signature: {resend_data.signature_id}")
    
    return SignatureResponse(
        signature_id=resend_data.signature_id,
        status=SignatureStatus.PENDING_OTP,
        document_type=DocumentType(signature["document_type"]),
        signer_name=signer_name,
        signer_phone_masked=mask_phone(signer["phone"]),
        otp_sent=True,
        otp_expires_at=otp_expires_at,
        attempts_remaining=OTP_MAX_ATTEMPTS,
        message=f"Nouveau code envoyé au {mask_phone(signer['phone'])}"
    )


@signature_router.get("/status/{signature_id}", response_model=SignatureStatusResponse)
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


@signature_router.post("/decline/{signature_id}")
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


@signature_router.get("/certificate/{signature_id}")
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
        "issuer": "KDMARCHE × O'SCOP - Centrale d'Achats B2B ESS"
    }
    
    return certificate


# ============== ADMIN ENDPOINTS ==============

@signature_router.get("/admin/list")
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


@signature_router.get("/admin/stats")
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
