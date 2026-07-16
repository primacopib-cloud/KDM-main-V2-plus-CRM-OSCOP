"""KDMARCHE GED — Enums, models, default metadata & helpers (split from routes_ged.py)."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import hashlib
import re
import os
import logging
import uuid

logger = logging.getLogger(__name__)

# ============== ENUMS & MODELS ==============

class DocumentType(str, Enum):
    CONVENTION = "convention"
    CG_OSCOP = "cg-oscop"
    CGV_KDMARCHE = "cgv-kdmarche"
    NOTE_PREVENTIVE = "note-preventive"


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: DocumentType
    ref: str  # Reference code (e.g., CONV-2026-001)
    version: str  # Semantic version (e.g., 1.0.0)
    version_number: int = 1
    title: str
    description: Optional[str] = None
    filename: str
    
    # Dates
    date_creation: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    date_effet: Optional[datetime] = None  # Effective date
    date_expiration: Optional[datetime] = None
    
    # Status
    status: DocumentStatus = DocumentStatus.DRAFT
    is_current: bool = True  # Current version flag
    
    # Integrity
    checksum_sha256: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Audit
    created_by: Optional[str] = None
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None
    
    # Template variables used
    template_vars: List[str] = []
    
    # Tags and categorization
    tags: List[str] = []
    audience: List[str] = []  # B2B, ADMIN, PUBLIC, etc.
    
    class Config:
        use_enum_values = True


class DocumentVersionHistory(BaseModel):
    """Version history entry"""
    version: str
    version_number: int
    date: datetime
    changes: Optional[str] = None
    author: Optional[str] = None


class DocumentRenderRequest(BaseModel):
    """Request to render document with variables"""
    variables: Dict[str, Any]
    format: str = "html"  # html or pdf


class DocumentCreateRequest(BaseModel):
    """Request to create/update document"""
    doc_type: DocumentType
    ref: str
    version: str
    title: str
    description: Optional[str] = None
    content: str  # HTML content
    date_effet: Optional[datetime] = None
    tags: List[str] = []
    audience: List[str] = ["B2B"]


# ============== DEFAULT DOCUMENTS METADATA ==============

DEFAULT_DOCUMENTS = [
    {
        "doc_type": DocumentType.CONVENTION,
        "ref": "CONV-KDM-OSCOP-2026-001",
        "version": "1.0.0",
        "version_number": 1,
        "title": "Convention de partenariat KDMARCHE – O'SCOP",
        "description": "Centrale d'achats B2B ESS — Partenariat (séparation stricte des rôles et flux)",
        "filename": "convention-kdmarche-oscop.html",
        "tags": ["partenariat", "b2b", "ess", "convention"],
        "audience": ["B2B", "ADMIN", "LEGAL"],
        "template_vars": [
            "REF_CONVENTION", "VERSION", "DATE_DOCUMENT",
            "KDM_LEGAL_NAME", "KDM_FORM", "KDM_SIRET", "KDM_ADDRESS", "KDM_REP_NAME", "KDM_REP_TITLE",
            "OSCOP_LEGAL_NAME", "OSCOP_FORM", "OSCOP_SIRET", "OSCOP_ADDRESS", "OSCOP_REP_NAME", "OSCOP_REP_TITLE",
            "DUREE_MOIS", "DATE_EFFET", "PREAVIS_JOURS",
            "DROIT_APPLICABLE", "JURIDICTION",
            "LIEU_SIGNATURE", "DATE_SIGNATURE"
        ]
    },
    {
        "doc_type": DocumentType.CG_OSCOP,
        "ref": "CG-OSCOP-2026-001",
        "version": "1.0.0",
        "version_number": 1,
        "title": "CG O'SCOP — Accès, Abonnements, Wallet Crédits",
        "description": "Conditions générales applicables aux services d'accès et d'usage O'SCOP (hors marchandises)",
        "filename": "cg-oscop.html",
        "tags": ["cg", "oscop", "abonnement", "wallet", "credits"],
        "audience": ["B2B", "PUBLIC"],
        "template_vars": [
            "REF_CG_OSCOP", "VERSION", "DATE_EFFET",
            "PLANS_LISTE", "DROIT_APPLICABLE", "JURIDICTION"
        ]
    },
    {
        "doc_type": DocumentType.CGV_KDMARCHE,
        "ref": "CGV-KDM-B2B-2026-001",
        "version": "1.0.0",
        "version_number": 1,
        "title": "CGV KDMARCHE B2B — Marchandises (EXW)",
        "description": "Conditions générales de vente B2B pour les marchandises (Incoterm EXW)",
        "filename": "cgv-kdmarche-b2b.html",
        "tags": ["cgv", "kdmarche", "b2b", "exw", "marchandises"],
        "audience": ["B2B", "PUBLIC"],
        "template_vars": [
            "REF_CGV_KDM", "VERSION", "DATE_EFFET",
            "POLITIQUE_RETOURS_REFERENCE", "DROIT_APPLICABLE", "JURIDICTION"
        ]
    },
    {
        "doc_type": DocumentType.NOTE_PREVENTIVE,
        "ref": "NOTE-ACPR-DGCCRF-2026-001",
        "version": "1.0.0",
        "version_number": 1,
        "title": "Note préventive ACPR / DGCCRF",
        "description": "Qualification et prévention de requalification (assurance, paiement, tromperie)",
        "filename": "note-preventive-acpr-dgccrf.html",
        "tags": ["compliance", "acpr", "dgccrf", "legal", "preventive"],
        "audience": ["ADMIN", "LEGAL"],
        "template_vars": [
            "REF_NOTE", "VERSION", "DATE_DOCUMENT"
        ]
    }
]

# Default template values
DEFAULT_TEMPLATE_VALUES = {
    "REF_CONVENTION": "CONV-KDM-OSCOP-2026-001",
    "REF_CG_OSCOP": "CG-OSCOP-2026-001",
    "REF_CGV_KDM": "CGV-KDM-B2B-2026-001",
    "REF_NOTE": "NOTE-ACPR-DGCCRF-2026-001",
    "VERSION": "1.0.0",
    "DATE_DOCUMENT": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    "DATE_EFFET": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    "DATE_SIGNATURE": "",
    
    # KDMARCHE
    "KDM_LEGAL_NAME": "KDMARCHE SAS",
    "KDM_FORM": "SAS",
    "KDM_SIRET": "XXX XXX XXX XXXXX",
    "KDM_ADDRESS": "[Adresse du siège social]",
    "KDM_REP_NAME": "[Nom du représentant]",
    "KDM_REP_TITLE": "Président",
    
    # O'SCOP
    "OSCOP_LEGAL_NAME": "O'SCOP SCIC",
    "OSCOP_FORM": "SCIC (Société Coopérative d'Intérêt Collectif)",
    "OSCOP_SIRET": "XXX XXX XXX XXXXX",
    "OSCOP_ADDRESS": "[Adresse du siège social]",
    "OSCOP_REP_NAME": "[Nom du représentant]",
    "OSCOP_REP_TITLE": "Directeur Général",
    
    # Contract terms
    "DUREE_MOIS": "36",
    "PREAVIS_JOURS": "90",
    "DROIT_APPLICABLE": "Droit français",
    "JURIDICTION": "Tribunaux de Fort-de-France",
    "LIEU_SIGNATURE": "",
    
    # Other
    "PLANS_LISTE": "Starter, Business, Enterprise",
    "POLITIQUE_RETOURS_REFERENCE": "POL-RET-KDM-2026-001",
}


# ============== HELPER FUNCTIONS ==============

def compute_checksum(content: str) -> str:
    """Compute SHA-256 checksum of content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_template_vars(content: str) -> List[str]:
    """Extract template variable names from content"""
    pattern = r'\{\{([A-Z_]+)\}\}'
    return list(set(re.findall(pattern, content)))


def render_template(content: str, variables: Dict[str, Any]) -> str:
    """Render template by replacing {{VAR}} placeholders"""
    result = content
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value) if value else "")
    return result


def load_document_content(filename: str) -> Optional[str]:
    """Load document content from file system"""
    # Try multiple paths
    paths = [
        f"/app/frontend/public/docs/{filename}",
        f"/app/docs/{filename}",
    ]
    
    for path in paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    
    return None


