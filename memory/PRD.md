# PRD — KDMARCHÉ / LOLODRIVE by O'SCOP

## Plateforme coopérative B2B2C — Centrale d'achats ESS Outre-mer

---

## 1. Original problem statement

Plateforme coopérative existante (KDMARCHÉ / LOLODRIVE by O'SCOP). L'objectif est de créer une interface web propre pour exploiter l'API V2 existante (moteur transactionnel : PASS Vie Chère, Wallet UC, Commandes, Stripe, Drive, POS, LOLO POINTS, LOLO HOUR) sans modifier les règles métier critiques. Le CRM O'SCOP est la couche relationnelle.

Exigences produit étendues :
- Intégrations Brevo (emails/SMS), Mapbox (géolocalisation)
- Multi-territoires (Guadeloupe, Martinique, Guyane, Réunion)
- Auto-renouvellement Stripe Subscriptions natives
- Système de parrainage idempotent
- Refonte UI Premium (Playfair Display, Or Métallisé)
- Scaffolding i18n (FR, EN, ES)
- **Charte graphique premium STRICTEMENT alignée sur le visuel fourni** (fond clair beige perle, accents or métallisé, typographies Playfair/Montserrat, palette Bleu Logistique #0B4D87 / Orange Énergie #FF7A00 / Violet Premium #6C4C8E / Vert Lime #8CC63E / Rose Magenta #E6007E / Rouge Corail #FF5A4A / Or Métallisé #D4AF37)

## 2. Architecture

### Frontend — React + TailwindCSS + Shadcn UI
- `/app/frontend/src/index.css` — Charte premium (variables CSS officielles + overrides Tailwind)
- `/app/frontend/src/App.css` — Utility classes light premium (.glass-panel, .btn-gold, .mini-card, .pill, etc.)
- `/app/frontend/src/components/` — NavBar, Footer, Header, LolodriveLayout, LoloPointsMap, TerritorySelector, LanguageSwitcher
- `/app/frontend/src/pages/` — 41 pages (Landing, Login, Register, Catalog, PassSpace, Logiscop, Oscop, Admin, SuperAdmin, etc.)
- `/app/frontend/src/i18n/` — i18next FR/EN/ES

### Backend — FastAPI + MongoDB (Motor)
- `/app/backend/server.py` — App FastAPI principale
- `/app/backend/routes_lolodrive_oscoop.py`
- `/app/backend/routes_lolodrive_checkout.py` — Stripe Checkout
- `/app/backend/routes_pass_subscription.py` — Stripe Subscriptions natives (auto-renew)
- `/app/backend/routes_pass_lifecycle.py` — Parrainage idempotent
- `/app/backend/routes_brevo_webhook.py` — Webhooks Brevo
- `/app/backend/routes_emergent_auth.py` — Google Login (scaffolding)
- `/app/backend/brevo_service.py` — Emails/SMS transactionnels
- `/app/backend/scheduler.py` — Cron PASS J-3 + auto-renew batch
- `/app/backend/seed_lolodrive.py` — Seed dataset démo

### Data model (MongoDB)
- `users` : {email, role, is_admin, contact_name, company_name, credits, subscription, created_at}
- `lolodrive_passes` : {user_id, status, balance_uc, activated_at, expires_at, is_auto_renew}
- `pass_referrals` : {wallet_id, ref_id, bonus_uc} — index unique (wallet_id, ref_id)
- `lolodrive_orders` : {user_id, status, total_cents, territory, lolo_point_id}
- `lolodrive_points` : {code, manager_user_id, lat, lng, territory}

## 3. Implementation timeline

### Iter 1-7 (sprints précédents) — DONE
- Brevo (emails + SMS)
- Mapbox (cartes admin & publique funnel)
- Multi-territoires DOM-TOM
- Dashboard gérant étendu (graphes, classement)
- Scaffolding Google Login
- Renaming UI "LOLODRIVE" (DB conserve "lolo_points")
- Webhooks Brevo (jours filter reporting)
- Parrainage PASS idempotent (index unique)
- Stripe Subscriptions natives (auto-renew)
- Charte graphique premium v1 (Or/Vert Lime, Playfair/Montserrat, OG image)
- Pages institutionnelles LOGI'SCOP & O'SCOP
- Scaffolding i18n FR/EN/ES

### Iter 8 (22 mai 2026) — Charte Premium Visuelle (DONE)
**Demande utilisateur** : la charte graphique doit ÊTRE EXACTEMENT comme la pièce jointe (fond clair premium, palette officielle, typographies Playfair/Montserrat).

**Implémenté** :
- 🎨 Fond clair premium : `linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)` avec halos or radiaux
- 🪙 Variables CSS root alignées : `--bg`, `--text`, `--gold`, `--green`, `--shadow`, `--font-display`, `--font-body`
- 🎨 Palette officielle exposée : `--kdm-bleu-logistique`, `--kdm-orange-energie`, `--kdm-violet-premium`, `--kdm-vert-lime`, `--kdm-rose-magenta`, `--kdm-rouge-corail`, `--kdm-or-metallise`, `--kdm-beige-perle`, `--kdm-anthracite`
- 🪙 Shadcn `@layer base` tokens light : `--background: 38 60% 96%`, `--foreground: 217 30% 18%`, `--border: 38 35% 84%`, etc.
- 🌟 Utility classes refondues (`/app/frontend/src/App.css`) : `.glass-panel`, `.glass-panel-soft`, `.btn-gold`, `.btn-ghost`, `.badge-status`, `.pill`, `.mini-card`, `.callout-gold`, `.ribbon`, `.card-highlight`, `.icon-dot`, `.logo-gold`, `.logo-green`, `.check-icon`, `.cross-icon` — toutes en version light premium
- 🪄 CSS overrides globaux (sans toucher au JSX) : remappent automatiquement `text-white/X`, `bg-white/X`, `border-white/X`, `bg-black/X`, et tous les hex foncés `bg-[#070A10]`, `bg-[#0a0d14]`, `bg-[#0c0f15]`, etc. vers anthracite/cream
- 🧭 NavBar/Footer/Header/LolodriveLayout : inline styles `rgba(7,10,16)` → `rgba(255,253,247)` light + bordures dorées
- 📜 Replace global multi-fichier (19 pages) du `linear-gradient(#05070C → #070A10 → #060913)` vers `linear-gradient(#FBF6EE → #F5EBD8 → #FBF6EE)`
- 🪞 LolodriveLayout : titre dégradé bleu logistique → or → métallisé (au lieu de blanc/or sur fond noir)
- 📐 Scrollbar premium : track beige perle + thumb gold gradient
- ✅ Inputs & forms : fond blanc, bordure or métallisé, focus or glow
- ✅ Sélections : highlight or métallisé translucide

**Validation** : Screenshots vérifiés sur Landing, Offers, LOGI'SCOP, O'SCOP, Login, Dashboard authentifié, SuperAdmin — rendu conforme à la charte fournie (fond perle, ribbons or, typographies Playfair/Montserrat, palette officielle).

### Iter 9 (22 mai 2026) — Code Quality Review (Phase 1 + 2) (DONE)
**Demande utilisateur** : appliquer les corrections de la revue de code (Phase 1 quick wins + Phase 2 React hook deps).

**Phase 1 — Backend** :
- 🔴 Circular import `routes_ess.py` ↔ `routes_v1_logiscop.py` brisé : extraction des constantes partagées (`DELIVERY_POLICY`, `DEFAULT_ROUTE_POLICY`, `ESS_ROUTE_TARIFFS`) dans le nouveau module `/app/backend/routes_logistics_shared.py`. DAG unidirectionnel rétabli.
- 🔴 Variable `ROUTE_POLICY` undefined (routes_ess.py:541) → corrigée en `DEFAULT_ROUTE_POLICY`.
- 🔴 Hardcoded test secrets (5 fichiers) → migration vers `os.environ.get()` avec fallback depuis `/app/backend/.env.test` (gitignored). Ajout de `tests/conftest.py` qui charge `.env.test` automatiquement.
- 🟡 Insecure random (5 fichiers) : migration `random.randint/choices` → `secrets.randbelow/choice` dans `routes_ess.py`, `routes_signature.py`, `routes_pod.py`, `routes_contracts.py`, `seed_ess_route_data.py`.
- 🟡 Dynamic imports (`__import__('datetime')`) dans `test_server.py` → import top-level `from datetime import datetime, timezone`. Bonus : `datetime.utcnow()` → `datetime.now(timezone.utc)` (timezone-aware).
- 🟡 Bonus auto-fix : 20 f-strings vides supprimés via `ruff --fix`.

**Phase 1 — Frontend (Array index keys, 8 occurrences sur 6 fichiers)** :
- `OffersPage.jsx` (2x), `RegisterPage.jsx`, `PosLolodrivePage.jsx`, `StatsPage.jsx` (3x), `SuperAdminPage.jsx` (2x), `VendorSpacePage.jsx` → clés stables basées sur `id`/`code`/`name` au lieu de l'index.

**Phase 2 — React hook deps** :
- 4 useEffect avec dépendances mal détectées (false positives ESLint pour fonctions stables) : ajout de `// eslint-disable-next-line react-hooks/exhaustive-deps` documentés (ne pas créer de boucles infinies).
- Fichiers traités : `WalletPage.jsx` (2 hooks), `VendorSpacePage.jsx`, `OnboardingPage.jsx`, `PaymentReturnPage.jsx`.
- Les 3 autres signalés (`NotificationsHistoryPage`, `ShoppingListsPage`, `ShoppingListDetailPage`) utilisent déjà `useCallback` avec deps correctes — false positives du rapport.

**Validation** : Backend redémarre OK (Health 200, login admin OK, ESS endpoints OK), frontend lint propre, tous les pages public + admin testées via screenshot.

### Iter 11 (22 mai 2026) — Réconciliation Stripe Admin (DONE)
**Demande utilisateur** : page admin "Réconciliation Stripe" avec commandes/PASS/recharges par jour, totaux par compte, lien Stripe Dashboard, export CSV pour comptable.

**Implémenté** :
- 🆕 Backend : `/app/backend/routes_stripe_reconciliation.py`
  - `GET /api/admin/stripe/reconciliation` : agrégation Mongo par jour + par kind + totaux par compte (oscop/kdmarche)
  - `GET /api/admin/stripe/reconciliation/export.csv` : export CSV `;`-delimited (compatible Excel FR) — colonnes: date, session_id, account, kind, montant EUR/cents, user, email, ref pack/order, applied_by
  - Filtre date range (date_from/date_to, défaut J-30 → aujourd'hui)
  - Sécurité : admin-only (`is_admin` requis), 403 sinon
- 🆕 Frontend : `/app/frontend/src/pages/StripeReconciliationPage.jsx`
  - Route `/admin/stripe-reconciliation`
  - Filtres date du/au + bouton Actualiser + Export CSV (download direct)
  - 3 cartes totaux : Global / O'SCOP (bleu logistique) / KDMARCHE (or métallisé) avec lien externe vers Stripe Dashboard
  - Graphique stacked bar quotidien (Recharts) avec tooltip FR
  - 2 cartes "Détail par produit" : PASS / Recharges / Commandes par compte
  - Badge "MODE LIVE" (vert) / "MODE TEST" (rouge) selon `STRIPE_MODE`
- 🔗 Lien ajouté dans NavBar admin
- ✅ Validation : screenshot OK, totaux corrects (60€ PASS test affiché), CSV téléchargeable, 403 pour non-admin

### Iter 12 (22 mai 2026) — Auto-refund Stripe (charge.refunded) (DONE)
**Demande utilisateur** : ajouter `charge.refunded` au webhook → reversal automatique des UC + PASS + ORDER.

**Implémenté** :
- 🆕 `payment_transactions` enrichi : `payment_intent_id` (persistance) + `refund_status` (`full`/`partial`/null) + `refund_amount_cents` + `refunded_at` + `refunded_by`
- 🆕 Webhook gère `charge.refunded` :
  - Mapping via `payment_intent` → `payment_transaction`
  - **Refund total** (`amount_refunded >= amount`) : claim atomique → reversal via `_apply_payment_refund(tx)`
  - **Refund partiel** : log WARNING + événement CRM `payment.refunded.partial` (pas d'auto-reversal, admin review)
- 🆕 `_apply_payment_refund(tx)` — miroir de `_apply_payment_success` :
  - `PASS` → `status=REFUNDED`, wallet -= 600 UC, ledger DEBIT (`reason=PASS_REFUND`)
  - `RECHARGE` → wallet -= pack.uc, ledger DEBIT (`reason=RECHARGE_REFUND`)
  - `ORDER` → `order.status=REFUNDED`, broadcast WS admin
- 🛡️ Wallet peut devenir **négatif** (UC déjà dépensées non récupérables) → événement CRM `wallet.negative_after_refund` pour suivi admin
- 📌 `payment_intent_id` aussi capturé lors du polling `/status/<id>` (backfill incluant transactions déjà appliquées)

**Tests E2E validés** :
- ✅ Webhook signé `charge.refunded` full → HTTP 200, `refund_status=full`, wallet 2300 → 1700 (-600 UC), ledger DEBIT `PASS_REFUND`
- ✅ Idempotence : 2e webhook = no-op (wallet reste 1700)
- ✅ Refund partiel → `refund_status=partial`, wallet intouché, log WARNING + CRM event

### Iter 13 (22 mai 2026) — Réconciliation Stripe : Refunds dans le dashboard + Brevo webhook sécurisé (DONE)

**Demande utilisateur** : étendre la page Réconciliation Stripe pour inclure les statuts et montants des remboursements ; durcir le webhook Brevo.

**Implémenté — Backend** :
- 🆕 `GET /api/admin/stripe/reconciliation/transactions` : liste plate paginée des transactions avec colonnes refund (`refund_status`, `refund_amount_cents`, `refunded_at`, `refunded_by`, `net_amount_cents`).
  - Filtres : `status_filter` (`all` / `paid` / `refunded_full` / `refunded_partial` / `refunded`), `account` (`oscop` / `kdmarche`), `date_from`, `date_to`, `limit`, `skip`.
  - Email du payeur résolu en batch (1 requête `users` quel que soit le nombre de transactions).
- 🔒 Webhook Brevo durci (`routes_brevo_webhook.py`) :
  - **Refuse désormais 401 si `BREVO_WEBHOOK_TOKEN` n'est pas configuré** (avant : acceptait silencieusement). Fail-fast en prod.
  - Token accepté via header `X-Brevo-Token` **OU** query param `?token=...` (fallback pour les configurations Brevo qui n'autorisent pas les headers custom).
  - Log warning avec IP source si token invalide.

**Implémenté — Frontend** :
- 🆕 `StripeReconciliationPage.jsx` enrichie :
  - 3 cartes globales : **Total encaissé brut / Total remboursé / Net comptable**
  - Cartes par compte : ajout de 3 mini-stats internes (`Remboursé total`, `Partiels`, `Net`) avec couleurs sémantiques (rouge corail #E64432 pour refunds, or pour total, bleu pour net).
  - Tableau "Détail des transactions" avec colonnes Date / Compte / Type / Email / **Brut / Remboursé / Net** / Statut.
  - Badges de statut : `Encaissé` (vert lime), `Remboursé` (rouge corail), `Partiel` (ambre).
  - Filtres : Statut (4 options) + Compte (oscop/kdmarche).
  - Pagination (25/page) avec contrôles Précédent/Suivant.
  - Graphique quotidien bascule sur `net_eur` (brut − remboursé) au lieu du brut seul.

**Tests E2E validés** :
- ✅ `GET /api/admin/stripe/reconciliation/transactions` filtre par `status_filter` (paid/refunded_full/refunded_partial) — comptages corrects.
- ✅ Filtre par `account` (oscop/kdmarche) — comptages corrects.
- ✅ Brevo webhook sans token → 401, token invalide → 401, header valide → 200, query param valide → 200.
- ✅ Screenshot UI conforme à la charte (badges, couleurs, hover, tableau responsive).

### Iter 15 (22 mai 2026) — Tests Jest verrouillant le contrat hooks (DONE)
**Demande utilisateur** : ajouter des tests pour empêcher la régression des hooks (1 effet par axe).

**Implémenté** :
- 🆕 `/app/frontend/src/setupTests.js` — polyfill `TextEncoder`/`TextDecoder` (requis par react-router v7 sous JSDOM) + `matchMedia` stub.
- 🆕 `/app/frontend/craco.config.js` enrichi avec une section `jest.configure` :
  - `moduleNameMapper` pour bypass le `exports` map de react-router-dom v7 → entrées CJS explicites.
  - Mirror de l'alias webpack `@/` → `<rootDir>/src/`.
- 🆕 Deps dev : `@testing-library/react@16`, `@testing-library/jest-dom@6`, `@testing-library/dom`, `@testing-library/user-event`.
- 🆕 `PublicLolodriveMapSection` exposé en **named export** depuis `LandingPage.jsx` pour pouvoir être monté en isolation.
- 🆕 `src/pages/LandingPage.test.jsx` (3 tests) :
  - Au montage : 1 appel `listTerritories` + 1 appel `listLoloPoints({territory: undefined})`.
  - Changement de territoire : `listLoloPoints` re-fetched avec le nouveau territoire, `listTerritories` jamais rappelé.
  - 3 changements consécutifs → exactement 4 appels `listLoloPoints` (1 mount + 3 changes) → pas de boucle infinie.
- 🆕 `src/pages/LolodriveCatalogPage.test.jsx` (4 tests) :
  - Non authentifié → redirection `/connexion`, aucun fetch catalogue/points.
  - Authentifié au montage → 1 territoires + 1 catalogue + 1 lolo-points.
  - Changement de territoire → catalogue + points re-fetched, territoires PAS rappelés.
  - 2 changements → exactement 3 appels `catalogProducts` (pas de boucle).

**Validation** :
- ✅ `CI=true yarn test --watchAll=false` → **7/7 tests pass**.
- ✅ Frontend dev server toujours HTTP 200 (`craco.config.js` n'impacte le webpack qu'en mode test).

### Iter 14 (22 mai 2026) — Refactor React hooks deps (zéro `eslint-disable`) (DONE)
**Demande utilisateur** : éliminer les 8 `eslint-disable-next-line react-hooks/exhaustive-deps` documentés dans le code.

**Refactors appliqués** :
- `WalletPage.jsx` — `pollPaymentStatus` enveloppé `useCallback([navigate])`, effet payment-return `[searchParams, navigate, pollPaymentStatus]`.
- `VendorSpacePage.jsx` — `fetchDashboard`/`fetchProducts`/`fetchCountries` en `useCallback` typés sur leurs deps réelles (`vendorId`, `statusFilter`), effet de chargement `[fetchDashboard, fetchProducts, fetchCountries]`.
- `LoloPointsMap.jsx` — territory initial capturé via `useRef(territory).current`, deps `[]` honnêtes (effet `flyTo` séparé sur `[territory]` existait déjà).
- `PaymentReturnPage.jsx` — disable retiré : tous les refs internes (`lolodriveAPI`, constantes, setters) sont module-level / stables, deps `[sessionId]` correctes.
- `OnboardingPage.jsx` — disable retiré : pareil, deps `[navigate]` correctes.
- `LoloPointsAdminPage.jsx` — `load()` scindé en deux effets : `useEffect([])` charge les territoires une fois ; `loadPoints` en `useCallback([territory])` charge les points sur changement de territoire. Alias `load = loadPoints` conservé pour boutons "Actualiser".
- `LandingPage.jsx` (`PublicLolodriveMapSection`) — scindé en deux effets : territoires une fois, points sur `[territory]`.
- `LolodriveCatalogPage.jsx` — scindé : territoires une fois ; catalogue + lolo-points sur `[navigate, filter, territory]`, reset de `selectedPoint` via setter functional `setSelectedPoint(prev => …)` pour éviter la dep instable.

**Validation** :
- ✅ `grep -rn eslint-disable.*exhaustive-deps src/` → **zéro occurrence** restante.
- ✅ ESLint global propre sur `/app/frontend/src`.
- ✅ Smoke tests sur les 6 pages affectées + Landing : aucune erreur console, comportement préservé.

## 4. Backlog

### P1 — Internationalisation
- Wrapper toutes les chaînes UI restantes avec `t()` (scaffolding i18n déjà en place)

### P2 — Test E2E LIVE (en attente coordination utilisateur)
- Effectuer un paiement réel de 1€ → déclencher un remboursement Stripe dashboard → vérifier que `charge.refunded` met bien à jour `refund_status=full` et que les UC du PASS sont annulées.

### P2 — Auth Google
- Brancher Google Login (Emergent-managed) avec `GOOGLE_CLIENT_ID` / `SECRET` fournis par l'utilisateur

### P2 — Stripe LIVE
- Bascule `STRIPE_MODE=live` quand l'utilisateur valide la mise en production (clé Live déjà dans le pod)

## 5. Test credentials
Voir `/app/memory/test_credentials.md`

## 6. Integrations
| Service | Statut | Mode |
|---|---|---|
| Stripe **O'SCOP** (PASS, recharges, livraisons) | ✅ **LIVE ACTIVÉ** | `sk_live_51ScyApLY9Vt...` + webhook signé |
| Stripe **KDMARCHE** (commandes produits DRIVE) | ✅ **LIVE ACTIVÉ** | `sk_live_51FqczfCo8uj...` + webhook signé |
| **Google OAuth natif KDMARCHE** | ✅ Actif | Branding KDMARCHE |
| Google OAuth Emergent-managed | ✅ Fallback | Disponible |
| Brevo Email + SMS | ✅ Configuré | API key dans `.env` |
| Mapbox GL | ✅ Configuré | `REACT_APP_MAPBOX_TOKEN` |

### Architecture Stripe multi-comptes (LIVE)
Centralisée dans `/app/backend/stripe_accounts.py`. Routage automatique :
- `kind=PASS` / `RECHARGE` / `SUBSCRIPTION` → compte **oscop** (sk_live_51ScyApLY...)
- `kind=ORDER` (commandes DRIVE) → compte **kdmarche** (sk_live_51FqczfCo...)
- Webhook unique `/api/webhook/stripe` essaie les 4 secrets configurés (`STRIPE_WEBHOOK_SECRETS_OSCOP` + `STRIPE_WEBHOOK_SECRETS_KDMARCHE`, chacun supportant TEST + LIVE en CSV).
- Signature obligatoire → 400 si invalide.
- SDK Stripe officiel utilisé directement (pas `emergentintegrations.payments.stripe.checkout` qui rerouatait vers un proxy stub via `INTEGRATION_PROXY_URL`).
- Idempotence atomique : claim `update_one({applied:{$ne:True}})` empêche les double-applications (polling + webhook race-safe).

### Bascule TEST ↔ LIVE
Mode contrôlé par `STRIPE_MODE` dans `/app/backend/.env`:
- `STRIPE_MODE=test` → `STRIPE_API_KEY` + `STRIPE_KDMARCHE_API_KEY` (sk_test_*)
- `STRIPE_MODE=live` → `STRIPE_LIVE_KEY` + `STRIPE_KDMARCHE_LIVE_KEY` (sk_live_*) ← **ACTUEL**
Toujours `sudo supervisorctl restart backend` après changement (force le rechargement des modules).
