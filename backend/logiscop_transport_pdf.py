"""Génération PDF from scratch : Convention Cadre LOGI'SCOP Mode D V1.2 + Ordre de Transport Nominatif V1.2."""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from logiscop_convention_text import (ARTICLES, CONVENTION_SUBTITLE, CONVENTION_TITLE,
                                      MODE_D_DECLARATION, MODE_D_REMINDER)

GOLD = colors.HexColor("#B8860B")
VIOLET = colors.HexColor("#2A1045")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], textColor=VIOLET, fontSize=13, leading=17),
        "sub": ParagraphStyle("s", parent=ss["Normal"], textColor=GOLD, fontSize=9,
                              alignment=1, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=9.5, spaceBefore=8, spaceAfter=2),
        "n": ParagraphStyle("n", parent=ss["Normal"], fontSize=8.2, leading=11.6, alignment=4),
        "small": ParagraphStyle("sm", parent=ss["Normal"], fontSize=7, textColor=colors.grey),
        "cell": ParagraphStyle("c", parent=ss["Normal"], fontSize=7.6, leading=10),
    }


def _table_style():
    return TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (0, -1), BG),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP")])


def _header_table_style():
    return TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP")])


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return iso or "—"


def build_logiscop_convention_pdf(conv: dict) -> bytes:
    """Convention Cadre Mode D V1.2, générée intégralement (fiche de paramétrage + 32 articles + signatures)."""
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    zones = ", ".join(conv.get("zones") or []) or "[À COMPLÉTER]"
    story = [
        Paragraph(CONVENTION_TITLE, st["title"]),
        Paragraph(CONVENTION_SUBTITLE, st["sub"]),
        Paragraph(f"Référence : <b>{conv['ref']}</b> — émise le {_fmt_date(conv.get('created_at'))}", st["n"]),
        Spacer(1, 3 * mm),
        Paragraph("FICHE DE PARAMÉTRAGE (ANNEXE 1) — IDENTIFICATION DES PARTIES", st["h2"]),
    ]
    fiche = [
        ["Référence", conv["ref"]],
        ["O'SCOP / LOGI'SCOP — Transporteur Contractant",
         "SCIC SAS OBJECTIF SCOP OUTREMER — contact@objectifscopoutremer.com"],
        ["Donneur d'Ordre — identité", conv.get("company_name") or "[À COMPLÉTER]"],
        ["Donneur d'Ordre — SIREN/SIRET", conv.get("siret") or "[À COMPLÉTER]"],
        ["Donneur d'Ordre — représentant", conv.get("contact_name") or "[À COMPLÉTER]"],
        ["Donneur d'Ordre — contacts", conv.get("email") or "[À COMPLÉTER]"],
        ["Transporteur Exécutant éventuel", "NON APPLICABLE — EXÉCUTION EN PROPRE"],
        ["Qualification", "[X] MODE D — TRANSPORTEUR CONTRACTANT / TRANSPORTEUR PUBLIC ROUTIER"],
        ["Mode d'exécution / base juridique", "EN PROPRE"],
        ["Territoires (zones souscrites par le Donneur d'Ordre)", zones],
        ["Registre / licence LOGI'SCOP", "[Références / copies déposées / validité — dossier LOGI'SCOP]"],
        ["Gestionnaire de transport LOGI'SCOP", "[Nom / attestation / délégation / validité]"],
        ["Assureur LOGI'SCOP", "[RC contractuelle transporteur / RC exploitation / police / plafonds]"],
        ["Contacts urgence", "LOGI'SCOP : contact@objectifscopoutremer.com — Donneur d'Ordre : "
                             + (conv.get("email") or "[À COMPLÉTER]")],
    ]
    tab = Table([[Paragraph(f"<b>{a}</b>", st["cell"]), Paragraph(b, st["cell"])] for a, b in fiche],
                colWidths=[62 * mm, 120 * mm])
    tab.setStyle(_table_style())
    story += [tab, PageBreak()]
    for title, text in ARTICLES:
        story += [Paragraph(title, st["h2"]), Paragraph(text, st["n"])]
    story.append(PageBreak())
    story.append(Paragraph("SIGNATURES", st["h2"]))
    story.append(Paragraph(
        f"Fait à {conv.get('signature_place') or '[LIEU]'}, le "
        f"{_fmt_date(conv.get('signed_at')) if conv.get('signed_at') else '[DATE]'}, en trois originaux ou par "
        "signature électronique. Chaque signataire reconnaît avoir reçu, lu, négocié et accepté la Convention et "
        "ses Annexes.", st["n"]))
    story.append(Spacer(1, 3 * mm))
    sig = conv.get("signature") or {}
    sig_rows = [["POUR O'SCOP / LOGI'SCOP", "POUR LE DONNEUR D'ORDRE", "POUR LE TRANSPORTEUR"],
                [Paragraph("Nom : SCIC SAS OBJECTIF SCOP OUTREMER<br/>Qualité : Transporteur Contractant<br/>"
                           f"Date : {_fmt_date(conv.get('signed_at')) if conv.get('signed_at') else '[À COMPLÉTER]'}"
                           "<br/>« Lu et approuvé » — signature électronique LOGI'SCOP", st["cell"]),
                 Paragraph(f"Nom : {sig.get('name') or '[À COMPLÉTER]'}<br/>"
                           f"Qualité : {sig.get('quality') or '[À COMPLÉTER]'}<br/>"
                           f"Date : {_fmt_date(sig.get('at')) if sig.get('at') else '[À COMPLÉTER]'}<br/>"
                           + ("« Lu et approuvé » — signature électronique" if sig.get("at")
                              else "Signature précédée de la mention « Lu et approuvé »"), st["cell"]),
                 Paragraph("NON APPLICABLE — EXÉCUTION EN PROPRE PAR LOGI'SCOP", st["cell"])]]
    tsig = Table(sig_rows, colWidths=[61 * mm, 61 * mm, 60 * mm])
    tsig.setStyle(_header_table_style())
    story += [tsig, Spacer(1, 5 * mm),
              Paragraph(MODE_D_REMINDER, st["small"]),
              Paragraph("Document généré automatiquement par le Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP Mode D "
                        "V1.2. Fait foi entre les Parties.", st["small"])]
    doc.build(story)
    return buf.getvalue()


def build_transport_order_pdf(ot: dict, conv: dict) -> bytes:
    """Ordre de Transport Nominatif LOGI'SCOP — Mode D (V1.2), généré intégralement."""
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=13 * mm, bottomMargin=13 * mm,
                            leftMargin=13 * mm, rightMargin=13 * mm)
    pk, dl = ot.get("pickup") or {}, ot.get("delivery") or {}
    price = f"{(ot.get('price_ht_cents') or 0) / 100:,.2f} EUR".replace(",", " ").replace(".", ",") \
        if ot.get("price_ht_cents") else "[À FIXER PAR LOGI'SCOP]"
    story = [
        Paragraph("ORDRE DE TRANSPORT NOMINATIF LOGI'SCOP — MODE D", st["title"]),
        Paragraph("Contrat d'application d'une mission confiée à LOGI'SCOP, Transporteur contractant, exécutée en "
                  "propre, par location avec conducteur ou, exceptionnellement, par un Transporteur Exécutant "
                  "autorisé — V1.2", st["sub"]),
    ]
    head = [
        ["Ordre", ot["ref"], "Date/heure émission", _fmt_date(ot.get("created_at"))],
        ["Convention-cadre", conv.get("ref") or "—", "Statut", ot.get("status")],
        ["Qualification", "MODE D — TRANSPORTEUR CONTRACTANT", "Territoire",
         f"{pk.get('zone_code') or '—'} → {dl.get('zone_code') or '—'}"],
        ["Transporteur contractant", "O'SCOP / LOGI'SCOP", "Transporteur Exécutant", "LOGI'SCOP EN PROPRE"],
        ["Donneur d'Ordre", conv.get("company_name") or "—", "Condition", "EN PROPRE"],
        ["Fondement légal", "L.3223-2 — NON APPLICABLE (exécution en propre)", "Déclaration / cumul",
         "NON APPLICABLE"],
    ]
    th = Table([[Paragraph(f"<b>{r[0]}</b>", st["cell"]), Paragraph(str(r[1]), st["cell"]),
                 Paragraph(f"<b>{r[2]}</b>", st["cell"]), Paragraph(str(r[3]), st["cell"])] for r in head],
               colWidths=[38 * mm, 57 * mm, 38 * mm, 51 * mm])
    th.setStyle(_table_style())
    story += [th, Paragraph("1. ITINÉRAIRE ET RENDEZ-VOUS", st["h2"])]
    iti_rows = [["Étape", "Adresse / coordonnées", "Date", "Créneau", "Contact", "Action"]]
    iti_rows.append(["Départ", f"{pk.get('address') or '—'} ({pk.get('zone_code') or '—'})",
                     pk.get("date") or "—", pk.get("slot") or "—", pk.get("contact") or "—", "charger / enlèvement"])
    iti_rows.append(["Arrivée", f"{dl.get('address') or '—'} ({dl.get('zone_code') or '—'})",
                     dl.get("date") or "—", dl.get("slot") or "—", dl.get("contact") or "—", "décharger / remise"])
    ti = Table([[Paragraph(str(c), st["cell"]) for c in r] for r in iti_rows],
               colWidths=[16 * mm, 66 * mm, 20 * mm, 24 * mm, 34 * mm, 24 * mm])
    ti.setStyle(_header_table_style())
    story += [ti, Paragraph("2. MARCHANDISES", st["h2"])]
    g_rows = [["Désignation / lot", "Colis", "Poids kg", "Volume m3", "Palettes", "Valeur EUR", "Température"]]
    for g in ot.get("goods") or []:
        g_rows.append([g.get("designation") or "—", g.get("colis") or "—", g.get("poids_kg") or "—",
                       g.get("volume_m3") or "—", g.get("palettes") or "—", g.get("valeur_eur") or "—",
                       g.get("temperature") or "ambiante"])
    tg = Table([[Paragraph(str(c), st["cell"]) for c in r] for r in g_rows],
               colWidths=[60 * mm, 18 * mm, 20 * mm, 21 * mm, 20 * mm, 23 * mm, 22 * mm])
    tg.setStyle(_header_table_style())
    story += [tg, Paragraph("3. MOYENS, TEMPÉRATURE, TRANSPORTEUR EXÉCUTANT ET SÉCURITÉ", st["h2"])]
    sec = [
        ["Mode", ot.get("mode") or "route", "Véhicule", "[Affecté par LOGI'SCOP]"],
        ["Température", ot.get("temperature") or "ambiante", "Tolérance", ot.get("temperature_tolerance") or "—"],
        ["Pré-refroidissement", "OUI" if ot.get("pre_cooling") else "NON", "Scellé départ", "[À la prise en charge]"],
        ["Sous-traitance ultérieure", "INTERDITE", "Valeur déclarée",
         f"{ot['valeur_declaree_eur']} EUR" if ot.get("valeur_declaree_eur") else "NON"],
        ["Base recours Exécutant", "NON APPLICABLE — EXÉCUTION EN PROPRE", "Intérêt spécial", "NON"],
    ]
    ts = Table([[Paragraph(f"<b>{r[0]}</b>", st["cell"]), Paragraph(str(r[1]), st["cell"]),
                 Paragraph(f"<b>{r[2]}</b>", st["cell"]), Paragraph(str(r[3]), st["cell"])] for r in sec],
               colWidths=[42 * mm, 53 * mm, 38 * mm, 51 * mm])
    ts.setStyle(_table_style())
    story += [ts, Paragraph("4. RESPONSABILITÉS OPÉRATIONNELLES", st["h2"])]
    resp = [["Opération", "Donneur d'Ordre / Expéditeur", "LOGI'SCOP", "Destinataire"],
            ["Conditionnement / étiquetage", "X", "", ""],
            ["Chargement", "X", "assistance", ""],
            ["Calage / arrimage", "", "X", ""],
            ["Déchargement", "", "assistance", "X"]]
    tr = Table([[Paragraph(str(c), st["cell"]) for c in r] for r in resp],
               colWidths=[58 * mm, 48 * mm, 40 * mm, 38 * mm])
    tr.setStyle(_header_table_style())
    story += [tr, Paragraph("5. PRIX CONTRACTUEL, PRIX D'EXÉCUTION ET FACTURATION", st["h2"])]
    prix = [["Transport LOGI'SCOP HT", price, "Unité", "forfait"],
            ["Indexation énergétique", "Selon Annexe 2 (CNR)", "Paiement Donneur → LOGI'SCOP",
             "30 jours max si applicable"],
            ["Facture Exécutant à", "NON APPLICABLE (exécution en propre)", "Devise", "EUR"]]
    tp = Table([[Paragraph(f"<b>{r[0]}</b>", st["cell"]), Paragraph(str(r[1]), st["cell"]),
                 Paragraph(f"<b>{r[2]}</b>", st["cell"]), Paragraph(str(r[3]), st["cell"])] for r in prix],
               colWidths=[46 * mm, 52 * mm, 48 * mm, 38 * mm])
    tp.setStyle(_table_style())
    story += [tp, Paragraph("6. DOCUMENTS ET PREUVES REQUIS", st["h2"]),
              Paragraph("[X] Lettre de voiture / CMR / e-CMR — [X] Bon de livraison / ePOD signé — "
                        "[X] Photographies départ et arrivée — [ ] Courbe de température brute — "
                        "[ ] Certificats sanitaires / origine / douane — [X] Liste colisage / poids / palettes — "
                        "[ ] Rapport incident / réserves", st["n"]),
              Paragraph("7. ACCEPTATION ET VALIDATIONS", st["h2"]),
              Paragraph(MODE_D_DECLARATION, st["small"]), Spacer(1, 2 * mm)]
    acc = ot.get("acceptance") or {}
    val_rows = [["O'SCOP / LOGI'SCOP — TRANSPORTEUR CONTRACTANT", "DONNEUR D'ORDRE", "TRANSPORTEUR EXÉCUTANT"],
                [Paragraph(("Nom : " + acc.get("admin_name", "[En attente]")) +
                           f"<br/>Date : {_fmt_date(acc.get('at')) if acc.get('at') else '[En attente]'}"
                           "<br/>Validation : " + ("ACCEPTÉ" if ot.get("status") == "ACCEPTE" else "EN ATTENTE"),
                           st["cell"]),
                 Paragraph(f"Nom : {ot.get('created_by_name') or conv.get('contact_name') or '—'}"
                           f"<br/>Date : {_fmt_date(ot.get('created_at'))}<br/>Validation : émission de l'Ordre "
                           "(validation électronique)", st["cell"]),
                 Paragraph("NON APPLICABLE — EXÉCUTION EN PROPRE", st["cell"])]]
    tv = Table(val_rows, colWidths=[61 * mm, 61 * mm, 60 * mm])
    tv.setStyle(_header_table_style())
    story += [tv, Paragraph("8. EXÉCUTION, RÉSERVES ET CLÔTURE", st["h2"]),
              Paragraph("Champ de clôture : [LIVRE CONFORME / LIVRE AVEC RESERVES / REFUSE / PARTIEL] — renseigné "
                        "à la livraison via le Dashboard (ePOD).", st["n"]),
              Spacer(1, 3 * mm), Paragraph(MODE_D_REMINDER, st["small"]),
              Paragraph("Ordre de transport opérationnel à rattacher à une Convention d'adhésion-cadre en vigueur "
                        f"({conv.get('ref') or '—'}). Généré par le Dashboard KDMARCHÉ × O'SCOP.", st["small"])]
    doc.build(story)
    return buf.getvalue()
