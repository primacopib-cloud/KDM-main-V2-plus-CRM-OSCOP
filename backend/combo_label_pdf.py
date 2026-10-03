"""Étiquette PDF d'un lot COOP'ACT (composition, allergènes, prix) à afficher en magasin POP'S."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
BG = colors.HexColor("#FBF6EE")


def _cur(c):
    return "€" if (c or "EUR") == "EUR" else c


def build_combo_label_pdf(offer: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A5, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm)
    h1 = ParagraphStyle("h1", fontSize=13, leading=16, textColor=DARK, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", fontSize=7.5, leading=10, textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle("cell", fontSize=8, leading=10, textColor=DARK)
    cur = _cur(offer.get("currency"))
    items = offer.get("items_detail") or []
    lot_type = offer.get("lot_type", "SAME")
    story = [
        Paragraph("COOP'ACT — LOT PROPOSÉ PAR VOTRE POP'S", ParagraphStyle(
            "k", fontSize=8, textColor=GOLD, fontName="Helvetica-Bold", spaceAfter=2)),
        Paragraph(offer.get("product_name") or "Lot", h1),
        Paragraph(f"Référence offre : {offer.get('id', '')[:13]} · {offer.get('company_name') or ''} "
                  f"({offer.get('locality') or ''})", small),
        Spacer(1, 4 * mm),
    ]
    rows = [[Paragraph("<b>Article</b>", cell), Paragraph("<b>Quantité</b>", cell),
             Paragraph("<b>Prix TTC</b>", cell), Paragraph("<b>Prix au kg/L</b>", cell)]]
    for it in items:
        ppu = it.get("price_per_unit")
        rows.append([
            Paragraph(f"{it.get('name', '')}" + (f"<br/><font size=6.5>{it['brand']}</font>" if it.get("brand") else ""), cell),
            Paragraph(it.get("format_label") or "—", cell),
            Paragraph(f"{it['unit_price_ttc']:.2f} {cur}" if (lot_type == "COMPOSED" and it.get("unit_price_ttc") is not None) else "—", cell),
            Paragraph(f"{ppu['value']:.2f} {cur}/{ppu['unit']}" if ppu else "—", cell),
        ])
    tbl = Table(rows, colWidths=[52 * mm, 26 * mm, 24 * mm, 26 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3 * mm))
    price = offer.get("final_price")
    if price is not None:
        story.append(Paragraph(
            f"PRIX DU LOT : {price:.2f} {cur} TTC"
            + (" (lot à unités identiques)" if lot_type == "SAME" else " (somme des articles)"),
            ParagraphStyle("p", fontSize=11, textColor=GOLD, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 3 * mm))
    for it in items:
        story.append(Paragraph(f"<b>{it.get('name', '')}</b> — Ingrédients : {it.get('ingredients') or '—'}. "
                               f"<b>Allergènes : {it.get('allergens') or '—'}</b>", small))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Prix exprimés en euros TTC. La DDM/DLC exacte est communiquée au plus tard à la remise du lot. "
        "Tout article indisponible suit la procédure prévue (avoir partiel) — aucun remplacement par un autre "
        "produit ou une autre marque n'est autorisé.", small))
    doc.build(story)
    return buf.getvalue()
