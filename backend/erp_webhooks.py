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


EVENT_LABELS = {"paid": "lolodrive.order.paid"}
STATUS_EVENT_KEYS = {"PREPARING": "preparing", "READY": "ready", "FULFILLED": "fulfilled"}
RETRY_DELAYS = [300, 900]


async def dispatch_lolodrive_order_event(order_id: str, event: str = "lolodrive.order.paid", extra: dict = None) -> None:
    """Notifie le relais LOLODRIVE (abonné API avec webhook) d'une commande / changement de statut sur son point."""
    try:
        order = await db.lolodrive_orders.find_one({"id": order_id}, {
            "_id": 0, "id": 1, "order_number": 1, "status": 1, "items": 1, "lolo_point_id": 1,
            "fulfillment_type": 1, "total_cents": 1, "total_uc": 1, "pay_with_uc": 1,
            "pickup_date": 1, "pickup_slot": 1, "created_at": 1})
        if not order or not order.get("lolo_point_id"):
            return
        point = await db.lolodrive_points.find_one(
            {"id": order["lolo_point_id"]}, {"_id": 0, "id": 1, "name": 1, "manager_user_id": 1})
        if not point or not point.get("manager_user_id"):
            return
        sub = await db.api_subscriptions.find_one(
            {"user_id": point["manager_user_id"], "status": "ACTIVE", "api_key_id": {"$exists": True}},
            sort=[("valid_until", -1)])
        if not sub:
            return
        key = await db.api_keys.find_one({
            "id": sub["api_key_id"], "is_active": True,
            "webhook_url": {"$exists": True, "$nin": ["", None]},
        }, {"_id": 0, "id": 1, "name": 1, "webhook_url": 1, "webhook_secret": 1, "webhook_events": 1,
            "webhook_paused": 1})
        if not key:
            return
        # Pause temporaire demandée par le relais : notification ignorée, configuration conservée
        if key.get("webhook_paused"):
            await db.webhook_deliveries.insert_one({
                "key_id": key["id"], "key_name": key.get("name"), "event": event, "order_id": order_id,
                "url": key["webhook_url"], "status_code": None, "ok": False, "paused": True,
                "error": "Webhook suspendu par le relais (pause)", "ts": datetime.now(timezone.utc).isoformat(),
            })
            return
        # Filtre des événements choisis par le relais (défaut : tous)
        wanted = key.get("webhook_events")
        if isinstance(wanted, list):
            if event == "lolodrive.order.paid":
                label = "paid"
            else:
                label = STATUS_EVENT_KEYS.get(((extra or {}).get("status") or "").upper())
            if label and label not in wanted:
                return
        payload = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), "order": order,
                   "data": {"lolo_point": {"id": point["id"], "name": point.get("name")}}}
        if extra:
            payload["data"].update(extra)
        await _deliver(key, event, order_id, json.dumps(payload, default=str))
    except Exception as exc:
        logger.error("Webhook relais LOLODRIVE %s/%s échoué : %s", event, order_id, exc)


async def send_test_event(key: dict) -> dict:
    """Envoie un événement d'exemple au webhook du partenaire et renvoie le résultat."""
    payload = {
        "event": "webhook.test", "ts": datetime.now(timezone.utc).isoformat(),
        "order": {"id": "test-order", "order_number": "KDM-TEST-0000", "zone_code": "GUADELOUPE",
                  "status": "CONFIRMED", "total_ttc_cents": 12345},
        "data": {"message": "Événement de test envoyé depuis KDMARCHÉ × O'SCOP — configuration OK"},
    }
    body = json.dumps(payload, default=str)
    headers = {"Content-Type": "application/json", "X-KDM-Event": "webhook.test"}
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
    ok = bool(status_code and status_code < 300)
    await db.webhook_deliveries.insert_one({
        "key_id": key["id"], "key_name": key.get("name"), "event": "webhook.test", "order_id": "test-order",
        "url": key["webhook_url"], "status_code": status_code, "ok": ok,
        "error": error, "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": ok, "status_code": status_code, "error": error}


async def _deliver(key: dict, event: str, order_id: str, body: str, attempt: int = 0) -> None:
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
    ok = bool(status_code and status_code < 300)
    await db.webhook_deliveries.insert_one({
        "key_id": key["id"], "key_name": key.get("name"), "event": event, "order_id": order_id,
        "url": key["webhook_url"], "status_code": status_code, "ok": ok,
        "attempt": attempt, "error": error, "ts": datetime.now(timezone.utc).isoformat(),
    })
    if not ok:
        logger.warning("Webhook %s → %s : %s %s (tentative %s)", key.get("name"), key["webhook_url"], status_code, error or "", attempt)
        if attempt < len(RETRY_DELAYS) and event != "webhook.test":
            asyncio.get_event_loop().create_task(_retry_later(key, event, order_id, body, attempt + 1))
    else:
        logger.info("Webhook %s notifié (%s, commande %s, tentative %s)", key.get("name"), event, order_id, attempt)


async def _retry_later(key: dict, event: str, order_id: str, body: str, attempt: int, delay: int = None) -> None:
    """Relance automatique différée d'une livraison échouée (2 tentatives : +5 min puis +15 min)."""
    await asyncio.sleep(delay if delay is not None else RETRY_DELAYS[attempt - 1])
    fresh = await db.api_keys.find_one({"id": key["id"], "is_active": True},
                                       {"_id": 0, "id": 1, "name": 1, "webhook_url": 1, "webhook_secret": 1,
                                        "webhook_paused": 1})
    if not fresh or not fresh.get("webhook_url") or fresh.get("webhook_paused"):
        return
    logger.info("Relance auto webhook %s (tentative %s, commande %s)", fresh.get("name"), attempt, order_id)
    await _deliver(fresh, event, order_id, body, attempt=attempt)
