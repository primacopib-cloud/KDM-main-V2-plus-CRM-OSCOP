"""Rapport hebdo d'activité — envoyé chaque lundi à l'équipe dirigeante (Brevo)."""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
weekly_report_router = APIRouter(prefix="/api/admin/reports", tags=["weekly-report"])
db = None

REPORT_EMAIL = os.environ.get("WEEKLY_REPORT_EMAIL") or os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


def set_weekly_report_database(database):
    global db
    db = database


async def _collect_stats(database, since: datetime) -> dict:
    since_iso = since.isoformat()
    orders = await database.orders.count_documents({"created_at": {"$gte": since}})
    revenue = 0
    async for row in database.orders.aggregate([
        {"$match": {"created_at": {"$gte": since}, "status": {"$nin": ["CANCELLED", "cancelled"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_ttc_cents"}}},
    ]):
        revenue = row["total"] or 0
    quotes = await database.quote_requests.count_documents({"created_at": {"$gte": since}})
    new_users = await database.users.count_documents({"created_at": {"$gte": since}})
    consultations = await database.consultations.count_documents({"created_at": {"$gte": since_iso}})
    testimonials = await database.testimonials.count_documents({"created_at": {"$gte": since_iso}})
    sent_week, clicks, conversions, active = 0, 0, 0, 0
    async for c in database.prospectia_campaigns.find({}, {"prospects": 1, "click_count": 1, "conversions_count": 1, "status": 1}):
        if c.get("status") == "running":
            active += 1
        clicks += c.get("click_count", 0)
        conversions += c.get("conversions_count", 0)
        sent_week += sum(1 for p in c.get("prospects", []) if (p.get("sent_at") or "") >= since_iso)
    return {"orders": orders, "revenue_eur": revenue / 100, "quotes": quotes, "new_users": new_users,
            "consultations": consultations, "testimonials": testimonials,
            "prospect_sent": sent_week, "prospect_clicks": clicks, "prospect_conversions": conversions,
            "campaigns_active": active}


def _row(label: str, value) -> str:
    return (f"<tr><td style='padding:8px 12px;border-bottom:1px solid #eee'>{label}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;font-weight:bold'>{value}</td></tr>")


async def send_weekly_activity_report(database, force: bool = False) -> bool:
    now = datetime.now(timezone.utc)
    if not force and now.weekday() != 0:
        return False
    week_key = now.strftime("%G-W%V")
    if not force and await database.system_flags.find_one({"key": "weekly_activity_report", "week": week_key}):
        return False
    since = now - timedelta(days=7)
    s = await _collect_stats(database, since)
    period = f"{since.strftime('%d/%m')} → {now.strftime('%d/%m/%Y')}"
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:600px'>"
        f"<h2 style='color:#5B2E8C'>📊 Rapport hebdo d'activité — Communityplace</h2>"
        f"<p style='color:#555'>Période : <b>{period}</b> (semaine {week_key})</p>"
        "<table style='width:100%;border-collapse:collapse;font-size:14px'>"
        + _row("🛒 Nouvelles commandes", s["orders"])
        + _row("💶 Chiffre d'affaires TTC (hors annulées)", f"{s['revenue_eur']:.2f} €")
        + _row("📄 Demandes de devis reçues", s["quotes"])
        + _row("👥 Nouveaux comptes membres", s["new_users"])
        + _row("⚖️ Consultations / enchères créées", s["consultations"])
        + _row("💬 Témoignages reçus", s["testimonials"])
        + _row("📤 Prospection : emails envoyés (7 j)", s["prospect_sent"])
        + _row("🖱 Prospection : clics cumulés", s["prospect_clicks"])
        + _row("✅ Prospection : conversions cumulées", s["prospect_conversions"])
        + _row("🚀 Campagnes PROSPECT'IA actives", s["campaigns_active"])
        + "</table>"
        "<p style='color:#999;font-size:11px;margin-top:18px'>Rapport automatique KDMARCHÉ × O'SCOP — envoyé chaque lundi.</p></div>"
    )
    from brevo_service import send_email
    await send_email(to_email=REPORT_EMAIL, to_name="Équipe dirigeante",
                     subject=f"📊 Rapport hebdo Communityplace — semaine {week_key}",
                     html_content=html, tags=["weekly-activity-report"])
    await database.system_flags.update_one(
        {"key": "weekly_activity_report", "week": week_key},
        {"$set": {"sent_at": now.isoformat(), "stats": s}}, upsert=True)
    logger.info("Rapport hebdo d'activité envoyé à %s (%s)", REPORT_EMAIL, week_key)
    return True


@weekly_report_router.post("/weekly/send")
async def trigger_weekly_report(admin: dict = Depends(require_admin)):
    await send_weekly_activity_report(db, force=True)
    return {"ok": True, "sent_to": REPORT_EMAIL}
