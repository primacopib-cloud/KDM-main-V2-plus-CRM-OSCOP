"""KDMARCHE GED — Admin endpoints, audit & initialization (split from routes_ged.py)."""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import hashlib
import uuid
import logging

from ged_models import (
    DocumentType, DocumentStatus, DocumentMetadata, DocumentCreateRequest,
    DEFAULT_DOCUMENTS, compute_checksum, extract_template_vars, load_document_content,
)

logger = logging.getLogger(__name__)

ged_admin_router = APIRouter(prefix="/api/ged")

db = None

def set_ged_admin_database(database):
    global db
    db = database

# ============== ADMIN ENDPOINTS ==============

@ged_admin_router.post("/admin/documents")
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


@ged_admin_router.post("/admin/documents/{doc_type}/publish")
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


@ged_admin_router.get("/admin/audit-log")
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
