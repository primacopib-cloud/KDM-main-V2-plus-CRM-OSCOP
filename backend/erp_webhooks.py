"""Webhooks ERP — notifie les partenaires (clés API avec webhook_url) des changements de statut commande."""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

db = None

ORDER_PROJ = {"_id": 0, "id": 1, "order_number": 1, "zone_code": 1, "status": 1, "incoterm": 1,
              "items_count": 1, "total_ttc_cents": 1, "updated_at": 1, "logistics": 1}


def set_webhooks_database(database):
    global db
    db = database


async def dispatch_order_event(order_id: str, event: str, extra: dict = None) -> None:
    """Fire-and-forget : POST l'événement à tous les webhooks actifs ayant le scope orders:read."""
    try:
        order = await db.orders.find_one({"id": order_id}, ORDER_PROJ)
        if not order:
            return
        keys = await db.api_keys.find({
            "is_active": True,
            "webhook_url": {"$exists": True, "$nin": ["", None]},
            "scopes": "orders:read",
        }, {"_id": 0, "id": 1, "name": 1, "webhook_url": 1, "webhook_secret": 1}).to_list(50)
        if not keys:
            return
        payload = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), "order": order}
        if extra:
            payload["data"] = extra
        body = json.dumps(payload, default=str)
        await asyncio.gather(*[_deliver(k, event, order_id, body) for k in keys])
    except Exception as exc:
        logger.error("Webhook dispatch %s/%s échoué : %s", event, order_id, exc)


async def _deliver(key: dict, event: str, order_id: str, body: str) -> None:
    headers = {"Content-Type": "application/json", "X-KDM-Event": event}
    if key.get("webhook_secret"):
        sig = hmac.new(key["webhook_secret"].encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-KDM-Signature"] = f"sha256={sig}"
    status_code, error = None, None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(key["webhook_url"], content=body, headers=headers)
            status_code = resp.status_code
    except Exception as exc:
        error = str(exc)[:200]
    await db.webhook_deliveries.insert_one({
        "key_id": key["id"], "key_name": key.get("name"), "event": event, "order_id": order_id,
        "url": key["webhook_url"], "status_code": status_code, "ok": bool(status_code and status_code < 300),
        "error": error, "ts": datetime.now(timezone.utc).isoformat(),
    })
    if error or (status_code and status_code >= 300):
        logger.warning("Webhook %s → %s : %s %s", key.get("name"), key["webhook_url"], status_code, error or "")
    else:
        logger.info("Webhook %s notifié (%s, commande %s)", key.get("name"), event, order_id)
