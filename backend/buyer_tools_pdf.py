"""PDF de comparaison de deux consultations (dossier d'achat)."""
from datetime import datetime, timezone
from io import BytesIO

VIOLET = "#451F6B"
GOLD = "#D4AF37"


def _eur(c):
    return "—" if c is None else f"{c / 100:.2f} EUR HT".replace(".", ",")


def generate_compare_pdf(a: dict, b: dict, deltas: dict, linked: bool) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=colors.HexColor(VIOLET), fontSize=16)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#666666"))
    story = [
        Paragraph("Comparaison de consultations — KDMARCHÉ × O'SCOP", h1),
        Paragraph(f"Édité le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC"
                  + (" · Lots liés par duplication" if linked else ""), small),
        Spacer(1, 8 * mm),
    ]
    rows = [
        ["", f"{a['ref']}", f"{b['ref']}"],
        ["Intitulé", a["title"], b["title"]],
        ["Statut", a["status"].replace("_", " "), b["status"].replace("_", " ")],
        ["Catégorie", a["category"], b["category"]],
        ["Procédure", a["procedure"], b["procedure"]],
        ["Clôture", str(a.get("closes_at", ""))[:10], str(b.get("closes_at", ""))[:10]],
        ["Inscrits", str(a["participants"]), str(b["participants"])],
        ["Offres valides", str(a["valid_bids"]), str(b["valid_bids"])],
        ["Meilleure offre", _eur(a["best_offer_ht_cents"]), _eur(b["best_offer_ht_cents"])],
        ["Offre médiane", _eur(a["median_offer_ht_cents"]), _eur(b["median_offer_ht_cents"])],
        ["Attributaire", a.get("winner") or "—", b.get("winner") or "—"],
    ]
    table = Table(rows, colWidths=[45 * mm, 65 * mm, 65 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VIOLET)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F1FA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 8 * mm))
    delta_lines = []
    if deltas.get("best_offer_diff_cents") is not None:
        sign = "+" if deltas["best_offer_diff_cents"] > 0 else ""
        delta_lines.append(f"Meilleure offre B vs A : {sign}{deltas['best_offer_diff_cents'] / 100:.2f} EUR "
                           f"({sign}{deltas['best_offer_diff_pct']} %)".replace(".", ","))
    delta_lines.append(f"Écart de participation : {deltas.get('participants_diff', 0):+d} inscrit(s)")
    delta_lines.append(f"Écart d'offres valides : {deltas.get('valid_bids_diff', 0):+d}")
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor(VIOLET), fontSize=11)
    story.append(Paragraph("Écarts constatés (B par rapport à A)", h2))
    for line in delta_lines:
        story.append(Paragraph(f"• {line}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Document indicatif à joindre au dossier d'achat — les CREDI'SCOP n'interviennent "
                           "jamais dans le classement des offres.", small))
    doc.build(story)
    return buf.getvalue()


def generate_risk_pdf(categories: list, method: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=colors.HexColor(VIOLET), fontSize=16)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#666666"))
    level_colors = {"ELEVE": "#C0392B", "MODERE": "#B9770E", "FAIBLE": "#1E8449"}
    story = [
        Paragraph("Rapport mensuel — Risque d'approvisionnement", h1),
        Paragraph(f"KDMARCHÉ × O'SCOP · Édité le {datetime.now(timezone.utc).strftime('%d/%m/%Y')} · {method}", small),
        Spacer(1, 8 * mm),
    ]
    rows = [["Catégorie", "Fournisseurs", "Tendance", "Lots 6 mois", "Score", "Niveau"]]
    for c in categories:
        rows.append([c["category"], str(c["eligible_vendors"]),
                     {"up": "Hausse", "down": "Baisse", "stable": "Stable"}.get(c["demand_trend"], "—"),
                     str(c["lots_6m"]), f"{c['risk_score']}/100", c["risk_level"]])
    table = Table(rows, colWidths=[45 * mm, 26 * mm, 24 * mm, 26 * mm, 22 * mm, 28 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VIOLET)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F1FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, c in enumerate(categories, start=1):
        style.append(("TEXTCOLOR", (5, i), (5, i), colors.HexColor(level_colors.get(c["risk_level"], "#333333"))))
        style.append(("FONTNAME", (5, i), (5, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    story.append(table)
    story.append(Spacer(1, 8 * mm))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor(VIOLET), fontSize=11)
    story.append(Paragraph("Recommandations", h2))
    for c in categories:
        story.append(Paragraph(f"• <b>{c['category']}</b> — {c['recommendation']}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Rapport indicatif destiné aux comités d'achat de la coopérative.", small))
    doc.build(story)
    return buf.getvalue()
