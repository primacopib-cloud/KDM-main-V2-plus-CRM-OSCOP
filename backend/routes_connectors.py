"""Routes admin unifiées des connecteurs externes — /api/connectors/*."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from admin_guard import require_admin
from auth import get_current_user_id
from connectors import base as connectors_base
from connectors import auto_sync, oscop_crm
from connectors import generic_app

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


@connectors_router.get("/ecosystem")
async def ecosystem_overview(_: dict = Depends(_admin)):
    """Vue synthèse : santé live de toutes les apps connectées + compteurs de synchro."""
    import asyncio

    registry = connectors_base.connectors_registry()
    oscop_shared: dict = {}

    async def _oscop_health():
        if "result" not in oscop_shared:
            try:
                await oscop_crm.health()
                oscop_shared["result"] = {"status": "OK"}
            except Exception as exc:
                oscop_shared["result"] = {"status": "ERROR", "error": str(exc)[:120]}
        return oscop_shared["result"]

    async def _health(conn):
        if not conn["enabled"]:
            return {"status": "DISABLED"}
        try:
            if conn["name"] in ("oscop-ged", "oscop-finance"):
                return await asyncio.wait_for(_oscop_health(), timeout=10)
            result = await asyncio.wait_for(generic_app.health(conn["name"]), timeout=10)
            return {"status": result.get("status", "ERROR"), "error": result.get("error")}
        except asyncio.TimeoutError:
            return {"status": "ERROR", "error": "Timeout (10s)"}
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc)[:120]}

    ged_finance = [c for c in registry if c["name"] in ("oscop-ged", "oscop-finance")]
    others = [c for c in registry if c["name"] not in ("oscop-ged", "oscop-finance")]
    shared = await asyncio.gather(_health(ged_finance[0]) if ged_finance else asyncio.sleep(0),
                                  *[_health(c) for c in others])
    health_map = {}
    if ged_finance:
        for c in ged_finance:
            health_map[c["name"]] = shared[0]
    for conn, h in zip(others, shared[1:]):
        health_map[conn["name"]] = h
    healths = [health_map[c["name"]] for c in registry]

    pipeline = [{"$group": {"_id": {"c": "$connector", "s": "$status"}, "n": {"$sum": 1}}}]
    agg = await db.connector_sync_events.aggregate(pipeline).to_list(100)
    counts: dict = {}
    for a in agg:
        counts.setdefault(a["_id"]["c"], {})[a["_id"]["s"]] = a["n"]

    apps = []
    for conn, health in zip(registry, healths):
        apps.append({
            **{k: conn[k] for k in ("name", "label", "kind", "base_url", "enabled")},
            "health": health,
            "sync": counts.get(conn["name"], {}),
        })
    return {"apps": apps, "total": len(apps), "ok": sum(1 for a in apps if a["health"]["status"] == "OK")}


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


@connectors_router.post("/oscop-ia-bois/sync")
async def sync_iabois_now(_: dict = Depends(_admin)):
    """Import manuel des projets IA Bois."""
    from connectors.iabois_sync import pull_iabois_projects

    return await pull_iabois_projects()


@connectors_router.get("/iabois/projects")
async def list_iabois_projects(limit: int = Query(50, le=200), _: dict = Depends(_admin)):
    docs = await db.iabois_quote_requests.find({}, {"_id": 0}).sort("imported_at", -1).limit(limit).to_list(limit)
    return {"projects": docs, "total": len(docs)}


@connectors_router.post("/iabois/projects/{project_id}/quote")
async def create_iabois_quote(project_id: str, _: dict = Depends(_admin)):
    """Crée un devis matériaux pré-rempli depuis un projet IA Bois (idempotent)."""
    from connectors.iabois_quotes import create_quote_from_project

    result = await create_quote_from_project(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Projet IA Bois introuvable")
    return result


@connectors_router.get("/iabois/quotes/{quote_id}")
async def get_iabois_quote(quote_id: str, _: dict = Depends(_admin)):
    quote = await db.iabois_quotes.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    return quote


@connectors_router.post("/broadcast-spots")
async def broadcast_spots(_: dict = Depends(_admin)):
    """Diffuse les spots vidéo IA vers les applications connectées de l'écosystème OSCOP."""
    import os

    base_url = os.environ.get("FRONTEND_URL", "")
    jobs = await db.ai_video_jobs.find(
        {"status": "DONE", "video_url": {"$ne": None}}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    spots, seen = [], set()
    for job in jobs:
        if job["product_id"] in seen:
            continue
        seen.add(job["product_id"])
        product = await db.vendor_products.find_one(
            {"id": job["product_id"]}, {"_id": 0, "name": 1, "video_urls": 1, "video_views": 1}) or {}
        vendor = await db.vendors.find_one(
            {"id": job["vendor_id"]}, {"_id": 0, "company_name": 1}) or {}
        urls = product.get("video_urls") or {"fr": job["video_url"]}
        spots.append({
            "product_id": job["product_id"],
            "product_name": product.get("name", "Produit"),
            "vendor_name": vendor.get("company_name", ""),
            "views": int(product.get("video_views") or 0),
            "videos": {lang: (u if u.startswith("http") else f"{base_url}{u}") for lang, u in urls.items()},
            "source": "kdmarche",
        })
    if not spots:
        return {"status": "EMPTY", "spots": 0, "results": []}

    payload = {"spots": spots, "count": len(spots)}
    results = []
    for definition in generic_app.GENERIC_APPS:
        cfg = generic_app.app_config(definition)
        name = definition["name"]
        if not cfg["enabled"]:
            results.append({"connector": name, "status": "SKIPPED", "detail": "Non configuré"})
            continue
        event_id = await connectors_base.record_event(
            connector=name, action="broadcast_spots", source="ai_video_jobs",
            source_id=f"batch-{len(spots)}", detail=f"Diffusion de {len(spots)} spot(s) vidéo")
        try:
            resp = await generic_app.request(name, "POST", "/api/kdmarche/spots", json_payload=payload)
            await connectors_base.mark_event(event_id, "SUCCESS", response_excerpt=str(resp)[:300])
            results.append({"connector": name, "status": "SUCCESS"})
        except Exception as exc:
            await connectors_base.mark_event(event_id, "ERROR", error=str(exc)[:300], increment_attempt=True)
            results.append({"connector": name, "status": "ERROR", "detail": str(exc)[:200]})
    return {"status": "DONE", "spots": len(spots), "results": results}


@connectors_router.get("/health-status")
async def connectors_health_status(_: dict = Depends(_admin)):
    """Derniers statuts relevés par la surveillance automatique (health watch)."""
    docs = await db.connector_health_status.find({}, {"_id": 0}).to_list(50)
    return {"statuses": docs}


@connectors_router.get("/health-history")
async def connectors_health_history(
    name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    _: dict = Depends(_admin),
):
    """Chronologie des pannes et rétablissements détectés par le health watch."""
    query = {"name": name} if name else {}
    docs = await db.connector_health_events.find(query, {"_id": 0}).sort("at", -1).limit(limit).to_list(limit)
    return {"events": docs, "total": len(docs)}


@connectors_router.get("/{name}/health")
async def connector_health(name: str, _: dict = Depends(_admin)):
    registry = {c["name"]: c for c in connectors_base.connectors_registry()}
    conn = registry.get(name)
    if not conn:
        raise HTTPException(status_code=404, detail="Connecteur inconnu")
    if not conn["enabled"]:
        return {"name": name, "status": "DISABLED", "detail": "Variables .env manquantes"}
    if name in ("oscop-ged", "oscop-finance"):
        try:
            external = await oscop_crm.health()
            return {"name": name, "status": "OK", "external": external}
        except Exception as exc:
            return {"name": name, "status": "ERROR", "error": str(exc)[:300]}
    return await generic_app.health(name)


@connectors_router.post("/push/order/{order_id}")
async def push_order(order_id: str, _: dict = Depends(_admin)):
    """Push manuel : facture -> GED + paiement -> Finance."""
    return await auto_sync.sync_order_paid(order_id)


@connectors_router.post("/push/contract/{contract_id}")
async def push_contract(contract_id: str, _: dict = Depends(_admin)):
    return await auto_sync.sync_contract_signed(contract_id)
