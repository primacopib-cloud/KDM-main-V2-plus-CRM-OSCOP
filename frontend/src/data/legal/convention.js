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
