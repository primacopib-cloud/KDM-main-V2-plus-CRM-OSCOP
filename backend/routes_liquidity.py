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


async def _alert_threshold(category: str, previous: int, current: int):
    """Email admin quand une catégorie franchit le seuil des 3 fournisseurs éligibles."""
    if not (previous < 3 <= current):
        return
    try:
        import os
        from brevo_service import send_email
        from email_alerts import ADMIN_ALERT_EMAIL
        admin_email = os.environ.get("ADMIN_ALERT_EMAIL", ADMIN_ALERT_EMAIL)
        await send_email(
            to_email=admin_email, to_name="Super Admin",
            subject=f"Seuil de liquidité atteint — catégorie « {category} » ({current} fournisseurs)",
            html_content=f"""<h2 style="color:#451F6B;">Catégorie « {category} » prête pour une enchère</h2>
            <p>Le nombre de fournisseurs éligibles vient d'atteindre <strong>{current}</strong>
            (précédemment {previous}). Une <strong>enchère inversée multicritère</strong> est désormais
            envisageable sur cette catégorie.</p>
            <p style="color:#777;font-size:12px;">Historique de liquidité : Super Admin → Consultations.</p>""",
            tags=["liquidity-threshold"])
        logger.info("Alerte seuil liquidité envoyée : %s (%d → %d)", category, previous, current)
    except Exception as exc:
        logger.warning("Alerte seuil liquidité %s : %s", category, exc)


async def snapshot_liquidity(database) -> int:
    """Cron (idempotent par jour) : un point par catégorie et par jour + alerte au franchissement du seuil de 3."""
    global db
    if db is None:
        db = database
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    for category in await db.vendor_products.distinct("category"):
        if not category:
            continue
        current = await _eligible_count(category)
        prev_doc = await db.liquidity_snapshots.find_one(
            {"category": category, "day": {"$lt": day}}, {"_id": 0, "eligible_vendors": 1}, sort=[("day", -1)])
        existing_today = await db.liquidity_snapshots.find_one(
            {"category": category, "day": day}, {"_id": 0, "eligible_vendors": 1})
        await db.liquidity_snapshots.update_one(
            {"category": category, "day": day},
            {"$set": {"eligible_vendors": current, "ts": datetime.now(timezone.utc).isoformat()}},
            upsert=True)
        baseline = (existing_today or prev_doc or {}).get("eligible_vendors")
        if baseline is not None:
            await _alert_threshold(category, baseline, current)
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
