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
- 📊 **P1** : Dashboard Gérant Lolo Point étendu (graphes temporels + classement réseau).
- 🔐 **P1** : Scaffolding Google Login Emergent-managed (UI + routes, sans clés actives).
- ⏰ **P1** : Cron/scheduler pour appel automatique du batch PASS J-3 (actuellement déclenchable par admin manuellement).

## Iteration 6 (22 mai 2026) — Carte Mapbox + Multi-territoires DOM

### Backend
- `routes_lolodrive_oscoop.py` :
  - `LoloPointCreate` enrichi : `territory` (GP/MQ/GF/RE), `lat`, `lng`.
  - `GET /api/lolodrive/territories` → liste 4 DOM avec `center` et `zoom` par défaut.
  - `GET /api/lolodrive/lolo-points?territory=GP|MQ|GF|RE` → filtre serveur.
- `seed_lolodrive.py` : 10 Lolo Points sur 4 territoires (GP×4, MQ×2, GF×2, RE×2) avec coordonnées GPS réelles.

### Frontend
- `mapbox-gl@latest` ajouté via yarn ; `REACT_APP_MAPBOX_TOKEN` exposé dans `frontend/.env`.
- **`components/TerritorySelector.jsx`** : pills DOM + persistance `localStorage` (`kdm_territory`).
- **`components/LoloPointsMap.jsx`** : carte Mapbox dark-v11, marqueurs custom or/violet avec code territoire, popups info, `flyTo` au changement de territoire, `fitBounds` quand "Tous".
- **`pages/LoloPointsAdminPage.jsx`** : refactor — toggle Carte/Liste, sélecteur territoire, KPI dynamiques (territoires/villes), formulaire création enrichi (territory dropdown + lat/lng).
- `services/api.js` : `listLoloPoints` accepte `{city, territory}`, nouveau `listTerritories()`.

### Tests E2E (Playwright)
- Login admin → `/admin/lolo-points` → carte rendue (10 markers visibles).
- Filtre **Martinique** → 2 markers MQ centrés sur la Caraïbe, KPI = 2/1/2.
- Toggle Liste (MQ) → 2 cartes "Fort-de-France" & "Le Lamentin" avec badges MQ.
- Reset "Tous" → 10 markers, vue mondiale.

### Backlog restant (P1)
- ✅ Dashboard Gérant Lolo Point étendu — DONE itération 7
- ✅ Scaffolding Google Login Emergent-managed — DONE itération 7
- ✅ Cron/scheduler PASS J-3 automatique — DONE itération 7
- ✅ Multi-territoires sur catalogue / commandes — DONE itération 7

## Iteration 7 (22 mai 2026) — Sprint P1 complet (Manager dashboard + Google Auth + Scheduler + Territory filter)

### Backend
- **Manager dashboard étendu** :
  - `GET /api/lolodrive/manager/my-timeseries?days=7|30|90` → série quotidienne {date, orders, revenue_cents, fulfilled} via aggregation MongoDB (clamp 7-90).
  - `GET /api/lolodrive/manager/network-ranking?days=N` → classement de tous les Lolo Points actifs trié par revenue puis orders, avec `my_rank` du gérant connecté et `total_points`.
- **Google Auth Emergent-managed** (`routes_emergent_auth.py`) :
  - `POST /api/auth/emergent/session` → exchange `session_id` URL-fragment via Emergent `/session-data`, upsert user, set httpOnly cookie + retour JWT pour compat avec hooks existants.
  - `GET /api/auth/emergent/me` → vérifie cookie (timezone-aware expiry).
  - `POST /api/auth/emergent/logout` → supprime session DB + cookie.
  - Indexes `emergent_sessions` (session_token unique, user_id, expires_at).
- **Scheduler** (`scheduler.py`) :
  - asyncio task lancée au startup, intervalle 6h, idempotent via `j3_notified_at`, gating Brevo (`is_brevo_configured()`).
  - Crash protection : try/except autour de chaque itération.
- **Filtres territory** :
  - `GET /catalog/products?territory=GP|MQ|GF|RE` → produits avec `territories=[]` ou contenant le code (default = disponible partout).
  - `GET /pos/orders?territory=...` → résolution via `lolodrive_points.territory` puis $in sur les ids.

### Frontend
- **`/connexion`** : ajout du bouton "Continuer avec Google" (data-testid `google-login-btn`) qui démarre le flux Emergent OAuth.
- **`/auth/callback`** : nouvelle page (AuthCallbackPage.jsx) qui parse `#session_id=`, échange via backend, puis redirect `/dashboard`.
- **`LoloPointManagerPage`** : 2 nouvelles sections — *Performance* (AreaChart CA + BarChart commandes/jour, sélecteur 7j/30j/90j) et *Classement réseau* (tableau top 10 + ligne du gérant surlignée + badge "Mon rang : #N/Total").
- **`LolodriveCatalogPage`** : ajout du `TerritorySelector` global (persistance localStorage).
- **`Badge` component** : forward des props (`...rest`) pour permettre les data-testid (fix testing agent).

### Tests
- Backend pytest **11/11 PASSED** (`/app/backend/tests/test_iter5_p1.py`) — endpoints manager/oauth/territory/cron startup log.
- Frontend Playwright **100%** — tous les data-testid vérifiés (google-login-btn, auth-callback-page, manager-performance-section, manager-ranking-section, days-7/30/90-btn, my-rank-badge, catalog-territory-selector, rank-row-LP-CAP highlighted).

### Backlog restant
- ✅ Affinage `territories` sur produits seedés — DONE itération 8
- ✅ Auto-renouvellement opt-in du PASS — DONE itération 8
- ✅ Métriques Brevo (delivered/bounced) via webhooks — DONE itération 8

## Iteration 8 (22 mai 2026) — Sprint complet : Renaming + Public map + Brevo webhooks + Auto-renew + Parrainage

### Branding & UI Renaming (sans casser l'API)
- Toutes les routes (`/admin/lolo-points`, collections `lolodrive_points`, params `lolo_point_id`) **conservées** pour ne pas casser le code existant.
- Labels UI mis à jour partout :
  - "LOLO POINTS" / "Lolo Point" → **"Réseau LOLODRIVE"** / **"Relais LOLODRIVE"**
  - Pages affectées : LoloPointsAdminPage, LoloPointManagerPage, LolodriveAdminDashboardPage, LolodriveCatalogPage, PosLolodrivePage, EssReportingPage, LoloPointsMap.
- Landing page :
  - H2 : "Centrale d'Achats B2B ESS" → **"Communityplace coopérative B2B2C"**.
  - `officialStatement` reformulé (mutualisation coopérative, agrégation collective).

### Section publique : carte des relais LOLODRIVE sur la landing
- Nouveau composant `<PublicLolodriveMapSection>` dans `LandingPage.jsx`.
- Carte Mapbox avec sélecteur territoire (filtrage côté client), compteur de relais actifs, CTA "Devenir relais LOLODRIVE".
- Endpoint `/api/lolodrive/lolo-points` accessible sans auth (déjà public).

### Brevo webhooks transactionnels (délivrabilité)
- `routes_brevo_webhook.py` :
  - `POST /api/brevo/webhook` (public, optional `X-Brevo-Token`) → persiste les events dans `brevo_events` + agrège dans `brevo_metrics_daily`.
  - `GET /api/brevo/metrics/summary?days=N` → délivrés / rejetés / ouverts / `delivery_rate` / `bounce_rate` / `open_rate` / `by_event`.
- Reporting ESS : nouvelle section "Délivrabilité notifications" avec 4 KPI + alerte si `delivery_rate < 97%`.

### PASS Auto-renew + Parrainage
- `routes_pass_lifecycle.py` :
  - `POST /api/lolodrive/pass/auto-renew` `{enabled}` → bascule `is_auto_renew` sur le PASS.
  - `GET /api/lolodrive/pass/referral/me` → crée/retourne code unique format `KDM-XXXXXX` (idempotent).
  - `POST /api/lolodrive/pass/referral/claim` `{code}` → crédit +50 UC parrain & filleul, plafond 10/parrain.
  - `GET /api/lolodrive/pass/referral/stats` (admin) → top sponsors + stats globales.
- Indexes : `code` unique, `referee_user_id` unique (defense in depth).
- UI dans `PassSpacePage` :
  - Bouton "Activer/Désactiver le renouvellement auto" + label dynamique.
  - Section "Parrainage coopérateur" : code copiable + input claim + toast feedback.

### Affinage territories sur produits seedés
- 7 nouveaux SKUs locaux : Rhum agricole + Banane locale (GP/MQ), Manioc + Cachiri (GF), Vanille Bourbon + Achards + Sucre canne (RE).
- Produits génériques gardent `territories=[]` (disponibles partout).

### Tests — Iteration 6 report
- **Backend pytest 14/14 PASSED** (`/app/backend/tests/test_iter6_sprint.py`).
- **Frontend Playwright ~95%** — tous les flows critiques validés (1 mini point sur le label "Relais LOLODRIVE" du select fulfillment qui ne s'affiche que dans le Sheet panier — comportement attendu, vérifié manuellement).
- Brevo webhooks idempotent par jour (upsert+$inc), referral lifecycle complet (claim/conflict/self/unauthorized).

### Code review — Recommandations futures
- ✅ Brevo metrics days filter — DONE iter 9
- ✅ Idempotency strict claim parrainage — DONE iter 9
- ✅ Stripe auto-renew (soft) — DONE iter 9
- ✅ OG/Twitter meta sur landing — DONE iter 9

## Iteration 9 (22 mai 2026) — Sprint hardening : Auto-renew Stripe + Idempotency + OG/social + Brevo days filter

### Backend
- **`pass_auto_renew.py`** (nouveau) :
  - `create_pass_renewal_session(db, user_id)` : crée une Stripe Checkout session pré-tagged `auto_renew=True, kind=PASS` + insertion `payment_transactions` (status=initiated).
  - `run_auto_renew_batch(db)` : scanne `lolodrive_passes` avec `is_auto_renew=true, status=ACTIVE, ends_at ∈ [now, now+36h]`, génère un lien Stripe et envoie email+SMS Brevo "Renouveler en 1 clic". Throttle 7j via `renew_email_sent_at`. Datetime naive UTC (cohérence avec seed legacy).
- **`scheduler.py`** : appelle aussi `run_auto_renew_batch` à chaque cycle (toutes les 6h).
- **`routes_lolodrive_oscoop.py`** : `POST /api/lolodrive/admin/notifications/auto-renew-batch` (require_admin) pour déclencher manuellement.
- **`routes_brevo_webhook.py`** : `metrics/summary` filtre désormais sur `date >= cutoff` (clamp 1-365j, ISO YYYY-MM-DD lexicographique).
- **`routes_pass_lifecycle.py`** :
  - Idempotent ledger via `update_one({wallet_id, ref_id}, {$setOnInsert: ...}, upsert=True)` + crédit conditionnel sur `result.upserted_id is not None`.
  - Index unique `(wallet_id, ref_id)` partial sur lolodrive_wallet_ledger (n'impacte pas les rows legacy sans `ref_id`).
  - `ref_id` désormais formaté `REF-{claim_id}-{SPONSOR|REFEREE}` pour distinguer les 2 crédits du même claim.

### Frontend
- **`public/index.html`** : title "KDMARCHÉ × O'SCOP — Communityplace coopérative B2B2C" + meta description riche + 7 OG tags (type/title/description/site_name/locale/image/image:width|height|alt) + 4 Twitter tags. Image fallback Unsplash (Mapbox Static API bloquée par les URL restrictions du token).

### Tests — Iteration 7 report
- **Backend pytest 15/15 iter7 + 14/14 régression iter6 = 29/29 PASSED**.
- **Frontend OG/Twitter meta DOM scan 100%**.
- Validé : days clamp (0/-5 → 1, 9999 → 365), auto-renew throttle (1er run sent=1, immediate retrigger sent=0), idempotency (3× upsert → 1 crédit), payment_transactions tagged `auto_renew=true`.

### Backlog restant
- 🛡️ Stripe Subscriptions natives (rebill auto réel) — actuellement "soft" via lien email. Nécessite migration vers Stripe SubscriptionSchedule.
- 🖼️ Image OG personnalisée hostée sur le CDN Emergent (actuellement Unsplash générique Caraïbes).
- 🌐 i18n : extraire les labels FR pour préparer l'export en EN/ES (marchés DOM hispanophones futurs ?).
