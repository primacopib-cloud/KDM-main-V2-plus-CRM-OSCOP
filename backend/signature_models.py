"""KDMARCHE × O'SCOP - SMS Signature: config, enums, models & helpers (split from routes_signature.py)."""
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

from email_service import send_otp_email, send_signature_confirmation_email, is_email_configured

logger = logging.getLogger(__name__)

db = None

def set_signature_models_database(database):
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


