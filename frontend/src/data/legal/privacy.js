// Politique de confidentialité (RGPD) — Communityplace KDMARCHÉ × O'SCOP
export const privacyContent = {
  id: "politique-confidentialite",
  title: "Politique de confidentialité",
  subtitle: "Protection des données personnelles — RGPD",
  version: "{{VERSION}}",
  dateEffet: "{{DATE_EFFET}}",
  reference: "PRIV-KDM-OSCOP-2026-001",
  entity: "KDMARCHE × O'SCOP",
  accentColor: "#0B4D87",
  sections: [
    {
      number: "1",
      title: "Responsables de traitement",
      content: `Selon les finalités, vos données sont traitées par :

- **SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP)** — SIRET {{OSCOP_SIRET}}, {{OSCOP_ADDRESS}} — pour les services d'accès, abonnements, CommunityPlace, espace investisseurs et services coopératifs.
- **PRIMACOP INTERNATIONAL BUSINESS (KDMARCHÉ)** — SIRET {{KDM_SIRET}}, {{KDM_ADDRESS}} — pour les ventes de marchandises du circuit partenaire (commandes, facturation, livraison).

Contact vie privée : {{OSCOP_EMAIL}} (délégué à la protection des données : à compléter).`
    },
    {
      number: "2",
      title: "Données collectées",
      content: `- **Identité et contact** : nom, prénom, email, téléphone, société, SIRET, fonction.
- **Compte et accès** : identifiants, rôle, zones autorisées, journaux de connexion.
- **Transactions** : commandes, factures, moyens de paiement (gérés par Stripe — nous ne stockons pas vos données de carte), historiques de participation CommunityPlace.
- **Logistique** : adresses de livraison ou d'enlèvement, preuves de livraison (signature, horodatage).
- **Support et messagerie** : échanges avec nos équipes.`
    },
    {
      number: "3",
      title: "Finalités et bases légales",
      content: `- **Exécution du contrat** : création de compte, commandes, livraisons, facturation, abonnements.
- **Obligations légales** : comptabilité, fiscalité, lutte contre la fraude.
- **Intérêt légitime** : sécurité de la plateforme, prévention de la fraude, statistiques d'usage, amélioration des services.
- **Consentement** : communications commerciales et alertes (désinscription possible à tout moment).`
    },
    {
      number: "4",
      title: "Destinataires et sous-traitants",
      content: `Vos données sont accessibles aux équipes habilitées d'O'SCOP et de PRIMACOP INTERNATIONAL BUSINESS, ainsi qu'à nos sous-traitants dans la stricte limite de leurs prestations :

- **Stripe** (paiements) — données de transaction ;
- **Brevo** (emails transactionnels et notifications) — adresse email, nom ;
- **Hébergeur** de la plateforme (infrastructure cloud) ;
- **LOGI'SCOP** (établissement de la SCIC O'SCOP) — données nécessaires aux livraisons.

Nous ne vendons ni ne louons vos données personnelles.`
    },
    {
      number: "5",
      title: "Transferts hors Union européenne",
      content: `Certains sous-traitants (notamment Stripe et Brevo) peuvent traiter des données hors de l'Union européenne. Ces transferts sont encadrés par des clauses contractuelles types de la Commission européenne ou tout mécanisme équivalent reconnu par le RGPD.`
    },
    {
      number: "6",
      title: "Durées de conservation",
      content: `- **Compte et accès** : durée de la relation contractuelle, puis 3 ans à des fins de prospection (professionnels).
- **Factures et pièces comptables** : 10 ans (obligations légales).
- **Preuves de livraison et journaux d'audit** : durée légale de conservation probatoire.
- **Données de paiement** : conservées par Stripe selon ses propres obligations ; nous conservons uniquement les références de transaction.`
    },
    {
      number: "7",
      title: "Vos droits",
      content: `Vous disposez des droits d'accès, de rectification, d'effacement, de limitation, d'opposition et de portabilité de vos données, ainsi que du droit de définir des directives post-mortem.

Pour exercer vos droits : {{OSCOP_EMAIL}} (justificatif d'identité possible en cas de doute).

Vous pouvez introduire une réclamation auprès de la **CNIL** (www.cnil.fr).`
    },
    {
      number: "8",
      title: "Cookies et traceurs",
      content: `La plateforme utilise des cookies strictement nécessaires au fonctionnement (session, panier, préférences de langue et de territoire). Des traceurs de mesure d'audience ou de suivi de conversion peuvent être utilisés de manière pseudonymisée. Vous pouvez configurer votre navigateur pour les refuser ; certaines fonctionnalités peuvent alors être dégradées.`
    },
    {
      number: "9",
      title: "Sécurité",
      content: `Nous mettons en œuvre des mesures techniques et organisationnelles appropriées : chiffrement des échanges (HTTPS), mots de passe hachés, contrôles d'accès par rôles, journalisation des actions sensibles et sauvegardes.`
    },
    {
      number: "10",
      title: "Mise à jour de la politique",
      content: `La présente politique peut être mise à jour pour rester conforme à la réglementation et à l'évolution des services. La version applicable est celle publiée sur la plateforme, avec sa date d'effet.`
    }
  ]
};
