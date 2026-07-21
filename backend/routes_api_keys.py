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
    monthly_quota: Optional[int] = 10000
    webhook_url: Optional[str] = None


class WebhookBody(BaseModel):
    webhook_url: str


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
        "monthly_quota": max(body.monthly_quota or 10000, 1), "month_usage": 0,
        "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "webhook_url": (body.webhook_url or "").strip(),
        "webhook_secret": f"whsec_{secrets.token_hex(16)}",
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


@api_keys_router.put("/{key_id}/webhook")
async def set_webhook(key_id: str, body: WebhookBody, admin: dict = Depends(require_admin)):
    """Définit ou retire (chaîne vide) l'URL de webhook ERP de la clé."""
    url = body.webhook_url.strip()
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL invalide (http/https requis)")
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="Clé introuvable")
    upd = {"webhook_url": url}
    if not key.get("webhook_secret"):
        upd["webhook_secret"] = f"whsec_{secrets.token_hex(16)}"
    await db.api_keys.update_one({"id": key_id}, {"$set": upd})
    from consultation_audit import audit
    await audit("API_KEY_WEBHOOK_SET", admin.get("email"), None, {"name": key.get("name"), "webhook_url": url})
    return {"ok": True, "webhook_url": url}


@api_keys_router.post("/{key_id}/webhook/test")
async def test_webhook(key_id: str, admin: dict = Depends(require_admin)):
    """Envoie un événement d'exemple au webhook ERP pour valider la configuration."""
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="Clé introuvable")
    if not key.get("webhook_url"):
        raise HTTPException(status_code=400, detail="Aucune URL de webhook configurée sur cette clé")
    from erp_webhooks import send_test_event
    result = await send_test_event(key)
    from consultation_audit import audit
    await audit("API_KEY_WEBHOOK_TESTED", admin.get("email"), None, {
        "name": key.get("name"), "webhook_url": key.get("webhook_url"),
        "ok": result["ok"], "status_code": result.get("status_code"), "error": result.get("error")})
    return result


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
