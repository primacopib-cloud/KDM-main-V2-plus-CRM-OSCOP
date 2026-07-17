"""Flux entrant IA Bois → KDMARCHÉ : projets de maisons importés comme demandes de devis matériaux.

Sync automatique toutes les 15 minutes + déclenchement manuel depuis la page Connecteurs.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from connectors import base
from connectors import generic_app

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 900

db = None


def set_iabois_sync_database(database) -> None:
    global db
    db = database


async def pull_iabois_projects() -> dict:
    """Importe les projets IA Bois dans `iabois_quote_requests` (upsert). Retourne {total, new}."""
    event_id = await base.record_event(
        connector="oscop-ia-bois", action="pull_projects", source="scheduler",
        source_id="iabois-projects", detail="Import des projets IA Bois",
    )
    try:
        resp = await generic_app.request("oscop-ia-bois", "GET", "/api/projects")
        projects = resp.get("projects", []) if isinstance(resp, dict) else []
        now = datetime.now(timezone.utc).isoformat()
        new_count = 0
        for p in projects:
            pid = p.get("id")
            if not pid:
                continue
            result = await db.iabois_quote_requests.update_one(
                {"id": pid},
                {
                    "$set": {
                        "title": p.get("title") or p.get("nom") or "Projet sans titre",
                        "client": p.get("client") or p.get("client_name"),
                        "source_created_at": p.get("created_at"),
                        "raw": {k: str(v)[:300] for k, v in list(p.items())[:15]},
                        "last_synced_at": now,
                    },
                    "$setOnInsert": {"status": "NEW", "imported_at": now},
                },
                upsert=True,
            )
            if result.upserted_id is not None:
                new_count += 1
        detail = f"{len(projects)} projet(s) IA Bois — {new_count} nouveau(x)"
        await base.mark_event(event_id, "SUCCESS", detail=detail)
        logger.info(f"IA Bois sync: {detail}")
        return {"status": "SUCCESS", "total": len(projects), "new": new_count, "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"IA Bois sync failed: {exc}")
        return {"status": "ERROR", "error": str(exc)[:300], "event_id": event_id}


async def iabois_sync_loop() -> None:
    await asyncio.sleep(120)
    while True:
        try:
            await pull_iabois_projects()
        except Exception as exc:
            logger.error(f"IA Bois sync loop error: {exc}")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
