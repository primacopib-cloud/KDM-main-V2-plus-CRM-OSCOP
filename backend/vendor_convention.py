"""Convention tripartite V1.5 — génération PDF dynamique multilingue (fiche remplie + document original fusionné)."""
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
TEMPLATE_V2_PATH = "/app/backend/assets/convention_cadre_v2_0.pdf"
ATTESTATION_V2_PATH = "/app/backend/assets/attestation_nominative_v2_0.pdf"

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#b8933e")

_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13.5, textColor=VIOLET_DARK, spaceAfter=4, leading=17)
_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#6b5a7a"), spaceAfter=8)
_H2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, textColor=VIOLET, spaceBefore=10, spaceAfter=4)
_BODY = ParagraphStyle("b", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#2a2233"), leading=13)

CONV_I18N = {
    "fr": {
        "title": "CONVENTION-CADRE D'ADHÉSION TRIPARTITE D'AGRÉGATION DE VOLUMES<br/>ET DE RETENUE CONTRIBUTIVE REMBOURSABLE — V1.5",
        "title_buyer": "CONVENTION-CADRE D'ADHÉSION TRIPARTITE D'ACHAT DE VOLUMES DE PRODUITS PRÉDÉFINIS<br/>ET DE RATTACHEMENT À LA RCR FOGEDOM-SCIC — V2.0",
        "ref_line": "Référence : {ref} · Fiche d'identification et de signature complétée dynamiquement — générée le {date} UTC · Le texte intégral de la Convention-cadre{attest} est joint ci-après et fait partie intégrante du présent exemplaire.",
        "attest": " et le modèle d'Attestation nominative FOGEDOM-SCIC",
        "supplier": "3. LE FOURNISSEUR", "denomination": "Dénomination", "contact": "Contact",
        "forme": "Forme sociale", "capital": "Capital social", "siret": "SIRET / SIREN", "rcs": "RCS",
        "siege": "Siège social", "rep": "Représentant", "email": "Email de notification",
        "phone": "Téléphone", "territories": "Territoire(s)", "member_quality": "Qualité du membre",
        "plan": "Formule d'adhésion",
        "buyer_val": "Acheteur Pro (achats mutualisés)", "vendor_val": "Vendeur Pro (fournisseur référencé)",
        "tbd": "À compléter", "tbs": "À préciser",
        "oscop_fields": "Champs réservés à O'SCOP",
        "oscop_body": "Plafond-cible RCR, référence du règlement FOGEDOM-RCR, composition du Comité FOGEDOM-RCR, PFH / support RCR et annexes techniques (2 à 7) : à compléter par O'SCOP conformément à l'Article 2 avant toute Attestation nominative.",
        "esign": "Signature électronique",
        "done_at": "Fait à", "on": "Le", "for_supplier": "Pour LE FOURNISSEUR — Nom",
        "quality": "Qualité", "mention": "Mention", "mention_val": "« Lu et approuvé » — acceptée électroniquement",
        "verif": "Code de vérification", "ip": "Empreinte (IP)",
        "legal": "Signature électronique réalisée conformément à l'Article 29 de la Convention-cadre (articles 1366 et 1367 du Code civil). Ce document et son code de vérification font preuve entre les parties. Un exemplaire est archivé dans la GED de la coopérative.",
        "unsigned": "Document non signé — aperçu avant signature électronique.",
    },
    "en": {
        "title": "TRIPARTITE MEMBERSHIP FRAMEWORK AGREEMENT ON VOLUME AGGREGATION<br/>AND REFUNDABLE CONTRIBUTORY RETENTION — V1.5",
        "title_buyer": "TRIPARTITE MEMBERSHIP FRAMEWORK AGREEMENT FOR THE PURCHASE OF PREDEFINED PRODUCT VOLUMES<br/>AND ATTACHMENT TO THE RCR FOGEDOM-SCIC — V2.0",
        "ref_line": "Reference: {ref} · Identification and signature sheet completed dynamically — generated on {date} UTC · The full French text of the Framework Agreement{attest} is attached hereafter and forms an integral part of this copy. In case of discrepancy, the French version prevails.",
        "attest": " and the FOGEDOM-SCIC nominative Certificate template",
        "supplier": "3. THE SUPPLIER", "denomination": "Company name", "contact": "Contact",
        "forme": "Legal form", "capital": "Share capital", "siret": "SIRET / SIREN", "rcs": "Trade register (RCS)",
        "siege": "Registered office", "rep": "Representative", "email": "Notification email",
        "phone": "Phone", "territories": "Territory(ies)", "member_quality": "Member capacity",
        "plan": "Membership plan",
        "buyer_val": "Pro Buyer (pooled purchasing)", "vendor_val": "Pro Seller (listed supplier)",
        "tbd": "To be completed", "tbs": "To be specified",
        "oscop_fields": "Fields reserved for O'SCOP",
        "oscop_body": "RCR target ceiling, FOGEDOM-RCR regulation reference, FOGEDOM-RCR Committee composition, PFH / RCR support and technical annexes (2 to 7): to be completed by O'SCOP in accordance with Article 2 before any nominative Certificate.",
        "esign": "Electronic signature",
        "done_at": "Done at", "on": "On", "for_supplier": "For THE SUPPLIER — Name",
        "quality": "Title", "mention": "Statement", "mention_val": "\"Read and approved\" — accepted electronically",
        "verif": "Verification code", "ip": "Fingerprint (IP)",
        "legal": "Electronic signature made in accordance with Article 29 of the Framework Agreement (articles 1366 and 1367 of the French Civil Code). This document and its verification code constitute proof between the parties. A copy is archived in the cooperative's document management system.",
        "unsigned": "Unsigned document — preview before electronic signature.",
    },
    "es": {
        "title": "CONVENIO-MARCO DE ADHESIÓN TRIPARTITO DE AGREGACIÓN DE VOLÚMENES<br/>Y DE RETENCIÓN CONTRIBUTIVA REEMBOLSABLE — V1.5",
        "title_buyer": "CONVENIO-MARCO DE ADHESIÓN TRIPARTITO DE COMPRA DE VOLÚMENES DE PRODUCTOS PREDEFINIDOS<br/>Y DE VINCULACIÓN A LA RCR FOGEDOM-SCIC — V2.0",
        "ref_line": "Referencia: {ref} · Ficha de identificación y firma completada dinámicamente — generada el {date} UTC · El texto íntegro en francés del Convenio-marco{attest} se adjunta a continuación y forma parte integrante del presente ejemplar. En caso de discrepancia, prevalece la versión francesa.",
        "attest": " y el modelo de Certificado nominativo FOGEDOM-SCIC",
        "supplier": "3. EL PROVEEDOR", "denomination": "Denominación", "contact": "Contacto",
        "forme": "Forma jurídica", "capital": "Capital social", "siret": "SIRET / SIREN", "rcs": "Registro mercantil (RCS)",
        "siege": "Sede social", "rep": "Representante", "email": "Email de notificación",
        "phone": "Teléfono", "territories": "Territorio(s)", "member_quality": "Calidad del miembro",
        "plan": "Fórmula de adhesión",
        "buyer_val": "Comprador Pro (compras mutualizadas)", "vendor_val": "Vendedor Pro (proveedor referenciado)",
        "tbd": "Por completar", "tbs": "Por precisar",
        "oscop_fields": "Campos reservados a O'SCOP",
        "oscop_body": "Techo objetivo RCR, referencia del reglamento FOGEDOM-RCR, composición del Comité FOGEDOM-RCR, PFH / soporte RCR y anexos técnicos (2 a 7): a completar por O'SCOP conforme al Artículo 2 antes de cualquier Certificado nominativo.",
        "esign": "Firma electrónica",
        "done_at": "Hecho en", "on": "El", "for_supplier": "Por EL PROVEEDOR — Nombre",
        "quality": "Cargo", "mention": "Mención", "mention_val": "«Leído y aprobado» — aceptada electrónicamente",
        "verif": "Código de verificación", "ip": "Huella (IP)",
        "legal": "Firma electrónica realizada conforme al Artículo 29 del Convenio-marco (artículos 1366 y 1367 del Código Civil francés). Este documento y su código de verificación constituyen prueba entre las partes. Un ejemplar queda archivado en la GED de la cooperativa.",
        "unsigned": "Documento no firmado — vista previa antes de la firma electrónica.",
    },
}


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
    """Pages 'Fiche d'identification et de signature' remplies dynamiquement (FR/EN/ES selon ob['locale'])."""
    tr = CONV_I18N.get(ob.get("locale") or "fr", CONV_I18N["fr"])
    conv = ob.get("convention") or {}
    is_buyer = _is_buyer_template(ob)
    ref_prefix = "OSC/KDM/ACH" if is_buyer else "OSC/KDM/FOUR"
    ref = f"{ref_prefix}/CADRE-AGR-RCR-FOGEDOM/{ob['id'][:8].upper()}"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=13 * mm,
                            leftMargin=17 * mm, rightMargin=17 * mm)
    el = [
        Paragraph(tr["title_buyer"] if is_buyer else tr["title"], _TITLE),
        Paragraph(tr["ref_line"].format(ref=ref, date=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
                                        attest=tr["attest"] if is_buyer else ""), _SUB),
        Paragraph("1. O'SCOP", _H2),
        _table([
            [tr["denomination"], "SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP)"],
            [tr["contact"], "contact@objectifscopoutremer.com"],
        ]),
        Paragraph("2. KDMARCHE", _H2),
        _table([
            [tr["denomination"], "KDMARCHE — marque KDMARCHE PRO (Communityplace B2B ESS)"],
            [tr["contact"], "contact@objectifscopoutremer.com"],
        ]),
        Paragraph(tr["supplier"], _H2),
        _table([
            [tr["denomination"], ob.get("company") or ""],
            [tr["forme"], conv.get("forme_sociale") or tr["tbs"]],
            [tr["capital"], f"{conv.get('capital') or tr['tbd']} €"],
            [tr["siret"], f"{ob.get('siret') or ''} / {(ob.get('siret') or '')[:9]}"],
            [tr["rcs"], f"RCS {conv.get('rcs_ville') or tr['tbd']}"],
            [tr["siege"], conv.get("adresse") or tr["tbd"]],
            [tr["rep"], f"{conv.get('rep_prenom') or ''} {conv.get('rep_nom') or ''} — {conv.get('rep_qualite') or ''}".strip(" —")],
            [tr["email"], ob.get("email") or ""],
            [tr["phone"], ob.get("phone") or ""],
            [tr["territories"], ", ".join(conv.get("territoires") or []) or tr["tbd"]],
            [tr["member_quality"], tr["buyer_val"] if ob.get("member_type") == "buyer" else tr["vendor_val"]],
            [tr["plan"], ob.get("plan_name") or ob.get("plan_slug") or ""],
        ]),
        Paragraph(tr["oscop_fields"], _H2),
        Paragraph(tr["oscop_body"], _BODY),
        Paragraph(tr["esign"], _H2),
    ]
    if signature:
        el.append(_table([
            [tr["done_at"], conv.get("lieu_signature") or tr["tbd"]],
            [tr["on"], signature.get("signed_at_display") or ""],
            [tr["for_supplier"], signature.get("nom") or ""],
            [tr["quality"], signature.get("qualite") or ""],
            [tr["mention"], tr["mention_val"]],
            [tr["verif"], signature.get("verification_code") or ""],
            [tr["ip"], signature.get("ip") or ""],
        ]))
        el.append(Spacer(1, 6))
        el.append(Paragraph(tr["legal"], _SUB))
    else:
        el.append(Paragraph(tr["unsigned"], _BODY))
    doc.build(el)
    return buf.getvalue()


def _is_buyer_template(ob: dict) -> bool:
    if ob.get("convention_template"):
        return ob["convention_template"] == "v2_0_buyer"
    return ob.get("member_type") == "buyer"


def build_convention_pdf(ob: dict, signature: dict | None = None) -> bytes:
    """Fiche remplie + texte intégral du contrat adapté au profil (V1.5 vendeur / V2.0 acheteur + attestation)."""
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(_fiche_pages(ob, signature))).pages:
        writer.add_page(page)
    if _is_buyer_template(ob):
        templates = [TEMPLATE_V2_PATH, ATTESTATION_V2_PATH]
    else:
        templates = [TEMPLATE_PATH]
    for path in templates:
        if os.path.exists(path):
            for page in PdfReader(path).pages:
                writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
