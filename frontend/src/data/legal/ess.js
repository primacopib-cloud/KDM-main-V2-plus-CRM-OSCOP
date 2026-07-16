export const charteESSContent = {
  id: "charte-ess",
  title: "Charte ESS de Mutualisation",
  subtitle: "Centrale d'achats B2B ESS — Transparence · Non-spéculation · Traçabilité",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CHARTE_ESS_MUT}}",
  entity: "KDMARCHE × O'SCOP",
  accentColor: "#10B981",
  officialClause: `« La mutualisation KDMARCHE – O'SCOP repose sur une logique ESS : accès collectif, règles transparentes, non-spéculation, traçabilité et séparation stricte des flux. Les conditions mutualisées sont financées par l'accès et l'usage, jamais par une commission sur les produits. »`,
  sections: [
    {
      number: "1",
      title: "Objet de la charte",
      content: `La présente charte fixe les principes et règles de mutualisation applicables au dispositif, afin de garantir une organisation non spéculative, équitable, traçable et conforme à l'esprit ESS.`
    },
    {
      number: "2",
      title: "Principes ESS directeurs",
      content: `- **Primauté de l'utilité collective** : continuité d'approvisionnement, accès mutualisé, réduction des surcoûts structurels.
- **Non-spéculation** : aucune rente, aucun objectif d'éviction, aucun détournement des flux mutualisés.
- **Transparence des flux** : marchandises (KDMARCHE) vs accès/usage (O'SCOP) strictement séparés.
- **Équité d'accès** : règles objectives, publiées, identiques à situations équivalentes.
- **Traçabilité** : décisions, droits, consommations et priorités journalisés (audit probant).`
    },
    {
      number: "3",
      title: "Définition de la mutualisation",
      content: `La mutualisation consiste à organiser collectivement l'accès à des conditions économiques B2B (prix, volumes, disponibilités, zones) en supprimant des coûts parasites (intermédiation, retail, fragmentation logistique), sans revente spéculative ni commission de plateforme indexée sur les ventes.

Elle porte sur l'**accès** (abonnement), l'**usage** (crédits), la **priorisation** (règles transparentes) et la structuration des **zones** (Outre-mer / export), et non sur l'appropriation de marges indues.`
    },
    {
      number: "4",
      title: "Règles d'accès au dispositif",
      content: `- **Accès réservé B2B** : seuls professionnels et structures éligibles.
- **Validation préalable** : dossier possible (immatriculation, signataire, conformité).
- **Abonnement actif** : condition d'accès aux conditions mutualisées.
- **Droits par zone** : accès limité aux zones autorisées selon droits souscrits.`
    },
    {
      number: "5",
      title: "Mutualisation des volumes et priorités",
      content: `Les priorités d'accès aux volumes mutualisés sont déterminées par des critères objectifs, notamment :
- statut d'abonnement (Accès / Volume / Impact),
- respect des procédures EXW et engagements d'enlèvement,
- historique de conformité (paiements, litiges, non-enlèvements),
- disponibilités stock par zone.

Ces règles sont documentées, publiées, auditables et appliquées via des contrôles d'accès automatisés (OPA/ABAC).`
    },
    {
      number: "6",
      title: "Politique de prix structurels et information loyale",
      content: `Les conditions mutualisées visent des **prix structurels** résultant de l'organisation (suppression de surcoûts, EXW, B2B). Toute communication doit être loyale, non trompeuse et non assimilable à une promotion artificielle.`
    },
    {
      number: "7",
      title: "Non-spéculation – Interdictions",
      highlight: true,
      content: `Sont strictement interdits :
- revente spéculative ou contournement des règles d'accès,
- prêt/revente d'accès à des tiers non autorisés,
- manipulation d'identités/zones, fraude documentaire,
- tentative d'accès sans abonnement actif,
- toute pratique créant une distorsion contraire à l'esprit ESS.`
    },
    {
      number: "8",
      title: "Crédits : unité de service et équité d'usage",
      content: `Les crédits sont une **unité de service interne** finançant l'usage (priorités, zones, documents, reporting) afin d'éviter que les utilisateurs intensifs ne soient financés par les utilisateurs modestes.

Ils ne constituent pas une monnaie, ne sont pas remboursables, ne sont pas convertibles en espèces et sont consommés selon un barème public et traçable.`
    },
    {
      number: "9",
      title: "Gouvernance, contrôle et audit",
      content: `O'SCOP pilote les règles d'accès et d'usage dans le respect de la présente charte. Les décisions sensibles (validation, suspension, priorités) sont tracées et auditées.`
    },
    {
      number: "10",
      title: "Sanctions – Suspension",
      content: `En cas de manquement : avertissement, suspension temporaire, désactivation de zones, résiliation selon CG applicables. La sanction est proportionnée, motivée et traçable.`
    },
    {
      number: "11",
      title: "Portée et opposabilité",
      content: `La présente charte s'impose à tout utilisateur/adhérent. Elle est annexée aux CG pertinentes, opposable pendant toute la durée d'accès et peut être mise à jour avec versioning et date d'effet.`
    }
  ]
};

// ANNEXE CGV LOGI'SCOP - Transport & Logistique de proximité ESS
export const annexeLogiscopContent = {
  id: "annexe-logiscop",
  title: "ANNEXE CGV — LIVRAISON LOGI'SCOP",
  subtitle: "Transport & logistique de proximité ESS — Outre-mer",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "ANNEXE-LOGISCOP-2026-001",
  entity: "LOGI'SCOP",
  accentColor: "#8B5CF6",
  applicableTo: "Ventes B2B réalisées par KDMARCHE",
  prestataire: "LOGI'SCOP — Établissement de transport ESS",
  officialPhrase: `« La livraison LOGI'SCOP est une prestation de transport distincte, facultative, proposée après mise à disposition EXW locale, et exécutée par un opérateur logistique ESS indépendant. »`,
  sections: [
    {
      number: "1",
      title: "Objet de l'annexe",
      content: `La présente annexe définit les conditions dans lesquelles une **option de livraison LOGI'SCOP** peut être proposée aux clients B2B de KDMARCHE, en complément de la mise à disposition EXW locale, dans le respect des règles de transport, de l'ESS et de la séparation des flux.`
    },
    {
      number: "2",
      title: "Principe général (EXW local comme socle)",
      content: `**2.1.** Sauf souscription expresse à l'option de livraison LOGI'SCOP, les marchandises sont mises à disposition **EXW locale** sur un site LOGI'SCOP.

**2.2.** Le retrait EXW local est **gratuit** (hors frais accessoires éventuels de préparation) et constitue le mode standard.`
    },
    {
      number: "3",
      title: "Option de livraison LOGI'SCOP (facultative)",
      content: `**3.1.** Une option de livraison LOGI'SCOP peut être proposée selon la zone, la nature des produits et les capacités opérationnelles.

**3.2.** Cette option est **facultative**, clairement affichée avant paiement, et acceptée expressément par le client.`
    },
    {
      number: "4",
      title: "Qualité des parties & séparation des flux",
      highlight: true,
      content: `**4.1.** KDMARCHE demeure **vendeur des marchandises** et n'est pas transporteur.

**4.2.** LOGI'SCOP intervient exclusivement comme **prestataire logistique et transporteur**, sans vendre ni encaisser les marchandises.

**4.3.** La prestation de transport est **distincte** de la vente des marchandises et ne constitue ni une commission, ni une intermédiation financière, ni un service O'SCOP.`
    },
    {
      number: "5",
      title: "Modalités de facturation du transport",
      content: `Selon l'organisation retenue par zone, la livraison LOGI'SCOP peut être facturée :

**5.1. Facturation indirecte (refacturation)**
- LOGI'SCOP facture la prestation à KDMARCHE,
- KDMARCHE refacture la prestation au client en tant que frais de transport distincts.

**5.2. Facturation directe**
- LOGI'SCOP facture directement la prestation de transport au client,
- La facture marchandises KDMARCHE reste strictement séparée.

👉 **Dans les deux cas, aucune marge de transport n'est intégrée au prix des marchandises.**`
    },
    {
      number: "6",
      title: "Zones, tournées & délais",
      content: `**6.1.** Les livraisons sont organisées par zone (Outre-mer / local).

**6.2.** LOGI'SCOP peut mettre en place des **tournées mutualisées TPE**, selon un calendrier communiqué.

**6.3.** Les délais sont indicatifs et dépendent :
- des fenêtres de consolidation,
- de la préparation,
- des conditions locales (trafic, météo, accès).`
    },
    {
      number: "7",
      title: "Transfert des risques",
      content: `**7.1.** En cas de **retrait EXW local** : transfert des risques à la mise à disposition.

**7.2.** En cas de **livraison LOGI'SCOP** : transfert des risques à la remise effective au client, matérialisée par un bon de livraison signé et horodaté.`
    },
    {
      number: "8",
      title: "Preuve de livraison & traçabilité",
      content: `**8.1.** Toute livraison LOGI'SCOP donne lieu à :
- un **bon de livraison**,
- une **signature** (manuscrite ou électronique),
- un **horodatage**,
- un **code de vérification** si applicable.

**8.2.** Ces éléments constituent la **preuve probante de livraison**.`
    },
    {
      number: "9",
      title: "Responsabilités",
      content: `**9.1.** LOGI'SCOP est responsable du transport dans les limites de la réglementation applicable au transport de marchandises.

**9.2.** KDMARCHE n'est pas responsable des incidents de transport imputables à LOGI'SCOP.

**9.3.** Le client s'engage à :
- être présent au créneau convenu,
- vérifier la marchandise à la livraison,
- formuler toute réserve immédiatement.`
    },
    {
      number: "10",
      title: "Cas d'impossibilité ou de refus",
      content: `**10.1.** En cas d'impossibilité de livraison (accès, absence, refus), LOGI'SCOP peut :
- reprogrammer une livraison,
- ou remettre la marchandise en EXW local.

**10.2.** Des frais supplémentaires peuvent s'appliquer selon le barème transport.`
    },
    {
      number: "11",
      title: "Conformité ESS & non-requalification",
      highlight: true,
      content: `La présente annexe s'inscrit dans une **logique ESS territoriale** :
- mutualisation des tournées,
- accessibilité pour les TPE,
- réduction de l'empreinte carbone,
- création d'emplois locaux.

**Elle ne constitue ni une activité d'assurance, ni un service de paiement, ni une pratique commerciale trompeuse.**`
    },
    {
      number: "12",
      title: "Acceptation",
      content: `La souscription à l'option de livraison LOGI'SCOP vaut **acceptation pleine et entière** de la présente annexe, qui fait partie intégrante des CGV KDMARCHE.`
    }
  ],
  tarification: {
    title: "Grille tarifaire indicative LOGI'SCOP",
    description: "Tarifs au poids ou au volume (règle du payant pour)",
    zones: [
      { code: "971", name: "Guadeloupe", base: "2,50€", perKg: "0,45€/kg", perM3: "85€/m³" },
      { code: "972", name: "Martinique", base: "2,80€", perKg: "0,50€/kg", perM3: "90€/m³" },
      { code: "973", name: "Guyane", base: "4,50€", perKg: "0,75€/kg", perM3: "150€/m³" },
      { code: "974", name: "La Réunion", base: "3,20€", perKg: "0,55€/kg", perM3: "110€/m³" },
      { code: "976", name: "Mayotte", base: "3,80€", perKg: "0,65€/kg", perM3: "120€/m³" }
    ],
    supplements: [
      { id: "EXPRESS", label: "Express (< 4h)", amount: "+25,00€" },
      { id: "RDV", label: "Sur rendez-vous", amount: "+5,00€" }
    ],
    preparation: [
      { label: "Picking par ligne", amount: "1,50€/ligne" },
      { label: "Packaging colis < 5kg", amount: "2,00€" },
      { label: "Packaging colis 5-20kg", amount: "3,50€" },
      { label: "Packaging colis > 20kg", amount: "5,00€" },
      { label: "Palettisation", amount: "15,00€/palette" },
      { label: "Étiquetage", amount: "0,50€/étiquette" }
    ],
    tvaNote: "TVA DOM applicable (8,5% ou exonération selon zone)"
  }
};

// Contrat de Transport LOGI'SCOP
