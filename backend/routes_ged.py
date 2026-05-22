"""
KDMARCHE × O'SCOP - Document Management System (GED)
Gestion des documents légaux avec versioning, métadonnées et templating

Features:
- Document master storage with versioning
- Metadata (ref, version, date_effet, checksums)
- Template placeholder mapping (Jinja2-style)
- PDF generation support
- Audit trail for document access
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import hashlib
import uuid
import re
import io
import os
import logging

logger = logging.getLogger(__name__)

# Router
ged_router = APIRouter(prefix="/api/ged")

# Database reference (set by server.py)
db = None


def set_ged_database(database):
    """Set database reference from main server"""
    global db
    db = database


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


# ============== API ENDPOINTS ==============

@ged_router.get("/documents")
async def list_documents(
    doc_type: Optional[DocumentType] = None,
    status: Optional[DocumentStatus] = None,
    audience: Optional[str] = None,
    include_archived: bool = False,
):
    """
    List all documents with optional filtering.
    Returns metadata only (not content).
    """
    query = {}
    
    if doc_type:
        query["doc_type"] = doc_type.value
    
    if status:
        query["status"] = status.value
    elif not include_archived:
        query["status"] = {"$ne": DocumentStatus.ARCHIVED.value}
    
    if audience:
        query["audience"] = audience
    
    # Check if documents exist in DB, initialize if not
    count = await db.ged_documents.count_documents({})
    if count == 0:
        await initialize_default_documents()
    
    documents = await db.ged_documents.find(
        query,
        {"content": 0}  # Exclude content from list
    ).sort([("doc_type", 1), ("version_number", -1)]).to_list(100)
    
    return [{k: v for k, v in doc.items() if k != "_id"} for doc in documents]


@ged_router.get("/documents/{doc_type}")
async def get_document(
    doc_type: DocumentType,
    version: Optional[str] = None,
    include_content: bool = False,
):
    """
    Get document metadata and optionally content.
    Returns current version by default, or specific version if specified.
    """
    query = {"doc_type": doc_type.value}
    
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        # Try to initialize defaults
        await initialize_default_documents()
        document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    result = {k: v for k, v in document.items() if k != "_id"}
    
    if not include_content:
        result.pop("content", None)
    
    return result


@ged_router.get("/documents/{doc_type}/versions")
async def get_document_versions(doc_type: DocumentType):
    """Get all versions of a document"""
    documents = await db.ged_documents.find(
        {"doc_type": doc_type.value},
        {"content": 0}
    ).sort("version_number", -1).to_list(50)
    
    if not documents:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    return [
        {
            "version": doc["version"],
            "version_number": doc["version_number"],
            "date_creation": doc["date_creation"],
            "status": doc["status"],
            "is_current": doc.get("is_current", False),
        }
        for doc in documents
    ]


@ged_router.get("/documents/{doc_type}/render", response_class=HTMLResponse)
async def render_document(
    doc_type: DocumentType,
    version: Optional[str] = None,
    # Template variables as query params
    org_legal_name: Optional[str] = None,
    org_siret: Optional[str] = None,
    org_address: Optional[str] = None,
    rep_name: Optional[str] = None,
    rep_title: Optional[str] = None,
    date_signature: Optional[str] = None,
    lieu_signature: Optional[str] = None,
):
    """
    Render document with template variables filled in.
    Returns rendered HTML.
    """
    query = {"doc_type": doc_type.value}
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    content = document.get("content")
    if not content:
        # Load from file
        content = load_document_content(document["filename"])
        if not content:
            raise HTTPException(status_code=404, detail="Contenu du document non trouvé")
    
    # Build variables dict
    variables = DEFAULT_TEMPLATE_VALUES.copy()
    
    # Override with provided values
    if org_legal_name:
        # For client-side rendering, we'd fill org details
        variables["CLIENT_LEGAL_NAME"] = org_legal_name
    if org_siret:
        variables["CLIENT_SIRET"] = org_siret
    if date_signature:
        variables["DATE_SIGNATURE"] = date_signature
    if lieu_signature:
        variables["LIEU_SIGNATURE"] = lieu_signature
    
    # Render
    rendered = render_template(content, variables)
    
    # Log access
    await log_document_access(doc_type.value, version or document["version"], "render")
    
    return HTMLResponse(content=rendered)


@ged_router.post("/documents/{doc_type}/render")
async def render_document_post(
    doc_type: DocumentType,
    request: DocumentRenderRequest,
    version: Optional[str] = None,
):
    """
    Render document with custom variables (POST with body).
    Supports more complex variable mappings.
    """
    query = {"doc_type": doc_type.value}
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    content = document.get("content")
    if not content:
        content = load_document_content(document["filename"])
        if not content:
            raise HTTPException(status_code=404, detail="Contenu du document non trouvé")
    
    # Merge defaults with provided variables
    variables = DEFAULT_TEMPLATE_VALUES.copy()
    variables.update(request.variables)
    
    # Render
    rendered = render_template(content, variables)
    
    # Log access
    await log_document_access(doc_type.value, version or document["version"], "render_custom")
    
    if request.format == "html":
        return HTMLResponse(content=rendered)
    elif request.format == "pdf":
        # PDF generation would require weasyprint or similar
        # For now, return HTML with instructions
        return {
            "message": "PDF generation disponible via conversion externe",
            "html_content": rendered,
            "suggested_tool": "weasyprint ou wkhtmltopdf"
        }
    
    return {"rendered_content": rendered}


@ged_router.get("/documents/{doc_type}/download")
async def download_document(
    doc_type: DocumentType,
    version: Optional[str] = None,
    format: str = Query(default="html", regex="^(html|raw)$"),
):
    """
    Download document as file.
    """
    query = {"doc_type": doc_type.value}
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    content = document.get("content")
    if not content:
        content = load_document_content(document["filename"])
        if not content:
            raise HTTPException(status_code=404, detail="Contenu du document non trouvé")
    
    # Log access
    await log_document_access(doc_type.value, version or document["version"], "download")
    
    filename = document["filename"]
    
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@ged_router.get("/documents/{doc_type}/metadata")
async def get_document_metadata(
    doc_type: DocumentType,
    version: Optional[str] = None,
):
    """
    Get full document metadata as JSON (for GED integration).
    """
    query = {"doc_type": doc_type.value}
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    # Build metadata response
    return {
        "id": document["id"],
        "doc_type": document["doc_type"],
        "ref": document["ref"],
        "version": document["version"],
        "version_number": document["version_number"],
        "title": document["title"],
        "description": document.get("description"),
        "filename": document["filename"],
        "status": document["status"],
        "is_current": document.get("is_current", False),
        "dates": {
            "creation": document["date_creation"],
            "effet": document.get("date_effet"),
            "expiration": document.get("date_expiration"),
            "publication": document.get("published_at"),
        },
        "integrity": {
            "checksum_sha256": document.get("checksum_sha256"),
            "content_hash": document.get("content_hash"),
        },
        "template": {
            "variables": document.get("template_vars", []),
            "default_values": {k: DEFAULT_TEMPLATE_VALUES.get(k) for k in document.get("template_vars", [])}
        },
        "classification": {
            "tags": document.get("tags", []),
            "audience": document.get("audience", []),
        },
        "audit": {
            "created_by": document.get("created_by"),
            "published_by": document.get("published_by"),
        }
    }


# ============== ADMIN ENDPOINTS ==============

@ged_router.post("/admin/documents")
async def create_document(
    request: DocumentCreateRequest,
    current_user: dict = None,  # Would come from auth dependency
):
    """
    Create a new document version (admin only).
    """
    # Check if document type already exists
    existing = await db.ged_documents.find_one({
        "doc_type": request.doc_type.value,
        "version": request.version,
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Cette version existe déjà")
    
    # Get latest version number
    latest = await db.ged_documents.find_one(
        {"doc_type": request.doc_type.value},
        sort=[("version_number", -1)]
    )
    
    version_number = (latest["version_number"] + 1) if latest else 1
    
    # Mark all previous versions as not current
    if latest:
        await db.ged_documents.update_many(
            {"doc_type": request.doc_type.value},
            {"$set": {"is_current": False}}
        )
    
    # Compute checksums
    content_hash = compute_checksum(request.content)
    
    # Extract template variables
    template_vars = extract_template_vars(request.content)
    
    # Create document
    doc = DocumentMetadata(
        doc_type=request.doc_type,
        ref=request.ref,
        version=request.version,
        version_number=version_number,
        title=request.title,
        description=request.description,
        filename=f"{request.doc_type.value}-v{request.version}.html",
        date_effet=request.date_effet,
        status=DocumentStatus.DRAFT,
        is_current=True,
        content_hash=content_hash,
        template_vars=template_vars,
        tags=request.tags,
        audience=request.audience,
    )
    
    doc_dict = doc.dict()
    doc_dict["content"] = request.content
    
    await db.ged_documents.insert_one(doc_dict)
    
    logger.info(f"Document created: {request.doc_type.value} v{request.version}")
    
    return {"id": doc.id, "message": "Document créé avec succès"}


@ged_router.post("/admin/documents/{doc_type}/publish")
async def publish_document(
    doc_type: DocumentType,
    version: Optional[str] = None,
):
    """
    Publish a document version (admin only).
    """
    query = {"doc_type": doc_type.value}
    if version:
        query["version"] = version
    else:
        query["is_current"] = True
    
    document = await db.ged_documents.find_one(query)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    if document["status"] == DocumentStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Document déjà publié")
    
    await db.ged_documents.update_one(
        {"id": document["id"]},
        {"$set": {
            "status": DocumentStatus.PUBLISHED.value,
            "published_at": datetime.now(timezone.utc),
        }}
    )
    
    logger.info(f"Document published: {doc_type.value} v{document['version']}")
    
    return {"message": "Document publié avec succès"}


# ============== AUDIT & LOGGING ==============

async def log_document_access(doc_type: str, version: str, action: str, user_id: str = None):
    """Log document access for audit trail"""
    await db.ged_access_log.insert_one({
        "id": str(uuid.uuid4()),
        "doc_type": doc_type,
        "version": version,
        "action": action,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc),
    })


@ged_router.get("/admin/audit-log")
async def get_audit_log(
    doc_type: Optional[DocumentType] = None,
    limit: int = Query(default=100, le=500),
):
    """Get document access audit log (admin only)"""
    query = {}
    if doc_type:
        query["doc_type"] = doc_type.value
    
    logs = await db.ged_access_log.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return [{k: v for k, v in log.items() if k != "_id"} for log in logs]


# ============== INITIALIZATION ==============

async def initialize_default_documents():
    """Initialize default documents in database"""
    for doc_data in DEFAULT_DOCUMENTS:
        existing = await db.ged_documents.find_one({
            "doc_type": doc_data["doc_type"].value,
            "version": doc_data["version"],
        })
        
        if existing:
            continue
        
        # Load content from file
        content = load_document_content(doc_data["filename"])
        
        if not content:
            logger.warning(f"Content not found for {doc_data['filename']}")
            continue
        
        # Compute checksums
        content_hash = compute_checksum(content)
        
        # Create document
        doc = DocumentMetadata(
            doc_type=doc_data["doc_type"],
            ref=doc_data["ref"],
            version=doc_data["version"],
            version_number=doc_data["version_number"],
            title=doc_data["title"],
            description=doc_data["description"],
            filename=doc_data["filename"],
            status=DocumentStatus.PUBLISHED,
            is_current=True,
            content_hash=content_hash,
            template_vars=doc_data["template_vars"],
            tags=doc_data["tags"],
            audience=doc_data["audience"],
            date_effet=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc),
        )
        
        doc_dict = doc.dict()
        doc_dict["content"] = content
        
        await db.ged_documents.insert_one(doc_dict)
        logger.info(f"Initialized document: {doc_data['title']}")
    
    # Create indexes
    await db.ged_documents.create_index("id", unique=True)
    await db.ged_documents.create_index([("doc_type", 1), ("version", 1)], unique=True)
    await db.ged_documents.create_index([("doc_type", 1), ("is_current", 1)])
    await db.ged_access_log.create_index("id", unique=True)
    await db.ged_access_log.create_index([("doc_type", 1), ("timestamp", -1)])
