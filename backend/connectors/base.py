"""Socle commun des connecteurs externes (multi-apps).

Chaque connecteur = 1 adaptateur (fichier) + 2-3 variables .env.
File de synchronisation unifiée : collection `connector_sync_events`.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

db = None


def set_connectors_database(database) -> None:
    global db
    db = database


async def ensure_connectors_indexes(database) -> None:
    await database.connector_sync_events.create_index("id", unique=True)
    await database.connector_sync_events.create_index([("connector", 1), ("created_at", -1)])
    await database.connector_sync_events.create_index([("status", 1), ("created_at", -1)])
    await database.favorites_alerts_log.create_index([("user_id", 1), ("product_id", 1), ("alert_type", 1), ("sent_at", -1)])
    await database.user_favorites.create_index("favorites.product_id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_event(
    *,
    connector: str,
    action: str,
    source: str,
    source_id: str,
    status: str = "PENDING",
    detail: Optional[str] = None,
    error: Optional[str] = None,
    response_excerpt: Optional[Any] = None,
) -> str:
    event_id = str(uuid.uuid4())
    await db.connector_sync_events.insert_one({
        "id": event_id,
        "connector": connector,
        "action": action,
        "source": source,
        "source_id": source_id,
        "status": status,
        "detail": detail,
        "error": error,
        "response_excerpt": response_excerpt,
        "attempts": 1,
        "created_at": _now(),
        "updated_at": _now(),
    })
    return event_id


async def mark_event(
    event_id: str,
    status: str,
    *,
    detail: Optional[str] = None,
    error: Optional[str] = None,
    response_excerpt: Optional[Any] = None,
    increment_attempt: bool = False,
) -> None:
    update: Dict[str, Any] = {"$set": {"status": status, "updated_at": _now()}}
    if detail is not None:
        update["$set"]["detail"] = detail
    update["$set"]["error"] = error
    if response_excerpt is not None:
        update["$set"]["response_excerpt"] = response_excerpt
    if increment_attempt:
        update["$inc"] = {"attempts": 1}
    await db.connector_sync_events.update_one({"id": event_id}, update)


# ---------------------------------------------------------------------------
# Registre des connecteurs (extensible : 1 entrée par app connectée)
# ---------------------------------------------------------------------------

def connectors_registry() -> List[Dict[str, Any]]:
    from connectors.oscop_crm import oscop_config
    from connectors.generic_app import GENERIC_APPS, app_config

    cfg = oscop_config()
    registry = [
        {
            "name": "oscop-ged",
            "label": "GED ESS — Objectif SCOP Outremer",
            "kind": "ged",
            "base_url": cfg["base_url"],
            "enabled": cfg["enabled"],
            "description": "Push automatique des factures (commande payée) et contrats signés vers la GED du CRM.",
        },
        {
            "name": "oscop-finance",
            "label": "Finance — Objectif SCOP Outremer",
            "kind": "finance",
            "base_url": cfg["base_url"],
            "enabled": cfg["enabled"],
            "description": "Push des paiements encaissés vers /api/paiements du CRM.",
        },
    ]
    for definition in GENERIC_APPS:
        app_cfg = app_config(definition)
        registry.append({
            "name": definition["name"],
            "label": definition["label"],
            "kind": definition["kind"],
            "base_url": app_cfg["base_url"],
            "enabled": app_cfg["enabled"],
            "description": definition["description"],
        })
    return registry
