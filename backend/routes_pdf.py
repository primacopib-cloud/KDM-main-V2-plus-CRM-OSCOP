"""
KDMARCHE × O'SCOP - PDF Generation API
Generate signed purchase orders and invoices as PDF
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import logging
import io
import os

logger = logging.getLogger(__name__)

# Router
pdf_router = APIRouter(prefix="/api/v2/pdf")

# Database reference
db = None

def set_pdf_database(database):
    global db
    db = database


# ============== PDF GENERATION USING REPORTLAB ==============

def generate_order_pdf(order: dict, org: dict = None, signature_data: dict = None) -> bytes:
    """Generate a professional PDF for a purchase order"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#D9B35A'),
        spaceBefore=15,
        spaceAfter=8,
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
    )
    
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
    )
    
    elements = []
    
    # ===== HEADER =====
    elements.append(Paragraph("KDMARCHE × O'SCOP", title_style))
    elements.append(Paragraph("Centrale d'Achats B2B - Économie Sociale et Solidaire", subtitle_style))
    
    # ===== ORDER INFO =====
    elements.append(Paragraph("BON DE COMMANDE", ParagraphStyle(
        'OrderTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=5,
    )))
    
    order_number = order.get('order_number', 'N/A')
    order_date = order.get('created_at', datetime.utcnow())
    if isinstance(order_date, str):
        try:
            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
        except:
            order_date = datetime.utcnow()
    
    elements.append(Paragraph(f"N° {order_number}", ParagraphStyle(
        'OrderNumber',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#D9B35A'),
        alignment=TA_CENTER,
        spaceAfter=5,
    )))
    elements.append(Paragraph(f"Date : {order_date.strftime('%d/%m/%Y %H:%M')}", ParagraphStyle(
        'OrderDate',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )))
    
    # ===== CLIENT INFO =====
    org_name = org.get('legal_name', 'Client') if org else 'Client'
    org_territory = org.get('territory', order.get('zone_code', 'N/A'))
    
    elements.append(Paragraph("INFORMATIONS CLIENT", section_style))
    client_data = [
        ['Raison sociale :', org_name],
        ['Territoire :', org_territory],
        ['Zone de livraison :', order.get('zone_code', 'N/A')],
        ['Incoterm :', order.get('incoterm', 'EXW')],
    ]
    
    client_table = Table(client_data, colWidths=[4*cm, 12*cm])
    client_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(client_table)
    
    # ===== PICKUP LOCATION =====
    pickup = order.get('pickup_location', {})
    if pickup:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("POINT D'ENLÈVEMENT EXW", section_style))
        pickup_info = f"{pickup.get('name', 'N/A')}<br/>{pickup.get('address', '')}, {pickup.get('city', '')}"
        elements.append(Paragraph(pickup_info, normal_style))
    
    # ===== PRODUCTS TABLE =====
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("DÉTAIL DE LA COMMANDE", section_style))
    
    # Table header
    table_data = [['Réf.', 'Désignation', 'Qté', 'Unité', 'P.U. HT', 'Total HT']]
    
    # Add items
    for item in order.get('items', []):
        table_data.append([
            item.get('product_sku', 'N/A'),
            item.get('product_name', 'N/A')[:40],
            str(item.get('quantity', 0)),
            item.get('unit', 'unité'),
            f"{item.get('price_ht_cents', 0) / 100:.2f} €",
            f"{item.get('line_total_ht_cents', 0) / 100:.2f} €",
        ])
    
    # Create table
    col_widths = [2.5*cm, 7*cm, 1.5*cm, 1.5*cm, 2*cm, 2.5*cm]
    products_table = Table(table_data, colWidths=col_widths)
    products_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Qty
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Unit
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Prices
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
        # Padding
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(products_table)
    
    # ===== TOTALS =====
    elements.append(Spacer(1, 15))
    
    subtotal = order.get('subtotal_ht_cents', 0)
    tax = order.get('tax_cents', 0)
    total = order.get('total_ttc_cents', 0)
    
    # Check for installment fees
    fees = 0
    if order.get('is_installment') and order.get('installment_plan'):
        fees = order['installment_plan'].get('total_fees_cents', 0)
        total += fees
    
    totals_data = [
        ['', '', 'Sous-total HT :', f"{subtotal / 100:.2f} €"],
        ['', '', 'TVA (8,5%) :', f"{tax / 100:.2f} €"],
    ]
    
    if fees > 0:
        totals_data.append(['', '', 'Frais paiement 4× :', f"{fees / 100:.2f} €"])
    
    totals_data.append(['', '', 'TOTAL TTC :', f"{total / 100:.2f} €"])
    
    totals_table = Table(totals_data, colWidths=[7*cm, 3*cm, 4*cm, 3*cm])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (2, 0), (2, -2), 'Helvetica'),
        ('FONTNAME', (2, -1), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, -1), (3, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('TEXTCOLOR', (2, -1), (2, -1), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (3, -1), (3, -1), colors.HexColor('#D9B35A')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (2, -1), (-1, -1), 1, colors.HexColor('#1a1a2e')),
    ]))
    elements.append(totals_table)
    
    # ===== SIGNATURE =====
    if signature_data:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("SIGNATURE ÉLECTRONIQUE", section_style))
        
        sig_info = [
            f"Signataire : {signature_data.get('signer_name', 'N/A')}",
            f"Email : {signature_data.get('signer_email', 'N/A')}",
            f"Date de signature : {signature_data.get('signed_at', 'N/A')}",
            f"ID de signature : {signature_data.get('signature_id', 'N/A')}",
        ]
        
        for info in sig_info:
            elements.append(Paragraph(info, small_style))
        
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            "✓ Ce document a été signé électroniquement conformément au règlement eIDAS.",
            ParagraphStyle('SignatureValid', parent=small_style, textColor=colors.HexColor('#22c55e'))
        ))
    
    # ===== FOOTER =====
    elements.append(Spacer(1, 30))
    footer_text = """
    KDMARCHE × O'SCOP - Centrale d'Achats B2B ESS<br/>
    Conditions générales de vente disponibles sur kdmarche-oscop.fr<br/>
    Document généré automatiquement - Ne pas renvoyer
    """
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=small_style,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#999999'),
    )))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_invoice_pdf(invoice: dict, order: dict = None) -> bytes:
    """Generate a professional PDF for an invoice"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("KDMARCHE × O'SCOP", title_style))
    elements.append(Paragraph("FACTURE", ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#D9B35A'),
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=10,
    )))
    
    # Invoice number
    elements.append(Paragraph(f"N° {invoice.get('invoice_number', 'N/A')}", ParagraphStyle(
        'InvoiceNumber',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=20,
    )))
    
    # Invoice details
    issue_date = invoice.get('issue_date', datetime.utcnow())
    if isinstance(issue_date, str):
        try:
            issue_date = datetime.fromisoformat(issue_date.replace('Z', '+00:00'))
        except:
            issue_date = datetime.utcnow()
    
    info_data = [
        ['Date d\'émission :', issue_date.strftime('%d/%m/%Y')],
        ['Commande :', invoice.get('order_number', 'N/A')],
        ['Client :', invoice.get('org_name', 'N/A')],
        ['Statut :', 'Payée' if invoice.get('payment_status') == 'PAID' else 'En attente'],
    ]
    
    info_table = Table(info_data, colWidths=[4*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Items table
    table_data = [['Désignation', 'Qté', 'P.U. HT', 'Total HT']]
    
    for item in invoice.get('items', []):
        table_data.append([
            item.get('product_name', 'N/A')[:50],
            str(item.get('quantity', 0)),
            f"{item.get('unit_price_ht_cents', 0) / 100:.2f} €",
            f"{item.get('line_total_ht_cents', 0) / 100:.2f} €",
        ])
    
    items_table = Table(table_data, colWidths=[9*cm, 2*cm, 3*cm, 3*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))
    
    # Totals
    subtotal = invoice.get('subtotal_ht_cents', 0)
    tax = invoice.get('tax_cents', 0)
    fees = invoice.get('total_fees_cents', 0)
    total = invoice.get('total_ttc_cents', 0)
    
    totals_data = [
        ['Sous-total HT :', f"{subtotal / 100:.2f} €"],
        [f"TVA ({invoice.get('tax_rate', 0.085) * 100:.1f}%) :", f"{tax / 100:.2f} €"],
    ]
    
    if fees > 0:
        totals_data.append(['Frais :', f"{fees / 100:.2f} €"])
    
    totals_data.append(['TOTAL TTC :', f"{total / 100:.2f} €"])
    
    totals_table = Table(totals_data, colWidths=[13*cm, 4*cm])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#D9B35A')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1a1a2e')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    
    # Payment status
    if invoice.get('payment_status') == 'PAID':
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("✓ FACTURE ACQUITTÉE", ParagraphStyle(
            'Paid',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#22c55e'),
            alignment=TA_CENTER,
        )))
        if invoice.get('paid_at'):
            paid_date = invoice['paid_at']
            if isinstance(paid_date, str):
                try:
                    paid_date = datetime.fromisoformat(paid_date.replace('Z', '+00:00'))
                except:
                    paid_date = None
            if paid_date:
                elements.append(Paragraph(f"Payée le {paid_date.strftime('%d/%m/%Y')}", ParagraphStyle(
                    'PaidDate',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#666666'),
                    alignment=TA_CENTER,
                )))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ============== DEPENDENCIES ==============

async def get_current_user_pdf(request: Request):
    """Get current user from token"""
    from auth import decode_token
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = auth_header.split(" ")[1]
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


# ============== ROUTES ==============

@pdf_router.get("/order/{order_id}")
async def download_order_pdf(
    order_id: str,
    current_user: dict = Depends(get_current_user_pdf),
):
    """Generate and download PDF for a purchase order"""
    # Get user's org
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    
    # Get order
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Check access
    if not current_user.get("is_admin"):
        if not membership or order["org_id"] != membership["org_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Get org info
    org = await db.orgs.find_one({"id": order["org_id"]})
    
    # Get signature data if available
    signature_data = None
    if order.get("signature_id"):
        signature = await db.signatures.find_one({"id": order["signature_id"]})
        if signature:
            signature_data = {
                "signature_id": signature["id"],
                "signer_name": signature.get("signer_name", current_user.get("contact_name", "N/A")),
                "signer_email": signature.get("signer_email", current_user.get("email", "N/A")),
                "signed_at": signature.get("signed_at", order.get("created_at")),
            }
    
    try:
        pdf_bytes = generate_order_pdf(order, org, signature_data)
        
        filename = f"bon_commande_{order['order_number']}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        logger.error(f"Error generating order PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de génération PDF: {str(e)}")


@pdf_router.get("/invoice/{invoice_id}")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: dict = Depends(get_current_user_pdf),
):
    """Generate and download PDF for an invoice"""
    # Get user's org
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    
    # Get invoice
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    # Check access
    if not current_user.get("is_admin"):
        if not membership or invoice["org_id"] != membership["org_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Get related order
    order = await db.orders.find_one({"id": invoice["order_id"]}) if invoice.get("order_id") else None
    
    try:
        pdf_bytes = generate_invoice_pdf(invoice, order)
        
        filename = f"facture_{invoice['invoice_number']}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        logger.error(f"Error generating invoice PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de génération PDF: {str(e)}")
