"""Matrice juridique produit — statuts ROUGE / ORANGE / VERT versionnés (art. L.442-8 C. com.).
ROUGE : enchère inversée interdite (offres scellées uniquement). ORANGE : validation juridique nominative requise.
VERT : enchère inversée ou offres scellées au choix. Jamais d'écrasement : chaque changement crée une nouvelle version."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

legal_matrix_router = APIRouter(prefix="/api/admin/legal-matrix", tags=["legal-matrix"])

db = None

STATUSES = ["ROUGE", "ORANGE", "VERT"]


def set_legal_matrix_database(database):
    global db
    db = database


class ClassifyBody(BaseModel):
    scope: str = "category"  # category | sku
    category: str
    sku_ean: Optional[str] = None
    status: str
    legal_reason: str
    legal_reference: str = "Art. L.442-8 Code de commerce"
    next_review_at: Optional[str] = None


@legal_matrix_router.post("")
async def classify(body: ClassifyBody, admin: dict = Depends(require_admin)):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide (ROUGE/ORANGE/VERT)")
    if not body.legal_reason.strip():
        raise HTTPException(status_code=400, detail="Motif juridique obligatoire")
    if body.scope == "sku" and not (body.sku_ean or "").strip():
        raise HTTPException(status_code=400, detail="SKU/EAN requis pour une classification par référence")
    key = {"scope": body.scope, "category": body.category.strip().lower()}
    if body.scope == "sku":
        key["sku_ean"] = body.sku_ean.strip()
    current = await db.legal_matrix.find_one({**key, "active": True}, {"_id": 0, "version": 1, "id": 1})
    version = ((current or {}).get("version") or 0) + 1
    if current:
        await db.legal_matrix.update_one({"id": current["id"]}, {"$set": {"active": False}})
    doc = {
        "id": str(uuid.uuid4()), **key, "sku_ean": key.get("sku_ean"),
        "status": body.status, "legal_reason": body.legal_reason.strip(),
        "legal_reference": body.legal_reference.strip(),
        "author": admin.get("email"), "validated_at": datetime.now(timezone.utc).isoformat(),
        "next_review_at": body.next_review_at, "version": version, "active": True,
    }
    await db.legal_matrix.insert_one({**doc})
    from consultation_audit import audit
    await audit("LEGAL_CLASSIFIED", admin.get("email"),
                payload={"category": key["category"], "sku": key.get("sku_ean"),
                         "status": body.status, "version": version})
    return doc


@legal_matrix_router.get("")
async def list_matrix(include_history: bool = False, admin: dict = Depends(require_admin)):
    q = {} if include_history else {"active": True}
    items = await db.legal_matrix.find(q, {"_id": 0}).sort([("category", 1), ("version", -1)]).limit(500).to_list(500)
    return {"items": items}


async def resolve_legal_status(category: str, sku_ean: Optional[str] = None) -> dict:
    """Résolution : la référence SKU prime sur la catégorie. Non classé → NON_CLASSE (publication bloquée)."""
    if sku_ean:
        m = await db.legal_matrix.find_one({"scope": "sku", "sku_ean": sku_ean.strip(), "active": True}, {"_id": 0})
        if m:
            return m
    m = await db.legal_matrix.find_one(
        {"scope": "category", "category": (category or "").strip().lower(), "active": True}, {"_id": 0})
    if m:
        return m
    return {"status": "NON_CLASSE", "id": None, "version": None}


@legal_matrix_router.get("/resolve")
async def resolve_endpoint(category: str, sku_ean: Optional[str] = None, admin: dict = Depends(require_admin)):
    return await resolve_legal_status(category, sku_ean)
