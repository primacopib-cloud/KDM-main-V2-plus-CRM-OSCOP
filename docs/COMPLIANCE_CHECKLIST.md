# KDMARCHE × O'SCOP - Checklist de Conformité

> Checklist opérationnelle et audit-ready pour le dispositif Centrale d'achats B2B ESS
> Conformité: DGCCRF, ACPR, ESS

---

## 1. Gouvernance et Cloisonnement des Rôles

### 1.1 Cloisonnement Contractuel (Obligatoire)

- [ ] **Convention de partenariat** KDMARCHE–O'SCOP signée, datée, versionnée
- [ ] **Article "Répartition des rôles"** explicite :
  - [ ] KDMARCHE = vendeur marchandises (catalogue, prix, factures marchandises, TVA, stocks, EXW)
  - [ ] O'SCOP = accès/usage (abonnements, crédits, services, gouvernance ESS)
- [ ] **Clause explicite** : O'SCOP ne vend pas, ne facture pas les marchandises, ne perçoit pas les paiements marchandises
- [ ] **Clause "non-commission"** : O'SCOP ne perçoit aucune commission indexée sur ventes/volumes

### 1.2 Séparation Comptable et Justificative

- [ ] **Deux séries de factures distinctes** :
  - [ ] Factures O'SCOP : abonnements / crédits / services
  - [ ] Factures KDMARCHE : marchandises
- [ ] **Aucune "facture hybride"** (service + marchandise) émise par un seul acteur

---

## 2. DGCCRF – Transparence Prix, Pratiques Commerciales, Information

### 2.1 Justification "jusqu'à –50%" (Anti-tromperie)

- [ ] Sur la page publique : mention "jusqu'à –50%" qualifiée comme **prix structurels**, non comme promo
- [ ] Encart **"Pourquoi les prix sont plus bas"** :
  - [ ] Mutualisation
  - [ ] Suppression d'intermédiaires
  - [ ] EXW (retrait à quai)
  - [ ] B2B uniquement
- [ ] **Aucun vocabulaire ambigu** : éviter "soldes", "promotion", "remise exceptionnelle" si non applicable
- [ ] **Preuves internes disponibles** :
  - [ ] Note de calcul "chaîne classique vs chaîne mutualisée"
  - [ ] Exemples de devis/factures fournisseurs (EXW)
  - [ ] Critères de sélection produits "qualité d'office"

### 2.2 Accès Conditionné (Abonnement) – Information Loyale

- [ ] **Mention claire** : abonnement obligatoire pour accéder aux conditions mutualisées
- [ ] **Affichage des prix** :
  - [ ] Non-abonné / non validé : prix masqués ou "prix sur abonnement"
  - [ ] Après validation + abonnement : prix affichés par zone
- [ ] **CG O'SCOP** : conditions d'accès, résiliation, renouvellement, suspension, impayés

### 2.3 Vente à Perte / Dumping (Prévention)

- [ ] O'SCOP ne vend pas les produits → **hors champ "vente à perte"** côté O'SCOP
- [ ] **KDMARCHE** :
  - [ ] Documentation interne de formation de prix (coût d'achat, logistique, taxes, frais fixes)
  - [ ] Évite les prix "d'appel" non justifiables
- [ ] Si "flash deals" : règles écrites (durée, quantités, zones, stocks)

### 2.4 Facturation, TVA et Mentions Obligatoires

- [ ] KDMARCHE facture la marchandise avec **mentions légales complètes** + TVA / régime applicable
- [ ] O'SCOP facture les services (abonnements/crédits) avec TVA applicable
- [ ] Conditions de paiement KDMARCHE **séparées des CG O'SCOP**

### 2.5 Droit de Rétractation / Retours (B2B)

- [ ] **Politique retours/avoirs adaptée B2B** (pas copier-coller B2C)
- [ ] **Règles de retour documentées** :
  - [ ] Délai
  - [ ] Conditions
  - [ ] État produit
  - [ ] DLC
  - [ ] Litiges
- [ ] Avoir vs remboursement : process écrit
- [ ] **Conservation des preuves** : BL, facture, photos, traçabilité stock

---

## 3. ACPR – Anti-requalification Assurance / Activité Financière

### 3.1 Absence d'Assurance

- [ ] **Aucune promesse d'indemnisation**, de couverture, de garantie de risque aléatoire
- [ ] **Aucune mutualisation de risques** probabilisables via cotisations
- [ ] **Aucun terme ambigu** : éviter "garantie", "couverture", "sinistre" dans ce périmètre

### 3.2 Absence d'Intermédiation Financière / PSP

- [ ] **Flux paiement marchandises** :
  - [ ] Payés **directement à KDMARCHE** (PSP KDMARCHE)
  - [ ] O'SCOP ne collecte pas pour compte de tiers
- [ ] **Flux paiement abonnements/crédits** :
  - [ ] Payés **directement à O'SCOP**
  - [ ] Justificatifs (factures) séparés
- [ ] **Aucun séquestre** par O'SCOP, aucun compte de cantonnement marchandises

### 3.3 Wallet Crédits (Sensible)

- [ ] **Définition contractuelle** : crédits = unité de service (accès/usage), pas une monnaie, pas une valeur remboursable
- [ ] **CG** : crédits non convertibles en cash, non transférables, non assimilables à instrument de paiement
- [ ] **Ledger probant** : toutes consommations horodatées + corrélation d'action

---

## 4. ESS – Alignement, Non-spéculation, Gouvernance

### 4.1 Principes ESS Affichés et Opposables

- [ ] **Charte ESS** "prix structurels" (non spéculatifs)
- [ ] **Principe de financement** : accès & usage, pas extraction de valeur sur produits
- [ ] **Politique d'affectation des excédents** (réinvestissement outil, intérêt collectif)

### 4.2 Critères "Produits de Qualité d'Office"

- [ ] **Grille de sélection fournisseurs/produits** :
  - [ ] Conformité réglementaire (traçabilité, normes, DLC)
  - [ ] Qualité minimale (certifications si applicables)
  - [ ] Engagement logistique (EXW, quantités, délais)
- [ ] **Procédure d'exclusion** (non-conformité, litiges répétés)
- [ ] **Archivage** des fiches fournisseurs & pièces qualité

---

## 5. Checklist Technique & Preuve (Audit IT / Contrôle)

### 5.1 Gating Automatique (Preuve d'Exécution)

- [x] **Règles ABAC en production** :
  - [x] Prix visibles seulement si : `org=APPROVED` + `sub=ACTIVE` + `zone autorisée` + `partner=ACCESS_ENABLED`
  - [x] Commande autorisée seulement si : `incoterm=EXW` (zones exw_only)
- [x] **Journaux probants (audit_log)** :
  - [x] Validation/refus B2B (qui/quand/pourquoi)
  - [x] Changements abonnements (ACTIVE/PAST_DUE)
  - [x] Suspensions/réactivations
  - [x] Provisioning/désactivation KDMARCHE
  - [x] Consommation crédits (ledger)

### 5.2 Sécurité & Données

- [x] **Multi-tenant strict** (org_id partout)
- [x] **Conservation et accès aux justificatifs** :
  - [x] Stockage sécurisé + checksum
  - [x] Contrôle d'accès par rôle
- [x] **Journalisation des accès administrateurs**

### 5.3 Webhooks / Événements

- [x] **Outbox pattern** (pas de perte d'événement)
- [ ] HMAC signatures + anti-replay (à implémenter si webhooks externes)
- [ ] Rejeu + DLQ documentés (à implémenter)

---

## 6. Pack "Preuve Contrôle" – Documents à Produire

En cas de contrôle, vous devez pouvoir sortir immédiatement :

| Document | Statut | Emplacement |
|----------|--------|-------------|
| Convention partenariat KDMARCHE–O'SCOP (signée) | ⏳ À préparer | `/app/docs/legal/` |
| CG O'SCOP (accès/abonnement/crédits) | ⏳ À préparer | `/app/docs/legal/` |
| CGV KDMARCHE B2B (marchandises/EXW/retours) | ⏳ À préparer | `/app/docs/legal/` |
| Note préventive ACPR/DGCCRF | ⏳ À préparer | `/app/docs/compliance/` |
| Exemples de factures (1 O'SCOP + 1 KDMARCHE) | ⏳ À préparer | `/app/docs/samples/` |
| Extrait audit_log | ✅ Disponible | `GET /api/v2/admin/audit-log` |
| Policy ABAC (gating prix/commande/EXW) | ✅ Implémenté | `/app/backend/abac_policy.py` |

---

## 7. Récapitulatif Statut Technique

### Implémenté ✅

| Fonctionnalité | Fichier | Status |
|----------------|---------|--------|
| Multi-tenant (org_id) | `schema_v2.py` | ✅ |
| RBAC (11 rôles) | `schema_v2.py` | ✅ |
| Machine d'états ORG | `routes_v2.py` | ✅ |
| Machine d'états SUBSCRIPTION | `schema_v2.py` | ✅ |
| Machine d'états PARTNER | `schema_v2.py` | ✅ |
| Wallet Ledger | `routes_v2.py` | ✅ |
| Zones EXW | `schema_v2.py` | ✅ |
| ABAC Policy Engine | `abac_policy.py` | ✅ |
| Audit Log | `routes_v2.py` | ✅ |
| Outbox Events | `schema_v2.py` | ✅ |

### À Implémenter ⏳

| Fonctionnalité | Priorité |
|----------------|----------|
| Webhooks HMAC | P2 |
| Catalogue KDMARCHE | P1 |
| Système de commandes | P1 |
| Paiement Stripe | P2 |

---

*Document de conformité KDMARCHE × O'SCOP*
*Version: 1.0 - Janvier 2025*
*Dernière mise à jour: 16/01/2025*
