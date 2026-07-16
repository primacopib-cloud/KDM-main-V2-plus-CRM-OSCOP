"""Routes admin unifiées des connecteurs externes — /api/connectors/*."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from admin_guard import require_admin
from auth import get_current_user_id
from connectors import base as connectors_base
from connectors import auto_sync, oscop_crm

connectors_router = APIRouter(prefix="/api/connectors", tags=["Connectors"])

db = None


def set_connectors_routes_database(database) -> None:
    global db
    db = database


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


@connectors_router.get("")
async def list_connectors(_: dict = Depends(_admin)):
    return {"connectors": connectors_base.connectors_registry()}


@connectors_router.get("/sync-events")
async def list_sync_events(
    connector: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    _: dict = Depends(_admin),
):
    query: dict = {}
    if connector:
        query["connector"] = connector
    if status:
        query["status"] = status.upper()
    docs = await db.connector_sync_events.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    agg = await db.connector_sync_events.aggregate(pipeline).to_list(10)
    return {"events": docs, "counts": {a["_id"]: a["count"] for a in agg}}


@connectors_router.post("/sync-events/{event_id}/retry")
async def retry_sync_event(event_id: str, _: dict = Depends(_admin)):
    event = await db.connector_sync_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return await auto_sync.retry_event(event)


@connectors_router.get("/{name}/health")
async def connector_health(name: str, _: dict = Depends(_admin)):
    registry = {c["name"]: c for c in connectors_base.connectors_registry()}
    conn = registry.get(name)
    if not conn:
        raise HTTPException(status_code=404, detail="Connecteur inconnu")
    if not conn["enabled"]:
        return {"name": name, "status": "DISABLED", "detail": "Variables .env manquantes"}
    try:
        external = await oscop_crm.health()
        return {"name": name, "status": "OK", "external": external}
    except Exception as exc:
        return {"name": name, "status": "ERROR", "error": str(exc)[:300]}


@connectors_router.post("/push/order/{order_id}")
async def push_order(order_id: str, _: dict = Depends(_admin)):
    """Push manuel : facture -> GED + paiement -> Finance."""
    return await auto_sync.sync_order_paid(order_id)


@connectors_router.post("/push/contract/{contract_id}")
async def push_contract(contract_id: str, _: dict = Depends(_admin)):
    return await auto_sync.sync_contract_signed(contract_id)
