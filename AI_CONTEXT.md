# AI_CONTEXT.md — KDMARCHÉ / LOLODRIVE by O'SCOP

Synthèse pour tout outil IA (Emergent ou autre) qui interviendra sur ce projet.

## Nature du projet

Plateforme coopérative B2C/B2B2C pour la lutte contre la vie chère.

## Architecture en deux couches

### 1. V2 — Moteur transactionnel (la source de vérité)
- PASS Vie Chère (activation, expiration 30 jours, **non renouvelable**)
- Wallet UC + ledger (CREDIT/DEBIT)
- Catalogue (ESSENTIELS et Hors25)
- Commandes (DRAFT → PENDING_PAYMENT → PAID → PREPARING → READY → FULFILLED)
- Paiement Stripe (PaymentIntents + webhook payment_intent.succeeded)
- Drive / Livraison / LOLO POINT
- POS (file commandes, scan retrait, transitions)
- LOLO POINTS (réseau coopératif, commissions, payout preview)
- LOLO HOUR (événements horaires, FLASH_PASS, FLASH_PUBLIC, LOLO_BIG_DEAL, PARTNER)

Code : `backend/routes_lolodrive_oscoop.py`, `routes_v2.py`, `routes_catalog.py`, `routes_payment.py`.

### 2. CRM O'SCOP — Couche relationnelle (jamais transactionnelle)
- Contacts (acteurs)
- Organisations (entreprises, lolo points, fournisseurs, institutionnels)
- Partenaires (sponsors, fournisseurs)
- Opportunités (pipeline commercial / partenariats)
- Dossiers (onboarding lolo point, référencement fournisseur, financement)
- Tâches / rappels
- Reporting impact ESS

Code : `backend/routes_crm_oscoop.py`.

Le CRM est nourri par des **events** émis par la V2 (`pass.activated`, `order.paid`, `lolo_point.created`, `partner.created`, `event.created`).

## Règles absolues à ne pas violer

1. **Ne pas remplacer le moteur UC par le CRM.** Le CRM lit la V2 ; il ne calcule ni les UC, ni les soldes, ni les commissions.
2. **Ne pas transformer les UC en monnaie.** Les UC = unité d'usage interne. Pas de conversion sortante, pas d'affichage "taux UC↔€" public.
3. **Le prix en euros reste la référence légale** (factures, fiscalité, ACPR/DGCCRF).
4. **Le PASS ne se renouvelle pas automatiquement.** Aucune souscription Stripe récurrente.
5. **Le frontend ne recalcule pas** les prix, UC, soldes, droits PASS ou commissions. Toujours validation serveur.

## Catalogue : règles tarifaires

```
SI product.catalog_type == ESSENTIAL et user.pass_active:
    prix affiché = price_pass_cents
SINON SI product.catalog_type == ESSENTIAL et NOT user.pass_active:
    prix affiché = price_public_cents
SI product.catalog_type == NORMAL (Hors25):
    prix affiché = price_public_cents (toujours)
    payable en UC SI user.pass_active (sans avantage de prix)
```

## Ressources clés

| Path | Description |
|------|-------------|
| `backend/routes_lolodrive_oscoop.py` | API LOLODRIVE complète |
| `backend/routes_crm_oscoop.py` | CRM Bridge |
| `backend/seed_lolodrive.py` | Seed démo (4 users, 12 produits, 4 lolo points, 4 events, etc.) |
| `frontend/src/pages/PassSpacePage.jsx` | Espace titulaire PASS |
| `frontend/src/pages/PosLolodrivePage.jsx` | Interface POS |
| `frontend/src/pages/LolodriveAdminDashboardPage.jsx` | Dashboard super admin |
| `frontend/src/pages/LoloPointsAdminPage.jsx` | Gestion LOLO POINTS |
| `frontend/src/pages/LoloHourAdminPage.jsx` | Gestion LOLO HOUR |
| `frontend/src/pages/CrmPartnersPage.jsx` | CRM Partenaires |
| `frontend/src/pages/EssReportingPage.jsx` | Reporting impact ESS |

## Test rapide (E2E)

1. Login `marie@example.com` / `Demo2026!`
2. Aller sur `/pass` — PASS actif visible, 450 UC dans le wallet
3. Catalogue `/catalogue-lolodrive` — voir prix PASS sur ESSENTIELS
4. Créer commande DRIVE → payer en UC ou via Stripe test
5. Login `pos@lolodrive.fr` → `/pos` — voir la commande, transition PREPARING → READY → FULFILLED (scan)
6. Login admin → `/super-admin` — voir KPIs LOLODRIVE et CRM impact

## Cartes Stripe test

- `4242 4242 4242 4242` — date future, CVC quelconque (succès)
- `4000 0000 0000 9995` — paiement insuffisant
