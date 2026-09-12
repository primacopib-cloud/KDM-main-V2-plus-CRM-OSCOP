"""Convention tripartite de partenariat économique (texte officiel 10/09/2026).

Pages du contrat générées dynamiquement en FR/EN/ES selon la langue du membre
(ob['locale'], gcf → fr). Le bloc du tiers (Fournisseur ou Acheteur Pro) est
rempli avec les informations saisies à l'étape convention de l'adhésion.
En cas de divergence, la version française prévaut.
"""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#b8933e")

_T = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=12.5, textColor=VIOLET_DARK, spaceAfter=2, leading=16, alignment=1)
_T2 = ParagraphStyle("t2", fontName="Helvetica-Bold", fontSize=10, textColor=VIOLET, spaceAfter=8, leading=13, alignment=1)
_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10, textColor=VIOLET, spaceBefore=10, spaceAfter=3)
_B = ParagraphStyle("b", fontName="Helvetica", fontSize=8.8, textColor=colors.HexColor("#2a2233"), leading=12.5, spaceAfter=4)
_META = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.HexColor("#6b5a7a"), spaceBefore=8)


def _fill_member_block(ob: dict, third_label: str) -> str:
    conv = ob.get("convention") or {}
    rep = f"{conv.get('rep_prenom') or ''} {conv.get('rep_nom') or ''}".strip() or "[•]"
    return (
        f"<b>{ob.get('company') or '[•]'}</b>, {conv.get('forme_sociale') or '[•]'} au capital de {conv.get('capital') or '[•]'} €, "
        f"immatriculée au RCS de {conv.get('rcs_ville') or '[•]'} sous le numéro {ob.get('siret') or '[•]'}, "
        f"dont le siège social est situé à {conv.get('adresse') or '[•]'}, représentée par {rep}"
        f"{(' — ' + conv.get('rep_qualite')) if conv.get('rep_qualite') else ''}, "
        f"(ci-après désignée « <b>{third_label}</b> »)."
    )


TEXTS = {
    "fr": {
        "title": "CONVENTION TRIPARTITE DE PARTENARIAT ÉCONOMIQUE",
        "subtitle": "Cadre d'intégration et distribution intracommunautaire Outre-mer",
        "parties_title": "ENTRE LES SOUSSIGNÉS :",
        "party_oscop": ("<b>OBJECTIF SCOP OUTREMER</b> (Enseigne : O'SCOP), SCIC SAS au capital variable, immatriculée au RCS de "
                        "Pointe-à-Pitre sous le numéro 903 459 139, dont l'établissement est situé au 13 rue Rodrigue YOUYOUTE, "
                        "97139 Les Abymes, représentée par son Président en exercice, (ci-après désignée « l'Opérateur Technique » ou « O'SCOP ») ;"),
        "party_kdm": ("<b>KDMARCHÉ</b>, enseigne de Madame Félixia Vanessa PIPEROL, Entrepreneure Individuelle (EI), nom commercial "
                      "PRIMACOP INTERNATIONAL BUSINESS, SIREN 433 230 703 — SIRET 433 230 703 00020, dont l'adresse professionnelle est située "
                      "Morne Bourg, chemin Symphart Lampecinado, 97170 Petit-Bourg, "
                      "(ci-après désignée « La Centrale d'Achat » ou « KDMARCHE ») ;"),
        "collectively": "Ci-après collectivement désignées « les Parties ».",
        "third_vendor": "Le Fournisseur",
        "third_buyer": "L'Acheteur Professionnel",
        "preamble_vendor": [
            "O'SCOP exploite la plateforme numérique Marketplace CommunityPlace visant à structurer, sécuriser et dynamiser les circuits de distribution et l'économie sociale ultramarine.",
            "KDMARCHE intervient sur cette plateforme en tant que distributeur de gros et demi-gros pour approvisionner les entreprises des Outre-mer à des « prix structurels mutualisés ».",
            "Le Fournisseur souhaite intégrer ce réseau vertueux pour référencer et vendre ses marchandises via la puissance logistique et commerciale combinée de KDMARCHE et de la plateforme numérique.",
        ],
        "preamble_buyer": [
            "O'SCOP exploite la plateforme numérique Marketplace CommunityPlace visant à structurer, sécuriser et dynamiser les circuits de distribution et l'économie sociale ultramarine.",
            "KDMARCHE intervient sur cette plateforme en tant que distributeur de gros et demi-gros pour approvisionner les entreprises des Outre-mer à des « prix structurels mutualisés ».",
            "L'Acheteur Professionnel souhaite intégrer ce réseau vertueux pour s'approvisionner via la puissance logistique et commerciale combinée de KDMARCHE et de la plateforme numérique.",
        ],
        "articles_vendor": [
            ("ARTICLE 1 : OBJET DE LA CONVENTION",
             "La présente convention a pour objet de définir les conditions techniques, financières et commerciales de leur collaboration :<br/>"
             "— L'intégration du catalogue du Fournisseur sur l'espace digital opéré par O'SCOP.<br/>"
             "— Les modalités de rachat, de stockage et de distribution des marchandises par KDMARCHE.<br/>"
             "— Le respect de la transparence des prix et de la traçabilité au profit des acheteurs finaux."),
            ("ARTICLE 2 : RÔLES ET ENGAGEMENTS DE CHAQUE PARTIE",
             "<b>2.1. Engagements de l'Opérateur Technique (O'SCOP)</b> :<br/>"
             "— <i>Mise à disposition technologique</i> : fournir l'infrastructure technique, sécurisée et le sous-domaine dédié à l'activité de revente de gros de la centrale.<br/>"
             "— <i>Garantie d'authenticité</i> : assurer l'intégrité des flux d'informations et des processus de commande grâce au dispositif cryptographique DOS DOMIUM.<br/>"
             "— <i>Zéro commission</i> : ne prélever aucun pourcentage sur le montant des ventes de marchandises conclues, l'outil étant financé par le modèle structurel d'abonnement.<br/><br/>"
             "<b>2.2. Engagements de la Centrale d'Achat (KDMARCHE)</b> :<br/>"
             "— <i>Facturation et distribution</i> : acheter les stocks convenus au Fournisseur, opérer la facturation directe aux acheteurs finaux professionnels et superviser la gestion logistique (Incoterms, transport).<br/>"
             "— <i>Application des prix structurels</i> : s'engager à répercuter la politique de mutualisation des coûts pour garantir un tarif compétitif aux acteurs économiques locaux.<br/><br/>"
             "<b>2.3. Engagements du Fournisseur</b> :<br/>"
             "— <i>Qualité et conformité</i> : livrer des produits conformes aux normes réglementaires françaises et européennes en vigueur, dotés d'un historique de traçabilité clair.<br/>"
             "— <i>Disponibilité des stocks</i> : informer en temps réel KDMARCHE de l'état de ses stocks et des capacités de production pour éviter toute rupture sur la marketplace."),
            ("ARTICLE 3 : FLUX FINANCIERS ET LOGISTIQUE",
             "— <b>Achat amont</b> : les conditions tarifaires d'achat des marchandises par KDMARCHE auprès du Fournisseur font l'objet d'une annexe tarifaire révisable annuellement.<br/>"
             "— <b>Paiement</b> : KDMARCHE règle directement le Fournisseur selon les délais légaux applicables au commerce de gros.<br/>"
             "— <b>Logistique</b> : sauf accord écrit contraire, les livraisons s'effectuent sous l'Incoterm DAP au dépôt logistique de KDMARCHE."),
        ],
        "articles_buyer": [
            ("ARTICLE 1 : OBJET DE LA CONVENTION",
             "La présente convention a pour objet de définir les conditions techniques, financières et commerciales de leur collaboration :<br/>"
             "— L'accès de l'Acheteur Professionnel au catalogue de la centrale sur l'espace digital opéré par O'SCOP.<br/>"
             "— Les modalités de vente et de distribution des marchandises par KDMARCHE au profit de l'Acheteur Professionnel.<br/>"
             "— Le respect de la transparence des prix et de la traçabilité."),
            ("ARTICLE 2 : RÔLES ET ENGAGEMENTS DE CHAQUE PARTIE",
             "<b>2.1. Engagements de l'Opérateur Technique (O'SCOP)</b> :<br/>"
             "— <i>Mise à disposition technologique</i> : fournir l'infrastructure technique, sécurisée et le sous-domaine dédié à l'activité de revente de gros de la centrale.<br/>"
             "— <i>Garantie d'authenticité</i> : assurer l'intégrité des flux d'informations et des processus de commande grâce au dispositif cryptographique DOS DOMIUM.<br/>"
             "— <i>Zéro commission</i> : ne prélever aucun pourcentage sur le montant des ventes de marchandises conclues, l'outil étant financé par le modèle structurel d'abonnement.<br/><br/>"
             "<b>2.2. Engagements de la Centrale d'Achat (KDMARCHE)</b> :<br/>"
             "— <i>Facturation et distribution</i> : opérer la facturation directe aux acheteurs professionnels et superviser la gestion logistique (Incoterms, transport).<br/>"
             "— <i>Application des prix structurels</i> : s'engager à répercuter la politique de mutualisation des coûts pour garantir un tarif compétitif aux acteurs économiques locaux.<br/><br/>"
             "<b>2.3. Engagements de l'Acheteur Professionnel</b> :<br/>"
             "— <i>Usage professionnel</i> : acquérir les marchandises pour les besoins de son activité professionnelle, dans le respect des CGV KDMARCHE et des CGU de la plateforme.<br/>"
             "— <i>Exactitude des informations</i> : maintenir à jour ses informations d'identification, de facturation et de livraison."),
            ("ARTICLE 3 : FLUX FINANCIERS ET LOGISTIQUE",
             "— <b>Commandes et paiement</b> : les commandes sont réglées selon les CGV KDMARCHE en vigueur sur la plateforme (moyens de paiement sécurisés intégrés).<br/>"
             "— <b>Logistique</b> : les livraisons s'effectuent selon l'Incoterm et le type de livraison indiqués sur chaque fiche produit du catalogue (EXW, FOB, CIF, DAP ou DDP)."),
        ],
        "tail_articles": [
            ("ARTICLE 4 : DURÉE ET RÉSILIATION",
             "La présente convention est conclue pour une durée déterminée de un (1) an à compter de sa signature. Elle se renouvelle par tacite reconduction pour des périodes de même durée, sauf dénonciation par l'une des Parties par lettre recommandée avec accusé de réception (LRAR) moyennant un préavis de trois (3) mois."),
            ("ARTICLE 5 : LITIGES ET LOI APPLICABLE",
             "La présente convention est régie par le droit français. Tout litige né de l'interprétation, de la validité ou de l'exécution du présent contrat tripartite sera porté devant le Tribunal de Commerce de Pointe-à-Pitre."),
        ],
        "sig_line": "Fait à {lieu}, le {date}. En trois (3) exemplaires originaux.",
        "sig_cols": ("Pour O'SCOP — Signature et cachet", "Pour KDMARCHE — Signature et cachet", "Pour {third} — Signature et cachet"),
        "version_note": "Version française faisant foi — générée le {gen} UTC.",
    },
    "en": {
        "title": "TRIPARTITE ECONOMIC PARTNERSHIP AGREEMENT",
        "subtitle": "Framework for integration and intra-community distribution — French Overseas Territories",
        "parties_title": "BETWEEN THE UNDERSIGNED:",
        "party_oscop": ("<b>OBJECTIF SCOP OUTREMER</b> (trade name: O'SCOP), a SCIC SAS with variable capital, registered with the Pointe-à-Pitre "
                        "Trade and Companies Register under number 903 459 139, whose establishment is located at 13 rue Rodrigue YOUYOUTE, "
                        "97139 Les Abymes, represented by its serving President, (hereinafter the \"Technical Operator\" or \"O'SCOP\");"),
        "party_kdm": ("<b>KDMARCHÉ</b>, trade name of Mrs Félixia Vanessa PIPEROL, sole trader (Entreprise Individuelle), commercial name "
                      "PRIMACOP INTERNATIONAL BUSINESS, SIREN 433 230 703 — SIRET 433 230 703 00020, whose business address is "
                      "Morne Bourg, chemin Symphart Lampecinado, 97170 Petit-Bourg, "
                      "(hereinafter the \"Purchasing Centre\" or \"KDMARCHE\");"),
        "collectively": "Hereinafter collectively referred to as the \"Parties\".",
        "third_vendor": "The Supplier",
        "third_buyer": "The Professional Buyer",
        "preamble_vendor": [
            "O'SCOP operates the CommunityPlace digital marketplace platform, designed to structure, secure and stimulate distribution channels and the social economy in the French Overseas Territories.",
            "KDMARCHE acts on this platform as a wholesale and semi-wholesale distributor supplying businesses in the Overseas Territories at \"mutualized structural prices\".",
            "The Supplier wishes to join this virtuous network to list and sell its goods through the combined logistics and commercial power of KDMARCHE and the digital platform.",
        ],
        "preamble_buyer": [
            "O'SCOP operates the CommunityPlace digital marketplace platform, designed to structure, secure and stimulate distribution channels and the social economy in the French Overseas Territories.",
            "KDMARCHE acts on this platform as a wholesale and semi-wholesale distributor supplying businesses in the Overseas Territories at \"mutualized structural prices\".",
            "The Professional Buyer wishes to join this virtuous network to purchase through the combined logistics and commercial power of KDMARCHE and the digital platform.",
        ],
        "articles_vendor": [
            ("ARTICLE 1: PURPOSE OF THE AGREEMENT",
             "This agreement defines the technical, financial and commercial conditions of their collaboration:<br/>"
             "— Integration of the Supplier's catalogue on the digital space operated by O'SCOP.<br/>"
             "— The terms of purchase, storage and distribution of goods by KDMARCHE.<br/>"
             "— Compliance with price transparency and traceability for the benefit of end buyers."),
            ("ARTICLE 2: ROLES AND COMMITMENTS OF EACH PARTY",
             "<b>2.1. Commitments of the Technical Operator (O'SCOP)</b>:<br/>"
             "— <i>Technological provision</i>: provide the secure technical infrastructure and the sub-domain dedicated to the purchasing centre's wholesale resale activity.<br/>"
             "— <i>Authenticity guarantee</i>: ensure the integrity of information flows and ordering processes through the DOS DOMIUM cryptographic device.<br/>"
             "— <i>Zero commission</i>: levy no percentage on the amount of goods sales concluded, the tool being financed by the structural subscription model.<br/><br/>"
             "<b>2.2. Commitments of the Purchasing Centre (KDMARCHE)</b>:<br/>"
             "— <i>Invoicing and distribution</i>: purchase the agreed stocks from the Supplier, invoice professional end buyers directly and supervise logistics management (Incoterms, transport).<br/>"
             "— <i>Application of structural prices</i>: pass on the cost-mutualization policy to guarantee a competitive tariff to local economic players.<br/><br/>"
             "<b>2.3. Commitments of the Supplier</b>:<br/>"
             "— <i>Quality and compliance</i>: deliver products compliant with applicable French and European regulatory standards, with a clear traceability history.<br/>"
             "— <i>Stock availability</i>: inform KDMARCHE in real time of stock levels and production capacity to avoid any shortage on the marketplace."),
            ("ARTICLE 3: FINANCIAL FLOWS AND LOGISTICS",
             "— <b>Upstream purchase</b>: the pricing conditions for KDMARCHE's purchase of goods from the Supplier are set out in an annually revisable pricing annex.<br/>"
             "— <b>Payment</b>: KDMARCHE pays the Supplier directly within the legal deadlines applicable to wholesale trade.<br/>"
             "— <b>Logistics</b>: unless otherwise agreed in writing, deliveries are made under Incoterm DAP to the KDMARCHE logistics depot."),
        ],
        "articles_buyer": [
            ("ARTICLE 1: PURPOSE OF THE AGREEMENT",
             "This agreement defines the technical, financial and commercial conditions of their collaboration:<br/>"
             "— The Professional Buyer's access to the purchasing centre's catalogue on the digital space operated by O'SCOP.<br/>"
             "— The terms of sale and distribution of goods by KDMARCHE for the benefit of the Professional Buyer.<br/>"
             "— Compliance with price transparency and traceability."),
            ("ARTICLE 2: ROLES AND COMMITMENTS OF EACH PARTY",
             "<b>2.1. Commitments of the Technical Operator (O'SCOP)</b>:<br/>"
             "— <i>Technological provision</i>: provide the secure technical infrastructure and the sub-domain dedicated to the purchasing centre's wholesale resale activity.<br/>"
             "— <i>Authenticity guarantee</i>: ensure the integrity of information flows and ordering processes through the DOS DOMIUM cryptographic device.<br/>"
             "— <i>Zero commission</i>: levy no percentage on the amount of goods sales concluded, the tool being financed by the structural subscription model.<br/><br/>"
             "<b>2.2. Commitments of the Purchasing Centre (KDMARCHE)</b>:<br/>"
             "— <i>Invoicing and distribution</i>: invoice professional buyers directly and supervise logistics management (Incoterms, transport).<br/>"
             "— <i>Application of structural prices</i>: pass on the cost-mutualization policy to guarantee a competitive tariff to local economic players.<br/><br/>"
             "<b>2.3. Commitments of the Professional Buyer</b>:<br/>"
             "— <i>Professional use</i>: purchase goods for the needs of its professional activity, in compliance with the KDMARCHE GCS and the platform's GCU.<br/>"
             "— <i>Accuracy of information</i>: keep its identification, invoicing and delivery information up to date."),
            ("ARTICLE 3: FINANCIAL FLOWS AND LOGISTICS",
             "— <b>Orders and payment</b>: orders are paid in accordance with the KDMARCHE GCS in force on the platform (integrated secure payment methods).<br/>"
             "— <b>Logistics</b>: deliveries are made according to the Incoterm and delivery type shown on each product sheet of the catalogue (EXW, FOB, CIF, DAP or DDP)."),
        ],
        "tail_articles": [
            ("ARTICLE 4: TERM AND TERMINATION",
             "This agreement is concluded for a fixed term of one (1) year from its signature. It is renewed by tacit agreement for periods of the same duration, unless terminated by either Party by registered letter with acknowledgment of receipt (LRAR) subject to three (3) months' notice."),
            ("ARTICLE 5: DISPUTES AND APPLICABLE LAW",
             "This agreement is governed by French law. Any dispute arising from the interpretation, validity or performance of this tripartite contract shall be brought before the Commercial Court of Pointe-à-Pitre."),
        ],
        "sig_line": "Done at {lieu}, on {date}. In three (3) original copies.",
        "sig_cols": ("For O'SCOP — Signature and stamp", "For KDMARCHE — Signature and stamp", "For {third} — Signature and stamp"),
        "version_note": "In case of discrepancy, the French version prevails — generated on {gen} UTC.",
    },
    "es": {
        "title": "CONVENIO TRIPARTITO DE ASOCIACIÓN ECONÓMICA",
        "subtitle": "Marco de integración y distribución intracomunitaria — Ultramar francés",
        "parties_title": "ENTRE LOS ABAJO FIRMANTES:",
        "party_oscop": ("<b>OBJECTIF SCOP OUTREMER</b> (nombre comercial: O'SCOP), SCIC SAS de capital variable, inscrita en el Registro Mercantil de "
                        "Pointe-à-Pitre con el número 903 459 139, cuyo establecimiento se encuentra en 13 rue Rodrigue YOUYOUTE, "
                        "97139 Les Abymes, representada por su Presidente en ejercicio, (en adelante el «Operador Técnico» u «O'SCOP»);"),
        "party_kdm": ("<b>KDMARCHÉ</b>, enseña de la Sra. Félixia Vanessa PIPEROL, empresaria individual (EI), nombre comercial "
                      "PRIMACOP INTERNATIONAL BUSINESS, SIREN 433 230 703 — SIRET 433 230 703 00020, con dirección profesional en "
                      "Morne Bourg, chemin Symphart Lampecinado, 97170 Petit-Bourg, "
                      "(en adelante la «Central de Compras» o «KDMARCHE»);"),
        "collectively": "En adelante denominadas colectivamente «las Partes».",
        "third_vendor": "El Proveedor",
        "third_buyer": "El Comprador Profesional",
        "preamble_vendor": [
            "O'SCOP explota la plataforma numérica Marketplace CommunityPlace, destinada a estructurar, asegurar y dinamizar los circuitos de distribución y la economía social ultramarina.",
            "KDMARCHE interviene en esta plataforma como distribuidor mayorista y semimayorista para abastecer a las empresas de Ultramar a «precios estructurales mutualizados».",
            "El Proveedor desea integrarse en esta red virtuosa para referenciar y vender sus mercancías a través de la potencia logística y comercial combinada de KDMARCHE y de la plataforma numérica.",
        ],
        "preamble_buyer": [
            "O'SCOP explota la plataforma numérica Marketplace CommunityPlace, destinada a estructurar, asegurar y dinamizar los circuitos de distribución y la economía social ultramarina.",
            "KDMARCHE interviene en esta plataforma como distribuidor mayorista y semimayorista para abastecer a las empresas de Ultramar a «precios estructurales mutualizados».",
            "El Comprador Profesional desea integrarse en esta red virtuosa para abastecerse a través de la potencia logística y comercial combinada de KDMARCHE y de la plataforma numérica.",
        ],
        "articles_vendor": [
            ("ARTÍCULO 1: OBJETO DEL CONVENIO",
             "El presente convenio tiene por objeto definir las condiciones técnicas, financieras y comerciales de su colaboración:<br/>"
             "— La integración del catálogo del Proveedor en el espacio digital operado por O'SCOP.<br/>"
             "— Las modalidades de compra, almacenamiento y distribución de las mercancías por KDMARCHE.<br/>"
             "— El respeto de la transparencia de los precios y de la trazabilidad en beneficio de los compradores finales."),
            ("ARTÍCULO 2: FUNCIONES Y COMPROMISOS DE CADA PARTE",
             "<b>2.1. Compromisos del Operador Técnico (O'SCOP)</b>:<br/>"
             "— <i>Puesta a disposición tecnológica</i>: proporcionar la infraestructura técnica, segura y el subdominio dedicado a la actividad de reventa mayorista de la central.<br/>"
             "— <i>Garantía de autenticidad</i>: asegurar la integridad de los flujos de información y de los procesos de pedido gracias al dispositivo criptográfico DOS DOMIUM.<br/>"
             "— <i>Cero comisión</i>: no percibir ningún porcentaje sobre el importe de las ventas de mercancías concluidas, financiándose la herramienta mediante el modelo estructural de suscripción.<br/><br/>"
             "<b>2.2. Compromisos de la Central de Compras (KDMARCHE)</b>:<br/>"
             "— <i>Facturación y distribución</i>: comprar las existencias convenidas al Proveedor, efectuar la facturación directa a los compradores finales profesionales y supervisar la gestión logística (Incoterms, transporte).<br/>"
             "— <i>Aplicación de los precios estructurales</i>: comprometerse a repercutir la política de mutualización de costes para garantizar una tarifa competitiva a los actores económicos locales.<br/><br/>"
             "<b>2.3. Compromisos del Proveedor</b>:<br/>"
             "— <i>Calidad y conformidad</i>: entregar productos conformes a las normas reglamentarias francesas y europeas vigentes, dotados de un historial de trazabilidad claro.<br/>"
             "— <i>Disponibilidad de existencias</i>: informar en tiempo real a KDMARCHE del estado de sus existencias y de las capacidades de producción para evitar cualquier ruptura en el marketplace."),
            ("ARTÍCULO 3: FLUJOS FINANCIEROS Y LOGÍSTICA",
             "— <b>Compra inicial</b>: las condiciones tarifarias de compra de las mercancías por KDMARCHE al Proveedor son objeto de un anexo tarifario revisable anualmente.<br/>"
             "— <b>Pago</b>: KDMARCHE paga directamente al Proveedor según los plazos legales aplicables al comercio mayorista.<br/>"
             "— <b>Logística</b>: salvo acuerdo escrito en contrario, las entregas se efectúan bajo el Incoterm DAP en el depósito logístico de KDMARCHE."),
        ],
        "articles_buyer": [
            ("ARTÍCULO 1: OBJETO DEL CONVENIO",
             "El presente convenio tiene por objeto definir las condiciones técnicas, financieras y comerciales de su colaboración:<br/>"
             "— El acceso del Comprador Profesional al catálogo de la central en el espacio digital operado por O'SCOP.<br/>"
             "— Las modalidades de venta y distribución de las mercancías por KDMARCHE en beneficio del Comprador Profesional.<br/>"
             "— El respeto de la transparencia de los precios y de la trazabilidad."),
            ("ARTÍCULO 2: FUNCIONES Y COMPROMISOS DE CADA PARTE",
             "<b>2.1. Compromisos del Operador Técnico (O'SCOP)</b>:<br/>"
             "— <i>Puesta a disposición tecnológica</i>: proporcionar la infraestructura técnica, segura y el subdominio dedicado a la actividad de reventa mayorista de la central.<br/>"
             "— <i>Garantía de autenticidad</i>: asegurar la integridad de los flujos de información y de los procesos de pedido gracias al dispositivo criptográfico DOS DOMIUM.<br/>"
             "— <i>Cero comisión</i>: no percibir ningún porcentaje sobre el importe de las ventas de mercancías concluidas, financiándose la herramienta mediante el modelo estructural de suscripción.<br/><br/>"
             "<b>2.2. Compromisos de la Central de Compras (KDMARCHE)</b>:<br/>"
             "— <i>Facturación y distribución</i>: efectuar la facturación directa a los compradores profesionales y supervisar la gestión logística (Incoterms, transporte).<br/>"
             "— <i>Aplicación de los precios estructurales</i>: comprometerse a repercutir la política de mutualización de costes para garantizar una tarifa competitiva a los actores económicos locales.<br/><br/>"
             "<b>2.3. Compromisos del Comprador Profesional</b>:<br/>"
             "— <i>Uso profesional</i>: adquirir las mercancías para las necesidades de su actividad profesional, respetando las CGV de KDMARCHE y las CGU de la plataforma.<br/>"
             "— <i>Exactitud de la información</i>: mantener actualizada su información de identificación, facturación y entrega."),
            ("ARTÍCULO 3: FLUJOS FINANCIEROS Y LOGÍSTICA",
             "— <b>Pedidos y pago</b>: los pedidos se abonan según las CGV de KDMARCHE vigentes en la plataforma (medios de pago seguros integrados).<br/>"
             "— <b>Logística</b>: las entregas se efectúan según el Incoterm y el tipo de entrega indicados en cada ficha de producto del catálogo (EXW, FOB, CIF, DAP o DDP)."),
        ],
        "tail_articles": [
            ("ARTÍCULO 4: DURACIÓN Y RESOLUCIÓN",
             "El presente convenio se concluye por un período determinado de un (1) año a partir de su firma. Se renovará por tacita reconducción por períodos de igual duración, salvo denuncia por una de las Partes mediante carta certificada con acuse de recibo (LRAR) con un preaviso de tres (3) meses."),
            ("ARTÍCULO 5: LITIGIOS Y LEY APLICABLE",
             "El presente convenio se rige por el derecho francés. Cualquier litigio derivado de la interpretación, validez o ejecución del presente contrato tripartito se someterá al Tribunal de Comercio de Pointe-à-Pitre."),
        ],
        "sig_line": "Hecho en {lieu}, el {date}. En tres (3) ejemplares originales.",
        "sig_cols": ("Por O'SCOP — Firma y sello", "Por KDMARCHE — Firma y sello", "Por {third} — Firma y sello"),
        "version_note": "En caso de discrepancia, prevalece la versión francesa — generado el {gen} UTC.",
    },
}


def _locale(ob: dict) -> str:
    loc = (ob.get("locale") or "fr")[:2]
    return loc if loc in TEXTS else "fr"


def build_tripartite_pages(ob: dict) -> bytes:
    """Pages du contrat tripartite (langue du membre, bloc tiers rempli dynamiquement)."""
    is_buyer = (ob.get("convention_template") == "v2_0_buyer") or (ob.get("member_type") == "buyer")
    tr = TEXTS[_locale(ob)]
    third = tr["third_buyer"] if is_buyer else tr["third_vendor"]
    conv = ob.get("convention") or {}
    lieu = conv.get("lieu_signature") or "Les Abymes"
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=13 * mm,
                            leftMargin=17 * mm, rightMargin=17 * mm)
    el = [
        Paragraph(tr["title"], _T),
        Paragraph(tr["subtitle"], _T2),
        Paragraph(tr["parties_title"], _H),
        Paragraph(tr["party_oscop"], _B),
        Paragraph(tr["party_kdm"], _B),
        Paragraph(_fill_member_block(ob, third), _B),
        Paragraph(f"<i>{tr['collectively']}</i>", _B),
        Paragraph("PREAMBULE" if _locale(ob) == "fr" else ("PREAMBLE" if _locale(ob) == "en" else "PREÁMBULO"), _H),
    ]
    for p in (tr["preamble_buyer"] if is_buyer else tr["preamble_vendor"]):
        el.append(Paragraph(p, _B))
    for title, body in (tr["articles_buyer"] if is_buyer else tr["articles_vendor"]) + tr["tail_articles"]:
        el.append(Paragraph(title, _H))
        el.append(Paragraph(body, _B))
    el.append(Spacer(1, 8))
    el.append(Paragraph(f"<b>{tr['sig_line'].format(lieu=lieu, date=today)}</b>", _B))
    for col in tr["sig_cols"]:
        el.append(Paragraph(f"• {col.format(third=third)}", _B))
    el.append(Paragraph(tr["version_note"].format(gen=datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')), _META))
    doc.build(el)
    return buf.getvalue()


_CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=7.3, leading=9, textColor=colors.HexColor("#2a2233"))
_CELLB = ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=7.3, leading=9, textColor=VIOLET)

ANNEX_COLUMNS = [
    ("sku_fournisseur", "Texte", "Oui", "Identifiant unique de l'article chez le Fournisseur (sans espace).", "KD-MILK-001"),
    ("code_ean", "Numérique", "Oui", "Code-barres international du produit (13 chiffres).", "3017620422003"),
    ("designation_produit", "Texte", "Oui", "Nom commercial clair de l'article (max. 150 caractères).", "Lait UHT Demi-Écrémé 1L x6"),
    ("categorie", "Texte", "Oui", "Arborescence de la catégorie (séparée par un chevron >).", "Alimentaire > Épicerie"),
    ("description", "Texte", "Non", "Description détaillée ou caractéristiques techniques.", "Lait d'origine France…"),
    ("prix_unitaire_ht", "Décimal", "Oui", "Prix de gros facturé à KDMARCHE. Séparateur décimal : point (.)", "5.45"),
    ("taux_tva", "Décimal", "Oui", "Taux applicable en Guadeloupe (0, 2.1, 8.5).", "2.1"),
    ("quantite_stock", "Entier", "Oui", "Quantité physique disponible immédiatement au dépôt.", "150"),
    ("conditionnement", "Texte", "Oui", "Unité minimale de commande (Palette, Carton, Unité).", "Carton de 6 briques"),
    ("poids_kg", "Décimal", "Non", "Poids brut de l'unité de conditionnement.", "6.20"),
    ("url_image", "Texte (URL)", "Non", "Lien direct vers la photo du produit (format JPG/PNG public).", "https://site.com"),
]


def build_annex_pages() -> bytes:
    """Annexe technique : spécifications des flux d'intégration catalogue (V1.0 — septembre 2026)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=13 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    rows = [[Paragraph(h, _CELLB) for h in ("Colonne", "Type", "Oblig.", "Description / format attendu", "Exemple")]]
    for c in ANNEX_COLUMNS:
        rows.append([Paragraph(str(v), _CELL) for v in c])
    table = Table(rows, colWidths=[33 * mm, 17 * mm, 12 * mm, 76 * mm, 42 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efe6f8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f4fc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    el = [
        Paragraph("ANNEXE TECHNIQUE : SPÉCIFICATIONS DES FLUX D'INTÉGRATION CATALOGUE", _T),
        Paragraph("Version : 1.0 (Septembre 2026) — Rattachée à : la Convention Tripartite de Partenariat Économique", _T2),
        Paragraph("1. Généralités et canaux de transmission", _H),
        Paragraph("Pour assurer l'intégration ou la mise à jour automatique des produits (prix, descriptions, niveaux de stocks) "
                  "sur la plateforme lacentrale.objectifscopoutremer.com, le Fournisseur doit fournir un fichier structuré selon "
                  "l'un des deux formats acceptés :<br/>"
                  "— <b>Format CSV</b> (séparateur : point-virgule « ; », encodage : UTF-8 impératif pour la gestion des accents).<br/>"
                  "— <b>Format Microsoft Excel</b> (extension .xlsx).<br/><br/>"
                  "Le fichier peut être déposé automatiquement par le Fournisseur sur le serveur SFTP sécurisé fourni par O'SCOP, "
                  "ou téléversé manuellement depuis l'espace Fournisseur de la plateforme. La fréquence d'actualisation par défaut "
                  "est fixée à une fois par jour (24 h).", _B),
        Paragraph("2. Structure obligatoire du fichier d'échange", _H),
        Paragraph("Le tableau ci-dessous liste les colonnes (en-têtes) obligatoires que le fichier doit contenir. "
                  "<b>L'ordre des colonnes doit être strictement respecté.</b>", _B),
        table,
        Paragraph("3. Règles de gestion et validation des données", _H),
        Paragraph("— <b>Gestion des stocks à zéro</b> : si un produit affiche 0 dans la colonne quantite_stock, il passera "
                  "automatiquement en statut « Rupture de stock » sur la marketplace sans être supprimé, empêchant les Acheteurs de le commander.<br/>"
                  "— <b>Mise à jour des prix</b> : toute modification de la colonne prix_unitaire_ht est répercutée automatiquement "
                  "sur la marketplace après validation par le système de tarification structurelle mutualisée de KDMARCHE.<br/>"
                  "— <b>Gestion des erreurs</b> : si le fichier comporte des caractères spéciaux corrompus (mauvais encodage) ou s'il "
                  "manque une donnée obligatoire, l'intégration est rejetée. Un e-mail d'erreur automatique contenant le rapport "
                  "d'anomalie est immédiatement envoyé au contact technique du Fournisseur.", _B),
        Paragraph("4. Contacts techniques", _H),
        Paragraph("— Support Plateforme (O'SCOP) : <b>tech@objectifscopoutremer.com</b><br/>"
                  "— Logistique &amp; Validation (KDMARCHE) : <b>data@kdmarche.com</b>", _B),
        Paragraph(f"Annexe générée le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC — version française faisant foi.", _META),
    ]
    doc.build(el)
    return buf.getvalue()
