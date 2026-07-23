"""Rapport de litige LOGI'SCOP (incident, pièces, résolution) — PDF + archivage GEDESS à la clôture."""
import logging
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)
GOLD = colors.HexColor("#B8860B")
VIOLET = colors.HexColor("#2A1045")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")

RESP_LABEL = {"INDETERMINEE": "Indéterminée", "TRANSPORTEUR": "Transporteur",
              "DONNEUR_ORDRE": "Donneur d'Ordre", "PARTAGEE": "Partagée"}
STATUS_LABEL = {"OPEN": "Ouvert", "UNDER_REVIEW": "En instruction", "RESOLVED": "Résolu"}


def build_dispute_report_pdf(dispute: dict, ot: dict) -> bytes:
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=VIOLET, fontSize=13)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10, spaceBefore=8, spaceAfter=2)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=8.5, leading=12)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    inc = dispute.get("incident") or {}
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (0, -1), BG),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP")])
    rows = [
        ["Référence du dossier", dispute["ref"]],
        ["Type", "Incident critique — rupture de température dirigée (article 12)"],
        ["Ordre de Transport", f"{dispute['ot_ref']} — {(ot.get('pickup') or {}).get('zone_code')} → "
                               f"{(ot.get('delivery') or {}).get('zone_code')}"],
        ["Donneur d'Ordre", dispute.get("company_name") or "—"],
        ["Ouvert le", (dispute.get("created_at") or "")[:16].replace("T", " ")],
        ["Statut", STATUS_LABEL.get(dispute["status"], dispute["status"])],
        ["Responsabilité retenue", RESP_LABEL.get(dispute.get("responsibility"), "—")],
        ["Clôturé le", (dispute.get("resolved_at") or "—")[:16].replace("T", " ")],
    ]
    tab = Table([[Paragraph(f"<b>{a}</b>", n), Paragraph(str(b), n)] for a, b in rows],
                colWidths=[55 * mm, 125 * mm])
    tab.setStyle(style)
    story = [Paragraph(f"RAPPORT DE LITIGE LOGI'SCOP — {dispute['ref']}", h1),
             Paragraph("Transport public routier de marchandises sous température dirigée — Mode D V1.2", small),
             Spacer(1, 3 * mm), tab,
             Paragraph("1. CONSTAT DE L'INCIDENT", h2),
             Paragraph(
                 f"Le relevé de température joint à l'ePOD révèle <b>{inc.get('violations_count', '—')} lecture(s)</b> "
                 f"hors consigne <b>{inc.get('consigne', '—')} °C ± {inc.get('tolerance', '—')}</b> sur "
                 f"{inc.get('readings_count', '—')} lectures enregistrées (minimum {inc.get('min', '—')} °C, "
                 f"maximum {inc.get('max', '—')} °C). Conformément à l'article 12 de la Convention, toute rupture "
                 "de la chaîne de température constitue un Incident critique ; les données brutes sont conservées.", n),
             Paragraph("2. PIÈCES DU DOSSIER", h2)]
    pieces = dispute.get("pieces") or []
    if pieces:
        for p in pieces:
            story.append(Paragraph(
                f"• {p['name']} — déposée par {p.get('by', '—')} le {(p.get('at') or '')[:16].replace('T', ' ')} "
                f"(archivée au dossier, id {p['id'][:8]})", n))
    else:
        story.append(Paragraph("Aucune pièce déposée.", n))
    story.append(Paragraph("3. CHRONOLOGIE", h2))
    for t in dispute.get("timeline") or []:
        story.append(Paragraph(f"• {(t.get('at') or '')[:16].replace('T', ' ')} — {t.get('by', '—')} : "
                               f"{t.get('action', '')}", n))
    story += [Paragraph("4. RÉSOLUTION", h2),
              Paragraph(dispute.get("resolution_note") or "Aucune note de résolution enregistrée.", n),
              Spacer(1, 4 * mm),
              Paragraph("Rapport généré automatiquement par le Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP. "
                        "Les journaux horodatés, ePOD, relevés de température et pièces constituent des éléments "
                        "de preuve conservés 5 ans (article 13).", small)]
    doc.build(story)
    return buf.getvalue()


async def archive_dispute_report_to_ged(db, dispute_id: str) -> None:
    """Archivage GEDESS du rapport de litige à la clôture (best effort, tâche de fond)."""
    try:
        from gedess_client import gedess_upload_file, is_gedess_configured
        if not is_gedess_configured():
            return
        d = await db.logiscop_disputes.find_one({"id": dispute_id}, {"_id": 0})
        if not d:
            return
        ot = await db.logiscop_transport_orders.find_one({"id": d["ot_id"]}, {"_id": 0}) or {}
        pdf = build_dispute_report_pdf(d, ot)
        doc = await gedess_upload_file(
            f"rapport-litige-{d['ref']}.pdf", pdf, categorie="rapport",
            description=f"Rapport de litige {d['ref']} — OT {d['ot_ref']} ({d.get('company_name')}) — "
                        f"responsabilité {d.get('responsibility')}",
            tags="logiscop,transport,litige", mime_type="application/pdf")
        await db.logiscop_disputes.update_one({"id": dispute_id}, {"$set": {"report_ged_doc_id": doc.get("id")}})
        logger.info("Rapport litige %s archivé en GEDESS", d["ref"])
    except Exception as exc:
        logger.warning("Archivage rapport litige %s échoué : %s", dispute_id, exc)
