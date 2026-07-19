"""Convention tripartite V1.5 — génération PDF dynamique (pages remplies + document original fusionné)."""
import io
import os
from datetime import datetime, timezone

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEMPLATE_PATH = "/app/backend/assets/convention_cadre_v1_5.pdf"

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#b8933e")

_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13.5, textColor=VIOLET_DARK, spaceAfter=4, leading=17)
_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#6b5a7a"), spaceAfter=8)
_H2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, textColor=VIOLET, spaceBefore=10, spaceAfter=4)
_BODY = ParagraphStyle("b", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#2a2233"), leading=13)

OSCOP_BLOCK = [
    ["Dénomination", "SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP)"],
    ["Contact", "contact@objectifscopoutremer.com"],
]
KDM_BLOCK = [
    ["Dénomination", "KDMARCHE — marque KDMARCHE PRO (Communityplace B2B ESS)"],
    ["Contact", "contact@objectifscopoutremer.com"],
]


def _table(rows):
    t = Table(rows, colWidths=[52 * mm, 118 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), VIOLET),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4eefa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _fiche_pages(ob: dict, signature: dict | None) -> bytes:
    """Pages 'Fiche d'identification et de signature' remplies dynamiquement."""
    conv = ob.get("convention") or {}
    ref = f"OSC/KDM/FOUR/CADRE-AGR-RCR-FOGEDOM/{ob['id'][:8].upper()}"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=13 * mm,
                            leftMargin=17 * mm, rightMargin=17 * mm)
    el = [
        Paragraph("CONVENTION-CADRE D'ADHÉSION TRIPARTITE D'AGRÉGATION DE VOLUMES<br/>ET DE RETENUE CONTRIBUTIVE REMBOURSABLE — V1.5", _TITLE),
        Paragraph(f"Référence : {ref} · Fiche d'identification et de signature complétée dynamiquement — "
                  f"générée le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC · "
                  "Le texte intégral de la Convention-cadre (33 pages) est joint ci-après et fait partie intégrante du présent exemplaire.", _SUB),
        Paragraph("1. O'SCOP", _H2), _table(OSCOP_BLOCK),
        Paragraph("2. KDMARCHE", _H2), _table(KDM_BLOCK),
        Paragraph("3. LE FOURNISSEUR", _H2),
        _table([
            ["Dénomination", ob.get("company") or ""],
            ["Forme sociale", conv.get("forme_sociale") or "À préciser"],
            ["Capital social", f"{conv.get('capital') or 'À compléter'} €"],
            ["SIRET / SIREN", f"{ob.get('siret') or ''} / {(ob.get('siret') or '')[:9]}"],
            ["RCS", f"RCS {conv.get('rcs_ville') or 'À compléter'}"],
            ["Siège social", conv.get("adresse") or "À compléter"],
            ["Représentant", f"{conv.get('rep_prenom') or ''} {conv.get('rep_nom') or ''} — {conv.get('rep_qualite') or ''}".strip(" —")],
            ["Email de notification", ob.get("email") or ""],
            ["Téléphone", ob.get("phone") or ""],
            ["Territoire(s)", ", ".join(conv.get("territoires") or []) or "À compléter"],
            ["Formule d'adhésion", ob.get("plan_name") or ob.get("plan_slug") or ""],
        ]),
        Paragraph("Champs réservés à O'SCOP", _H2),
        Paragraph("Plafond-cible RCR, référence du règlement FOGEDOM-RCR, composition du Comité FOGEDOM-RCR, PFH / support RCR "
                  "et annexes techniques (2 à 7) : à compléter par O'SCOP conformément à l'Article 2 avant toute Attestation nominative.", _BODY),
        Paragraph("Signature électronique", _H2),
    ]
    if signature:
        el.append(_table([
            ["Fait à", conv.get("lieu_signature") or "À compléter"],
            ["Le", signature.get("signed_at_display") or ""],
            ["Pour LE FOURNISSEUR — Nom", signature.get("nom") or ""],
            ["Qualité", signature.get("qualite") or ""],
            ["Mention", "« Lu et approuvé » — acceptée électroniquement"],
            ["Code de vérification", signature.get("verification_code") or ""],
            ["Empreinte (IP)", signature.get("ip") or ""],
        ]))
        el.append(Spacer(1, 6))
        el.append(Paragraph(
            "Signature électronique réalisée conformément à l'Article 29 de la Convention-cadre (articles 1366 et 1367 du Code civil). "
            "Ce document et son code de vérification font preuve entre les parties. Un exemplaire est archivé dans la GED de la coopérative.", _SUB))
    else:
        el.append(Paragraph("Document non signé — aperçu avant signature électronique.", _BODY))
    doc.build(el)
    return buf.getvalue()


def build_convention_pdf(ob: dict, signature: dict | None = None) -> bytes:
    """Fiche remplie + texte intégral original fusionnés."""
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(_fiche_pages(ob, signature))).pages:
        writer.add_page(page)
    if os.path.exists(TEMPLATE_PATH):
        for page in PdfReader(TEMPLATE_PATH).pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
