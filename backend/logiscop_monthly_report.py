"""Synthèse mensuelle Transport LOGI'SCOP (CA, avoirs, litiges) — PDF envoyé aux admins le 1er du mois."""
import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

VIOLET = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#B8860B")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")
REPORT_EMAIL = os.environ.get("ADMIN_ALERT_EMAIL") or os.environ.get("WEEKLY_REPORT_EMAIL") \
    or os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


async def collect_monthly_stats(db, month: str) -> dict:
    """Statistiques transport du mois YYYY-MM : OT, facturation, encaissements, avoirs, litiges."""
    s = {"month": month, "ot_created": 0, "ot_delivered": 0, "on_time": 0, "on_time_base": 0,
         "invoiced_ht_cents": 0, "invoiced_ttc_cents": 0, "paid_ttc_cents": 0, "invoices": [],
         "unpaid_count": 0, "unpaid_ttc_cents": 0, "credits": [], "credits_ttc_cents": 0,
         "disputes_opened": [], "disputes_resolved": 0}
    closed = ["LIVRE_CONFORME", "LIVRE_AVEC_RESERVES", "PARTIEL"]
    async for ot in db.logiscop_transport_orders.find({}, {"_id": 0}):
        if (ot.get("created_at") or "")[:7] == month:
            s["ot_created"] += 1
        epod_at = ((ot.get("epod") or {}).get("at") or "")[:7]
        if ot.get("status") in closed and epod_at == month:
            s["ot_delivered"] += 1
            due = (ot.get("delivery") or {}).get("date")
            done = ((ot.get("execution") or {}).get("delivered_at") or (ot.get("epod") or {}).get("at") or "")[:10]
            if due and done:
                s["on_time_base"] += 1
                if done <= due:
                    s["on_time"] += 1
    async for inv in db.logiscop_transport_invoices.find({}, {"_id": 0}):
        if (inv.get("issued_at") or "")[:7] == month:
            s["invoiced_ht_cents"] += inv.get("amount_ht_cents") or 0
            s["invoiced_ttc_cents"] += inv.get("total_ttc_cents") or 0
            s["invoices"].append(inv)
        if (inv.get("paid_at") or "")[:7] == month:
            s["paid_ttc_cents"] += inv.get("total_ttc_cents") or 0
        if inv.get("status") != "PAID" and (inv.get("issued_at") or "")[:7] <= month:
            s["unpaid_count"] += 1
            s["unpaid_ttc_cents"] += inv.get("total_ttc_cents") or 0
    async for c in db.logiscop_transport_credits.find({}, {"_id": 0}):
        if (c.get("created_at") or "")[:7] == month:
            s["credits"].append(c)
            s["credits_ttc_cents"] += c.get("total_ttc_cents") or 0
    async for d in db.logiscop_disputes.find({}, {"_id": 0}):
        if (d.get("created_at") or "")[:7] == month:
            s["disputes_opened"].append(d)
        if d.get("status") == "RESOLVED" and (d.get("resolved_at") or d.get("updated_at") or "")[:7] == month:
            s["disputes_resolved"] += 1
    return s


def build_monthly_report_pdf(s: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=VIOLET, fontSize=14)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10.5, spaceBefore=8)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
    on_time_rate = f"{100 * s['on_time'] / s['on_time_base']:.0f} %" if s["on_time_base"] else "—"
    kpis = Table([
        ["OT créés", "OT livrés", "Ponctualité", "CA facturé HT", "CA facturé TTC", "Encaissé TTC"],
        [str(s["ot_created"]), str(s["ot_delivered"]), on_time_rate,
         _eur(s["invoiced_ht_cents"]), _eur(s["invoiced_ttc_cents"]), _eur(s["paid_ttc_cents"])]],
        colWidths=[30 * mm] * 6)
    kpis.setStyle(style)
    story = [
        Paragraph(f"SYNTHÈSE MENSUELLE TRANSPORT LOGI'SCOP — {s['month']}", h1),
        Paragraph(f"Éditée le {datetime.now(timezone.utc).strftime('%d/%m/%Y')} — envoi automatique aux "
                  "administrateurs KDMARCHÉ × O'SCOP", small),
        Spacer(1, 4 * mm), kpis, Spacer(1, 2 * mm),
        Paragraph(f"Encours impayé fin de période : <b>{s['unpaid_count']} facture(s)</b> pour "
                  f"<b>{_eur(s['unpaid_ttc_cents'])} TTC</b>.", n),
        Paragraph(f"Avoirs de service émis (article 22) : <b>{len(s['credits'])}</b> pour "
                  f"<b>{_eur(s['credits_ttc_cents'])} TTC</b>.", n),
        Paragraph(f"Litiges : <b>{len(s['disputes_opened'])} ouvert(s)</b> sur la période, "
                  f"<b>{s['disputes_resolved']} résolu(s)</b>.", n),
    ]
    if s["invoices"]:
        rows = [["Facture", "OT", "Donneur d'Ordre", "HT", "TTC", "Statut"]]
        for inv in sorted(s["invoices"], key=lambda i: i.get("issued_at") or ""):
            rows.append([inv["ref"], inv["ot_ref"], (inv.get("company_name") or "—")[:32],
                         _eur(inv.get("amount_ht_cents")), _eur(inv.get("total_ttc_cents")),
                         "Payée" if inv.get("status") == "PAID" else "En attente"])
        t = Table(rows, colWidths=[34 * mm, 34 * mm, 52 * mm, 22 * mm, 22 * mm, 18 * mm])
        t.setStyle(style)
        story += [Paragraph("FACTURES ÉMISES SUR LA PÉRIODE", h2), t]
    if s["credits"]:
        rows = [["Avoir", "Facture", "Motifs", "TTC"]]
        for c in s["credits"]:
            rows.append([c["ref"], c.get("invoice_ref") or "—", " + ".join(c.get("reasons") or []),
                         f"-{_eur(c.get('total_ttc_cents'))}"])
        t = Table(rows, colWidths=[40 * mm, 44 * mm, 60 * mm, 26 * mm])
        t.setStyle(style)
        story += [Paragraph("AVOIRS DE SERVICE ÉMIS", h2), t]
    if s["disputes_opened"]:
        rows = [["Litige", "OT", "Statut", "Responsabilité"]]
        for d in s["disputes_opened"]:
            rows.append([d.get("ref"), d.get("ot_ref") or "—", d.get("status") or "—",
                         d.get("liability") or "—"])
        t = Table(rows, colWidths=[40 * mm, 50 * mm, 40 * mm, 40 * mm])
        t.setStyle(style)
        story += [Paragraph("LITIGES OUVERTS SUR LA PÉRIODE", h2), t]
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP Mode D V1.2 — synthèse générée automatiquement.", small))
    doc.build(story)
    return buf.getvalue()


async def send_monthly_transport_report(db, force: bool = False, month: str | None = None) -> bool:
    """Le 1er du mois : synthèse PDF du mois précédent envoyée aux admins (idempotent via system_flags)."""
    now = datetime.now(timezone.utc)
    if not force and now.day != 1:
        return False
    month = month or (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    if not force and await db.system_flags.find_one({"key": "logiscop_monthly_report", "month": month}):
        return False
    s = await collect_monthly_stats(db, month)
    if not (s["ot_created"] or s["invoices"] or s["credits"] or s["disputes_opened"]):
        await db.system_flags.insert_one({"key": "logiscop_monthly_report", "month": month,
                                          "skipped": True, "sent_at": now.isoformat()})
        return False
    pdf = build_monthly_report_pdf(s)
    from brevo_service import send_email, is_brevo_configured
    if not is_brevo_configured():
        return False
    html = (
        f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#5B2E8C'>Synthèse transport LOGI'SCOP — {month}</h2>"
        f"<p><b>{s['ot_created']}</b> OT créés · <b>{s['ot_delivered']}</b> livrés · "
        f"CA facturé <b>{_eur(s['invoiced_ttc_cents'])} TTC</b> · encaissé <b>{_eur(s['paid_ttc_cents'])} TTC</b>.</p>"
        f"<p>Avoirs de service : <b>{len(s['credits'])}</b> ({_eur(s['credits_ttc_cents'])} TTC) — "
        f"Litiges : <b>{len(s['disputes_opened'])}</b> ouverts, <b>{s['disputes_resolved']}</b> résolus.</p>"
        f"<p>Encours impayé : <b>{s['unpaid_count']} facture(s)</b> ({_eur(s['unpaid_ttc_cents'])} TTC).</p>"
        "<p>La synthèse détaillée est jointe en PDF.</p>"
        "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
    await send_email(
        to_email=REPORT_EMAIL, to_name="Administration LOGI'SCOP",
        subject=f"[LOGI'SCOP] Synthèse mensuelle transport — {month}",
        html_content=html, tags=["logiscop-monthly-report"],
        attachments=[{"content": base64.b64encode(pdf).decode(),
                      "name": f"synthese-transport-{month}.pdf"}])
    await db.system_flags.update_one(
        {"key": "logiscop_monthly_report", "month": month},
        {"$set": {"sent_at": now.isoformat(), "skipped": False}}, upsert=True)
    logger.info("Synthèse mensuelle transport %s envoyée à %s", month, REPORT_EMAIL)
    return True
