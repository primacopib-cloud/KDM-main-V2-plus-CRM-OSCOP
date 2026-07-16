"""
KDMARCHE GED — Gestion Électronique de Documents
Endpoints publics : listing, rendu, téléchargement, versions.

Découpé en modules : ged_models, routes_ged_admin.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import hashlib
import uuid
import re
import io
import os
import logging

from ged_models import (
    DocumentType, DocumentStatus, DocumentMetadata, DocumentRenderRequest,
    DocumentCreateRequest, DocumentVersionHistory, DEFAULT_DOCUMENTS, DEFAULT_TEMPLATE_VALUES,
    compute_checksum, extract_template_vars, render_template, load_document_content,
)
from routes_ged_admin import (
    initialize_default_documents, log_document_access, set_ged_admin_database,
)

logger = logging.getLogger(__name__)

ged_router = APIRouter(prefix="/api/ged")

db = None

def set_ged_database(database):
    global db
    db = database
    set_ged_admin_database(database)

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


