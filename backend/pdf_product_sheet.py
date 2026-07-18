"""Génération PDF de la fiche produit vendeur (téléchargeable depuis l'Espace Vendeur)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")


def generate_product_sheet_pdf(product: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=DARK, fontSize=18)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GOLD, fontSize=10)
    normal = styles["Normal"]

    rows = [
        ("SKU / Référence", product.get("sku", "—")),
        ("Code EAN-13", product.get("ean13") or "—"),
        ("Catégorie", product.get("category", "—")),
        ("Marque", product.get("brand") or "—"),
        ("Prix HT", f"{product.get('price_ht', 0):.2f} €"),
        ("Taux TVA", f"{product.get('tva_rate', 0)}%"),
        ("Prix TTC", f"{product.get('price_ttc', 0):.2f} €"),
        ("Stock", str(product.get("stock_quantity", 0))),
        ("Quantité min. commande", str(product.get("min_order_quantity", 1))),
        ("Unité de vente", product.get("unit_type", "—")),
        ("Conditionnement", product.get("format_type", "—")),
        ("Origine", f"{product.get('country_of_origin', '—')} {product.get('region_of_origin') or ''}".strip()),
        ("DLC (jours)", str(product.get("dlc_days") or "—")),
        ("Conditions de stockage", product.get("storage_conditions") or "—"),
        ("Zones de disponibilité", ", ".join(product.get("available_zones") or []) or "—"),
        ("Statut", product.get("status", "—")),
        ("Vendeur", product.get("vendor_name", "—")),
    ]
    table = Table([[Paragraph(f"<b>{k}</b>", normal), Paragraph(str(v), normal)] for k, v in rows],
                  colWidths=[60 * mm, 105 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FBF6EE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    elements = [
        Paragraph("FICHE PRODUIT", title),
        Paragraph("KDMARCHÉ × O'SCOP — Communityplace B2B ESS", sub),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>{product.get('name', 'Produit')}</b>", ParagraphStyle("n", parent=styles["Heading2"], textColor=DARK)),
        Paragraph(product.get("description", ""), normal),
        Spacer(1, 5 * mm),
        table,
    ]
    doc.build(elements)
    return buf.getvalue()
