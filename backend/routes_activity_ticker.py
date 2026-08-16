"""Ticker public d'activité : dernières commandes et adhésions anonymisées."""
from datetime import datetime
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

activity_ticker_router = APIRouter(prefix="/api/public", tags=["Activity Ticker"])

db = None


def set_activity_ticker_database(database):
    global db
    db = database


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value or ""


@activity_ticker_router.get("/activity-ticker")
async def activity_ticker():
    items = []
    async for o in db.orders.find(
            {"zone_code": {"$ne": None}}, {"_id": 0, "zone_code": 1, "total_ttc_cents": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10):
        items.append({"type": "order", "zone": o.get("zone_code"),
                      "amount_cents": o.get("total_ttc_cents"), "at": _iso(o.get("created_at"))})
    async for org in db.orgs.find(
            {"hidden": {"$ne": True}}, {"_id": 0, "territory": 1, "member_type": 1, "created_at": 1}
    ).sort("created_at", -1).limit(6):
        items.append({"type": "membership", "zone": org.get("territory"),
                      "member_type": org.get("member_type"), "at": _iso(org.get("created_at"))})
    items.sort(key=lambda i: i["at"] or "", reverse=True)
    return {"items": items[:14]}
