"""Espace livreur mobile — accès par lien à jeton (24h) pour encaisser et faire signer les livraisons COD."""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
courier_admin_router = APIRouter(prefix="/api/admin/courier", tags=["courier-admin"])
courier_router = APIRouter(prefix="/api/courier", tags=["courier"])
db = None


def set_courier_database(database):
    global db
    db = database


@courier_admin_router.post("/tokens")
async def create_courier_token(body: dict = None, admin: dict = Depends(require_admin)):
    body = body or {}
    token = secrets.token_urlsafe(24)
    doc = {
        "id": str(uuid.uuid4()), "token": token,
        "name": (body.get("name") or "Livreur").strip()[:60],
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "revoked": False, "collected_count": 0,
    }
    await db.courier_tokens.insert_one({**doc})
    from consultation_audit import audit
    await audit("COURIER_TOKEN_CREATED", admin.get("email"), None, {"name": doc["name"]})
    return {"id": doc["id"], "name": doc["name"], "token": token, "expires_at": doc["expires_at"],
            "path": f"/livreur?token={token}"}


@courier_admin_router.get("/tokens")
async def list_courier_tokens(admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    items = await db.courier_tokens.find(
        {"revoked": {"$ne": True}, "expires_at": {"$gt": now}},
        {"_id": 0, "token": 0}).sort("created_at", -1).to_list(20)
    return {"items": items}


@courier_admin_router.delete("/tokens/{token_id}")
async def revoke_courier_token(token_id: str, admin: dict = Depends(require_admin)):
    res = await db.courier_tokens.update_one({"id": token_id}, {"$set": {"revoked": True}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Accès introuvable")
    return {"ok": True}


async def _require_token(token: str) -> dict:
    doc = await db.courier_tokens.find_one({"token": token, "revoked": {"$ne": True}})
    if not doc or doc["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=401, detail="Accès livreur invalide ou expiré — demandez un nouveau lien")
    return doc


@courier_router.get("/orders")
async def courier_orders(token: str = Query(...)):
    t = await _require_token(token)
    items = await db.orders.find(
        {"payment_method": "cod", "payment_status": "cod_pending"},
        {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "cod_amount_due_cents": 1,
         "total_ttc_cents": 1, "confirmed_at": 1},
    ).sort("confirmed_at", 1).to_list(50)
    org_ids = list({o["org_id"] for o in items if o.get("org_id")})
    orgs = {o["id"]: o.get("legal_name") or o.get("name") for o in
            await db.organizations.find({"id": {"$in": org_ids}}, {"id": 1, "legal_name": 1, "name": 1}).to_list(100)}
    for o in items:
        o["org_name"] = orgs.get(o.get("org_id"), "")
        o.pop("org_id", None)
        if o.get("confirmed_at") and not isinstance(o["confirmed_at"], str):
            o["confirmed_at"] = o["confirmed_at"].isoformat()
    return {"courier": t["name"], "items": items}


@courier_router.post("/orders/{order_id}/collected")
async def courier_collect(order_id: str, body: dict = None, token: str = Query(...)):
    t = await _require_token(token)
    from routes_cod import collect_order_core
    result = await collect_order_core(order_id, body or {}, f"livreur:{t['name']}")
    await db.courier_tokens.update_one({"id": t["id"]}, {"$inc": {"collected_count": 1}})
    return result
