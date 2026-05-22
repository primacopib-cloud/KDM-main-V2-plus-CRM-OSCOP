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


---

## Iteration 2 (22 mai 2026) — Recentrage 3 écrans critiques

### Backend (additions démo)
- `POST /api/lolodrive/demo/simulate-pass-activation` — active PASS + crédite 600 UC sans Stripe webhook
- `POST /api/lolodrive/demo/simulate-order-payment/{order_id}` — passe une commande à PAID
- `GET /api/lolodrive/me/savings` — calcule économies réalisées par l'utilisateur (savings_cents, essential_items, orders_count)

### Frontend - 3 écrans critiques enrichis
1. **`/lolodrive` Dashboard admin** :
   - Sélecteur de période 7j/30j/90j avec rechargement KPI
   - Répartition revenus visuelle (barre stackée Drive/Livraison/Lolo Point)
   - Panneau "Engagement PASS" (conversion %, panier moyen, UC débités)
   - Section "Activité POS en cours" avec aperçu temps réel
   - Badges "Phase 2 · léger" sur les modules non-critiques
2. **`/pass` Espace titulaire** :
   - KPI **Économies réalisées** (calcul automatique sur commandes ESSENTIELS)
   - Indicateurs d'expiration J-7 / J-3 avec couleurs (amber/red)
   - Bouton démo "Activer mon PASS (mode démo)" pour démos sans Stripe réel
   - Bouton "Voir le catalogue" (lien direct parcours commande)
   - Libellés humanisés du wallet ledger
3. **`/pos` Interface POS** :
   - **Auto-refresh polling 15s** avec détection nouvelles commandes
   - **Notification sonore (beep)** quand nouvelle commande PAID arrive
   - **Banner "X commandes à traiter"** visible en haut
   - Switch "Vue compacte" (réduit hauteur des cartes)
   - Affichage nom client, items avec badge `E` pour essentiels
   - Boutons workflow : Préparer → Marquer prête → Remettre client (scan)

### Frontend - 4 modules Phase 2 (allégés)
- `/admin/lolo-points`, `/admin/lolo-hour`, `/crm`, `/reporting-impact` : ajout `<Phase2Banner>` indiquant la version légère

### Tests Iteration 2
- Backend pytest 30/30 PASSED (24 itération 1 + 6 nouveaux : demo endpoints + KPI périodes)
- Frontend 100% — 6 écrans critiques + 4 banners Phase 2 vérifiés
- Parcours E2E complet validé : activation PASS → commande → paiement → POS → retrait → KPI admin


---

## Iteration 3 (22 mai 2026) — Stripe réel + WS POS + alertes opérationnelles

### Backend (5 ajouts majeurs)
- **`routes_lolodrive_checkout.py`** (nouveau) :
  - `POST /api/lolodrive/checkout/pass-session` — Stripe Checkout hosted pour PASS 60 €
  - `POST /api/lolodrive/checkout/recharge-session` — packs MINI/STANDARD/MAXI
  - `POST /api/lolodrive/checkout/order-session` — paiement commande
  - `GET /api/lolodrive/checkout/status/{session_id}` — polling idempotent
  - `POST /api/webhook/stripe` — webhook officiel (signature validée)
  - Collection `payment_transactions` (idempotence)
- **`POST /api/lolodrive/pos/orders/{id}/cancel`** — annulation avec refund UC optionnel
- **`GET /api/lolodrive/admin/kpi/dashboard`** — UC en circulation, UC consommées, CA jour/mois, Top 5 produits, Alertes
- **WebSocket `/api/ws/notifications`** (préfixe corrigé) avec broadcast `lolodrive_pos_event`
- Seed/index : `payment_transactions.session_id` unique

### Frontend (5 ajouts/refactos)
- **`PaymentReturnPage`** (`/paiement/retour`) : polling status + animation succès/échec
- **`StripeCheckoutButton`** : redirige vers Stripe hosted (real test mode)
- **`useLolodriveWebSocket`** hook : reconnect 3s, ping 25s
- **POS** : indicateur Wifi/WifiOff temps réel, bouton "Annuler" + dialog avec refund UC
- **Dashboard** : 4 nouveaux KPIs + section Alertes + Top produits
- **FavoriteButton** : 401 silencieux (no console pollution)

### Tests Iteration 3
- Backend pytest 41/41 PASSED (30 régression + 11 nouveaux : 5 Stripe + 1 webhook + 3 POS cancel + 1 KPI dashboard + 1 WebSocket)
- Frontend 100% (0 console errors)
- Parcours E2E complet validé : activation PASS → commande → paiement CB/UC → préparation POS → retrait → KPI admin

### Récap Phase 1 MVP - 3 écrans critiques COMPLETS

#### Dashboard admin (`/lolodrive`)
- PASS actifs / Commandes période (7/30/90j) / LOLO POINTS / LOLO HOUR
- CA aujourd'hui / CA mois / UC en circulation / UC consommées
- Alertes opérationnelles
- Top 5 produits (30j)
- Répartition revenus Drive / Livraison / Lolo Point
- Engagement PASS (conversion, panier moyen, UC débités)
- Activité POS temps réel
- Accès rapide modules

#### Espace PASS client (`/pass`)
- Statut PASS + couleur expiration J-7/J-3
- Solde UC + date expiration
- Recharger UC (Stripe Checkout réel)
- Activer PASS (Stripe Checkout réel + mode démo)
- Catalogue essentiel (via lien `/catalogue-lolodrive`)
- Historique commandes
- Historique UC ledger
- Économies réalisées (calculé serveur)

#### POS LOLODRIVE (`/pos`)
- Commandes à préparer / prêtes / retirées / annulées
- Scan / recherche par n° commande
- WebSocket temps réel + fallback polling 30s
- Notification son sur nouvelle PAID
- Boutons workflow : Préparer / Marquer prêt / Remettre / Annuler+refund UC
- Vue compacte togglable


---

## Iteration 4 (22 mai 2026) — Phase 2 complète : LOLO HOUR / LOLO POINTS / CRM / Reporting

### Backend (15 nouveaux endpoints)
- **LOLO HOUR** :
  - `GET /api/lolodrive/events?scope=upcoming|live|ended|all` filtré + `reservations_count` + `remaining_stock`
  - `GET /api/lolodrive/events/{id}` détail (linked_products enrichis avec name/image/public_price)
  - `POST /api/lolodrive/events/{id}/reserve` (PASS requis si pass_only, limit/user, stock global)
  - `DELETE /api/lolodrive/events/{id}/reserve`
  - `GET /api/lolodrive/admin/events/{id}/reservations` (enrichi user_name/email)
  - `POST /api/lolodrive/admin/events/{id}/products` (linked_products + flash prices)
- **LOLO POINTS gérant** :
  - `GET /api/lolodrive/manager/my-point`
  - `GET /api/lolodrive/manager/my-orders`
  - `GET /api/lolodrive/manager/my-payout-preview`
- **Reporting** :
  - `GET /api/lolodrive/admin/kpi/timeseries?metric={revenue|orders|uc_consumed|pass_activations}&days=N` (agg MongoDB par jour)
- **CRM** :
  - `PATCH /api/crm/opportunities/{id}/stage` (drag-drop)
  - `PATCH /api/crm/tasks/{id}/status`
  - `PATCH /api/crm/dossiers/{id}/status`

### Frontend (4 pages réécrites + 1 nouvelle)
1. **`/admin/lolo-hour`** : tabs Planifiés/Live/Terminés, barres de stock, dialog "Détail" avec liste réservations, dialog "Lier produits" avec saisie flash price + UC
2. **`/lolo-point/dashboard`** (NEW) : page gérant — vue de SON point, ses commandes + filtres + commissions plafonnées
3. **`/crm`** : Kanban drag-and-drop natif HTML5 (7 colonnes pipeline), 4 dialogs création (contact/org/opp/tâche), toggle tasks done
4. **`/reporting-impact`** : 4 graphes Recharts (AreaChart CA, BarChart commandes, LineChart UC, BarChart PASS), sélecteur période 7/30/90j, export PDF via print + Export JSON, styles `@media print` dédiés

### Documentation
- `README.md` : section **Webhook Stripe en production** (config dashboard Stripe + STRIPE_WEBHOOK_SECRET)
- Phase2Banner retiré de LOLO HOUR / CRM / Reporting (devenues complètes)

### Tests Iteration 4
- Backend pytest **66/66 PASSED** (25 nouveaux iter4 + 41 régression iter1+2+3)
- Frontend 100% (tous les data-testid iter4 vérifiés, 0 console errors)
- 0 issues critiques / 0 mineures

### Phase 2 livraison complète
- ✅ LOLO HOUR — créer événements, stock, prix flash, accès PASS, réservations
- ✅ LOLO POINTS — gérer points relais, gérants dédiés (login), commandes du point, rémunération plafonnée
- ✅ CRM partenaires — pipeline drag&drop + contacts/orgs/oppos/dossiers/tâches étendus
- ✅ Reporting ESS avancé — graphes Recharts + export PDF + rapports investisseurs
- ✅ Webhook Stripe — déjà implémenté + instructions config prod documentées



## Iteration 5 (22 mai 2026) — Brevo Email + SMS transactionnels

### Backend
- **`/app/backend/brevo_service.py`** : nouveau service async (httpx + Brevo REST `/v3/smtp/email`, `/v3/transactionalSMS/sms`).
  - 3 helpers domaine : `notify_pass_activated`, `notify_order_ready`, `notify_pass_expiry_j3` (chacun envoie email **et** SMS, French templates inline).
  - `_normalize_phone` : convertit `06...`, `+33...`, `+590...` en E.164.
  - Best-effort : exceptions/échecs Brevo loggés mais ne cassent jamais le flux métier.
- **Hooks intégrés** :
  - `routes_lolodrive_checkout.py::_apply_payment_success` (kind=PASS) → email + SMS confirmation activation.
  - `routes_lolodrive_oscoop.py::pos_update_order_status` (status=READY) → email + SMS commande prête (avec nom du Lolo Point).
- **2 nouveaux endpoints admin** :
  - `POST /api/lolodrive/admin/notifications/test` — envoie un email + SMS au compte admin courant pour valider la config Brevo.
  - `POST /api/lolodrive/admin/notifications/pass-expiry-j3` — batch idempotent (marqueur `j3_notified_at`) pour les PASS qui expirent dans ~3 jours.

### Configuration
- `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, `BREVO_SMS_SENDER` dans `/app/backend/.env`.
- Sender email actuel : `no_reply@kdmarche-oscop.fr` (à vérifier dans dashboard Brevo pour la prod).

### Tests
- `backend/tests/test_brevo_service.py` : tests unitaires (normalize_phone, skip-when-unconfigured).
- Validation E2E réelle : `POST /admin/notifications/test` → Brevo retourne 201 (Email + SMS livrés, 12.1 crédits SMS consommés).
- Validation E2E ordre→READY → Brevo SMS+Email envoyés (logs httpx 201 Created).

### Backlog restant (P0/P1)
- 🗺️ **P0** : Carte Mapbox des Lolo Points (clé fournie : `pk.eyJ1IjoiZmVsaXhpYSIs...`).
- 🌍 **P0** : Multi-territoires (Guadeloupe, Martinique, Guyane, Réunion) — sélecteur admin + adaptation seed.
- 📊 **P1** : Dashboard Gérant Lolo Point étendu (graphes temporels + classement réseau).
- 🔐 **P1** : Scaffolding Google Login Emergent-managed (UI + routes, sans clés actives).
- ⏰ **P1** : Cron/scheduler pour appel automatique du batch PASS J-3 (actuellement déclenchable par admin manuellement).
