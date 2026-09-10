"""Convention de financement ponctuel O'SCOP × Investisseur — PDF bilingue FR/EN rempli dynamiquement.

Texte officiel fourni (10/09/2026). Remplissage : montants avec/sans marge, option logistique,
échéancier, identité du Financeur (investisseur), Bon d'engagement (opération/fournisseur),
signatures électroniques (règlement eIDAS n° 910/2014, art. 1367 Code civil) avec QR de vérification.
"""
import io
import os
from datetime import date, datetime, timedelta, timezone

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from routes_product_financing import build_repayment_schedule

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#b8933e")

_T = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=12.5, textColor=VIOLET_DARK, spaceAfter=2, leading=16, alignment=1)
_T2 = ParagraphStyle("t2", fontName="Helvetica-Bold", fontSize=9.5, textColor=VIOLET, spaceAfter=8, leading=13, alignment=1)
_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10, textColor=VIOLET, spaceBefore=9, spaceAfter=3)
_B = ParagraphStyle("b", fontName="Helvetica", fontSize=8.8, textColor=colors.HexColor("#2a2233"), leading=12.5, spaceAfter=4)
_CELL = ParagraphStyle("c", fontName="Helvetica", fontSize=7.6, leading=9.5, textColor=colors.HexColor("#2a2233"))
_CELLB = ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=7.6, leading=9.5, textColor=VIOLET)
_META = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=7.2, textColor=colors.HexColor("#6b5a7a"), spaceBefore=6)

BLANK = "____________"


def _fmt(amount: float, lang: str) -> str:
    if lang == "en":
        return f"€{amount:,.2f}"
    s = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} €"


def _d(iso: str | None, lang: str) -> str:
    if not iso:
        return BLANK
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return BLANK
    return d.strftime("%d/%m/%Y") if lang != "en" else d.strftime("%m/%d/%Y")


def _qr_png(url: str) -> bytes:
    img = qrcode.make(url, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _table(rows, widths=None):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), VIOLET),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f4fc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


TEXTS = {
    "fr": {
        "title": "CONVENTION DE FINANCEMENT PONCTUEL",
        "summary": "Financement sans intérêt de {capital} remboursable sur {months} mois",
        "sum_rows": lambda v: [
            ["Capital", v["capital"]],
            ["Rémunération", "0,00 € soit 0 %"],
            ["Durée", v["months_txt"]],
            ["Total à rembourser", v["capital"]],
            ["Marge cible O'SCOP", v["margin_txt"]],
            ["Rythme", v["rhythm_txt"]],
        ],
        "months_txt": lambda n: f"{n} mois",
        "rhythm_txt": lambda n: f"{n} échéances mensuelles",
        "parties": "ENTRE LES SOUSSIGNÉS :",
        "funder_h": "Le Financeur",
        "funder_rows": lambda f: [
            ["Nom ou dénomination sociale", f.get("denomination") or BLANK],
            ["Forme juridique et capital", f.get("forme_capital") or BLANK],
            ["Numéro d'immatriculation", f.get("immatriculation") or BLANK],
            ["Adresse ou siège", f.get("adresse") or BLANK],
            ["Représenté par", f"{f.get('rep_nom') or BLANK}, en qualité de {f.get('rep_qualite') or BLANK}"],
            ["Email", f.get("email") or BLANK],
        ],
        "funder_end": "Ci-après dénommé le « Financeur ».",
        "debtor_h": "Le Débiteur",
        "debtor": ("SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP), société coopérative d'intérêt collectif constituée sous forme de "
                   "société par actions simplifiée, au capital de 10 500 euros, SIRET 903 459 139 00015, dont le siège social est situé "
                   "13 rue Rodrigue YOUYOUTE, 97139 LES ABYMES, représentée par Monsieur Olivier NUDOL, dûment habilité aux fins des présentes."),
        "debtor_end": "Ci-après dénommée « O'SCOP » ou le « Débiteur ».",
        "parties_end": "Le Financeur et le Débiteur sont ci-après désignés individuellement une « Partie » et ensemble les « Parties ».",
        "articles": None,  # rempli ci-dessous
        "sched_head": ("Échéance", "Date", "Capital remboursé", "Capital restant dû"),
        "disb_mode": ("☒ Compte O'SCOP", "☐ Paiement direct du fournisseur"),
        "annexes_h": "Annexes contractuelles",
        "annex_rows": [
            ("Annexe 1", "Bon d'engagement et description de l'opération financée"),
            ("Annexe 2", "Échéancier daté après décaissement"),
            ("Annexe 3", "Devis, bon de commande ou facture pro forma"),
            ("Annexe 4", "Coordonnées bancaires et justificatif de décaissement"),
            ("Annexe 5", "Décisions et pouvoirs des signataires"),
            ("Annexe 6", "Déclaration fiscale n° 2062, lorsqu'elle est applicable"),
        ],
        "bon_h": "Article A — Bon d'engagement",
        "bon_rows": lambda v: [
            ["Objet précis de l'achat", v["objet"]],
            ["Fournisseur", v["fournisseur"]],
            ["Montant hors taxes", v["base_ht"]],
            ["Date prévue du décaissement", v["dec_date"]],
            ["Mode de décaissement", v["dec_mode"]],
            ["Compte de remboursement", v["remb_compte"]],
        ],
        "sign_h": "Signatures électroniques (règlement eIDAS n° 910/2014 — art. 1367 du Code civil)",
        "sign_funder": "Pour le Financeur",
        "sign_debtor": "Pour O'SCOP (le Débiteur)",
        "sign_pending": "En attente de signature électronique.",
        "sign_line": "Signé électroniquement par {nom} ({qualite}) le {date} — « Lu et approuvé » — Code de vérification : {code}",
        "verify_line": "Vérification publique : scannez ce QR code ou visitez {url}",
        "logistics_line": "Option logistique incluse dans l'opération : coût {cost} + marge LOGI'SCOP {lmargin} (total logistique {ltotal}).",
        "generated": "Document généré le {gen} UTC — version {lang_up} — référence {ref}.",
    },
    "en": {
        "title": "ONE-TIME FINANCING AGREEMENT",
        "summary": "Interest-free financing of {capital} repayable over {months} months",
        "sum_rows": lambda v: [
            ["Principal", v["capital"]],
            ["Remuneration", "€0.00 i.e. 0%"],
            ["Duration", v["months_txt"]],
            ["Total to be repaid", v["capital"]],
            ["O'SCOP target margin", v["margin_txt"]],
            ["Rhythm", v["rhythm_txt"]],
        ],
        "months_txt": lambda n: f"{n} months",
        "rhythm_txt": lambda n: f"{n} monthly instalments",
        "parties": "BETWEEN THE UNDERSIGNED:",
        "funder_h": "The Funder",
        "funder_rows": lambda f: [
            ["Name or legal name", f.get("denomination") or BLANK],
            ["Legal form and capital", f.get("forme_capital") or BLANK],
            ["Registration number", f.get("immatriculation") or BLANK],
            ["Address or registered office", f.get("adresse") or BLANK],
            ["Represented by", f"{f.get('rep_nom') or BLANK}, acting as {f.get('rep_qualite') or BLANK}"],
            ["Email", f.get("email") or BLANK],
        ],
        "funder_end": "Hereinafter referred to as the \"Funder\".",
        "debtor_h": "The Debtor",
        "debtor": ("SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP), a cooperative company of collective interest incorporated as a "
                   "simplified joint-stock company, with a share capital of €10,500, SIRET 903 459 139 00015, whose registered office is located "
                   "at 13 rue Rodrigue YOUYOUTE, 97139 LES ABYMES, represented by Mr Olivier NUDOL, duly authorised for the purposes hereof."),
        "debtor_end": "Hereinafter referred to as \"O'SCOP\" or the \"Debtor\".",
        "parties_end": "The Funder and the Debtor are hereinafter referred to individually as a \"Party\" and together as the \"Parties\".",
        "articles": None,
        "sched_head": ("Instalment", "Date", "Principal repaid", "Outstanding principal"),
        "disb_mode": ("☒ O'SCOP account", "☐ Direct payment to the supplier"),
        "annexes_h": "Contractual annexes",
        "annex_rows": [
            ("Appendix 1", "Commitment voucher and description of the financed transaction"),
            ("Appendix 2", "Dated schedule after disbursement"),
            ("Appendix 3", "Quote, purchase order or pro forma invoice"),
            ("Appendix 4", "Bank details and proof of disbursement"),
            ("Appendix 5", "Decisions and powers of the signatories"),
            ("Appendix 6", "Tax declaration no. 2062, where applicable"),
        ],
        "bon_h": "Article A — Commitment voucher",
        "bon_rows": lambda v: [
            ["Precise purpose of the purchase", v["objet"]],
            ["Supplier", v["fournisseur"]],
            ["Amount excluding taxes", v["base_ht"]],
            ["Expected disbursement date", v["dec_date"]],
            ["Disbursement mode", v["dec_mode"]],
            ["Repayment account", v["remb_compte"]],
        ],
        "sign_h": "Electronic signatures (Regulation (EU) No 910/2014 \"eIDAS\" — art. 1367 French Civil Code)",
        "sign_funder": "For the Funder",
        "sign_debtor": "For O'SCOP (the Debtor)",
        "sign_pending": "Awaiting electronic signature.",
        "sign_line": "Electronically signed by {nom} ({qualite}) on {date} — \"Read and approved\" — Verification code: {code}",
        "verify_line": "Public verification: scan this QR code or visit {url}",
        "logistics_line": "Logistics option included in the transaction: cost {cost} + LOGI'SCOP margin {lmargin} (total logistics {ltotal}).",
        "generated": "Document generated on {gen} UTC — {lang_up} version — reference {ref}.",
    },
}


def _articles(lang: str, v: dict) -> list[tuple[str, str]]:
    """Texte des 17 articles avec variables injectées. v = valeurs formatées."""
    if lang == "en":
        return [
            ("Article 1 — Purpose and one-off nature",
             f"This agreement organises one-off financing intended for the acquisition of goods identified in the attached Commitment Voucher "
             f"(« {v['objet']} »). The financing may not be used for another transaction without the Funder's prior written consent. The Parties declare "
             f"that the transaction is isolated. It constitutes neither a revolving line of credit, nor a recurring financing authorisation, nor a "
             f"subscription, nor an issue of securities, nor a collection of repayable funds from the public. Any new transaction shall be subject to a "
             f"separate agreement and a new legal review."),
            ("Article 2 — Amount and disbursement",
             f"The Funder makes available to the Debtor a principal of {v['capital']}. Disbursement takes place in a single instalment, no later than "
             f"{v['dec_date']}, after fulfilment of the conditions set out in Article 8, either by transfer to the Debtor's account or by direct payment "
             f"to the supplier designated in the Commitment Voucher. Direct payment to the supplier is equivalent to making the principal available to the "
             f"Debtor and gives rise to its repayment debt up to that amount. The bank details of the recipient of the funds and proof of payment are "
             f"attached. No cash disbursement is permitted."),
            ("Article 3 — Duration",
             f"The agreement enters into force on its signature date and produces its financial effects from the effective disbursement date. The "
             f"repayment period is set at {v['months']} months. The first instalment falls one month after disbursement, then each month on the same day. "
             f"If that day is not a business day, payment is made on the first following business day, without surcharge."),
            ("Article 4 — No remuneration of the Funder",
             f"The financing is granted without interest, commission, premium, application fees, management fees, indexation or profit sharing. The "
             f"Funder's flat-rate remuneration is set at €0.00, i.e. 0% of the principal. In the absence of any mandatory ancillary cost, the annual "
             f"percentage rate of the financing is 0%. The commercial margin provided for in Article 6 belongs exclusively to the Debtor. It does not "
             f"constitute direct or indirect remuneration of the Funder."),
            ("Article 5 — Repayment and schedule",
             f"The Debtor repays the Funder the total sum of {v['capital']} by {v['months']} monthly transfers, according to the schedule below. "
             f"The last instalment is adjusted to settle the principal exactly. Payments are made to the bank account indicated by the Funder in the "
             f"appendix. The Debtor may repay all or part of the principal early, without penalty. Any early repayment is applied exclusively to the "
             f"outstanding principal and reduces the final instalments."),
            ("Article 6 — Debtor's commercial margin",
             f"For the financed transaction, the Debtor sets a target commercial margin of {v['margin_txt']}. This margin is an internal economic "
             f"objective of the Debtor; it increases neither the repayable principal nor the Funder's rights. The target commercial receipts of the "
             f"transaction are set at no less than {v['encaissements']} excluding taxes, before taking into account logistical, tax, insurance or "
             f"commercial costs not included in the financed principal.{v['logistics_txt']} The Debtor remains free in its commercial policy and bears "
             f"the sale risk. Insufficient sales or margin does not suspend the repayment instalments."),
            ("Article 7 — Allocation and traceability of flows",
             "The Debtor keeps accounts making it possible to identify the disbursement, purchases, sales, receipts and repayments attached to the "
             "transaction. Receipts are allocated as a priority to the payment of due taxes, instalments due to the Funder and costs essential to the "
             "performance of the transaction. The balance remains vested in the Debtor. At the Funder's reasonable request, the Debtor shall transmit, "
             "within ten business days, supplier invoices, customer invoices, proof of receipt and the outstanding principal statement. This information "
             "confers no management power on the Funder over O'SCOP."),
            ("Article 8 — Conditions precedent to disbursement",
             "Disbursement is conditional upon delivery of the following documents: the agreement signed by both Parties and the completed Commitment "
             "Voucher; the internal decision authorising the transaction and empowering the Debtor's signatory; the verified identity, powers and bank "
             "details of the Funder and of the payee; the quote, purchase order or pro forma invoice describing the financed purchase; a declaration on "
             "the lawful origin of funds and compliance with anti-money-laundering and counter-terrorist-financing rules; the dated schedule, drawn up "
             "from the effective disbursement date."),
            ("Article 9 — Debtor's undertakings",
             "During the term of the agreement, the Debtor undertakes to use the funds in accordance with their purpose, to keep the supporting documents, "
             "to inform the Funder without delay of any event likely to prevent an instalment, not to sell the goods outside the ordinary course of "
             "business to the Funder's detriment, and to maintain the insurance necessary for the transport, storage and marketing of the goods."),
            ("Article 10 — Representations of the Parties",
             "Each Party declares that it has the capacity and powers necessary to enter into the agreement. The Funder declares that it is the economic "
             "owner of the funds, acts on its own behalf and does not carry out the transaction in the course of a habitual credit activity subject to "
             "authorisation. The Debtor declares that it has examined its projected repayment capacity. The Parties acknowledge that the agreement does "
             "not constitute legal, tax or financial advice and that they must have the consequences specific to their status validated before signing, "
             "in particular with regard to the banking monopoly, reporting obligations and their internal governance rules."),
            ("Article 11 — Late payment and acceleration",
             "Any unpaid instalment shall bear, after a formal notice has remained without effect for fifteen calendar days, interest at the applicable "
             "statutory rate, calculated only on the sum due and for the duration of the delay. This default interest compensates for the delay and does "
             "not constitute remuneration for the financing. After the same formal notice, the Funder may declare acceleration of the outstanding "
             "principal only where the default is substantial, in particular in the event of non-payment of two instalments, misappropriation of funds, "
             "decisive false declaration or dissolution of the Debtor. The Debtor may regularise until expiry of the formal notice period."),
            ("Article 12 — FOGEDOM-SCIC",
             "FOGEDOM-SCIC is an internal support and prevention fund of SCIC SAS OBJECTIF SCOP OUTREMER. It is neither lender, nor co-borrower, nor "
             "insurer, nor surety, nor automatic guarantor of this agreement. Any possible intervention remains optional, individualised, limited to "
             "available resources and subject to a separate decision in accordance with its internal rules."),
            ("Article 13 — Taxation and loan declaration",
             "The Parties fulfil their tax and accounting obligations. Where declaration of a loan agreement is required, the Debtor files it within the "
             "applicable deadlines, in particular by means of tax form no. 2062 and its schedule, and provides a copy to the Funder. Voluntary "
             "registration of the agreement may be requested to give it a certain date; the costs are borne by the requesting Party, unless otherwise agreed."),
            ("Article 14 — Confidentiality and data",
             "Commercial, banking and accounting information exchanged for the performance of the agreement is confidential. It may only be communicated "
             "to advisers, statutory auditors, administrations, courts and legally authorised authorities, or with the written consent of the other Party."),
            ("Article 15 — Assignment and amendment",
             "Neither Party may assign the agreement or its contractual position without the prior written consent of the other Party. Any amendment must "
             "be recorded in a signed addendum. Tolerating a breach constitutes neither a waiver nor an amendment."),
            ("Article 16 — Applicable law and dispute resolution",
             "The agreement is governed by French law, in particular Articles 1103 and 1104 of the Civil Code on binding force and good faith, Articles "
             "1217, 1231-6 and 1344 on non-performance, delay and formal notice, Articles 1892, 1905 and 1907 on loans and interest, Article L. 511-5 of "
             "the Monetary and Financial Code on habitual credit transactions and, where applicable, Article 49 B of Annex III to the General Tax Code on "
             "the declaration of loan agreements. In the event of a dispute, the Parties shall seek an amicable solution for thirty days from written "
             "notification of the dispute. Failing agreement, the dispute shall fall to the materially and territorially competent court under the rules "
             "of ordinary law."),
            ("Article 17 — Entire agreement and signatures",
             "The agreement and its annexes express the entire agreement relating to the financing. In the event of contradiction, the agreement "
             "prevails, then the dated schedule, then the Commitment Voucher. A reliable electronic signature and a handwritten signature have the value "
             "recognised to them by law."),
        ]
    return [
        ("Article 1 — Objet et caractère ponctuel",
         f"La présente convention organise un financement ponctuel destiné à l'acquisition de marchandises identifiées dans le Bon d'engagement annexé "
         f"(« {v['objet']} »). Le financement ne peut être utilisé pour une autre opération sans l'accord écrit préalable du Financeur. Les Parties "
         f"déclarent que l'opération est isolée. Elle ne constitue ni une ligne de crédit renouvelable, ni une autorisation de financement récurrente, "
         f"ni un abonnement, ni une émission de titres, ni une collecte de fonds remboursables du public. Toute nouvelle opération devra faire l'objet "
         f"d'une convention distincte et d'un nouvel examen juridique."),
        ("Article 2 — Montant et mise à disposition",
         f"Le Financeur met à la disposition du Débiteur un capital de {v['capital']}. Le décaissement intervient en une seule fois, au plus tard le "
         f"{v['dec_date']}, après réalisation des conditions prévues à l'article 8, soit par virement sur le compte du Débiteur, soit par paiement direct "
         f"du fournisseur désigné dans le Bon d'engagement. Le paiement direct du fournisseur vaut mise à disposition du capital au Débiteur et fait "
         f"naître sa dette de remboursement à due concurrence. Les coordonnées bancaires du destinataire des fonds et les justificatifs du paiement sont "
         f"joints en annexe. Aucun décaissement en espèces n'est autorisé."),
        ("Article 3 — Durée",
         f"La convention entre en vigueur à sa date de signature et produit ses effets financiers à compter de la date de décaissement effectif. La durée "
         f"de remboursement est fixée à {v['months']} mois. La première échéance intervient un mois après le décaissement, puis chaque mois au même "
         f"quantième. Si ce jour n'est pas ouvré, le paiement est effectué le premier jour ouvré suivant, sans majoration."),
        ("Article 4 — Absence de rémunération du Financeur",
         "Le financement est consenti sans intérêt, commission, prime, frais de dossier, frais de gestion, indexation ni participation aux résultats. "
         "La rémunération forfaitaire du Financeur est fixée à 0,00 €, soit 0 % du capital. En l'absence de coût obligatoire accessoire, le taux effectif "
         "global du financement est de 0 %. La marge commerciale prévue à l'article 6 appartient exclusivement au Débiteur. Elle ne constitue pas une "
         "rémunération directe ou indirecte du Financeur."),
        ("Article 5 — Remboursement et échéancier",
         f"Le Débiteur rembourse au Financeur la somme totale de {v['capital']} par {v['months']} virements mensuels, selon l'échéancier ci-dessous. La "
         f"dernière échéance est ajustée afin de solder exactement le capital. Les paiements sont effectués sur le compte bancaire indiqué par le "
         f"Financeur en annexe. Le Débiteur peut rembourser tout ou partie du capital par anticipation, sans pénalité. Tout remboursement anticipé "
         f"s'impute exclusivement sur le capital restant dû et réduit les dernières échéances."),
        ("Article 6 — Marge commerciale du Débiteur",
         f"Pour l'opération financée, le Débiteur fixe une marge commerciale cible de {v['margin_txt']}. Cette marge est un objectif économique interne "
         f"au Débiteur ; elle n'augmente ni le capital remboursable ni les droits du Financeur. Les encaissements commerciaux cibles de l'opération sont "
         f"fixés à au moins {v['encaissements']} hors taxes, avant prise en compte des coûts logistiques, fiscaux, assurantiels ou commerciaux non "
         f"compris dans le capital financé.{v['logistics_txt']} Le Débiteur demeure libre de sa politique commerciale et supporte le risque de vente. "
         f"L'insuffisance des ventes ou de la marge ne suspend pas les échéances de remboursement."),
        ("Article 7 — Affectation et traçabilité des flux",
         "Le Débiteur tient une comptabilité permettant d'identifier le décaissement, les achats, les ventes, les encaissements et les remboursements "
         "rattachés à l'opération. Les recettes sont affectées en priorité au paiement des taxes exigibles, des échéances dues au Financeur et des coûts "
         "indispensables à l'exécution de l'opération. Le solde demeure acquis au Débiteur. À la demande raisonnable du Financeur, le Débiteur transmet, "
         "dans un délai de dix jours ouvrés, les factures fournisseurs, factures clients, justificatifs d'encaissement et état du capital restant dû. "
         "Cette information ne confère au Financeur aucun pouvoir de gestion sur O'SCOP."),
        ("Article 8 — Conditions préalables au décaissement",
         "Le décaissement est subordonné à la remise des pièces suivantes : la convention signée par les deux Parties et le Bon d'engagement complété ; "
         "la décision interne autorisant l'opération et habilitant le signataire du Débiteur ; l'identité, les pouvoirs et les coordonnées bancaires "
         "vérifiés du Financeur et du bénéficiaire du virement ; le devis, le bon de commande ou la facture pro forma décrivant l'achat financé ; une "
         "déclaration sur l'origine licite des fonds et le respect des règles de lutte contre le blanchiment et le financement du terrorisme ; "
         "l'échéancier daté, établi à partir de la date effective de décaissement."),
        ("Article 9 — Engagements du Débiteur",
         "Pendant la durée de la convention, le Débiteur s'engage à employer les fonds conformément à leur objet, conserver les justificatifs, informer "
         "sans délai le Financeur de tout événement susceptible d'empêcher une échéance, ne pas céder les marchandises hors du cours normal de "
         "l'activité au préjudice du Financeur et maintenir les assurances nécessaires au transport, au stockage et à la commercialisation des biens."),
        ("Article 10 — Déclarations des Parties",
         "Chaque Partie déclare avoir la capacité et les pouvoirs nécessaires pour conclure la convention. Le Financeur déclare être le propriétaire "
         "économique des fonds, agir pour son propre compte et ne pas réaliser l'opération dans le cadre d'une activité habituelle de crédit soumise à "
         "agrément. Le Débiteur déclare avoir examiné sa capacité prévisionnelle de remboursement. Les Parties reconnaissent que la convention ne "
         "constitue pas un conseil juridique, fiscal ou financier et qu'elles doivent faire valider, avant signature, les conséquences propres à leur "
         "statut, notamment au regard du monopole bancaire, des obligations déclaratives et de leurs règles internes de gouvernance."),
        ("Article 11 — Retard et exigibilité anticipée",
         "Toute échéance impayée produit, après mise en demeure restée sans effet pendant quinze jours calendaires, intérêt au taux légal applicable, "
         "calculé uniquement sur la somme échue et pour la durée du retard. Cet intérêt moratoire répare le retard et ne constitue pas la rémunération "
         "du financement. Après la même mise en demeure, le Financeur peut prononcer l'exigibilité anticipée du seul capital restant dû lorsque le défaut "
         "est substantiel, notamment en cas de non-paiement de deux échéances, de détournement des fonds, de fausse déclaration déterminante ou de "
         "dissolution du Débiteur. Le Débiteur peut régulariser jusqu'à l'expiration du délai de mise en demeure."),
        ("Article 12 — FOGEDOM-SCIC",
         "FOGEDOM-SCIC est un fonds interne d'appui et de prévention de la SCIC SAS OBJECTIF SCOP OUTREMER. Il n'est ni prêteur, ni coemprunteur, ni "
         "assureur, ni caution, ni garant automatique de la présente convention. Toute intervention éventuelle demeure facultative, individualisée, "
         "limitée aux ressources disponibles et subordonnée à une décision distincte conforme à ses règles internes."),
        ("Article 13 — Fiscalité et déclaration du prêt",
         "Les Parties accomplissent les obligations fiscales et comptables qui leur incombent. Lorsque la déclaration d'un contrat de prêt est requise, "
         "le Débiteur la dépose dans les délais applicables, notamment au moyen du formulaire fiscal n° 2062 et de son échéancier, et en remet une copie "
         "au Financeur. L'enregistrement volontaire de la convention peut être demandé afin de lui conférer date certaine ; les frais sont supportés par "
         "la Partie qui le sollicite, sauf accord contraire."),
        ("Article 14 — Confidentialité et données",
         "Les informations commerciales, bancaires et comptables échangées pour l'exécution de la convention sont confidentielles. Elles ne peuvent être "
         "communiquées qu'aux conseils, commissaires aux comptes, administrations, juridictions et autorités légalement habilitées, ou avec l'accord "
         "écrit de l'autre Partie."),
        ("Article 15 — Cession et modification",
         "Aucune Partie ne peut céder la convention ou sa position contractuelle sans l'accord écrit préalable de l'autre Partie. Toute modification doit "
         "être constatée par un avenant signé. La tolérance d'un manquement ne vaut ni renonciation ni modification."),
        ("Article 16 — Droit applicable et règlement des différends",
         "La convention est régie par le droit français, notamment par les articles 1103 et 1104 du Code civil sur la force obligatoire et la bonne foi, "
         "les articles 1217, 1231-6 et 1344 sur l'inexécution, le retard et la mise en demeure, les articles 1892, 1905 et 1907 sur le prêt et les "
         "intérêts, l'article L. 511-5 du Code monétaire et financier relatif aux opérations de crédit effectuées à titre habituel et, lorsqu'il est "
         "applicable, l'article 49 B de l'annexe III au Code général des impôts sur la déclaration des contrats de prêt. En cas de différend, les Parties "
         "recherchent une solution amiable pendant trente jours à compter de la notification écrite du différend. À défaut d'accord, le litige relève de "
         "la juridiction matériellement et territorialement compétente selon les règles de droit commun."),
        ("Article 17 — Intégralité contractuelle et signatures",
         "La convention et ses annexes expriment l'intégralité de l'accord relatif au financement. En cas de contradiction, la convention prévaut, puis "
         "l'échéancier daté, puis le Bon d'engagement. La signature électronique fiable et la signature manuscrite ont la valeur que leur reconnaît la loi."),
    ]


def build_financing_contract_pdf(op: dict, lang: str = "fr", verify_base: str = "") -> bytes:
    lang = "en" if lang == "en" else "fr"
    tr = TEXTS[lang]
    contract = op.get("contract") or {}
    funder = dict(contract.get("funder") or {})
    funder.setdefault("email", op.get("paid_by") or "")
    sigs = contract.get("signatures") or {}

    capital = float(op.get("repayment_amount_eur") or op.get("total_price_eur") or 0)
    base = float(op.get("base_price_eur") or 0)
    logi_cost = float(op.get("logistics_cost_eur") or 0)
    logi_total = float(op.get("logistics_total_eur") or 0)
    months = int(op.get("repayment_duration_months") or 12)
    margin_eur = round(capital - base - (logi_total or 0), 2)
    margin_pct = op.get("margin_percent")
    paid_at = op.get("paid_at")
    dec_date = (datetime.fromisoformat(str(paid_at).replace("Z", "+00:00")).date() + timedelta(days=7)).isoformat() if paid_at else None

    margin_txt = f"{_fmt(margin_eur, lang)} soit {margin_pct} %" if lang == "fr" else f"{_fmt(margin_eur, lang)} i.e. {margin_pct} %"
    v = {
        "capital": _fmt(capital, lang),
        "months": months,
        "months_txt": tr["months_txt"](months),
        "rhythm_txt": tr["rhythm_txt"](months),
        "margin_txt": margin_txt,
        "encaissements": _fmt(round(capital + max(margin_eur, 0), 2), lang),
        "objet": op.get("name") or BLANK,
        "dec_date": _d(dec_date, lang),
        "logistics_txt": "",
    }
    if logi_cost:
        v["logistics_txt"] = " " + tr["logistics_line"].format(
            cost=_fmt(logi_cost, lang),
            lmargin=_fmt(round(logi_total - logi_cost, 2), lang),
            ltotal=_fmt(logi_total, lang))

    schedule = build_repayment_schedule(op) or []
    sched_rows = [[Paragraph(h, _CELLB) for h in tr["sched_head"]]]
    remaining = capital
    for i, s in enumerate(schedule, 1):
        amt = float(s["amount_eur"])
        remaining = round(remaining - amt, 2)
        sched_rows.append([Paragraph(str(i), _CELL), Paragraph(_d(s["due_date"], lang), _CELL),
                           Paragraph(_fmt(amt, lang), _CELL), Paragraph(_fmt(max(remaining, 0), lang), _CELL)])

    verify_url = f"{verify_base}/verifier-financement/{op['id']}" if verify_base else ""
    bon_v = {
        "objet": op.get("name") or BLANK,
        "fournisseur": op.get("supplier_name") or op.get("vendor_name") or (BLANK if lang == "fr" else BLANK),
        "base_ht": _fmt(base + logi_cost, lang),
        "dec_date": v["dec_date"],
        "dec_mode": f"{tr['disb_mode'][0]}   {tr['disb_mode'][1]}" if paid_at else f"☐ {tr['disb_mode'][0][2:]}   {tr['disb_mode'][1][2:]}",
        "remb_compte": contract.get("repayment_account") or BLANK,
    }

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=13 * mm,
                            leftMargin=17 * mm, rightMargin=17 * mm)
    el = [
        Paragraph(tr["title"], _T),
        Paragraph(tr["summary"].format(capital=v["capital"], months=months), _T2),
        _table(tr["sum_rows"](v), widths=[60 * mm, 110 * mm]),
        Spacer(1, 6),
        Paragraph(tr["parties"], _H),
        Paragraph(tr["funder_h"], _H),
        _table(tr["funder_rows"](funder), widths=[55 * mm, 115 * mm]),
        Paragraph(tr["funder_end"], _B),
        Paragraph(tr["debtor_h"], _H),
        Paragraph(tr["debtor"], _B),
        Paragraph(tr["debtor_end"], _B),
        Paragraph(f"<i>{tr['parties_end']}</i>", _B),
    ]
    for title, body in _articles(lang, v):
        el.append(Paragraph(title, _H))
        el.append(Paragraph(body, _B))
        if title.startswith("Article 5") and sched_rows:
            el.append(Table(sched_rows, colWidths=[20 * mm, 40 * mm, 55 * mm, 55 * mm], style=TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efe6f8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f4fc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])))
            el.append(Spacer(1, 4))

    el.append(Paragraph(tr["annexes_h"], _H))
    el.append(_table([[Paragraph(a, _CELL), Paragraph(d, _CELL)] for a, d in tr["annex_rows"]], widths=[30 * mm, 140 * mm]))
    el.append(Paragraph(tr["bon_h"], _H))
    el.append(_table([[Paragraph(a, _CELL), Paragraph(b, _CELL)] for a, b in tr["bon_rows"](bon_v)], widths=[55 * mm, 115 * mm]))

    el.append(Spacer(1, 8))
    el.append(Paragraph(tr["sign_h"], _H))
    for key, label in (("investor", tr["sign_funder"]), ("oscop", tr["sign_debtor"])):
        sig = sigs.get(key)
        el.append(Paragraph(f"<b>{label}</b>", _B))
        if sig:
            el.append(Paragraph(tr["sign_line"].format(
                nom=sig.get("nom") or "", qualite=sig.get("qualite") or "",
                date=_d((sig.get("signed_at") or "")[:10], lang), code=sig.get("verification_code") or ""), _B))
        else:
            el.append(Paragraph(f"<i>{tr['sign_pending']}</i>", _B))
    if verify_url:
        el.append(Spacer(1, 4))
        el.append(RLImage(io.BytesIO(_qr_png(verify_url)), width=26 * mm, height=26 * mm))
        el.append(Paragraph(tr["verify_line"].format(url=verify_url), _META))
    el.append(Paragraph(tr["generated"].format(
        gen=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
        lang_up=lang.upper(), ref=op.get("reference") or op.get("id", "")[:8]), _META))
    doc.build(el)
    return buf.getvalue()
