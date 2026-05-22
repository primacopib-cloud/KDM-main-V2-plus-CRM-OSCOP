"""
Brevo transactional webhooks → délivrabilité metrics.

Brevo envoie un webhook par event (delivered, opened, soft_bounce, hard_bounce, blocked, etc.).
Doc: https://developers.brevo.com/docs/transactional-webhooks

We persist all events into `brevo_events` and keep a per-recipient aggregated counter
in `brevo_metrics_daily` for the ESS reporting dashboard.

Public endpoint (no auth) — Brevo posts JSON to /api/brevo/webhook.
Optional shared-secret header `X-Brevo-Token` can be configured via BREVO_WEBHOOK_TOKEN.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/brevo", tags=["Brevo Webhooks"])

db = None


def set_brevo_webhook_database(database):
    global db
    db = database


# Brevo event names
DELIVERY_EVENTS = {"delivered"}
ENGAGEMENT_EVENTS = {"opened", "click", "unique_opened"}
FAILURE_EVENTS = {"soft_bounce", "hard_bounce", "blocked", "spam", "invalid_email", "deferred", "error"}


@router.post("/webhook")
async def brevo_webhook(
    request: Request,
    x_brevo_token: Optional[str] = Header(None, alias="X-Brevo-Token"),
):
    """Receive a Brevo event payload (single event or list)."""
    expected = os.environ.get("BREVO_WEBHOOK_TOKEN", "").strip()
    if expected and x_brevo_token != expected:
        raise HTTPException(status_code=401, detail="Invalid Brevo webhook token")

    body = await request.json()
    events: List[Dict[str, Any]] = body if isinstance(body, list) else [body]
    if db is None:
        raise HTTPException(status_code=500, detail="Brevo webhook DB not initialized")

    now = datetime.now(timezone.utc)
    inserted = 0
    for ev in events:
        event_name = (ev.get("event") or "").lower()
        recipient = ev.get("email") or ev.get("recipient")
        message_id = ev.get("message-id") or ev.get("messageId") or ev.get("id")
        tag = ev.get("tag")
        if isinstance(tag, list):
            tag = tag[0] if tag else None
        ts = ev.get("ts") or ev.get("date") or now.isoformat()

        doc = {
            "event": event_name,
            "recipient": recipient,
            "message_id": message_id,
            "tag": tag,
            "raw_ts": ts,
            "received_at": now,
            "raw": ev,
        }
        try:
            await db.brevo_events.insert_one(doc)
            inserted += 1
        except Exception as exc:
            logger.warning("Brevo event insert failed: %s", exc)
            continue

        # Aggregate daily counters per event
        day_key = now.strftime("%Y-%m-%d")
        await db.brevo_metrics_daily.update_one(
            {"date": day_key, "event": event_name},
            {"$inc": {"count": 1}, "$setOnInsert": {"date": day_key, "event": event_name}},
            upsert=True,
        )
    return {"ok": True, "received": inserted}


@router.get("/metrics/summary")
async def brevo_metrics_summary(days: int = 30):
    """Aggregated delivered/bounced/opened metrics for the last N days. Used by ESS reporting."""
    if db is None:
        raise HTTPException(status_code=500, detail="Brevo webhook DB not initialized")
    days = max(1, min(days, 365))
    pipeline = [
        {"$group": {"_id": "$event", "total": {"$sum": "$count"}}},
        {"$sort": {"total": -1}},
    ]
    rows = await db.brevo_metrics_daily.aggregate(pipeline).to_list(100)
    by_event = {r["_id"]: r["total"] for r in rows}
    delivered = sum(by_event.get(k, 0) for k in DELIVERY_EVENTS)
    bounced = sum(by_event.get(k, 0) for k in {"soft_bounce", "hard_bounce", "blocked"})
    opened = by_event.get("opened", 0) + by_event.get("unique_opened", 0)
    failures = sum(by_event.get(k, 0) for k in FAILURE_EVENTS)
    total_attempts = delivered + failures
    return {
        "days": days,
        "delivered": delivered,
        "bounced": bounced,
        "opened": opened,
        "failures": failures,
        "delivery_rate": round(delivered / total_attempts, 4) if total_attempts else None,
        "bounce_rate": round(bounced / total_attempts, 4) if total_attempts else None,
        "open_rate": round(opened / delivered, 4) if delivered else None,
        "by_event": by_event,
    }


async def setup_brevo_webhook_indexes(database):
    await database.brevo_events.create_index("recipient")
    await database.brevo_events.create_index("event")
    await database.brevo_events.create_index([("received_at", -1)])
    await database.brevo_metrics_daily.create_index([("date", 1), ("event", 1)], unique=True)
