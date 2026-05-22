from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime


def generate_offer_pdf() -> BytesIO:
    """Generate the commercial offer PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#D9B35A'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=15,
        spaceBefore=20
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#57D19A'),
        spaceAfter=10,
        spaceBefore=15
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#444444'),
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    quote_style = ParagraphStyle(
        'Quote',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15,
        spaceBefore=15,
        leftIndent=20,
        rightIndent=20,
        borderPadding=10,
        backColor=colors.HexColor('#F5F5F5'),
        alignment=TA_CENTER,
        leading=16
    )
    
    # Content
    story = []
    
    # Header
    story.append(Paragraph("OFFRE COMMERCIALE OFFICIELLE", title_style))
    story.append(Paragraph("Centrale d'achats B2B ESS", subtitle_style))
    story.append(Paragraph("Partenariat KDMARCHE – O'SCOP", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Date
    story.append(Paragraph(f"Document généré le {datetime.now().strftime('%d/%m/%Y')}", body_style))
    story.append(Spacer(1, 20))
    
    # Section 1: Logique du partenariat
    story.append(Paragraph("1. LOGIQUE DU PARTENARIAT", section_style))
    story.append(Paragraph(
        "Le partenariat repose sur une séparation stricte et assumée des fonctions :",
        body_style
    ))
    
    partner_data = [
        ['Acteur', 'Rôle'],
        ['KDMARCHE', 'Opérateur commercial et logistique B2B'],
        ["O'SCOP", "Centrale coopérative d'ingénierie ESS, accès et mutualisation"]
    ]
    
    partner_table = Table(partner_data, colWidths=[4*cm, 12*cm])
    partner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D9B35A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(partner_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(
        "<b>→ Un seul vend les produits (KDMARCHE)</b><br/>"
        "<b>→ L'autre ne vend rien (O'SCOP)</b><br/><br/>"
        "Ce cloisonnement est volontaire, contractuel et opposable.",
        body_style
    ))
    
    # Section 2: Rôle de KDMARCHE
    story.append(Paragraph("2. RÔLE DE KDMARCHE (B2B OPÉRATIONNEL)", section_style))
    story.append(Paragraph("KDMARCHE agit en tant que :", body_style))
    
    kdmarche_roles = [
        "• Opérateur de vente B2B",
        "• Gestionnaire des catalogues produits",
        "• Gestionnaire des stocks par zones",
        "• Émetteur des factures marchandises",
        "• Opérateur logistique (EXW, zones pays)",
        "• Responsable de la conformité produit (TVA, douanes, DLC, traçabilité)"
    ]
    
    for role in kdmarche_roles:
        story.append(Paragraph(role, body_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>KDMARCHE assume seul :</b> le prix produit, la relation fournisseur, "
        "la facturation, la TVA, la livraison EXW.",
        body_style
    ))
    
    # Section 3: Rôle d'O'SCOP
    story.append(Paragraph("3. RÔLE D'O'SCOP (INGÉNIERIE & ACCÈS ESS)", section_style))
    story.append(Paragraph("O'SCOP agit exclusivement comme :", body_style))
    
    oscop_roles = [
        "• Centrale d'ingénierie d'achats ESS",
        "• Organisateur de la mutualisation",
        "• Opérateur de l'accès à la plateforme",
        "• Gestionnaire des abonnements",
        "• Gestionnaire du wallet crédits",
        "• Garant du cadre ESS et coopératif"
    ]
    
    for role in oscop_roles:
        story.append(Paragraph(role, body_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>O'SCOP ne vend pas, ne facture pas les produits, ne perçoit aucun paiement "
        "fournisseur, ne prend aucune commission sur les ventes.</b>",
        body_style
    ))
    
    # Section 4: Pourquoi les prix à -50%
    story.append(Paragraph("4. POURQUOI LES PRIX PEUVENT ÊTRE À –50%", section_style))
    story.append(Paragraph(
        "Les prix pratiqués par KDMARCHE dans le cadre du partenariat résultent de :",
        body_style
    ))
    
    price_reasons = [
        "• La mutualisation organisée par O'SCOP",
        "• Les volumes consolidés",
        "• La suppression d'intermédiaires",
        "• Une vente exclusivement B2B",
        "• Un modèle EXW sans coûts retail"
    ]
    
    for reason in price_reasons:
        story.append(Paragraph(reason, body_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>Il ne s'agit ni de remises, ni de promotions, mais de prix structurels B2B.</b>",
        body_style
    ))
    
    # Section 5: Offres d'abonnement
    story.append(Paragraph("5. OFFRES D'ABONNEMENT O'SCOP", section_style))
    
    pricing_data = [
        ['Formule', 'Prix', 'Caractéristiques'],
        ['ESS ACCÈS PRO', '149€ HT/mois', 
         '1 zone incluse, prix mutualisés, wallet de base'],
        ['ESS VOLUME PRO', '349€ HT/mois', 
         'Accès prioritaire, multi-catégories, reporting'],
        ['ESS IMPACT PRO', '749€ HT/mois', 
         'Multi-zones, projets collectifs, fournisseurs stratégiques']
    ]
    
    pricing_table = Table(pricing_data, colWidths=[4*cm, 3.5*cm, 8.5*cm])
    pricing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#57D19A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(pricing_table)
    
    # Section 6: Phrase officielle
    story.append(Paragraph("6. PHRASE OFFICIELLE DU PARTENARIAT", section_style))
    story.append(Paragraph(
        "« Dans le cadre du partenariat KDMARCHE – O'SCOP, KDMARCHE commercialise "
        "les produits, O'SCOP organise l'accès coopératif aux conditions économiques. "
        "Les prix résultent d'une mutualisation ESS, non de remises commerciales. »",
        quote_style
    ))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "<b>Contact :</b> contact@centrale-ess.fr | www.centrale-ess.fr",
        body_style
    ))
    story.append(Paragraph(
        f"© 2025 Centrale d'Achats B2B ESS - KDMARCHE & O'SCOP",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
