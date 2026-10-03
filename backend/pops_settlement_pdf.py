"""Relevé mensuel PDF des règlements O'SCOP → POP'S (cessions, déductions articles manquants, net)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
BG = colors.HexColor("#FBF6EE")


def build_settlement_statement_pdf(pops: dict, month: str, rows: list) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm)
    h1 = ParagraphStyle("h1", fontSize=14, leading=18, textColor=DARK, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", fontSize=7.5, leading=10, textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle("cell", fontSize=8, leading=10, textColor=DARK)
    story = [
        Paragraph("O'SCOP × COOP'ACT — RELEVÉ MENSUEL DES RÈGLEMENTS POP'S", ParagraphStyle(
            "k", fontSize=8, textColor=GOLD, fontName="Helvetica-Bold", spaceAfter=2)),
        Paragraph(f"{pops.get('company_name') or ''} — {month}", h1),
        Paragraph(f"{pops.get('locality') or ''} · Montants en euros TTC. "
                  "Règlement = prix de cession convenu, déduction faite de la valeur TTC des articles non remis.", small),
        Spacer(1, 5 * mm),
    ]
    header = [Paragraph(f"<b>{h}</b>", cell) for h in
              ("Lot", "Remporté le", "Gagnant", "Cession TTC", "Déduction (manquants)", "Règlement net")]
    data = [header]
    tot_cession = tot_ded = tot_net = 0.0
    for r in rows:
        tot_cession += r["cession"]
        tot_ded += r["deduction"]
        tot_net += r["net"]
        data.append([
            Paragraph(f"{r['title']}<br/><font size=6.5>{r['reference']}</font>", cell),
            Paragraph((r["won_at"] or "")[:10], cell),
            Paragraph(r["winner"] or "—", cell),
            Paragraph(f"{r['cession']:.2f} €", cell),
            Paragraph(f"−{r['deduction']:.2f} €<br/><font size=6.5>{r['missing']}</font>" if r["deduction"] else "—", cell),
            Paragraph(f"<b>{r['net']:.2f} €</b>", cell),
        ])
    data.append([Paragraph("<b>TOTAL</b>", cell), "", "",
                 Paragraph(f"<b>{tot_cession:.2f} €</b>", cell),
                 Paragraph(f"<b>−{tot_ded:.2f} €</b>" if tot_ded else "—", cell),
                 Paragraph(f"<b>{tot_net:.2f} €</b>", cell)])
    tbl = Table(data, colWidths=[52 * mm, 20 * mm, 30 * mm, 24 * mm, 32 * mm, 24 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("BACKGROUND", (0, -1), (-1, -1), BG),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Tout article indisponible au retrait suit la procédure prévue : avoir partiel au gagnant et déduction "
        "sur le règlement — aucun remplacement par un autre produit ou une autre marque n'est autorisé.", small))
    doc.build(story)
    return buf.getvalue()
