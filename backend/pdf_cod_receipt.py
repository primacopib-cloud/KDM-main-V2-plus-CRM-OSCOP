"""Reçu d'encaissement PDF (paiement à la livraison)."""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")


def generate_cod_receipt_pdf(order: dict, org_name: str, invoice_number: str = None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=DARK, fontSize=18)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GOLD, fontSize=10)
    normal = styles["Normal"]

    now = datetime.now()
    amount = (order.get("amount_paid_cents") or order.get("cod_amount_due_cents") or order.get("total_ttc_cents") or 0) / 100
    receipt_num = f"RE-{now.strftime('%Y%m%d')}-{(order.get('id') or '')[-8:].upper()}"

    rows = [
        ["Désignation", "Montant"],
        [f"Commande {order.get('order_number')} — règlement à la livraison", f"{amount:.2f} € TTC"],
        ["Total encaissé", f"{amount:.2f} € TTC"],
    ]
    table = Table(rows, colWidths=[120 * mm, 50 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FDF6E3")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story = [
        Paragraph("REÇU D'ENCAISSEMENT", title),
        Paragraph("KDMARCHÉ × O'SCOP — Communityplace B2B ESS des Outre-mer", sub),
        Spacer(1, 8 * mm),
        Paragraph(f"Reçu n° : <b>{receipt_num}</b>", normal),
        Paragraph(f"Date d'encaissement : {now.strftime('%d/%m/%Y à %H:%M')}", normal),
        Paragraph(f"Client : <b>{org_name or 'N/A'}</b>", normal),
        Paragraph(f"Mode de règlement : Paiement à la livraison (espèces / à réception)", normal),
    ]
    if invoice_number:
        story.append(Paragraph(f"Facture associée : {invoice_number}", normal))
    story += [
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 10 * mm),
        Paragraph("Nous vous remercions pour votre confiance. Ce reçu atteste du règlement intégral de la commande ci-dessus.", normal),
    ]
    doc.build(story)
    return buf.getvalue()
