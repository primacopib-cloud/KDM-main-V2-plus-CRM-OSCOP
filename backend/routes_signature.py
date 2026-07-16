"""
KDMARCHE × O'SCOP - SMS Signature Service
Workflow de signature électronique par SMS (OTP)
Conforme eIDAS niveau AES (Advanced Electronic Signature)

Découpé en modules : signature_models, routes_signature_admin.
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging
import uuid

from signature_models import (
    OTP_LENGTH, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS, OTP_RESEND_COOLDOWN_SECONDS,
    SIGNATURE_EXPIRY_DAYS,
    SignatureStatus, DocumentType, SignerInfo,
    InitiateSignatureRequest, VerifyOTPRequest, ConfirmSignatureRequest,
    ResendOTPRequest, SignatureResponse, SignatureStatusResponse,
    generate_otp, hash_otp, mask_phone, generate_signature_hash,
    add_audit_entry, send_sms_otp,
    set_signature_models_database,
)
from routes_signature_admin import set_signature_admin_database

logger = logging.getLogger(__name__)

signature_router = APIRouter(prefix="/api/signatures")

db = None

def set_signature_database(database):
    global db
    db = database
    set_signature_models_database(database)
    set_signature_admin_database(database)

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


