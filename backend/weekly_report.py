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
    q_counts = {"pending": 0, "contacted": 0, "converted": 0, "lost": 0}
    quotes_converted_week = 0
    async for q in database.quote_requests.find({}, {"status": 1, "status_history": 1}):
        s0 = q.get("status")
        key = "contacted" if s0 == "processed" else (s0 if s0 in q_counts else "pending")
        q_counts[key] += 1
        if key == "converted":
            hist = q.get("status_history") or []
            at = next((h.get("at") for h in reversed(hist) if h.get("to") == "converted"), None)
            if at and at >= since_iso:
                quotes_converted_week += 1
    q_total = sum(q_counts.values())
    quote_conversion_rate = round(q_counts["converted"] / q_total * 100, 1) if q_total else 0
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
    return {"orders": orders, "revenue_eur": revenue / 100, "quotes": quotes,
            "quotes_converted_week": quotes_converted_week,
            "quote_conversion_rate": quote_conversion_rate,
            "quotes_pending": q_counts["pending"], "quotes_contacted": q_counts["contacted"],
            "quotes_converted": q_counts["converted"], "quotes_lost": q_counts["lost"],
            "new_users": new_users,
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
        + _row("🤝 Devis convertis en membres (7 j)", s.get("quotes_converted_week", 0))
        + _row("📈 Taux de conversion des devis (global)", f"{s.get('quote_conversion_rate', 0)} %")
        + _row("🗂 Pipeline devis (nouveau / contacté / converti / perdu)",
               f"{s.get('quotes_pending', 0)} / {s.get('quotes_contacted', 0)} / {s.get('quotes_converted', 0)} / {s.get('quotes_lost', 0)}")
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


@weekly_report_router.get("/weekly/history")
async def weekly_history(admin: dict = Depends(require_admin)):
    items = await db.system_flags.find(
        {"key": "weekly_activity_report"}, {"_id": 0, "week": 1, "sent_at": 1, "stats": 1},
    ).sort("week", -1).to_list(8)
    return {"items": items}


REPORT_ROWS = [
    ("orders", "Nouvelles commandes"),
    ("revenue_eur", "Chiffre d'affaires TTC (hors annulées)"),
    ("quotes", "Demandes de devis reçues"),
    ("quotes_converted_week", "Devis convertis en membres (7 j)"),
    ("quote_conversion_rate", "Taux de conversion des devis (%)"),
    ("quotes_pending", "Pipeline devis : nouveaux"),
    ("quotes_contacted", "Pipeline devis : contactés"),
    ("quotes_converted", "Pipeline devis : convertis"),
    ("quotes_lost", "Pipeline devis : perdus"),
    ("new_users", "Nouveaux comptes membres"),
    ("consultations", "Consultations / enchères créées"),
    ("testimonials", "Témoignages reçus"),
    ("prospect_sent", "Prospection : emails envoyés (7 j)"),
    ("prospect_clicks", "Prospection : clics cumulés"),
    ("prospect_conversions", "Prospection : conversions cumulées"),
    ("campaigns_active", "Campagnes PROSPECT'IA actives"),
]


@weekly_report_router.get("/weekly/{week}/pdf")
async def weekly_report_pdf(week: str, admin: dict = Depends(require_admin)):
    from fastapi import HTTPException
    from fastapi.responses import Response
    doc = await db.system_flags.find_one({"key": "weekly_activity_report", "week": week}, {"_id": 0})
    if not doc or not doc.get("stats"):
        raise HTTPException(status_code=404, detail="Rapport introuvable pour cette semaine")
    prev = await db.system_flags.find_one(
        {"key": "weekly_activity_report", "week": {"$lt": week}}, {"_id": 0, "stats": 1}, sort=[("week", -1)])
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    s, ps = doc["stats"], (prev or {}).get("stats") or {}
    rows = [["Indicateur", "Valeur", "Évolution"]]
    for key, label in REPORT_ROWS:
        cur = s.get(key, 0)
        val = f"{cur:.2f} €" if key == "revenue_eur" else str(cur)
        delta = ""
        if key in ps:
            diff = (cur or 0) - (ps.get(key) or 0)
            delta = "stable" if diff == 0 else f"{'+' if diff > 0 else ''}{diff:.0f}"
        rows.append([label, val, delta])
    table = Table(rows, colWidths=[100 * mm, 35 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2A3A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    styles = getSampleStyleSheet()
    buf = BytesIO()
    pdf_doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    pdf_doc.build([
        Paragraph("Rapport hebdo d'activité — Communityplace", ParagraphStyle("t", parent=styles["Title"], fontSize=17)),
        Paragraph(f"Semaine {week} — KDMARCHÉ × O'SCOP", ParagraphStyle("s", parent=styles["Normal"], textColor=colors.HexColor("#B8860B"))),
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 8 * mm),
        Paragraph("Rapport généré automatiquement chaque lundi. Évolution calculée par rapport à la semaine précédente disponible.", styles["Normal"]),
    ])
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=rapport-hebdo-{week}.pdf"})
