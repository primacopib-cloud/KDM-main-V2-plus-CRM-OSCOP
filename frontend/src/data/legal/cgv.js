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
  accentColor: "#D4AF37",
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
      content: `**11.1.** O'SCOP ne fournit aucune assurance, ne mutualise aucun risque et n'indemnise aucun sinistre dans le cadre de la Communityplace.

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
