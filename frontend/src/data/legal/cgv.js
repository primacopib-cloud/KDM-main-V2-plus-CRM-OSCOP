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

**Hébergeur du site** : {{HOST_NAME}} — {{HOST_ADDRESS}} — SIRET {{HOST_SIRET}} ({{HOST_RCS}}) — Tél. {{HOST_PHONE}}

**Éditeur du site** : {{OSCOP_LEGAL_NAME}} — SIREN {{OSCOP_SIREN}}, {{OSCOP_SIEGE_ADDRESS}} — Directeur de la publication : {{OSCOP_REP_NAME}}, {{OSCOP_REP_TITLE}}.

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

// CG O'SCOP remplacées par les CGU CommunityPlace officielles (voir ./cgu_mentions.js) — 10/09/2026


// Convention de partenariat KDMARCHE-O'SCOP (Version consolidée avec clause rémunération)
