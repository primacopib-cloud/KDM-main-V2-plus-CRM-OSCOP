"""
KDMARCHE × O'SCOP - Signature Models
Pydantic schemas for eIDAS-compliant electronic signatures
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


# ============== ENUMS ==============

class SignatureLevel(str, Enum):
    """eIDAS signature levels"""
    SES = "simple_electronic_signature"           # Simple - basic
    AES = "electronic_signature"                  # Advanced - standard
    QES = "qualified_electronic_signature"        # Qualified - highest


class SignatureStatus(str, Enum):
    """Signature request status"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"           # Waiting for signatures
    ONGOING = "ONGOING"           # Some signatures done
    SIGNED = "SIGNED"             # All signatures complete
    DECLINED = "DECLINED"         # Signer refused
    EXPIRED = "EXPIRED"           # Past expiration date
    CANCELED = "CANCELED"         # Manually canceled


class DocumentType(str, Enum):
    """Types of documents to sign"""
    CGV_KDMARCHE = "CGV_KDMARCHE"           # Conditions Générales de Vente
    CG_OSCOP = "CG_OSCOP"                   # Conditions Générales O'SCOP
    CONVENTION = "CONVENTION"               # Convention de partenariat
    ADHESION = "ADHESION"                   # Contrat d'adhésion B2B
    BON_COMMANDE = "BON_COMMANDE"           # Bon de commande (>10k€)
    AUTRE = "AUTRE"


class SignerRole(str, Enum):
    """Signer roles in multi-signer workflows"""
    SIGNER = "signer"
    APPROVER = "approver"
    WITNESS = "witness"


# ============== SIGNER MODELS ==============

class SignerInfo(BaseModel):
    """Signer information"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    role: SignerRole = SignerRole.SIGNER


class SignerCreate(SignerInfo):
    """Create a signer for a signature request"""
    signature_level: SignatureLevel = SignatureLevel.AES
    page: int = Field(default=1, ge=1)
    x: int = Field(default=100, ge=0)
    y: int = Field(default=700, ge=0)
    width: int = Field(default=200, ge=50)
    height: int = Field(default=50, ge=20)


class SignerStatus(BaseModel):
    """Signer status in a signature request"""
    email: EmailStr
    name: str
    role: SignerRole
    status: str  # pending, signed, declined
    signed_at: Optional[datetime] = None
    declined_reason: Optional[str] = None


# ============== AUDIT MODELS ==============

class AuditEntry(BaseModel):
    """Audit trail entry"""
    action: str  # CREATED, SENT, VIEWED, SIGNED, DECLINED, etc.
    timestamp: datetime
    actor: Optional[str] = None  # user_id or "system"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict] = None


# ============== SIGNATURE REQUEST MODELS ==============

class SignatureRequestCreate(BaseModel):
    """Create a new signature request"""
    document_type: DocumentType
    document_version: Optional[str] = None
    signers: List[SignerCreate]
    name: Optional[str] = None
    expiration_days: int = Field(default=7, ge=1, le=90)
    reminder_days: Optional[int] = Field(default=3, ge=1)
    redirect_url: Optional[str] = None  # URL after signing


class SignatureRequestResponse(BaseModel):
    """Signature request response"""
    id: str
    org_id: Optional[str] = None
    user_id: str
    document_type: DocumentType
    document_version: Optional[str] = None
    status: SignatureStatus
    yousign_request_id: Optional[str] = None
    signing_url: Optional[str] = None
    signers: List[SignerStatus]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    signed_document_url: Optional[str] = None


class SignatureRequestInDB(BaseModel):
    """Signature request stored in database"""
    id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    org_id: Optional[str] = None
    user_id: str
    document_type: DocumentType
    document_version: Optional[str] = None
    name: str
    status: SignatureStatus = SignatureStatus.DRAFT
    yousign_request_id: Optional[str] = None
    yousign_document_id: Optional[str] = None
    signing_url: Optional[str] = None
    signers: List[dict] = Field(default_factory=list)
    audit_trail: List[dict] = Field(default_factory=list)
    signed_document_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============== WEBHOOK MODELS ==============

class YousignWebhookEvent(BaseModel):
    """Yousign webhook event payload"""
    event_id: str
    event_name: str  # signature_request.done, signer.signed, etc.
    event_time: datetime
    data: dict


class WebhookSignerSigned(BaseModel):
    """Webhook payload when a signer signs"""
    signature_request_id: str
    signer_id: str
    signer_email: str
    signed_at: datetime


class WebhookSignatureComplete(BaseModel):
    """Webhook payload when all signatures complete"""
    signature_request_id: str
    completed_at: datetime
    document_url: str


# ============== API RESPONSE MODELS ==============

class InitiateSignatureResponse(BaseModel):
    """Response when initiating a signature"""
    signature_id: str
    signing_url: str
    status: SignatureStatus
    expires_at: datetime
    message: str = "Signature request created successfully"


class SignatureStatusResponse(BaseModel):
    """Response for signature status check"""
    signature_id: str
    status: SignatureStatus
    signers: List[SignerStatus]
    progress: str  # "0/2", "1/2", "2/2"
    completed: bool
    signed_document_available: bool


class DownloadSignedDocumentResponse(BaseModel):
    """Response for downloading signed document"""
    signature_id: str
    document_url: str
    filename: str
    content_type: str = "application/pdf"
    expires_at: datetime  # URL expiration
