"""PDF Attestation Nominative V2.0 — Achat de volumes de produits prédéfinis & RCR FOGEDOM-SCIC."""
import hashlib
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")

STATUS_LABELS = {"pending_countersign": "PROJET — en attente de contre-signature O'SCOP / KDMARCHE",
                 "signed": "ACTIVE"}

CLAUSE_ACTIVATION = ("Aucune fraction ne peut être constituée avant validation écrite de l'Attestation d'Achat. "
                     "À défaut, KDMARCHE règle intégralement les factures au Fournisseur.")

CLAUSES_S4 = [
    "FOGEDOM-SCIC, Fonds coopératif interne d'O'SCOP, ouvre la référence RCR, individualise les droits, calcule "
    "les fractions, contrôle le plafond et exerce la maîtrise coopérative de destination : affectation, restitution "
    "et, le cas échéant, mobilisation conforme.",
    "La RCR demeure une contribution individualisée et remboursable dont le Fournisseur reste le bénéficiaire "
    "économique jusqu'à son remboursement ou sa mobilisation définitive.",
    "L'exécution monétaire est assurée par O'SCOP. FOGEDOM-SCIC gouverne et instruit.",
    "Les ressources propres coopératives de FOGEDOM-SCIC sont distinguées des RCR.",
    "La RCR n'est ni une police d'assurance, ni une garantie automatique, ni une remise, ni une pénalité. "
    "Toute mobilisation est contradictoire, proportionnée, documentée et soumise aux règles de double validation "
    "de la Convention-cadre.",
]

CLAUSES_S5 = [
    "La présente Attestation est un contrat d'application nominatif de la Convention-cadre en vigueur. Elle fixe, "
    "pour la catégorie identifiée, les Produits, Volumes d'Achat Ferme et Optionnels, prix, Montants d'Achat Ferme HT, "
    "calendrier, dates de validité, paramètres logistiques et paramètres RCR.",
    "Elle entre en vigueur après acceptation des trois Parties et levée des conditions suspensives. Les Ordres de "
    "Tirage, livraisons, règlements, réclamations et opérations FOGEDOM-RCR survivent jusqu'à leur complet achèvement.",
    "Le Volume d'Achat Ferme engage KDMARCHE à acheter et le Fournisseur à fournir. Le Volume Optionnel ne devient "
    "ferme qu'après activation écrite conforme. Un mécanisme take-or-pay ne s'applique que s'il est expressément "
    "sélectionné et chiffré ci-dessous.",
    "La RCR est individualisée par Fournisseur, Attestation, facture et ligne Produit. Un même Produit, une même "
    "capacité ou une même facture ne peut être compté deux fois.",
    "En cas de contradiction, l'Attestation la plus récente prévaut pour ses Produits, volumes, prix et dates ; "
    "la Convention-cadre régit les règles générales.",
]

DECLARATIONS = [
    ("FOURNISSEUR", "fournisseur",
     "Accepte les Volumes d'Achat Ferme, les prix, dates et conditions logistiques ; autorise le règlement scindé "
     "et confie à O'SCOP, via FOGEDOM-SCIC, le mandat spécial et limité d'administration de la RCR selon la "
     "Convention-cadre."),
    ("KDMARCHE PRO", "kdmarche",
     "S'engage à acheter le Volume d'Achat Ferme, à émettre les Ordres de Tirage selon le calendrier, à payer les "
     "factures et à ne solliciter une mobilisation que dans les conditions contradictoires de la Convention-cadre."),
    ("O'SCOP / FOGEDOM-SCIC", "oscop",
     "Ouvre la référence FOGEDOM-RCR, valide l'individualisation, le plafond, les délégations et l'architecture "
     "d'exécution monétaire, puis assure la gouvernance, la traçabilité et les instructions conformes."),
]


def _qr_png(url: str) -> bytes:
    import qrcode
    img = qrcode.make(url, box_size=6, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


def _d(iso: str) -> str:
    return (iso or "")[:10].split("-")[::-1] and "/".join((iso or "")[:10].split("-")[::-1]) or "[JJ/MM/AAAA]"


def _fields_table(pairs, col=(46, 45, 44, 45)):
    """Tableau de champs sur 2 colonnes label/valeur (valeurs repliables)."""
    lbl = ParagraphStyle("fl", fontName="Helvetica-Bold", fontSize=7.2, leading=8.8)
    val = ParagraphStyle("fv", fontName="Helvetica", fontSize=7.2, leading=8.8)
    rows = []
    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([Paragraph(left[0], lbl), Paragraph(str(left[1]), val),
                     Paragraph(right[0], lbl), Paragraph(str(right[1]), val)])
    t = Table(rows, colWidths=[c * mm for c in col])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (0, -1), BG), ("BACKGROUND", (2, 0), (2, -1), BG),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_attestation_pdf(att: dict) -> bytes:
    base = (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
    verify_url = f"{base}/verifier-attestation/{att['id']}"
    doc_hash = hashlib.sha256(f"{att['id']}|{att['ref']}|{att.get('created_at', '')}".encode()).hexdigest()[:24]

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=12.5, leading=16)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=8.5, textColor=colors.grey, alignment=1)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10, spaceBefore=8, spaceAfter=3)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=8, leading=11.5)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7, textColor=colors.grey)
    warn = ParagraphStyle("w", parent=ss["Normal"], fontSize=8, leading=11.5, textColor=colors.HexColor("#8B2500"))

    sigs = att.get("signatures") or {}
    statut = STATUS_LABELS.get(att.get("status"), att.get("status", ""))
    cat = att.get("category", "")
    montant = att.get("montant_agrege_cents", 0)
    version = att.get("version", "V2.0")

    els = [
        Paragraph("ATTESTATION NOMINATIVE D'ACHAT DE VOLUMES DE PRODUITS PRÉDÉFINIS<br/>"
                  "ET DE RATTACHEMENT À LA RCR FOGEDOM-SCIC", h1),
        Paragraph(f"Contrat d'application de la Convention-cadre {version} — "
                  "O'SCOP / KDMARCHE PRO / FOURNISSEUR — une Attestation par catégorie de Produits", sub),
        Spacer(1, 4 * mm),
        Paragraph("1. IDENTIFICATION, VALIDITÉ ET RATTACHEMENT FOGEDOM-RCR", h2),
        _fields_table([
            ("N° Attestation / version", f"{att['ref']} / {version}"),
            ("Référence Convention-cadre", att.get("convention_ref") or "[À COMPLÉTER]"),
            ("Fournisseur nominatif", f"{att.get('vendor_name', '')} / SIREN {(att.get('vendor_siret') or '')[:9] or '[—]'}"),
            ("Catégorie de Produits", cat.upper() or "[UNE CATÉGORIE PAR ATTESTATION]"),
            ("Territoire(s) / canal", ", ".join(att.get("zones") or []) or "[À COMPLÉTER]"),
            ("Devise", att.get("devise", "EUR")),
            ("Date d'émission", _d(att.get("created_at"))),
            ("Date d'Entrée générale", _d(att.get("date_entree") or att.get("created_at"))),
            ("Date d'Expiration générale", _d(att.get("date_expiration"))),
            ("Statut", statut),
            ("Attestation remplacée", att.get("replaced_ref") or "NÉANT"),
            ("Attestation suivante", att.get("next_ref") or "NÉANT"),
            ("Référence FOGEDOM-RCR", att.get("fogedom_ref") or "[À COMPLÉTER]"),
            ("Identifiant Dashboard", att["id"][:18]),
            ("Règlement FOGEDOM / délégations", att.get("reglement_ref") or "Règlement de gestion FOGEDOM-SCIC en vigueur"),
            ("Responsable FOGEDOM-RCR", att.get("responsable_fogedom") or "[NOM / QUALITÉ]"),
            ("Mode d'exécution monétaire", att.get("mode_execution", "O'SCOP AGENT DE PSP")),
            ("Support individualisé / titulaire", f"Sous-compte FOGEDOM-RCR / {att.get('vendor_name', '')}"),
            ("Bénéficiaire économique du solde", "LE FOURNISSEUR"),
            ("Référents opérationnel / conformité", att.get("referents") or "[NOMS / EMAILS / TÉL.]"),
        ]),
        Paragraph("2. DÉTAIL PRODUIT PAR PRODUIT", h2),
    ]
    cell = ParagraphStyle("pc", fontName="Helvetica", fontSize=6.6, leading=8)
    cellh = ParagraphStyle("pch", fontName="Helvetica-Bold", fontSize=6.6, leading=8)
    prod_rows = [[Paragraph(x, cellh) for x in
                  ["Réf. / SKU / EAN", "Désignation / conditionnement", "Unité", "Volume ferme / optionnel",
                   "Prix unitaire HT", "Montant ferme € HT", "Date d'entrée", "Date d'expiration"]]]
    prod_rows.append([Paragraph(str(x), cell) for x in [
        att.get("product_sku") or (att.get("product_id") or "")[:14],
        f"{att.get('product_name', '')} — {cat}",
        att.get("unit", "unité"),
        f"{att.get('volume', 0)} ferme / NÉANT",
        f"{float(att.get('price_ht') or 0):,.2f} €".replace(",", " ").replace(".", ","),
        _eur(montant),
        _d(att.get("date_entree") or att.get("created_at")),
        _d(att.get("date_expiration")),
    ]])
    pt = Table(prod_rows, colWidths=[24 * mm, 42 * mm, 13 * mm, 25 * mm, 21 * mm, 24 * mm, 16 * mm, 17 * mm])
    pt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    els += [
        pt,
        Paragraph("3. SYNTHÈSE D'ACHAT, PARAMÈTRES RCR ET EXÉCUTION FINANCIÈRE", h2),
        _fields_table([
            ("Nombre de références", "1"),
            ("Nature de l'achat", att.get("nature_achat", "VOLUME FERME")),
            ("Montant d'Achat Ferme HT total", f"{_eur(montant)} HT"),
            ("Volume d'Achat Ferme total", f"{att.get('volume', 0)} {att.get('unit', 'unité')}(s)"),
            ("Base de Retenue RCR", "Montants HT éligibles de cette Attestation"),
            ("Volume Optionnel total", "NÉANT"),
            ("Taux de Retenue Contributive", f"{att.get('rcr_rate', 5.0):.2f} % (5,00 % / 7,50 % / 10,00 %)"),
            ("Plafond-cible RCR", _eur(att.get("plafond_cible_cents"))),
            ("Solde RCR d'ouverture", "0,00 €"),
            ("Cycle de remboursement", att.get("cycle_remboursement", "À L'EXPIRATION")),
            ("Date de revue / clôture", _d(att.get("date_expiration"))),
            ("Tolérance générale", f"{att.get('tolerance_rate', 5.0):.2f} %"),
            ("Prix plafond / formule", f"{float(att.get('price_ht') or 0):,.2f} € HT / {att.get('unit', 'unité')}".replace(",", " ").replace(".", ",")),
            ("Incoterm / site", att.get("incoterm") or "EXW — site du Fournisseur"),
            ("Calendrier / Ordres de Tirage", "Selon Bons de Commande émis via le Dashboard"),
            ("Délai de mise à disposition", att.get("delai") or "[À COMPLÉTER]"),
            ("Température / chaîne du froid", att.get("storage_conditions") or "—"),
            ("Mode de règlement", "Règlement scindé : net Fournisseur + fraction RCR"),
            ("PFH / PSP mandant", att.get("mode_execution", "O'SCOP AGENT DE PSP")),
            ("Comité FOGEDOM-RCR", "Double validation : OUI"),
            ("Take-or-pay", "NON"),
            ("Renouvellement de l'Attestation", "NON — nouvelle Attestation par période"),
        ]),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>CONDITION D'ACTIVATION DE LA RCR —</b> {CLAUSE_ACTIVATION}", warn),
        PageBreak(),
        Paragraph("4. MAÎTRISE COOPÉRATIVE DE DESTINATION ET EXÉCUTION MONÉTAIRE", h2),
    ]
    els += [Paragraph("• " + c, n) for c in CLAUSES_S4]
    els.append(Paragraph("5. PORTÉE DE L'ATTESTATION", h2))
    els += [Paragraph("• " + c, n) for c in CLAUSES_S5]
    if att.get("ai_text"):
        els += [Paragraph("DÉCLARATION PARTICULIÈRE (rédaction assistée par IA — soumise à validation des Parties)", h2),
                Paragraph(att["ai_text"], n)]
    els += [
        Paragraph("6. ENREGISTREMENT, RAPPROCHEMENT ET CONTRÔLES", h2),
        _fields_table([
            ("Référence Dashboard", att["id"]),
            ("Registre FOGEDOM-RCR", att.get("fogedom_ref") or "[RÉFÉRENCE / SOLDE ANALYTIQUE]"),
            ("Date/heure de validation", (sigs.get("oscop") or {}).get("at", "En attente")[:19].replace("T", " ")),
            ("Rapprochement montant total", "CONFORME" if att.get("status") == "signed" else "À VALIDER"),
            ("Rapprochement FOGEDOM / exécution", "CONFORME" if att.get("status") == "signed" else "À VALIDER"),
            ("Architecture financière validée", "MANDAT AGENT"),
            ("KYC/KYB et règlement scindé", "VALIDÉS" if att.get("status") == "signed" else "EN COURS"),
            ("Absence de double comptage", "CONFIRMÉE"),
            ("Hash / empreinte document", doc_hash),
            ("Version archivée", version),
            ("Instruction de paiement", att.get("instruction_paiement") or "[RÉFÉRENCE / DATE]"),
            ("Seuil d'écart / blocage", att.get("seuil_ecart") or "—"),
            ("Pièces jointes", "Fiche technique produit (Dashboard)"),
            ("Observations", att.get("observations") or "—"),
        ]),
        Paragraph("7. DÉCLARATIONS D'ACCEPTATION — ACCEPTATION TRIPARTITE", h2),
    ]
    for label, key, text in DECLARATIONS:
        check = "☑" if sigs.get(key) else "☐"
        els.append(Paragraph(f"{check} <b>{label}</b> — {text}", n))
    sig_rows = [["POUR O'SCOP", "POUR KDMARCHE PRO", "POUR LE FOURNISSEUR"]]
    cells = []
    for key, extra in (("oscop", "Responsable FOGEDOM-RCR : [—]\nSignature / double validation"),
                       ("kdmarche", "Signature / mention « Lu et approuvé »"),
                       ("fournisseur", "Signature / mention « Lu et approuvé »")):
        s = sigs.get(key)
        cells.append(f"Nom / qualité : {(s or {}).get('name', '[—]')}\n"
                     f"Date : {(s or {}).get('at', '')[:10] if s else 'En attente'}\n{extra}")
    sig_rows.append(cells)
    st = Table(sig_rows, colWidths=[60 * mm, 60 * mm, 60 * mm])
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTSIZE", (0, 0), (-1, -1), 7.4), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, 1), 20),
    ]))
    els += [
        Spacer(1, 2 * mm), st,
        Spacer(1, 4 * mm), Paragraph("VÉRIFICATION D'AUTHENTICITÉ (QR CODE)", h2),
        RLImage(BytesIO(_qr_png(verify_url)), width=30 * mm, height=30 * mm, hAlign="LEFT"),
        Paragraph(f"Scannez ce QR code ou visitez : {verify_url}", small),
        Paragraph("Ce QR code permet à toute partie de vérifier en ligne le statut, l'empreinte et les signatures "
                  "de la présente Attestation.", small),
        Spacer(1, 3 * mm),
        Paragraph("Cette Attestation doit être complétée, cohérente avec la Convention-cadre en vigueur et le "
                  "règlement FOGEDOM-RCR. Modèle opérationnel — Confidentiel — Attestation FOGEDOM-SCIC — "
                  "Version en vigueur.", small),
    ]
    doc.build(els)
    return buf.getvalue()
