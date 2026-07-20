"""Historique de liquidité : snapshots quotidiens du nombre de fournisseurs éligibles par catégorie."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

liquidity_router = APIRouter(prefix="/api/admin/liquidity", tags=["liquidity"])

db = None


def set_liquidity_database(database):
    global db
    db = database


async def _eligible_count(category: str) -> int:
    vendor_ids = await db.vendor_products.distinct("vendor_id", {"category": category})
    emails = set()
    if vendor_ids:
        async for v in db.vendors.find({"id": {"$in": vendor_ids}}, {"_id": 0, "email": 1}):
            if v.get("email"):
                emails.add(v["email"].lower())
    return len(emails)


async def snapshot_liquidity(database) -> int:
    """Cron (idempotent par jour) : un point par catégorie et par jour."""
    global db
    if db is None:
        db = database
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    for category in await db.vendor_products.distinct("category"):
        if not category:
            continue
        await db.liquidity_snapshots.update_one(
            {"category": category, "day": day},
            {"$set": {"eligible_vendors": await _eligible_count(category),
                      "ts": datetime.now(timezone.utc).isoformat()}},
            upsert=True)
        count += 1
    return count


@liquidity_router.get("/history")
async def liquidity_history(admin: dict = Depends(require_admin)):
    await snapshot_liquidity(db)
    out = {}
    async for s in db.liquidity_snapshots.find({}, {"_id": 0}).sort("day", 1):
        out.setdefault(s["category"], []).append({"day": s["day"], "eligible_vendors": s["eligible_vendors"]})
    items = []
    for category, series in sorted(out.items()):
        series = series[-30:]
        current = series[-1]["eligible_vendors"]
        previous = series[-2]["eligible_vendors"] if len(series) > 1 else current
        items.append({"category": category, "current": current, "trend": current - previous, "series": series})
    return {"items": items}
