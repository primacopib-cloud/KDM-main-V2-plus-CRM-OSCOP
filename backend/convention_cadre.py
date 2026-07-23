"""Convention cadre tripartite O'SCOP × KDMARCHÉ × Fournisseur — génération IA + PDF."""
import logging
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core_deps import get_current_user
from convention_settings import get_convention_settings
from db import get_database

logger = logging.getLogger(__name__)
convention_router = APIRouter(prefix="/api/convention", tags=["convention"])

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")

ARTICLES = [
    ("Article 1 — Définitions", "Les termes « Attestation Nominative », « Volume Agrégé », « Montant Agrégé HT », « Retenue Contributive Remboursable (RCR) », « FOGEDOM-SCIC », « Dashboard » et « Bon de Commande » ont le sens qui leur est donné dans la présente Convention."),
    ("Article 2 — Objet, adhésion et architecture", "La Convention organise l'adhésion du Fournisseur au dispositif coopératif d'agrégation de volumes par catégorie de produits, opéré par O'SCOP et commercialisé par KDMARCHÉ PRO."),
    ("Article 3 — Rôle d'O'SCOP et qualité coopérative du FOGEDOM-SCIC", "O'SCOP agit en qualité d'opérateur coopératif : organisation de l'adhésion, émission des Attestations Nominatives, tenue du Dashboard et contrôle coopératif des contributions via le FOGEDOM-SCIC. O'SCOP n'achète, ne vend, ni ne facture les produits pour son propre compte."),
    ("Article 4 — Rôle de KDMARCHÉ PRO", "KDMARCHÉ PRO référence, achète, commercialise et/ou revend les produits auprès de sa clientèle B2B, émet les Bons de Commande et détermine librement ses prix de revente."),
    ("Article 5 — Adhésion et obligations générales du Fournisseur", "Le Fournisseur fournit des informations produits exactes, maintient les volumes agrégés acceptés, confirme ou refuse les Bons de Commande, livre des produits conformes et maintient les assurances requises."),
    ("Article 6 — Agrégation des volumes par catégorie", "Les volumes sont agrégés par catégorie de produits et matérialisés par des Attestations Nominatives émises via le Dashboard."),
    ("Article 7 — Attestations nominatives, validité, commandes et absence de take-or-pay", "Chaque Attestation matérialise une capacité de disponibilité acceptée par le Fournisseur ; elle ne constitue pas un engagement ferme d'achat (absence de take-or-pay)."),
    ("Article 8 — Prix plafond et formule de prix", "Le prix plafond HT et, le cas échéant, la formule d'indexation applicable figurent dans l'Attestation et l'Annexe 3."),
    ("Article 9 — Logistique, livraison et conformité alimentaire", "Le Fournisseur livre selon les Incoterms et niveaux de service convenus et garantit la conformité réglementaire, sanitaire et alimentaire des produits."),
    ("Article 10 — Dashboard, indicateurs et preuve", "Le Dashboard constitue le registre central des Attestations, volumes, commandes, livraisons, fractions de RCR et statuts ; ses enregistrements font preuve entre les Parties."),
    ("Article 11 — Calcul, affectation et contrôle coopératif de la RCR", "La RCR est calculée par fraction sur chaque facture éligible : Base de Retenue HT × Taux de Retenue Contributive, dans la limite du Plafond-cible de l'Attestation."),
    ("Article 12 — Qualité coopérative du FOGEDOM-SCIC et exécution monétaire", "Le FOGEDOM-SCIC reçoit, conserve et exécute les contributions selon son règlement de gestion, sous double validation du Comité FOGEDOM-RCR."),
    ("Article 13 — Ajustement, expiration des Attestations et clôture", "À l'expiration d'une Attestation, la RCR constituée est ajustée puis restituée selon l'Article 18, et le compte FOGEDOM-RCR correspondant est clôturé."),
    ("Article 14 — Alerte, mise en demeure et plan correctif", "Tout manquement déclenche une alerte Dashboard, puis une mise en demeure et, le cas échéant, un plan correctif contradictoire."),
    ("Article 15 — Cas de mobilisation de la RCR", "La RCR ne peut être mobilisée que pour les préjudices éligibles définis à l'Article 17, après instruction contradictoire."),
    ("Article 16 — Instruction contradictoire et mobilisation par le FOGEDOM-SCIC", "Toute mobilisation est instruite contradictoirement et exécutée par le FOGEDOM-SCIC sous double validation."),
    ("Article 17 — Préjudices éligibles et exclusions", "Sont éligibles les préjudices directs, documentés et imputables au Fournisseur ; sont exclus les préjudices indirects et les cas de force majeure."),
    ("Article 18 — Remboursement de la RCR par Attestation", "La RCR non mobilisée est remboursée au Fournisseur par le FOGEDOM-SCIC dans le délai contractuel après expiration de l'Attestation."),
    ("Article 19 — Équilibre économique, contreparties et proportionnalité", "Le dispositif garantit des contreparties réelles et proportionnées : visibilité commerciale, agrégation, mutualisation logistique et résilience coopérative."),
    ("Article 20 — Facturation et paiements", "Le Fournisseur facture KDMARCHÉ PRO selon le schéma de facturation retenu en Annexe 1 ; le paiement scindé affecte la fraction RCR au FOGEDOM-SCIC sur instruction expresse."),
    ("Article 21 — Responsabilité, assurances et dispositif de résilience coopérative", "Chaque Partie répond de ses manquements dans la limite du plafond contractuel ; le Fournisseur maintient une assurance RC exploitation/professionnelle/produits."),
    ("Article 22 — Confidentialité, données et propriété intellectuelle", "Les Parties protègent les informations confidentielles et respectent le RGPD ; chaque Partie conserve ses droits de propriété intellectuelle."),
    ("Article 23 — Audit, conformité et loyauté commerciale", "Chaque Partie peut auditer le respect de la Convention dans des conditions raisonnables et s'interdit toute pratique déloyale."),
    ("Article 24 — Force majeure et imprévision", "Les événements de force majeure suspendent les obligations affectées ; l'imprévision ouvre une renégociation de bonne foi."),
    ("Article 25 — Durée de la Convention cadre et des Attestations", "La Convention est conclue pour une durée initiale de 12 mois, renouvelable ; chaque Attestation porte sa propre période de validité."),
    ("Article 26 — Cession, changement de contrôle et sous-traitance", "Toute cession requiert l'accord préalable écrit des autres Parties ; les sous-traitants restent sous la responsabilité du Fournisseur."),
    ("Article 27 — Notifications", "Les notifications sont valablement effectuées par écrit (courrier recommandé ou voie électronique horodatée via le Dashboard)."),
    ("Article 28 — Intégralité contractuelle et hiérarchie", "La Convention et ses Annexes forment l'intégralité de l'accord ; en cas de contradiction, la Convention prévaut sur les Annexes, et l'Attestation sur les documents généraux."),
    ("Article 29 — Preuve, exemplaires et signature électronique", "La Convention peut être signée par voie électronique ; les enregistrements du Dashboard (dont QR codes de vérification) font preuve."),
    ("Article 30 — Droit applicable, règlement amiable et juridiction", "La Convention est soumise au droit français ; tout différend fait l'objet d'une tentative de règlement amiable avant saisine du Tribunal de commerce compétent."),
]

ANNEXES = [
    "Annexe 1 — Identification, rôles et schéma de facturation",
    "Annexe 2 — Modèle d'Attestation Nominative d'agrégation de volumes par catégorie",
    "Annexe 3 — Prix, formule, niveaux de service et paramètres de paiement",
    "Annexe 4 — Calcul de la RCR par Attestation et matrice des risques",
    "Annexe 5 — Règlement de gestion FOGEDOM-SCIC et convention de conservation/exécution de la RCR",
    "Annexe 6 — Dashboard : indicateurs, statuts et seuils",
    "Annexe 7 — Formulaires de mise en demeure, mobilisation et remboursement de la RCR",
    "Annexe 8 — Références légales et checklist de validation",
]


async def _ai_expose(vendor: dict, zones: list, settings: dict) -> str:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"convention-{uuid.uuid4()}",
            system_message=("Tu es un assistant juridique spécialisé en droit commercial coopératif français. "
                            "Rédige en français, style juridique sobre, sans markdown."),
        ).with_model("openai", "gpt-5.4")
        prompt = (
            "Rédige l'EXPOSÉ PRÉALABLE (4 à 6 phrases) d'une convention cadre tripartite d'adhésion "
            "entre O'SCOP (opérateur coopératif SCIC, gestionnaire du fonds FOGEDOM-SCIC), KDMARCHÉ PRO "
            "(partenaire commercial B2B) et le fournisseur suivant :\n"
            f"- Fournisseur : {vendor.get('company_name')}\n"
            f"- Contact : {vendor.get('contact_name')}\n"
            f"- Territoire(s) : {', '.join(zones) or 'Outre-mer'}\n"
            f"- Taux de Retenue Contributive Remboursable par défaut : {settings['rcr_default_rate']}%\n"
            "Mentionne l'agrégation de volumes par catégorie, les attestations nominatives, "
            "l'absence d'engagement take-or-pay et la finalité coopérative ESS du dispositif.")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = str(resp).strip()
        if len(text) > 100:
            return text
    except Exception as exc:
        logger.warning("IA exposé convention indisponible : %s", exc)
    return ("Le Fournisseur souhaite adhérer au dispositif coopératif d'agrégation de volumes par catégorie "
            "de produits opéré par O'SCOP et commercialisé par KDMARCHÉ PRO. Les volumes acceptés sont "
            "matérialisés par des Attestations Nominatives, sans engagement ferme d'achat (absence de "
            "take-or-pay). Une Retenue Contributive Remboursable (RCR) est constituée par fractions et "
            "conservée par le FOGEDOM-SCIC dans une finalité de résilience coopérative, conformément aux "
            "valeurs de l'économie sociale et solidaire.")


async def ensure_convention(db, vendor_id: str) -> dict:
    """Crée (ou retourne) la convention cadre du fournisseur — idempotent."""
    existing = await db.conventions_cadres.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if existing:
        return existing
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    settings = await get_convention_settings(db)
    user = await db.users.find_one({"vendor_id": vendor_id}, {"_id": 0})
    zones = []
    if user:
        membership = await db.org_memberships.find_one({"user_id": user["id"]})
        if membership:
            ents = await db.org_zone_entitlements.find(
                {"org_id": membership["org_id"], "status": "ACTIVE"}).to_list(20)
            zone_ids = [e["zone_id"] for e in ents]
            async for z in db.zones_v2.find({"id": {"$in": zone_ids}}):
                zones.append(z.get("name") or z.get("code"))
    seq = await db.conventions_cadres.count_documents({}) + 1
    ref = f"OSC/KDM/FOUR/CADRE-AGR-RCR-FOGEDOM/{datetime.utcnow().strftime('%Y')}-{seq:04d}"
    expose = await _ai_expose(vendor, zones, settings)
    doc = {
        "id": str(uuid.uuid4()), "ref": ref, "vendor_id": vendor_id,
        "vendor_name": vendor.get("company_name"), "vendor_siret": vendor.get("siret"),
        "vendor_contact": vendor.get("contact_name"), "vendor_email": vendor.get("email"),
        "zones": zones, "rcr_rate": settings["rcr_default_rate"],
        "rcr_global_cap_eur": settings["rcr_global_cap_eur"],
        "duration_months": 12, "status": "ACTIVE", "expose": expose,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.conventions_cadres.insert_one({**doc})
    logger.info("Convention cadre %s créée pour %s", ref, vendor.get("company_name"))
    return doc


def build_convention_pdf(conv: dict, settings: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=15, leading=19)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=11, spaceBefore=8)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=12.5)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, textColor=colors.grey)
    o, k = settings["oscop"], settings["kdmarche"]
    els = [
        Paragraph("CONVENTION CADRE D'ADHÉSION TRIPARTITE", h1),
        Paragraph("Agrégation de volumes par catégorie — RCR — FOGEDOM-SCIC", n),
        Paragraph(f"Référence : {conv['ref']}", n),
        Paragraph(f"Générée le {datetime.now().strftime('%d/%m/%Y')} — assistance de rédaction IA, "
                  "document contractuel soumis à validation des parties.", small),
        Spacer(1, 5 * mm),
        Paragraph("ENTRE LES SOUSSIGNÉES", h2),
        Paragraph(f"<b>1. {o['denomination']}</b>, capital {o['capital']} €, siège {o['siege']}, "
                  f"RCS {o['rcs']}, SIREN {o['siren']}, représentée par {o['representant']} "
                  "(ci-après « O'SCOP », opérateur coopératif, gestionnaire du FOGEDOM-SCIC) ;", n),
        Paragraph(f"<b>2. {k['denomination']}</b>, {k['forme']}, capital {k['capital']} €, siège {k['siege']}, "
                  f"RCS {k['rcs']}, SIREN {k['siren']}, représentée par {k['representant']} "
                  "(ci-après « KDMARCHÉ PRO », partenaire commercial et opérationnel) ;", n),
        Paragraph(f"<b>3. {conv.get('vendor_name', '[À COMPLÉTER]')}</b>, SIRET {conv.get('vendor_siret') or '[À COMPLÉTER]'}, "
                  f"représentée par {conv.get('vendor_contact') or '[À COMPLÉTER]'} — {conv.get('vendor_email', '')} "
                  "(ci-après « le Fournisseur »).", n),
        Spacer(1, 4 * mm),
        Paragraph("EXPOSÉ PRÉALABLE", h2),
        Paragraph(conv.get("expose", ""), n),
        Spacer(1, 3 * mm),
        Paragraph("PARAMÈTRES DE LA CONVENTION", h2),
    ]
    params = Table([
        ["Territoire(s)", ", ".join(conv.get("zones") or []) or "[À COMPLÉTER]"],
        ["Durée initiale", f"{conv.get('duration_months', 12)} mois, renouvelable"],
        ["Taux de Retenue Contributive (défaut)", f"{conv.get('rcr_rate', 5.0):.2f} % (7,50 % / 10,00 % selon matrice des risques)"],
        ["Plafond global RCR consolidé", f"{conv.get('rcr_global_cap_eur', 50000):,.0f} €".replace(",", " ")],
        ["Marge de tolérance volumes", f"{settings['tolerance_rate']:.2f} %"],
        ["Délai de remboursement RCR", f"{int(settings['reimbursement_days'])} jours calendaires (30-60 j)"],
        ["Plafond de responsabilité contractuelle", f"{settings['liability_cap_eur']:,.0f} €".replace(",", " ")],
        ["Assurance RC minimale du Fournisseur", f"{settings['insurance_min_eur']:,.0f} € par sinistre et par an".replace(",", " ")],
        ["Tribunal de commerce compétent", settings["tribunal"]],
    ], colWidths=[70 * mm, 100 * mm])
    params.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    els += [params, PageBreak(), Paragraph("CORPS DE LA CONVENTION", h1), Spacer(1, 2 * mm)]
    for title, body in ARTICLES:
        els += [Paragraph(title, h2), Paragraph(body, n)]
    els += [PageBreak(), Paragraph("ANNEXES (faisant partie intégrante de la Convention)", h2)]
    for a in ANNEXES:
        els.append(Paragraph("• " + a, n))
    els += [
        Spacer(1, 6 * mm), Paragraph("SIGNATURES", h2),
        Paragraph("Fait en trois exemplaires originaux ou par signature électronique. "
                  "Chaque signataire fait précéder sa signature de la mention « Lu et approuvé ».", n),
        Spacer(1, 3 * mm),
        Table([[f"Pour O'SCOP\n{o['representant']}", f"Pour KDMARCHÉ PRO\n{k['representant']}",
                f"Pour le Fournisseur\n{conv.get('vendor_contact') or ''}"]],
              colWidths=[57 * mm, 57 * mm, 57 * mm],
              style=TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
                                ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 22)])),
    ]
    doc.build(els)
    return buf.getvalue()


@convention_router.get("/vendor/{vendor_id}")
async def get_vendor_convention(vendor_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    if not current_user.get("is_admin") and current_user.get("vendor_id") != vendor_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    conv = await ensure_convention(db, vendor_id)
    conv.pop("expose", None)
    return conv


@convention_router.get("/{conv_id}/pdf")
async def download_convention_pdf(conv_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    conv = await db.conventions_cadres.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Convention non trouvée")
    if not current_user.get("is_admin") and current_user.get("vendor_id") != conv["vendor_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    settings = await get_convention_settings(db)
    pdf = build_convention_pdf(conv, settings)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=convention-cadre-{conv['ref'].split('/')[-1]}.pdf"})
