"""Reçu PDF + email pour l'achat d'une zone additionnelle (crédits ou carte)."""
import base64
import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)
GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")


def build_zone_receipt_pdf(user: dict, zone_name: str, method: str,
                           credits_spent: int, amount_eur: float, ref: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=DARK, fontSize=18)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GOLD, fontSize=10)
    normal = styles["Normal"]

    now = datetime.now()
    invoice_num = f"ZN-{now.strftime('%Y%m%d')}-{ref[-8:].upper()}"
    if method == "credits":
        amount_label = f"{credits_spent} crédits CREDI'SCOP"
        pay_line = "Paiement effectué par débit de votre solde CREDI'SCOP."
    else:
        amount_label = f"{amount_eur:.2f} € HT"
        pay_line = "Paiement reçu par carte bancaire via Stripe."

    lines = [
        ["Désignation", "Montant"],
        [f"Zone additionnelle — {zone_name} (accès tarifs & commandes)", amount_label],
        ["TOTAL", amount_label],
    ]
    table = Table(lines, colWidths=[115 * mm, 50 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FBF6EE")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FBF6EE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    doc.build([
        Paragraph("REÇU", title),
        Paragraph("KDMARCHÉ × O'SCOP — Communityplace B2B ESS", sub),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>Reçu n° :</b> {invoice_num}", normal),
        Paragraph(f"<b>Date :</b> {now.strftime('%d/%m/%Y %H:%M')}", normal),
        Paragraph(f"<b>Référence :</b> {ref}", normal),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>Client :</b> {user.get('company_name', '—')}", normal),
        Paragraph(f"{user.get('contact_name', '')} — {user.get('email', '')}", normal),
        Spacer(1, 6 * mm),
        table,
        Spacer(1, 6 * mm),
        Paragraph(pay_line, normal),
        Paragraph("L'accès à la zone est actif immédiatement et de façon permanente.", normal),
    ])
    return buf.getvalue()


async def send_zone_receipt_email(user: dict, zone_name: str, method: str,
                                  credits_spent: int, amount_eur: float, ref: str) -> None:
    """Reçu PDF envoyé par email après l'achat d'une zone additionnelle (best effort)."""
    try:
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        if not is_brevo_configured() or not user.get("email"):
            return
        pdf = build_zone_receipt_pdf(user, zone_name, method, credits_spent, amount_eur, ref)
        paid = (f"{credits_spent} crédits CREDI&rsquo;SCOP" if method == "credits"
                else f"{amount_eur:.2f} € HT par carte bancaire")
        body = (
            f"<p>Bonjour {user.get('contact_name') or ''},</p>"
            f"<p>Votre zone additionnelle <strong>{zone_name}</strong> est activée ! "
            f"Règlement : <strong>{paid}</strong>.</p>"
            "<p>Vous accédez dès maintenant aux tarifs mutualisés de cette zone et pouvez y passer commande. "
            "Votre reçu est en pièce jointe.</p>"
        )
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject=f"✓ Zone {zone_name} activée — votre reçu KDMARCHÉ",
            html_content=_wrap_html(f"Zone additionnelle — {zone_name}", body),
            tags=["zone-addon-receipt"],
            attachments=[{
                "content": base64.b64encode(pdf).decode(),
                "name": f"recu-zone-{ref[-8:]}.pdf",
            }],
        )
        logger.info("Zone receipt email sent to %s (%s, %s)", user["email"], zone_name, ref)
    except Exception as exc:
        logger.error("Zone receipt email failed: %s", exc)
