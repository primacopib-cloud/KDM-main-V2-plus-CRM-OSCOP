"""Suivi de la consommation IA (visuels, scripts, traductions) pour piloter le budget."""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
ai_usage_router = APIRouter(prefix="/api/admin/ai-usage", tags=["ai-usage"])
db = None

IMAGE_KINDS = {"storyboard_image", "product_image"}
KIND_LABELS = {
    "script": "Scripts de prospection",
    "campaign_extras": "Variantes A/B + relances",
    "storyboard_image": "Storyboards vidéo (images)",
    "product_copy": "Descriptions produits",
    "product_image": "Visuels produits",
    "translation": "Traductions témoignages",
    "polish": "Reformulations témoignages",
    "invite_email": "Emails d'invitation IA",
    "encheria_report": "Rapports d'adjudication",
    "product_scan": "Scans fiche produit (IA)",
    "transportia_invite": "TRANSPORT'IA — invitations & relances",
    "transportia_assist": "TRANSPORT'IA — assistant",
    "parrainia_campaign": "PARRAIN'IA — animations parrainage",
}


def set_ai_usage_database(database):
    global db
    db = database


async def log_ai_usage(database, kind: str, detail: str = None, units: int = 1) -> None:
    try:
        now = datetime.now(timezone.utc)
        await database.ai_usage.insert_one({
            "kind": kind, "detail": (detail or "")[:150], "units": max(1, units),
            "month": now.strftime("%Y-%m"), "created_at": now.isoformat()})
    except Exception as exc:
        logger.warning("log_ai_usage échoué : %s", exc)


async def _month_summary(month: str) -> dict:
    cost_image = float(os.environ.get("AI_COST_IMAGE_EUR", "0.04"))
    cost_text = float(os.environ.get("AI_COST_TEXT_EUR", "0.01"))
    items, total = [], 0.0
    async for row in db.ai_usage.aggregate([
        {"$match": {"month": month}},
        {"$group": {"_id": "$kind", "count": {"$sum": "$units"}}},
        {"$sort": {"count": -1}},
    ]):
        kind = row["_id"]
        unit = cost_image if kind in IMAGE_KINDS else cost_text
        cost = round(row["count"] * unit, 2)
        total += cost
        items.append({"kind": kind, "label": KIND_LABELS.get(kind, kind),
                      "count": row["count"], "cost_eur": cost,
                      "is_image": kind in IMAGE_KINDS})
    return {"month": month, "items": items, "total_cost_eur": round(total, 2),
            "total_count": sum(i["count"] for i in items)}


@ai_usage_router.get("")
async def ai_usage_summary(admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    prev = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    current = await _month_summary(month)
    previous = await _month_summary(prev)
    return {"current": current,
            "previous": {"month": prev, "total_cost_eur": previous["total_cost_eur"],
                         "total_count": previous["total_count"]}}
