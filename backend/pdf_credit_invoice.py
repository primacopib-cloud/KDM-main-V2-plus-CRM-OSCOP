"""Facture PDF pour l'achat d'un pack de crédits vendeur."""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")


def generate_credit_invoice_pdf(vendor: dict, pack: dict, credited: int, bonus: int,
                                amount_eur: float, session_id: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=DARK, fontSize=18)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GOLD, fontSize=10)
    normal = styles["Normal"]

    now = datetime.now()
    invoice_num = f"CR-{now.strftime('%Y%m%d')}-{session_id[-8:].upper()}"

    lines = [
        ["Désignation", "Quantité", "Montant"],
        [f"{pack['name']} — crédits plateforme KDMARCHÉ", f"{pack['credits']} crédits", f"{amount_eur:.2f} €"],
    ]
    if bonus > 0:
        lines.append([f"Bonus promotionnel offert", f"+{bonus} crédits", "0,00 €"])
    lines.append(["TOTAL TTC", f"{credited} crédits", f"{amount_eur:.2f} €"])

    table = Table(lines, colWidths=[90 * mm, 40 * mm, 35 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FBF6EE")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FBF6EE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements = [
        Paragraph("FACTURE", title),
        Paragraph("KDMARCHÉ × O'SCOP — Communityplace B2B ESS", sub),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>Facture n° :</b> {invoice_num}", normal),
        Paragraph(f"<b>Date :</b> {now.strftime('%d/%m/%Y %H:%M')}", normal),
        Paragraph(f"<b>Référence paiement Stripe :</b> {session_id}", normal),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>Client :</b> {vendor.get('company_name', '—')}", normal),
        Paragraph(f"{vendor.get('contact_name', '')} — {vendor.get('email', '')}", normal),
        Spacer(1, 6 * mm),
        table,
        Spacer(1, 6 * mm),
        Paragraph("Paiement reçu via Stripe. Les crédits ont été ajoutés immédiatement à votre solde.", normal),
    ]
    doc.build(elements)
    return buf.getvalue()
