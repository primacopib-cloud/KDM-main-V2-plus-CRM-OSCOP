"""Export PDF des contrats rédigés par Oracle Admin — en-tête O'SCOP."""
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GREY = colors.HexColor("#555555")


def build_contract_pdf(contract_text: str, query: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Contrat — O'SCOP × Oracle")
    brand = ParagraphStyle("brand", fontSize=9, leading=12, textColor=GOLD, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", fontSize=13, leading=17, textColor=DARK, fontName="Helvetica-Bold",
                        spaceBefore=6, spaceAfter=4)
    h2 = ParagraphStyle("h2", fontSize=10.5, leading=14, textColor=DARK, fontName="Helvetica-Bold",
                        spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("body", fontSize=9, leading=12.5, textColor=DARK, spaceAfter=3)
    small = ParagraphStyle("small", fontSize=7.5, leading=10, textColor=GREY)

    story = [
        Paragraph("O'SCOP — OBJECTIF SCOP OUTREMER × KDMARCHÉ", brand),
        Paragraph("Projet de contrat commercial rédigé par Oracle (assistant IA)", small),
        Spacer(1, 4 * mm),
    ]
    lines = [ln.strip() for ln in (contract_text or "").splitlines()]
    first_title = False
    for ln in lines:
        if not ln:
            continue
        esc = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        upperish = ln.upper()
        if not first_title and (upperish.isupper() or ln.startswith("PROJET DE")) and len(ln) < 120:
            story.append(Paragraph(esc, h1))
            first_title = True
        elif upperish.startswith("ARTICLE ") or (ln[:3].rstrip(".").isdigit() and len(ln) < 110):
            story.append(Paragraph(esc, h2))
        else:
            story.append(Paragraph(esc, body))
    story.append(Spacer(1, 6 * mm))
    gen = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    story.append(Paragraph(
        f"Document généré le {gen} par Oracle (KDMARCHÉ × O'SCOP) — demande : {query[:140]}<br/>"
        "Projet généré par IA : à faire relire et valider par un conseil juridique avant signature. "
        "Ce document ne constitue pas un conseil juridique.", small))
    doc.build(story)
    return buf.getvalue()
