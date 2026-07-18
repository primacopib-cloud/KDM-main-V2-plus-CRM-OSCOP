"""Relevé CREDI'SCOP unifié en PDF (crédits IA, wallet org, avantages)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")

SOURCE_LABELS = {
    "vendor": "Crédits IA Vendeur",
    "org": "CREDI'SCOP Organisation",
    "user": "CREDI'SCOP Personnel",
}


def generate_crediscop_statement_pdf(statement: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=DARK, fontSize=18)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GOLD, fontSize=9)
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=7.5, textColor=colors.HexColor("#666666"))

    elements = [
        Paragraph("RELEVÉ CREDI'SCOP", title),
        Paragraph("Capital d'usage coopératif — Mes droits coopératifs mobilisables", sub),
        Spacer(1, 3 * mm),
        Paragraph(f"Titulaire : <b>{statement['holder']}</b> — Édité le {statement['generated_at'][:10]}", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]

    balance_rows = [["Compartiment", "Solde"]]
    for b in statement["balances"]:
        balance_rows.append([SOURCE_LABELS.get(b["kind"], b["kind"]), f"{b['balance']} crédits"])
    bt = Table(balance_rows, colWidths=[110 * mm, 60 * mm])
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements += [bt, Spacer(1, 5 * mm), Paragraph("Derniers mouvements", styles["Heading3"])]

    rows = [["Date", "Compartiment", "Libellé", "Mouvement", "Solde après"]]
    for e in statement["entries"][:40]:
        amount = e["amount"]
        rows.append([
            (e.get("at") or "")[:10],
            SOURCE_LABELS.get(e["source"], e["source"]),
            (e.get("label") or "")[:48],
            f"{'+' if amount >= 0 else ''}{amount}",
            str(e.get("balance_after", "")),
        ])
    if len(rows) == 1:
        rows.append(["—", "—", "Aucun mouvement", "—", "—"])
    mt = Table(rows, colWidths=[20 * mm, 42 * mm, 72 * mm, 20 * mm, 22 * mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E5E5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBF6EE")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements += [
        mt,
        Spacer(1, 6 * mm),
        Paragraph(
            "Les unités inscrites dans CREDI'SCOP constituent des droits d'usage internes. "
            "Elles ne représentent ni des parts sociales, ni un dépôt bancaire, ni un crédit financier, "
            "ni de la monnaie électronique, sauf lorsqu'un service réglementé est expressément fourni "
            "par un prestataire agréé.", small),
    ]
    doc.build(elements)
    return buf.getvalue()
