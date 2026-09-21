"""Statistiques d'usage des langues du site : ping public + tableau superadmin."""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

lang_stats_router = APIRouter(prefix="/api", tags=["lang-stats"])

db = None

SUPPORTED_LANGS = ["fr", "en", "es", "gcf", "ar"]


def set_lang_stats_database(database):
    global db
    db = database


class LangPing(BaseModel):
    lang: str


@lang_stats_router.post("/lang-usage")
async def record_lang_usage(payload: LangPing):
    lang = (payload.lang or "").lower()
    lang = "gcf" if lang.startswith("gcf") else lang[:2]
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Langue non prise en charge")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.lang_usage.update_one(
        {"day": day, "lang": lang},
        {"$inc": {"count": 1}, "$setOnInsert": {"day": day, "lang": lang}},
        upsert=True,
    )
    return {"ok": True}


@lang_stats_router.get("/admin/lang-usage/stats")
async def lang_usage_stats(request: Request, days: int = 30):
    from admin_plans_common import get_current_admin_from_request
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    days = max(1, min(days, 365))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = await db.lang_usage.find({"day": {"$gte": since}}, {"_id": 0}).to_list(5000)
    totals = {lg: 0 for lg in SUPPORTED_LANGS}
    daily = {}
    for r in rows:
        totals[r["lang"]] = totals.get(r["lang"], 0) + r["count"]
        daily.setdefault(r["day"], {})[r["lang"]] = r["count"]
    grand = sum(totals.values())
    shares = {lg: (round(totals[lg] * 100 / grand, 1) if grand else 0) for lg in SUPPORTED_LANGS}
    return {"days": days, "total": grand, "totals": totals, "shares": shares,
            "daily": [{"day": d, **v} for d, v in sorted(daily.items())]}
