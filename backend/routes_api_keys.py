"""Gestion des clés API ERP (connecteurs externes) par le Super Admin."""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

api_keys_router = APIRouter(prefix="/api/admin/api-keys", tags=["api-keys"])

db = None

VALID_SCOPES = ["catalog:read", "orders:read", "territories:read", "stock:write"]


def set_api_keys_database(database):
    global db
    db = database


class KeyBody(BaseModel):
    name: str
    scopes: List[str]
    partner_email: Optional[str] = None


@api_keys_router.get("")
async def list_keys(admin: dict = Depends(require_admin)):
    items = await db.api_keys.find({}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(200)
    return {"items": items, "valid_scopes": VALID_SCOPES}


@api_keys_router.post("")
async def create_key(body: KeyBody, admin: dict = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis (ex : ERP Vendeur Guadeloupe)")
    scopes = [s for s in body.scopes if s in VALID_SCOPES]
    if not scopes:
        raise HTTPException(status_code=400, detail="Au moins un scope valide requis")
    raw_key = f"kdm_live_{secrets.token_hex(24)}"
    doc = {
        "id": str(uuid.uuid4()), "name": name,
        "prefix": raw_key[:16] + "…",
        "key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
        "scopes": scopes, "partner_email": (body.partner_email or "").strip(),
        "is_active": True, "requests_count": 0, "last_used_at": None,
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.api_keys.insert_one({**doc})
    from consultation_audit import audit
    await audit("API_KEY_CREATED", admin.get("email"), None, {"name": name, "scopes": scopes})
    logger.info("Clé API créée : %s (%s) par %s", name, doc["prefix"], admin.get("email"))
    doc.pop("key_hash")
    return {**doc, "api_key": raw_key}


@api_keys_router.patch("/{key_id}")
async def toggle_key(key_id: str, admin: dict = Depends(require_admin)):
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="Clé introuvable")
    new_state = not key.get("is_active", True)
    await db.api_keys.update_one({"id": key_id}, {"$set": {"is_active": new_state}})
    from consultation_audit import audit
    await audit("API_KEY_TOGGLED", admin.get("email"), None, {"name": key.get("name"), "is_active": new_state})
    return {"ok": True, "is_active": new_state}


@api_keys_router.delete("/{key_id}")
async def revoke_key(key_id: str, admin: dict = Depends(require_admin)):
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="Clé introuvable")
    await db.api_keys.delete_one({"id": key_id})
    from consultation_audit import audit
    await audit("API_KEY_REVOKED", admin.get("email"), None, {"name": key.get("name"), "prefix": key.get("prefix")})
    logger.info("Clé API révoquée : %s par %s", key.get("name"), admin.get("email"))
    return {"ok": True}
