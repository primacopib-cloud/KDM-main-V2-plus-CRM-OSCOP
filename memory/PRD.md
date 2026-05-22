# PRD - KDMARCHÉ / LOLODRIVE by O'SCOP — Itération 1

## Original problem statement
Voici un projet existant : KDMARCHÉ / LOLODRIVE by O'SCOP.
Objectif : créer une interface web propre pour exploiter l'API existante sans modifier les règles métier critiques.

## User personas
- **SUPER_ADMIN / ADMIN** : pilote KPIs, gère plans, autorise organisations
- **TITULAIRE_PASS** : activer PASS, recharger UC, commander, consulter wallet
- **OPERATEUR_POS** : gérer file commandes, scan retrait
- **GERANT_LOLO_POINT** : suivi commissions, contributions coopératives
- **PARTENAIRE_CRM** / **CONSEIL_COOPERATIF** : CRM, reporting impact

## Règles métier non négociables
1. V2 = source de vérité transactionnelle. CRM = relationnel.
2. UC ≠ monnaie. Référence légale : euros.
3. PASS Vie Chère : 60 € = 600 UC, 30 jours, **sans renouvellement auto**.
4. ESSENTIELS : prix PASS si PASS actif. Hors25 : prix normal, payable UC sans avantage.
5. Frontend ne recalcule pas prix/UC/soldes/droits PASS/commissions.

## Architecture
- Backend FastAPI + Motor MongoDB (héritage : `routes_lolodrive_oscoop.py`, `routes_crm_oscoop.py`)
- Frontend React 19 + Tailwind + Shadcn/UI
- Auth JWT custom multi-rôles
- Stripe PaymentIntents (test mode `sk_test_emergent`)

## What's been implemented (Itération 1)

### Backend (importé du ZIP fourni)
- 302 routes au total : auth, PASS, wallet UC, catalogue ESSENTIELS/NORMAL, commandes, POS, LOLO POINTS, LOLO HOUR, partenaires, CRM, KPI
- Seed démo : 4 users, 12 produits, 4 lolo points, 4 events, 4 partenaires, PASS actif, 3 commandes
- Stripe configuré en mode test

### Frontend - 7 nouvelles pages
1. `/lolodrive` - Dashboard Super Admin (KPIs V2 + CRM impact, accès rapide modules)
2. `/pass` - Espace titulaire PASS (activation PASS, wallet UC, ledger, commandes, recharge)
3. `/pos` - Interface POS LOLODRIVE (file commandes, transitions PAID→PREPARING→READY, scan retrait)
4. `/admin/lolo-points` - Gestion LOLO POINTS (création, aperçu commissions, plafonds ESS)
5. `/admin/lolo-hour` - Gestion événements LOLO HOUR (création, FLASH_PASS, FLASH_PUBLIC, LOLO_BIG_DEAL, PARTNER)
6. `/crm` - CRM Partenaires (contacts, organisations, opportunités, dossiers, tâches)
7. `/reporting-impact` - Reporting impact ESS (indicateurs sociaux/économiques/réseau, export JSON)

### Bonus
- `/catalogue-lolodrive` - Catalogue B2C avec prix PASS dynamiques, panier, paiement UC ou Stripe

### Documentation
- `README.md` à la racine
- `AI_CONTEXT.md` à la racine
- `memory/test_credentials.md` à jour

## P0 backlog (next iterations)
- Wire complète Stripe Elements (saisie CB intégrée + retour après paiement)
- Page commandes individuelles pour le titulaire avec relances et statut temps réel
- WebSocket notifs POS (commande payée → toast)
- Personnalisation logos/branding O'SCOP final

## P1 backlog
- Module GERANT_LOLO_POINT (vue gérant : SES commandes, SES commissions)
- Module PARTENAIRE_CRM (login partenaire avec vue restreinte)
- Module CONSEIL_COOPERATIF (signatures conseils, validations gouvernance)
- Renouvellement non-auto + notification J-7 J-3 J-1

## P2 backlog
- Activation Google Login en option secondaire
- Tests automatisés Playwright

