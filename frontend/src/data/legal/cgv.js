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
      content: `Les présentes CGV s'appliquent aux ventes de marchandises réalisées par KDMARCHE auprès de clients professionnels disposant d'un accès B2B valide.

**Identité du vendeur** :
- **Enseigne** : KDMARCHÉ
- **Exploitant / vendeur juridique** : {{KDM_LEGAL_NAME}}
- **SIRET** : {{KDM_SIRET}} — **RCS** : {{KDM_RCS}}
- **Siège** : {{KDM_ADDRESS}}
- **Email** : {{KDM_EMAIL}} — **Téléphone** : {{KDM_PHONE}}
- **TVA intracommunautaire** : {{KDM_TVA}}
- **Représentant** : {{KDM_REP_NAME}} ({{KDM_REP_TITLE}})

Cette identité figure sur les bons de commande, bons de livraison et factures. **Chaque offre du catalogue identifie son vendeur juridique et l'émetteur de la facture** (voir article 5 bis — circuits de vente).`
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
      title: "Livraison, incoterms et zones de disponibilité",
      content: `**5.1.** Chaque fiche produit précise, lorsqu'ils sont renseignés : le **type de livraison** proposé (livraison standard, express, réfrigérée, sur palette, retrait entrepôt EXW, point relais, fret maritime ou aérien), l'**incoterm** applicable (EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU, DDP — Incoterms® 2020) et les **zones de disponibilité** de l'offre.

**5.2.** Lorsque EXW s'applique, l'acheteur organise l'enlèvement à l'adresse EXW de la zone, selon les créneaux et modalités communiqués. Les risques sont transférés conformément aux règles de l'incoterm indiqué sur la fiche produit.

**5.3.** Une option de livraison LOGI'SCOP peut être proposée en complément de la mise à disposition EXW locale, selon l'annexe CGV LOGI'SCOP (prestation de transport distincte).`
    },
    {
      number: "5 bis",
      title: "Circuits de vente — identification du vendeur (CLAUSE INTÉGRÉE)",
      highlight: true,
      content: `Le catalogue distingue plusieurs circuits de vente, **identifiés sur chaque offre** :

- **Vente partenaire directe** : la vente est conclue avec le partenaire vendeur référencé (KDMARCHÉ / PRIMACOP INTERNATIONAL BUSINESS ou un fournisseur référencé), qui facture et encaisse.
- **Achat-revente O'SCOP** : sur les offres expressément marquées « Vendu et facturé par O'SCOP », la vente est conclue avec la SCIC SAS OBJECTIF SCOP OUTREMER, régie par les CGV O'SCOP propres à ce circuit (page « CGV O'SCOP »).

Le vendeur juridique, l'émetteur de la facture et le bénéficiaire du paiement sont toujours identifiés **avant la commande** et rappelés sur la facture.`
    },
    {
      number: "6",
      title: "Facturation et paiement",
      content: `Le vendeur identifié sur l'offre émet la facture des marchandises. Le paiement est effectué directement auprès de ce vendeur selon les moyens proposés ({{MOYENS_PAIEMENT}}).

Certains vendeurs peuvent restreindre le règlement à la **carte bancaire uniquement** ; cette mention est affichée sur l'offre concernée avant la commande.

Aucun paiement de marchandises du circuit partenaire n'est encaissé par O'SCOP ; sur le circuit achat-revente, le paiement est encaissé par O'SCOP en qualité de vendeur.`
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
      number: "6 ter",
      title: "Règlement à Réception Pro (CLAUSE INTÉGRÉE)",
      highlight: true,
      content: `Certaines commandes peuvent, après validation expresse par KDMARCHÉ, bénéficier du dispositif **« Règlement à Réception Pro »**. Ce dispositif permet à l'Acheteur professionnel de commander les marchandises éligibles sans versement préalable d'un acompte sur leur prix.

Le prix devient exigible à la réception effective des marchandises au lieu de livraison convenu, matérialisée par la signature électronique du bon de livraison, la validation d'un code sécurisé ou toute preuve électronique équivalente.

L'Acheteur autorise KDMARCHÉ à déclencher le moyen de paiement enregistré immédiatement après cette confirmation.

En cas de réserve précise, circonstanciée et portée sur le bon de livraison, seule la valeur des marchandises directement concernées peut être temporairement suspendue. La valeur des marchandises reçues sans réserve demeure exigible.

L'accès au dispositif est **personnel, révocable** et subordonné au maintien d'une adhésion O'SCOP active, à la validation préalable de KDMARCHÉ, à l'existence d'un moyen de paiement valide, à l'absence d'incident et à la disponibilité du plafond attribué.

KDMARCHÉ peut réduire, suspendre ou supprimer le plafond en cas d'incident de paiement, de modification de la situation économique de l'Acheteur ou d'utilisation non conforme du dispositif.`
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
  subtitle: "Accès – Abonnements – CREDI'SCOP (B2B)",
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

**2.2.** Par principe, O'SCOP ne vend aucune marchandise du circuit partenaire et n'encaisse aucun paiement relatif à celles-ci. **Exception** : sur les offres du circuit achat-revente expressément marquées « Vendu et facturé par O'SCOP », O'SCOP agit en qualité de vendeur-facturier selon ses CGV propres à ce circuit.

**2.3.** Les ventes de marchandises du circuit partenaire sont conclues directement entre l'Acheteur et le vendeur référencé (KDMARCHÉ / PRIMACOP INTERNATIONAL BUSINESS ou fournisseur référencé), selon les CGV applicables au vendeur identifié sur l'offre.`
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

**6.4.** Factures : émises par O'SCOP, distinctes des factures de marchandises KDMARCHE.

**6.5. Abonnement API coopérative (relais LOLODRIVE)** : un abonnement annuel « API Coopérative B2B2C » (2 500 € HT/an) est proposé exclusivement aux gérants de relais LOLODRIVE. Il donne accès à l'API catalogue/commandes (clé nominative, quota mensuel d'appels, webhooks temps réel). L'abonnement est renouvelable à échéance ; à défaut de renouvellement, la clé est désactivée et réactivée telle quelle lors d'un renouvellement ultérieur, sans reconfiguration.`
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
      title: "CREDI'SCOP – Définition juridique et règles d'usage (clause sensible)",
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
      number: "8 bis",
      title: "CommunityPlace — offres, demandes et participations",
      content: `**8 bis.1.** Le service CommunityPlace permet le dépôt public d'offres produits et de demandes d'achat. Le dépôt peut être soumis à des **frais de publication** affichés avant validation (montants en vigueur consultables sur la plateforme).

**8 bis.2.** La **participation mutualisée** permet de rejoindre une demande groupée moyennant une participation calculée au prorata du nombre de participants (minimum 1 €), affichée avant paiement. Elle rémunère le service de mise en relation et d'ingénierie collective ; elle ne constitue ni un acompte sur des marchandises, ni un investissement.

**8 bis.3.** Les membres disposant d'un abonnement actif (acheteurs professionnels) ou d'un référencement fournisseur approuvé bénéficient de conditions de participation adaptées, affichées sur la plateforme.`
    },
    {
      number: "8 ter",
      title: "Espace investisseurs — CREDI'SCOP-INVEST",
      content: `O'SCOP propose aux membres éligibles un espace investisseurs permettant de financer des opérations d'achat-revente ou des prestations logistiques identifiées, vendues et facturées par O'SCOP.

Les conditions spécifiques (unités CREDI'SCOP, engagements, échéanciers de remboursement, risques) sont fixées par les documents dédiés : « Conditions CREDI'SCOP-I et investissement », « Convention investisseur » et « Financement logistique investisseur », accessibles depuis l'espace investisseur. **Les CREDI'SCOP sont des unités internes de services : ils ne constituent ni un placement financier, ni une monnaie, ni un instrument de paiement ; ils ne sont ni remboursables en espèces ni productifs d'intérêts.**`
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
