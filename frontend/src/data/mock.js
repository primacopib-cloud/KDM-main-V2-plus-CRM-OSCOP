// Mock data for B2B ESS Commercial Offer

export const partners = {
  kdmarche: {
    name: "KDMARCHE",
    role: "Opérateur commercial et logistique B2B",
    logo: "https://customer-assets.emergentagent.com/job_b2b-ess-market/artifacts/81criz40_KDMARCHE%20PRO.svg",
    responsibilities: [
      "Opérateur de vente B2B",
      "Gestionnaire des catalogues produits",
      "Gestionnaire des stocks par zones",
      "Émetteur des factures marchandises",
      "Opérateur logistique (EXW, zones pays)",
      "Responsable de la conformité produit (TVA, douanes, DLC, traçabilité)"
    ],
    assumes: [
      "Le prix produit",
      "La relation fournisseur",
      "La facturation",
      "La TVA",
      "La livraison EXW"
    ]
  },
  oscop: {
    name: "O'SCOP",
    fullName: "Objectif SCOP Outremer",
    role: "Centrale coopérative d'ingénierie ESS, accès et mutualisation",
    logo: "https://customer-assets.emergentagent.com/job_b2b-ess-market/artifacts/7ef2z2pb_LOGO%20OBJECTIF%20SCOP%20OUTREMER%202026.png",
    responsibilities: [
      "Centrale d'ingénierie d'achats ESS",
      "Organisateur de la mutualisation",
      "Opérateur de l'accès à la plateforme",
      "Gestionnaire des abonnements",
      "Gestionnaire du wallet crédits",
      "Garant du cadre ESS et coopératif"
    ],
    restrictions: [
      "Ne vend pas",
      "Ne facture pas les produits",
      "Ne perçoit aucun paiement fournisseur",
      "Ne prend aucune commission sur les ventes"
    ]
  }
};

export const subscriptionPlans = [
  {
    id: "ess-acces-pro",
    name: "ESS ACCÈS PRO",
    price: 149,
    period: "mois",
    highlight: false,
    features: [
      "Accès à la centrale d'achats KDMARCHE B2B",
      "1 zone géographique incluse",
      "Accès aux prix structurels mutualisés",
      "Wallet crédits de base",
      "Accès promos flash de la zone"
    ]
  },
  {
    id: "ess-volume-pro",
    name: "ESS VOLUME PRO",
    price: 349,
    period: "mois",
    highlight: true,
    popular: true,
    features: [
      "Accès prioritaire aux volumes",
      "Accès élargi aux gammes KDMARCHE",
      "Wallet crédits renforcé",
      "Accès multi-catégories",
      "Reporting d'usage"
    ]
  },
  {
    id: "ess-impact-pro",
    name: "ESS IMPACT PRO",
    price: 749,
    period: "mois",
    highlight: false,
    features: [
      "Accès multi-zones",
      "Accès projets collectifs",
      "Reporting ESS / impact",
      "Appui structuration coopérative",
      "Accès fournisseurs stratégiques"
    ]
  }
];

export const logisticsSteps = [
  { step: "Accès plateforme", responsible: "O'SCOP" },
  { step: "Abonnement / crédits", responsible: "O'SCOP" },
  { step: "Catalogue produits", responsible: "KDMARCHE" },
  { step: "Prix produits", responsible: "KDMARCHE" },
  { step: "Facturation produits", responsible: "KDMARCHE" },
  { step: "Paiement produits", responsible: "KDMARCHE" },
  { step: "Transport (EXW)", responsible: "Client" }
];

export const walletCreditsUsage = [
  "L'usage intensif",
  "L'accès prioritaire",
  "Les zones supplémentaires",
  "Les services ESS"
];

export const compliancePoints = {
  guaranteed: [
    "Transparence totale des rôles",
    "Note préventive ACPR / DGCCRF intégrée"
  ],
  excluded: [
    "Aucune vente à perte (prix KDMARCHE économiquement justifiés)",
    "Aucune intermédiation financière",
    "Aucune activité d'assurance",
    "Aucune pratique commerciale trompeuse"
  ]
};

export const officialStatement = `Dans le cadre du partenariat KDMARCHE – O'SCOP,
KDMARCHE commercialise les produits,
O'SCOP organise l'accès coopératif aux conditions économiques.
Les prix résultent d'une mutualisation ESS, non de remises commerciales.`;

export const priceAdvantages = [
  "Mutualisation organisée par O'SCOP",
  "Volumes consolidés",
  "Suppression d'intermédiaires",
  "Vente exclusivement B2B",
  "Modèle EXW sans coûts retail"
];

export const contractualDocuments = [
  "Convention de partenariat KDMARCHE – O'SCOP",
  "CG O'SCOP (accès & usage)",
  "CGV KDMARCHE B2B",
  "Charte ESS de mutualisation",
  "FAQ clients & administrations",
  "Page web commune \"Centrale d'achats ESS\""
];

export const mockUsers = [
  {
    id: "1",
    email: "demo@oscop.fr",
    password: "demo123",
    name: "Entreprise Demo",
    company: "SARL Demo ESS",
    subscription: "ess-volume-pro",
    credits: 250
  }
];

export const mockQuoteRequests = [
  {
    id: "1",
    company: "Coopérative Solidaire",
    email: "contact@coop-solidaire.fr",
    phone: "0690123456",
    message: "Intéressés par l'offre ESS Volume Pro pour notre coopérative de 15 membres.",
    plan: "ess-volume-pro",
    createdAt: "2025-08-01T10:30:00Z",
    status: "pending"
  }
];
