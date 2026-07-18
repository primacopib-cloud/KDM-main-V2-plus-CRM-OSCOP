# SPÉCIFICATION DE RENOMMAGE — CREDI'SCOP (Capital d'usage coopératif)

> Document à copier-coller dans l'agent Emergent de chaque application de l'écosystème O'SCOP :
> - OSCOP IA Bois — https://oscop-ia-bois.emergent.host
> - O'SCOP GE — https://ge-outremer-hub.emergent.host
> - COPPAM (trésorerie) — https://treasury-dash-4.emergent.host
> - CRM ESS — https://fastapi-react-crm-4.emergent.host
>
> Le renommage est DÉJÀ appliqué sur KDMARCHÉ (référence d'implémentation).

---

## PROMPT À COLLER DANS CHAQUE APP

Dans toute l'application, remplacer le terme « Wallet » (et ses variantes « wallet », « Wallet Crédits », « porte-monnaie ») par la marque **CREDI'SCOP** selon les règles suivantes :

### 1. Libellé d'interface
- Libellé principal (menu, page, onglet) : **Mon CREDI'SCOP**
- Libellés secondaires (boutons, colonnes, cartes) : **CREDI'SCOP**
- Typographie : toujours écrire **CREDI'SCOP** avec l'apostrophe (cohérent avec BATI'SCOP, LOGI'SCOP, FLORAL'SCOP)

### 2. Signature courte (sous le titre de la page CREDI'SCOP)
> Mes droits coopératifs mobilisables

### 3. Définition institutionnelle (introduction de la page)
> CREDI'SCOP désigne l'espace individuel permettant au membre de consulter, recevoir et
> mobiliser ses droits d'usage, crédits coopératifs, contributions valorisées et avantages
> mutualisés au sein de l'écosystème O'SCOP.

### 4. Mention juridique obligatoire (pied de la page CREDI'SCOP, petit corps de texte)
> Les unités inscrites dans CREDI'SCOP constituent des droits d'usage internes.
> Elles ne représentent ni des parts sociales, ni un dépôt bancaire, ni un crédit financier,
> ni de la monnaie électronique, sauf lorsqu'un service réglementé est expressément fourni
> par un prestataire agréé.

### 5. Sous-titre / baseline de marque
> CREDI'SCOP — Capital d'usage coopératif

### 6. Règles techniques
- Ne renommer QUE les libellés visibles (i18n, textes en dur JSX/HTML, PDF, emails).
- NE PAS renommer les clés techniques : routes (`/wallet`), clés i18n (`wallet.*`),
  collections MongoDB (`wallets`), champs API (`balance_credits`) — pour ne rien casser.
- Couvrir toutes les langues (FR/EN/ES si l'app est multilingue) : la marque CREDI'SCOP
  reste identique dans toutes les langues (« My CREDI'SCOP », « Mi CREDI'SCOP »).
- Vérifier les fichiers : locales i18n, breadcrumbs, menus de navigation, dashboards,
  CGV/CGU, emails transactionnels, exports PDF.

---

## RÉFÉRENCE — Implémentation faite sur KDMARCHÉ (2026-07-18)
- 15 fichiers i18n (fr/en/es × app/admin/site/data/core) : valeurs « Wallet » → « CREDI'SCOP »
- Page `/wallet` : titre « Mon CREDI'SCOP » + signature + définition + mention juridique
- Breadcrumb, QuickNav, CatalogHeader, DashboardPage, DocumentsPage (CG), cgv.js
- Les clés techniques (`/wallet`, `wallet.*`, collection `wallets`) sont inchangées
