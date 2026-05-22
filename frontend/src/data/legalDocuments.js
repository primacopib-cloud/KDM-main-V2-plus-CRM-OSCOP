// Legal Documents Data - CGV KDMARCHE B2B, CG O'SCOP & Convention de partenariat
// Includes consolidated versions with Rémunération clauses
// Template variables are replaced at runtime with actual values

export const legalVariables = {
  // CGV KDMARCHE
  VERSION: "2.0",
  DATE_EFFET: "17 janvier 2026",
  REF_CGV_KDM: "CGV-KDM-2026-002",
  KDM_LEGAL_NAME: "KDMARCHE SAS",
  KDM_FORM: "Société par Actions Simplifiée",
  KDM_CAPITAL: "50 000 €",
  KDM_SIRET: "XXX XXX XXX XXXXX",
  KDM_RCS: "RCS Pointe-à-Pitre",
  KDM_ADDRESS: "387 Rue de l'Industrie, Parc d'Activité de la Jaille, 97122 Baie-Mahault, Guadeloupe",
  KDM_EMAIL: "contact@kdmarche.fr",
  KDM_PHONE: "+590 590 XX XX XX",
  KDM_TVA: "FR XX XXX XXX XXX",
  KDM_REP_NAME: "[Nom du représentant]",
  KDM_REP_TITLE: "Président",
  MOYENS_PAIEMENT: "Virement bancaire, Carte bancaire, Prélèvement SEPA B2B",
  REGLES_POINTS_EXW: "Plateforme logistique de la zone sélectionnée (adresse communiquée lors de la validation de commande)",
  DELAI_RECLAMATION_JOURS: "5",
  DUREE_AVOIR_JOURS: "90",
  FRAIS_RETOUR_CHARGE: "l'Acheteur",
  DROIT_APPLICABLE: "Droit français",
  JURIDICTION_COMPETENTE: "Tribunaux de Pointe-à-Pitre",
  JURIDICTION: "Tribunaux de Pointe-à-Pitre",
  
  // CG O'SCOP
  REF_CG_OSCOP: "CG-OSCOP-2026-002",
  OSCOP_LEGAL_NAME: "OBJECTIF SCOP OUTREMER",
  OSCOP_FORM: "Société Coopérative d'Intérêt Collectif (SCIC)",
  OSCOP_CAPITAL: "Variable",
  OSCOP_SIRET: "XXX XXX XXX XXXXX",
  OSCOP_RCS: "RCS Pointe-à-Pitre",
  OSCOP_ADDRESS: "387 Rue de l'Industrie, Parc d'Activité de la Jaille, 97122 Baie-Mahault, Guadeloupe",
  OSCOP_EMAIL: "contact@oscop.fr",
  OSCOP_PHONE: "+590 590 XX XX XX",
  OSCOP_TVA: "FR XX XXX XXX XXX",
  OSCOP_REP_NAME: "[Nom du représentant]",
  OSCOP_REP_TITLE: "Directeur Général",
  PLAN_ESS_ACCES: "ESS Accès Pro – 49€ HT/mois",
  PLAN_ESS_VOLUME: "ESS Volume – 149€ HT/mois",
  PLAN_ESS_IMPACT: "ESS Impact – 299€ HT/mois",
  POLITIQUE_IMPAYE: "PAST_DUE après 3 jours, GRACE_PERIOD de 7 jours, SUSPENDED après 10 jours",
  CANAL_SUPPORT: "Email, Téléphone, Espace client",
  HORAIRES_SUPPORT: "Lun-Ven 8h-18h (heure locale)",
  PLAFOND_RESPONSABILITE_OSCOP: "le montant total des abonnements payés sur les 12 derniers mois",
  URL_PRIVACY: "/documents/politique-confidentialite",
  
  // Convention de partenariat
  REF_CONVENTION: "CONV-KDM-OSCOP-2026-001",
  DATE_DOCUMENT: "17 janvier 2026",
  DATE_SIGNATURE: "17 janvier 2026",
  LIEU_SIGNATURE: "Baie-Mahault",
  DUREE_MOIS: "36",
  PREAVIS_JOURS: "90",
  
  // Charte ESS de mutualisation
  REF_CHARTE_ESS_MUT: "CHARTE-ESS-MUT-2026-001",
  
  // Contrat de Transport LOGI'SCOP
  REF_CONTRAT_TRANSPORT: "CTR-LSC-2026-001",
  LOGISCOP_LEGAL_NAME: "LOGI'SCOP",
  LOGISCOP_FORM: "Établissement secondaire de la SCIC O'SCOP",
  LOGISCOP_ADDRESS: "387 Rue de l'Industrie, Parc d'Activité de la Jaille, 97122 Baie-Mahault, Guadeloupe",
  LOGISCOP_SIRET: "XXX XXX XXX XXXXX",
  LOGISCOP_TVA: "FR XX XXX XXX XXX",
  LOGISCOP_EMAIL: "logistique@oscop.fr",
  LOGISCOP_PHONE: "+590 590 XX XX XX",
  
  // Facture
  LOGO_SRC: "/kdmarche-logo.svg",
  FACTURE_NUM: "FAC-XXXX-XXXX",
  DATE_FACTURE: "[Date facture]",
  DATE_ECHEANCE: "[Date échéance]",
  DEVISE: "EUR",
  ZONE_CODE: "[Code zone]",
  CLIENT_LEGAL_NAME: "[Raison sociale client]",
  CLIENT_ADDRESS: "[Adresse client]",
  CLIENT_SIRET: "[SIRET client]",
  CLIENT_TVA: "[N° TVA client]",
  CLIENT_CONTACT: "[Contact client]",
  COMMANDE_REF: "[Réf commande]",
  POINT_EXW_ADRESSE: "[Adresse point EXW]",
  CRENEAU_EXW: "[Créneau enlèvement]",
  PICKUP_REF: "[Réf enlèvement]",
  IBAN: "FR76 XXXX XXXX XXXX XXXX XXXX XXX",
  BIC: "XXXXFRPP",
  TVA_TAUX: "20",
};

// CGV KDMARCHE B2B Content (Version consolidée avec clause rémunération)
export const cgvKdmarcheContent = {
  id: "cgv-kdmarche",
  title: "CGV KDMARCHE B2B",
  subtitle: "Marchandises – EXW – Version consolidée avec clause rémunération",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CGV_KDM}}",
  entity: "KDMARCHE",
  accentColor: "#D9B35A",
  sections: [
    {
      number: "1",
      title: "Champ d'application",
      content: `Les présentes CGV s'appliquent aux ventes de marchandises réalisées par KDMARCHE auprès de clients professionnels disposant d'un accès B2B valide.`
    },
    {
      number: "2",
      title: "Accès B2B et zones",
      content: `Les prix et disponibilités sont déterminés par zone. L'accès à certaines zones peut être conditionné (validation, abonnement actif et droits par zone selon le dispositif).`
    },
    {
      number: "3",
      title: "Prix",
      content: `Les prix sont exprimés HT, déterminés par zone, et peuvent varier selon la disponibilité et la logistique. Les prix dits "jusqu'à –50%" sont des prix structurels B2B issus de l'organisation et non des promotions artificielles.`
    },
    {
      number: "4",
      title: "Commande",
      content: `- Commande via espace B2B ; quantités souvent vendues en lots/palettes selon produits.
- Validation sous réserve de disponibilité stock et respect des règles de zone.`
    },
    {
      number: "5",
      title: "Incoterm EXW (enlèvement)",
      content: `Lorsque EXW s'applique, l'acheteur organise l'enlèvement à l'adresse EXW de la zone, selon les créneaux et modalités communiqués. Les risques sont transférés conformément aux règles EXW.`
    },
    {
      number: "6",
      title: "Facturation et paiement",
      content: `KDMARCHE émet la facture des marchandises. Le paiement est effectué directement à KDMARCHE selon les moyens proposés. Aucun paiement marchandises n'est encaissé par O'SCOP.`
    },
    {
      number: "6 bis",
      title: "Rémunération de KDMARCHE (CLAUSE INTÉGRÉE)",
      highlight: true,
      content: `**KDMARCHE se rémunère exclusivement par la marge commerciale intégrée au prix de vente des marchandises qu'elle vend en qualité de vendeur B2B, conformément aux présentes CGV.**

Cette marge correspond à la différence entre le coût d'acquisition des marchandises (incluant, le cas échéant, les frais logistiques amont, taxes et charges applicables) et le prix de vente facturé à l'acheteur.

**KDMARCHE ne perçoit aucune commission, aucun abonnement, aucun crédit, aucun droit d'accès, ni aucune rémunération liée aux services d'accès, de mutualisation ou d'ingénierie fournis par O'SCOP.**

La rémunération de KDMARCHE n'est ni indexée sur les abonnements O'SCOP, ni sur les crédits O'SCOP, ni sur le volume ou la valeur des services fournis par O'SCOP.

Il n'existe **aucune subvention croisée** entre KDMARCHE et O'SCOP, ni aucun mécanisme de compensation financière visant à financer une réduction de prix des marchandises.`
    },
    {
      number: "7",
      title: "Retours / Avoirs / Remboursements (B2B)",
      content: `Les retours sont encadrés B2B : conditions, délais, état produit, preuve d'achat, et conditions particulières liées aux DLC. KDMARCHE peut proposer un avoir ou un remboursement selon la politique applicable.`
    },
    {
      number: "8",
      title: "Responsabilité",
      content: `La responsabilité de KDMARCHE est limitée aux obligations résultant de la vente de marchandises, dans la limite autorisée par la loi.`
    },
    {
      number: "9",
      title: "Droit applicable",
      content: `- **Droit applicable** : {{DROIT_APPLICABLE}}.
- **Juridiction compétente** : {{JURIDICTION}}.`
    }
  ]
};

// CG O'SCOP Content
export const cgOscopContent = {
  id: "cg-oscop",
  title: "CG O'SCOP",
  subtitle: "Accès – Abonnements – Wallet Crédits (B2B)",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CG_OSCOP}}",
  entity: "O'SCOP",
  accentColor: "#57D19A",
  sections: [
    {
      number: "1",
      title: "Identification de l'Opérateur",
      content: `**O'SCOP** (ci-après « O'SCOP »)

- **Dénomination** : {{OSCOP_LEGAL_NAME}}
- **Forme** : {{OSCOP_FORM}} — **Capital** : {{OSCOP_CAPITAL}}
- **SIREN/SIRET** : {{OSCOP_SIRET}} — **RCS** : {{OSCOP_RCS}}
- **Siège** : {{OSCOP_ADDRESS}}
- **Email** : {{OSCOP_EMAIL}} — **Téléphone** : {{OSCOP_PHONE}}
- **TVA intracom** : {{OSCOP_TVA}}`
    },
    {
      number: "2",
      title: "Objet – Nature des services (clause essentielle)",
      content: `**2.1.** Les présentes conditions générales (« CG ») régissent l'accès et l'usage des services O'SCOP :
- validation B2B, gestion d'accès, abonnements, wallet crédits, droits par zones, services ESS associés.

**2.2.** O'SCOP ne vend aucune marchandise, ne facture aucun produit, et n'encaisse aucun paiement relatif aux marchandises.

**2.3.** Les ventes de marchandises sont conclues directement entre l'Acheteur et KDMARCHE, selon les CGV KDMARCHE B2B.`
    },
    {
      number: "3",
      title: "Définitions",
      content: `- **Compte Entreprise / Organisation (Org)** : entité cliente disposant d'un identifiant d'organisation.
- **Utilisateur** : personne physique rattachée à une Organisation.
- **Abonnement** : redevance d'accès aux services O'SCOP.
- **Crédits** : unité de service interne permettant de financer l'usage (priorités, zones, documents, reporting).
- **Zone** : périmètre géographique ouvrant des droits d'accès spécifiques.`
    },
    {
      number: "4",
      title: "Éligibilité B2B – Dossier – Validation",
      content: `**4.1.** Les services sont réservés aux Organisations exerçant une activité professionnelle.

**4.2.** O'SCOP peut exiger un dossier de validation comprenant notamment : immatriculation, identité du signataire, justificatifs de conformité.

**4.3.** O'SCOP peut refuser une demande pour dossier incomplet, incohérent, risque de fraude, ou incompatibilité avec les règles d'accès/ESS.

**4.4.** Les décisions de validation/refus peuvent être tracées (audit), horodatées et motivées.`
    },
    {
      number: "5",
      title: "Création de compte – Rôles – Responsabilités",
      content: `**5.1.** L'Organisation désigne un Administrateur (OWNER) responsable des habilitations internes.

**5.2.** O'SCOP propose des rôles (ex. OWNER/BUYER/VIEWER) et des contrôles d'accès par états (APPROVED/ACTIVE, zones autorisées).

**5.3.** L'Organisation est responsable des identifiants, de la sécurité interne et des usages effectués via son compte.`
    },
    {
      number: "6",
      title: "Abonnements – Plans – Facturation",
      content: `**6.1.** L'accès à la centrale est conditionné à un abonnement actif, selon les plans suivants :
- {{PLAN_ESS_ACCES}}
- {{PLAN_ESS_VOLUME}}
- {{PLAN_ESS_IMPACT}}

**6.2.** Paiement : à l'avance, par mensualité (sauf stipulation contraire).

**6.3.** Renouvellement : tacite reconduction jusqu'à résiliation.

**6.4.** Factures : émises par O'SCOP, distinctes des factures de marchandises KDMARCHE.`
    },
    {
      number: "7",
      title: "Impayés – Suspension automatique – Réactivation",
      content: `**7.1.** En cas d'échec de paiement : passage en état PAST_DUE puis GRACE_PERIOD selon politique ({{POLITIQUE_IMPAYE}}).

**7.2.** O'SCOP suspend automatiquement les droits d'accès (zones, prix visibles, commandes possibles) et peut déclencher la désactivation partenaire.

**7.3.** Réactivation : à régularisation intégrale et levée éventuelle des mesures de conformité.`
    },
    {
      number: "8",
      title: "Wallet Crédits – Définition juridique et règles d'usage (clause sensible)",
      content: `**8.1.** Les crédits constituent une unité de service interne permettant de financer l'usage des fonctionnalités O'SCOP.

**8.2.** Les crédits :
- ne constituent pas une monnaie,
- ne sont pas remboursables,
- ne sont pas convertibles en espèces,
- ne sont pas un instrument de paiement,
- ne produisent aucun intérêt.

**8.3.** Les crédits sont consommés selon un barème publié (ex : activation zone, accès priorité, génération documents, reporting).

**8.4.** Les crédits peuvent être achetés sous forme de packs (facture distincte « crédits »).

**8.5.** O'SCOP peut refuser une consommation en cas d'insuffisance de solde, compte suspendu, ou fraude suspectée.`
    },
    {
      number: "9",
      title: "Zones – Droits – Conditions EXW (articulation avec KDMARCHE)",
      content: `**9.1.** L'accès à certaines zones peut être inclus dans le plan ou proposé en option payante.

**9.2.** Les règles d'accès par zone et les modalités logistiques (dont EXW-only) sont appliquées côté partenaire.

**9.3.** O'SCOP ne garantit pas la disponibilité des produits, stocks, ni délais d'exécution du partenaire.`
    },
    {
      number: "10",
      title: "Support – Disponibilité – Maintenance",
      content: `**10.1.** O'SCOP fournit un support selon {{CANAL_SUPPORT}} et horaires {{HORAIRES_SUPPORT}}.

**10.2.** O'SCOP peut interrompre temporairement les services pour maintenance, sécurité ou amélioration.`
    },
    {
      number: "11",
      title: "Conformité – Audit – Prévention de requalification",
      content: `**11.1.** O'SCOP ne fournit aucune assurance, ne mutualise aucun risque et n'indemnise aucun sinistre dans le cadre de la centrale d'achats.

**11.2.** O'SCOP ne manipule pas de fonds pour compte de tiers concernant les marchandises.

**11.3.** O'SCOP conserve des journaux probants (audit) des actions sensibles : validations, états d'abonnement, provisioning partenaire, consommations de crédits.`
    },
    {
      number: "12",
      title: "Résiliation",
      content: `**12.1.** L'Organisation peut résilier selon les modalités indiquées dans l'espace compte (effet à fin de période ou immédiat selon option).

**12.2.** O'SCOP peut résilier/suspendre pour manquements graves : fraude, contournement, non-paiement prolongé, atteinte à l'intégrité du dispositif.`
    },
    {
      number: "13",
      title: "Responsabilité – Limites",
      content: `**13.1.** O'SCOP n'est pas partie aux ventes de marchandises et n'assume pas les obligations vendeur (conformité produit, livraison, retours).

**13.2.** O'SCOP est tenu à une obligation de moyens sur ses services, dans les limites légales.

**13.3.** Exclusion des dommages indirects ; plafonnement éventuel : {{PLAFOND_RESPONSABILITE_OSCOP}} (sauf faute lourde/dol).`
    },
    {
      number: "14",
      title: "Données – Confidentialité – RGPD",
      content: `**14.1.** Les données sont traitées pour l'exécution des services, la sécurité, la conformité et les obligations légales.

**14.2.** O'SCOP met en œuvre des mesures de sécurité et de contrôle d'accès.

**14.3.** Une politique de confidentialité détaillée est accessible : {{URL_PRIVACY}}.`
    },
    {
      number: "15",
      title: "Droit applicable – Litiges",
      content: `- **Droit applicable** : {{DROIT_APPLICABLE}}.
- **Tribunal compétent** : {{JURIDICTION_COMPETENTE}} (entre professionnels).`
    }
  ]
};

// Convention de partenariat KDMARCHE-O'SCOP (Version consolidée avec clause rémunération)
export const conventionContent = {
  id: "convention",
  title: "Convention de partenariat KDMARCHE – O'SCOP",
  subtitle: "Centrale d'achats B2B ESS — Séparation stricte des rôles, flux et rémunérations",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CONVENTION}}",
  entity: "KDMARCHE × O'SCOP",
  accentColor: "#8B5CF6",
  parties: {
    kdmarche: {
      name: "{{KDM_LEGAL_NAME}}",
      form: "{{KDM_FORM}}",
      siret: "{{KDM_SIRET}}",
      address: "{{KDM_ADDRESS}}",
      rep_name: "{{KDM_REP_NAME}}",
      rep_title: "{{KDM_REP_TITLE}}"
    },
    oscop: {
      name: "{{OSCOP_LEGAL_NAME}}",
      form: "{{OSCOP_FORM}}",
      siret: "{{OSCOP_SIRET}}",
      address: "{{OSCOP_ADDRESS}}",
      rep_name: "{{OSCOP_REP_NAME}}",
      rep_title: "{{OSCOP_REP_TITLE}}"
    }
  },
  sections: [
    {
      number: "1",
      title: "Objet",
      content: `La présente convention a pour objet de définir les conditions dans lesquelles les Parties coopèrent afin d'opérer une **centrale d'achats B2B à vocation ESS**, reposant sur une **séparation stricte** des rôles, des flux financiers et des responsabilités.`
    },
    {
      number: "2",
      title: "Répartition des rôles (CLAUSE CARDINALE)",
      content: `**2.1 Rôle de KDMARCHE.** KDMARCHE agit exclusivement en qualité de vendeur B2B de marchandises. À ce titre, KDMARCHE est notamment responsable :
- du catalogue produits, des stocks par zones, des prix produits et promotions (si applicables) ;
- de la facturation des marchandises, de la TVA et de la conformité produit ;
- des conditions de vente et d'exécution des commandes (incluant l'Incoterm EXW lorsque requis).

**2.2 Rôle d'O'SCOP.** O'SCOP agit exclusivement comme centrale coopérative d'ingénierie ESS et gestionnaire d'accès (abonnements, crédits, droits, mutualisation). **O'SCOP ne vend aucune marchandise, ne facture aucun produit, et ne perçoit aucun paiement relatif aux marchandises.**`
    },
    {
      number: "3",
      title: "Séparation des flux financiers",
      content: `Les flux financiers sont strictement séparés :
— Abonnements, crédits, services : facturés et encaissés exclusivement par **O'SCOP** ;
— Marchandises : facturées et encaissées exclusivement par **KDMARCHE**.

Aucune commission, rétrocession ou rémunération indexée sur le prix ou le volume des marchandises n'est due entre les Parties, sauf stipulation expresse et distincte validée par écrit, compatible ESS et sans indexation aux ventes.`
    },
    {
      number: "4",
      title: "Rémunération des Parties (CLAUSE INTÉGRÉE)",
      highlight: true,
      content: `**KDMARCHE se rémunère exclusivement par la marge commerciale intégrée au prix de vente des marchandises qu'elle commercialise en qualité de vendeur B2B.**

**O'SCOP se rémunère exclusivement par les abonnements, crédits et services d'accès qu'elle fournit**, sans perception d'aucune commission sur les ventes de marchandises réalisées par KDMARCHE.

Les Parties reconnaissent expressément qu'il n'existe :
— aucune commission d'apport d'affaires,
— aucune rétrocession,
— aucune rémunération croisée,
— aucune indexation de rémunération sur les ventes ou volumes de marchandises.

**Les flux économiques des Parties sont juridiquement, comptablement et opérationnellement indépendants.**`
    },
    {
      number: "5",
      title: "Accès à la centrale",
      content: `L'accès aux conditions économiques mutualisées est strictement réservé aux entreprises :
(i) validées par O'SCOP, (ii) disposant d'un abonnement O'SCOP actif, (iii) respectant les règles d'accès par zone.

Les règles techniques d'accès (permissions, états, zones, incoterms) sont appliquées par des politiques de contrôle d'accès (OPA/ABAC) et des journaux probants (audit).`
    },
    {
      number: "6",
      title: "Conformité & non-requalification",
      content: `Les Parties déclarent que le partenariat ne constitue ni une activité d'assurance, ni une activité d'intermédiation financière, ni une activité de services de paiement, ni un courtage. Les prix dits "jusqu'à –50%" sont des prix structurels résultant de l'organisation (mutualisation, suppression d'intermédiaires, EXW), et ne constituent pas des promotions artificielles.`
    },
    {
      number: "7",
      title: "Durée – Résiliation",
      content: `La présente convention est conclue pour une durée de **{{DUREE_MOIS}}** mois à compter du {{DATE_EFFET}}, renouvelable par tacite reconduction, sauf dénonciation par l'une des Parties avec un préavis de {{PREAVIS_JOURS}} jours.`
    },
    {
      number: "8",
      title: "Confidentialité – Données",
      content: `Chaque Partie s'engage à préserver la confidentialité des informations non publiques reçues. Les données clients sont traitées conformément au RGPD et aux finalités strictement nécessaires à l'exécution du partenariat.`
    },
    {
      number: "9",
      title: "Droit applicable – Litiges",
      content: `- **Droit applicable** : {{DROIT_APPLICABLE}}.
En cas de litige, les Parties recherchent une solution amiable avant toute action contentieuse.
- **Juridiction compétente** : {{JURIDICTION}}.`
    }
  ]
};

// Tableau de lecture rapide (commissaire aux comptes / contrôle)
export const auditComplianceTable = {
  title: "Tableau de lecture rapide (Audit / Contrôle)",
  headers: ["Élément analysé", "KDMARCHE", "O'SCOP"],
  rows: [
    { element: "Encaissement marchandises", kdmarche: true, oscop: false },
    { element: "Marge commerciale", kdmarche: true, oscop: false },
    { element: "Abonnements", kdmarche: false, oscop: true },
    { element: "Crédits / wallet", kdmarche: false, oscop: true },
    { element: "Commission croisée", kdmarche: false, oscop: false },
    { element: "Subvention interne", kdmarche: false, oscop: false }
  ],
  officialPhrase: `« KDMARCHE est rémunérée exclusivement par sa marge commerciale sur les marchandises qu'elle vend en B2B.
O'SCOP est rémunérée exclusivement par les abonnements et crédits d'accès à la plateforme.
Les flux sont indépendants, non indexés et non subventionnés. »`
};

// Invoice template configuration
export const invoiceTemplate = {
  id: "facture",
  title: "Facture KDMARCHE B2B",
  subtitle: "Marchandises — EXW — Premium Or & Violet",
  fields: {
    header: [
      { key: "FACTURE_NUM", label: "N° Facture" },
      { key: "DATE_FACTURE", label: "Date" },
      { key: "DATE_ECHEANCE", label: "Échéance" },
      { key: "DEVISE", label: "Devise" },
      { key: "ZONE_CODE", label: "Zone" }
    ],
    vendor: [
      { key: "KDM_LEGAL_NAME", label: "Raison sociale" },
      { key: "KDM_FORM", label: "Forme juridique" },
      { key: "KDM_ADDRESS", label: "Adresse" },
      { key: "KDM_SIRET", label: "SIRET" },
      { key: "KDM_TVA", label: "N° TVA" },
      { key: "KDM_EMAIL", label: "Email" },
      { key: "KDM_PHONE", label: "Téléphone" }
    ],
    client: [
      { key: "CLIENT_LEGAL_NAME", label: "Raison sociale" },
      { key: "CLIENT_ADDRESS", label: "Adresse" },
      { key: "CLIENT_SIRET", label: "SIRET" },
      { key: "CLIENT_TVA", label: "N° TVA" },
      { key: "CLIENT_CONTACT", label: "Contact" }
    ],
    order: [
      { key: "COMMANDE_REF", label: "Réf. Commande" },
      { key: "POINT_EXW_ADRESSE", label: "Point EXW" },
      { key: "CRENEAU_EXW", label: "Créneau enlèvement" },
      { key: "PICKUP_REF", label: "Réf. enlèvement" }
    ],
    payment: [
      { key: "IBAN", label: "IBAN" },
      { key: "BIC", label: "BIC" }
    ]
  },
  productColumns: ["Désignation", "Lot/Palette", "Qté", "PU HT", "Total HT"],
  feesTypes: [
    { id: "preparation", label: "Frais de préparation de commande EXW", description: "Pick & pack / palettisation" },
    { id: "manutention", label: "Frais de manutention EXW", description: "Chargement quai" },
    { id: "stockage", label: "Frais de stockage exceptionnel", description: "Non-enlèvement > X jours" }
  ],
  compliance_note: "Les frais accessoires sont liés à l'exécution de la vente B2B (EXW) et sont prévus aux CGV KDMARCHE. Aucun abonnement, crédit ou service O'SCOP n'est facturé sur ce document.",
  footer_note: "KDMARCHE — Facture B2B (EXW). Flux marchandises uniquement. Services d'accès (abonnements/crédits) : facturation séparée par O'SCOP."
};

// Charte ESS de mutualisation
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
export const contratTransportLogiscopContent = {
  id: "contrat-transport",
  title: "CONTRAT DE TRANSPORT DE MARCHANDISES",
  subtitle: "Livraison LOGI'SCOP — B2B Outre-mer",
  version: "1.0",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CONTRAT_TRANSPORT}}",
  entity: "LOGI'SCOP",
  accentColor: "#8B5CF6",
  disclaimer: "La livraison LOGI'SCOP est une prestation de transport indépendante, distincte de la vente des marchandises, exécutée par un opérateur logistique ESS.",
  sections: [
    {
      number: "1",
      title: "Objet",
      content: `Le présent contrat définit les conditions dans lesquelles LOGI'SCOP assure, à la demande du Client, une prestation de transport de marchandises depuis un **point EXW local LOGI'SCOP** jusqu'au lieu de livraison indiqué.

Ce contrat est **distinct** de toute vente de marchandises réalisée par un tiers (notamment KDMARCHE).`
    },
    {
      number: "2",
      title: "Nature juridique de la prestation",
      highlight: true,
      content: `- LOGI'SCOP agit exclusivement en qualité de **transporteur/logisticien**.
- LOGI'SCOP **ne vend pas**, **n'achète pas** et **n'encaisse pas** le prix des marchandises.
- Le contrat ne constitue ni mandat de vente, ni commission commerciale, ni intermédiation financière, ni assurance.
- La prestation est réalisée dans le respect de la réglementation applicable au transport routier de marchandises.`
    },
    {
      number: "3",
      title: "Conditions de souscription",
      content: `La livraison LOGI'SCOP est une **option facultative**, proposée après la mise à disposition EXW locale.

Le Client souscrit la prestation :
- soit directement auprès du Transporteur,
- soit via l'interface de commande KDMARCHE, lorsque la refacturation est autorisée.

La souscription vaut acceptation pleine et entière du présent contrat.`
    },
    {
      number: "4",
      title: "Périmètre de la prestation",
      content: `La prestation comprend, selon la zone et l'option souscrite :
- enlèvement des marchandises au point EXW LOGI'SCOP,
- chargement du véhicule,
- transport jusqu'à l'adresse du Client,
- déchargement standard,
- remise de la marchandise contre preuve de livraison.

**Exclusions** (sauf stipulation expresse) :
- montage, installation, manutention spéciale,
- livraison en étage sans ascenseur,
- formalités douanières,
- assurance ad valorem spécifique.`
    },
    {
      number: "5",
      title: "Zones, tournées et délais",
      content: `Les livraisons sont organisées par zone géographique. LOGI'SCOP peut mettre en place des **tournées mutualisées** (logique ESS) afin d'optimiser les coûts et l'empreinte carbone.

Les délais communiqués sont indicatifs et peuvent dépendre :
- de la consolidation,
- des contraintes locales,
- des conditions de circulation et météorologiques.`
    },
    {
      number: "6",
      title: "Tarifs et facturation",
      content: `Les tarifs sont communiqués avant la confirmation de la livraison.

La facturation est émise :
- soit directement par LOGI'SCOP au Client,
- soit par refacturation via KDMARCHE lorsque prévu contractuellement.

**Les frais de transport sont distincts du prix des marchandises.**`
    },
    {
      number: "7",
      title: "Transfert des risques",
      content: `Le transport débute après la prise en charge des marchandises au point EXW locale LOGI'SCOP.

LOGI'SCOP assume la responsabilité des marchandises pendant le transport, dans les limites prévues à l'article 9.

Le transfert des risques intervient à la remise effective au Client, matérialisée par une **preuve de livraison**.`
    },
    {
      number: "8",
      title: "Obligations du Client",
      content: `Le Client s'engage à :
- fournir une adresse exacte et accessible,
- être présent ou représenté au créneau convenu,
- vérifier l'état des marchandises à la livraison,
- formuler toute réserve immédiatement et par écrit sur le bon de livraison.`
    },
    {
      number: "9",
      title: "Responsabilité du Transporteur",
      content: `La responsabilité de LOGI'SCOP est limitée conformément à la réglementation applicable au transport de marchandises (plafonds légaux par kilogramme ou par envoi).

LOGI'SCOP n'est pas responsable :
- des vices propres de la marchandise,
- des emballages fournis par des tiers,
- des dommages indirects (perte d'exploitation, manque à gagner).`
    },
    {
      number: "10",
      title: "Assurances",
      content: `LOGI'SCOP déclare être titulaire d'une **assurance responsabilité civile transporteur** couvrant les dommages aux marchandises transportées.

Une attestation d'assurance est tenue à disposition du Client sur demande.`
    },
    {
      number: "11",
      title: "Impossibilité de livraison",
      content: `En cas d'absence du Client, d'adresse inaccessible ou de refus de livraison :
- la livraison peut être reprogrammée,
- des frais supplémentaires peuvent être facturés,
- ou la marchandise peut être remise à disposition EXW locale.`
    },
    {
      number: "12",
      title: "Force majeure",
      content: `Aucune Partie ne pourra être tenue responsable d'un manquement résultant d'un événement de force majeure tel que défini par la jurisprudence française.`
    },
    {
      number: "13",
      title: "Données & confidentialité",
      content: `Les données personnelles sont traitées exclusivement pour l'exécution de la prestation, conformément au RGPD.

Les informations commerciales et logistiques sont confidentielles.`
    },
    {
      number: "14",
      title: "Durée",
      content: `Le présent contrat s'applique pour chaque prestation de transport souscrite et prend fin à l'issue de la livraison ou de la remise EXW locale.`
    },
    {
      number: "15",
      title: "Droit applicable & litiges",
      content: `- **Droit applicable** : {{DROIT_APPLICABLE}}.
- **Juridiction compétente** : {{JURIDICTION}} (après tentative de résolution amiable).`
    },
    {
      number: "16",
      title: "Acceptation & signature",
      highlight: true,
      content: `La souscription à une livraison LOGI'SCOP vaut **acceptation contractuelle** du présent contrat.

Le Client reconnaît avoir lu et accepté les conditions du présent contrat. Les preuves de signature (certificat, horodatage, empreinte) sont conservées à des fins probantes.`
    }
  ],
  parties: {
    transporteur: {
      name: "LOGI'SCOP",
      form: "Établissement secondaire de la SCIC O'SCOP",
      role: "Opérateur logistique et transporteur",
      address: "{{LOGISCOP_ADDRESS}}",
      siret: "{{LOGISCOP_SIRET}}",
      email: "logistique@oscop.fr"
    },
    client: {
      name: "{{CLIENT_LEGAL_NAME}}",
      role: "Client final B2B",
      address: "{{CLIENT_ADDRESS}}",
      siret: "{{CLIENT_SIRET}}"
    }
  }
};

// Annexe Tournées Mutualisées ESS
export const annexeTourneesESSContent = {
  id: "annexe-tournees-ess",
  title: "ANNEXE — MODE « TOURNÉES MUTUALISÉES ESS »",
  subtitle: "Tournées planifiées, mutualisation des coûts, règles équitables, traçabilité probante",
  version: "1.0",
  dateEffet: "{{DATE_EFFET}}",
  reference: "ANNEXE-ESS-ROUTE-2026-001",
  entity: "LOGI'SCOP",
  accentColor: "#10B981",
  officialClause: `« La livraison en Tournées ESS est une tournée mutualisée planifiée, destinée à réduire les coûts et l'empreinte carbone. Elle implique une fenêtre de livraison et des règles d'accès équitables et traçables. »`,
  sections: [
    {
      number: "1",
      title: "Objet de l'annexe",
      content: `La présente annexe fixe les conditions particulières applicables lorsque le Client souscrit à un mode de livraison en **tournées mutualisées ESS** (« Tournées ESS »), organisé par LOGI'SCOP dans une logique d'intérêt collectif, de réduction des coûts et d'optimisation environnementale.`
    },
    {
      number: "2",
      title: "Définition des Tournées ESS",
      content: `Une Tournée ESS est une tournée planifiée regroupant plusieurs livraisons B2B sur une zone afin de :
- **Mutualiser** les kilomètres et la capacité véhicule
- **Réduire** le coût unitaire de livraison
- **Diminuer** l'empreinte carbone
- **Garantir** un service accessible aux TPE

Cette tournée est une **prestation de transport distincte** de la vente de marchandises.`
    },
    {
      number: "3",
      title: "Conditions d'éligibilité",
      content: `Sont éligibles les clients situés dans les secteurs couverts par la tournée. Les critères de participation peuvent varier selon :
- La densité de livraisons
- La saisonnalité
- Les contraintes opérationnelles de la zone`
    },
    {
      number: "4",
      title: "Planification / créneaux / fenêtres",
      content: `- LOGI'SCOP communique un **calendrier indicatif** (jours et fenêtres horaires)
- Le Client accepte une **fenêtre de livraison** (ex. 09:00–13:00) et non une heure fixe, sauf option spéciale
- Des **cut-off** (fenêtres de consolidation) peuvent s'appliquer : après cut-off, report à la tournée suivante`
    },
    {
      number: "5",
      title: "Tarification ESS (transparence & non-spéculation)",
      highlight: true,
      content: `La tarification Tournées ESS est déterminée par :
- Une **part fixe mutualisée**
- Le cas échéant, une **part variable** (poids/volume/cartons)

Elle est **affichée avant confirmation**, n'est pas indexée sur le montant de marchandises achetées et exclut toute logique spéculative.`
    },
    {
      number: "6",
      title: "Engagements du client",
      content: `- Être **disponible** sur la fenêtre annoncée
- Fournir un **accès de livraison praticable** et un point de dépôt accessible
- **Vérifier la marchandise** immédiatement à la remise et formuler toute réserve sur le POD
- Limiter les modifications tardives hors-process`
    },
    {
      number: "7",
      title: "Absence / refus / impossibilité",
      content: `En cas d'absence, d'adresse erronée ou d'accès impossible :
- La livraison peut être **reprogrammée**
- Des **frais** peuvent s'appliquer selon barème public
- La marchandise peut être remise à disposition **EXW local**`
    },
    {
      number: "8",
      title: "Priorisation équitable (règle ESS)",
      highlight: true,
      content: `En cas de saturation, LOGI'SCOP applique une priorisation **objective et transparente** basée sur :
- Respect des créneaux
- Historique d'absences
- Stabilité du client
- Critères territoriaux publiés le cas échéant

Toute priorisation est **traçable** (log interne audit).`
    },
    {
      number: "9",
      title: "Preuve de livraison (POD) obligatoire",
      content: `Chaque livraison ESS génère un POD probant comprenant :
- **Signature destinataire** + horodatage
- **Code de vérification** + référence tournée (TourID)
- **Réserves** consignées immédiatement si casse/manquant`
    },
    {
      number: "10",
      title: "Responsabilité & assurance",
      content: `La responsabilité pendant le transport suit la réglementation applicable au transport de marchandises. Les limitations et exclusions prévues au contrat principal s'appliquent.`
    },
    {
      number: "11",
      title: "Durée & acceptation",
      content: `La souscription au mode Tournées ESS vaut **acceptation de la présente annexe**. Elle s'applique à chaque prestation sélectionnée et peut être résiliée selon les dispositions du contrat principal.`
    },
    {
      number: "12",
      title: "Annexe technique (API / documents)",
      content: `Champs recommandés pour l'industrialisation :
- **fulfillment_mode** = LOGISCOP_DELIVERY
- **delivery_mode** = ESS_ROUTE
- **tour_id** (identifiant tournée)
- **route_window_start / route_window_end**
- **pod_verify_code** + **pod_timestamp**
- **priority_reason_code** (si applicable)`
    }
  ],
  tarification: {
    title: "Grille tarifaire indicative Tournées ESS",
    description: "Tarifs mutualisés (réduits vs livraison standard)",
    zones: [
      { code: "971", name: "Guadeloupe", base: "1,80€", perKg: "0,35€/kg", perCarton: "1,20€/carton" },
      { code: "972", name: "Martinique", base: "2,00€", perKg: "0,38€/kg", perCarton: "1,30€/carton" },
      { code: "973", name: "Guyane", base: "3,50€", perKg: "0,60€/kg", perCarton: "2,00€/carton" },
      { code: "974", name: "La Réunion", base: "2,50€", perKg: "0,45€/kg", perCarton: "1,50€/carton" },
      { code: "976", name: "Mayotte", base: "3,00€", perKg: "0,55€/kg", perCarton: "1,80€/carton" }
    ],
    benefits: [
      { label: "Économie vs livraison standard", value: "Jusqu'à -30%" },
      { label: "Réduction empreinte carbone", value: "Mutualisation trajets" },
      { label: "Accessibilité TPE", value: "Pas de minimum de commande" }
    ],
    tvaNote: "TVA DOM applicable (8,5% ou exonération selon zone)"
  }
};

// All legal documents list
export const allLegalDocuments = [
  cgvKdmarcheContent,
  cgOscopContent,
  conventionContent,
  charteESSContent,
  annexeLogiscopContent,
  contratTransportLogiscopContent,
  annexeTourneesESSContent
];

// Helper function to replace template variables
export const replaceVariables = (text, variables = legalVariables) => {
  if (!text) return '';
  let result = text;
  Object.entries(variables).forEach(([key, value]) => {
    result = result.replace(new RegExp(`{{${key}}}`, 'g'), value);
  });
  return result;
};

// Get document by ID
export const getDocumentById = (id) => {
  return allLegalDocuments.find(doc => doc.id === id) || null;
};
