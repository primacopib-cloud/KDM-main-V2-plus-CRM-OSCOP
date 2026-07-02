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
- 🆕 `PublicLolodriveMapSection` exposé en **named export** depuis `LandingPage.jsx`.
- 🆕 `src/pages/LandingPage.test.jsx` (3 tests) — verrouille `1 listTerritories + N listLoloPoints`.
- 🆕 `src/pages/LolodriveCatalogPage.test.jsx` (4 tests) — verrouille auth-gate + contrat hooks catalogue.

**Validation** : `CI=true yarn test --watchAll=false` → 7/7 pass.

### Iter 16 (23 mai 2026) — Pont GED ESS externe : intégration légère contrôlée (DONE)
**Demande utilisateur** : intégrer le ZIP `KDM-main-V2-plus-CRM-OSCOP-main-GED-bridge.zip` en câblant le pont GED ESS externe sans remplacer la GED interne, et sans refactorer massivement `server.py`.

**Implémenté** :
- 🆕 `backend/ged_external_client.py` — client async `httpx` (Bearer + HMAC `X-GED-ESS-Signature`).
- 🆕 `backend/routes_ged_bridge.py` — routeur `/api/ged-bridge/*` admin-only :
  - `GET /health`, `GET /scopes`, `GET /sync-events`, `POST /documents`, `POST /pdf/generate`
  - `POST /crm/dossiers/{id}/push` (template `OSCOP_CONTRAT_COOPERATIF`) → met à jour `crm_dossiers.ged_external_document_id`
  - `POST /lolodrive/orders/{id}/push` (template `KDMARCHE_APPEL_CONTRIBUTION`)
- 🆕 Collection `ged_bridge_sync_events` (audit), 3 indexes Mongo créés au startup.
- 🪶 `server.py` enrichi de **9 lignes** seulement (zéro refactor).
- 🆕 `/app/backend/.env.example` documenté avec toutes les vars critiques.
- 🆕 `/app/docs/GED_ESS_BRIDGE.md`.

### Iter 17 (23 mai 2026) — Pont GED stabilisation + page admin minimaliste (DONE)
- `GET /api/ged-bridge/health` ré-écrit : statut **OK / DEGRADED / DISABLED** + diagnostic config (toujours HTTP 200).
- `GET /api/ged-bridge/sync-events` enrichi : `{events, counts}` + filtre `status=`.
- 🆕 `POST /api/ged-bridge/sync-events/{id}/retry` — rejoue un événement en échec.
- 🆕 Frontend `/admin/ged-bridge` (`GedBridgeAdminPage.jsx`) : carte santé + 3 compteurs + tableau sync-events avec filtres + bouton "Re-pousser" sur chaque erreur. Lien ajouté dans NavBar.

- Lien "Pont GED ESS" ajouté dans NavBar.

### Iter 18 (23 mai 2026) — Badge "Client" visible + personas démo + GED activée (DONE)
- `LogisticsSection.jsx` : badge Client passé en bleu logistique #1F4D87 (lisible sur fond crème).
- Seed `/app/backend/seed_demo_personas.py` (idempotent) : ajoute vendeur pro `vendor-pro@kdmarche.fr` (Distillerie Damoiseau + 3 produits), acheteur B2B `acheteur-pro@kdmarche.fr` (Restaurant La Caravelle + 250 crédits), commande de réassort LP pour gérant existant.
- Activation GED interne : 4 documents de référence (`convention`, `cg-oscop`, `cgv-kdmarche`, `note-preventive`) en statut PUBLISHED.

### Iter 19 (23 mai 2026) — Microservice finance-api séparé (P1 → P5) (DONE)
- 📂 `/app/finance-api/` projet FastAPI indépendant (SQLAlchemy 2.x, JWT, SQLite en dev / PostgreSQL en prod)
- 13 endpoints opérationnels : `/health`, `/setup/bootstrap`, `/auth/token`, `/parties`, `/receivables`, `/payments` (+ mark-paid + refund), `/sepa/mandates` (+ activate/revoke), `/installment-plans`, `/webhooks/{stripe,gocardless}`, `/reporting/dashboard`, `/ledger/entries`, `/audit/verify-ledger-chain`
- **Journal financier chaîné** SHA-256 — tamper-test validé (altération `payload_json` détectée à la séquence exacte)
- Port 8030 en sandbox (8010 occupé par infra Emergent), 8010 documenté pour prod
- Bootstrap admin : `admin@finance.kdm-oscop.fr` / `AdminFinance2026!`
- Aucun changement sur le backend KDM.

### Iter 20 (23 mai 2026) — Bouton "Retour à la page précédente" global back-office (DONE)
- 🆕 `BackButton.jsx` (~50 lignes) monté une seule fois dans `App.js`, 15 patterns regex de routes back-office.
- Style pastille glass-morphism bleu logistique #1F4D87, position fixed top-left sous NavBar, responsive.
- Validation Playwright sur 9 routes : pages publiques sans bouton, back-office avec bouton.

### Iter 21 (23 mai 2026) — P6 + P7 : bridge KDM ↔ finance-api + page admin (DONE)
- 🆕 `backend/finance_external_client.py` + `routes_finance_bridge.py` (8 routes admin-only, journal Mongo).
- 🆕 Frontend `/admin/finance-bridge` : santé + 3 compteurs + tableau sync-events + 2 actions rapides.
- `server.py` : 9 lignes ajoutées, zéro refactor. Tests curl + Playwright OK.

### Iter 22 (14 juin 2026) — P8 : SDK Stripe + GoCardless réels dans psp_adapters (DONE)

**Demande** : brancher les vrais SDK Stripe + GoCardless dans `finance-api/app/services/psp_adapters.py`.

**Implémenté** :
- 🆕 Dépendances : `stripe>=10.0` (14.1.0) et `gocardless-pro>=2.0` (3.4.1) ajoutées au `requirements.txt`.
- 🆕 `psp_adapters.py` ré-écrit avec **vraies intégrations SDK** :
  - **Stripe** : `_stripe_checkout()` utilise `stripe.checkout.Session.create(mode='payment', payment_method_types=['card'], …)`. `_stripe_refund()` utilise `stripe.Refund.create(payment_intent=…)` avec les `reason` valides Stripe + fallback metadata. Métadonnées flatten en string.
  - **GoCardless** : `_gocardless_billing_request()` utilise `client.billing_requests.create()` + `client.billing_request_flows.create()` pour la page de signature hébergée (mandate + first payment). `_gocardless_refund()` utilise `client.refunds.create()`.
  - **Manual** : conservé pour les tests.
  - **Fail-soft** : si clé absente → `status: "FAILED"` avec `raw.error` clair, **jamais de crash**.
- 🆕 Vérification de signature webhooks :
  - `verify_stripe_signature()` utilise `stripe.Webhook.construct_event(payload, sig, secret)`. Retourne le `Event` parsé ou `None` (secret manquant / signature invalide).
  - `verify_gocardless_signature()` utilise `gocardless_pro.webhooks.parse()`. Nouvelle var env `GOCARDLESS_WEBHOOK_SECRET` (séparée du token API).
- 🆕 `routes/webhooks.py` enrichi : lit le header (`Stripe-Signature` / `Webhook-Signature`), tente la vérification, stocke `signature_valid: bool` dans `WebhookEvent`. Idempotence conservée. Réponses incluent `signature_valid` pour debug admin.
- 🆕 `/health` expose maintenant `stripe_webhook_configured`, `gocardless_env`, `gocardless_webhook_configured`.

**Tests E2E (sandbox)** :
- ✅ Manual PSP : payment created `status=PENDING`, hosted_url `manual_session_*` (toujours fonctionnel).
- ✅ Stripe sans clé : `status=FAILED`, `failure_reason="STRIPE_SECRET_KEY non configurée — adaptateur Stripe non opérationnel."`
- ✅ Stripe avec clé bidon `sk_test_FAKE_…` → SDK appelé pour de vrai → erreur remontée propre : `"Stripe error: Invalid API Key provided: sk_test_****LLED"`. Confirme que le SDK est wired (pas un mock).
- ✅ GoCardless sans token : `status=FAILED`, message clair.
- ✅ GoCardless avec token bidon → SDK appelé → `"GoCardless error: The access token you've used is not a valid sandbox API access token"`. SDK wired.
- ✅ Webhook Stripe sans signature → 200, `signature_valid: false`, événement stocké.
- ✅ Webhook Stripe rejoué (même `id`) → 200, `duplicate: true`. Idempotence OK.

**État production** :
- `.env` final restauré sans clés → finance-api démarre, `/health` retourne `stripe_configured: false, gocardless_configured: false` (DISABLED clean).
- Pour activer en prod : remplir `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `GOCARDLESS_ACCESS_TOKEN` + `GOCARDLESS_WEBHOOK_SECRET` + redémarrer.



**P6 — Bridge backend** :
- 🆕 `/app/backend/finance_external_client.py` (~180 lignes) : client `httpx` synchrone vers finance-api avec auto-login OAuth2 password, cache JWT en mémoire, retry une fois sur 401 (refresh token), erreurs typées `FinanceExternalError`.
- 🆕 `/app/backend/routes_finance_bridge.py` (~280 lignes) : routeur admin-only `/api/finance-bridge/*` :
  - `GET /health` → 200 + statut OK/DEGRADED/DISABLED + relais santé finance-api
  - `POST /parties/from-customer/{customer_id}` — idempotent (réutilise via `external_customer_id`)
  - `POST /receivables/from-order/{order_id}` — résout/crée le party d'abord
  - `POST /payments/create`, `POST /installment-plans/create`, `POST /sepa/mandates/create` — passthrough avec audit
  - `GET /sync-events` — journal local Mongo + counts agrégés
- 🪶 `server.py` enrichi de **9 lignes** (import + `set_finance_bridge_database` + `include_router` + `ensure_finance_bridge_indexes` au startup). Zéro refactor.
- 🆕 4 vars env dans `/app/backend/.env` (`FINANCE_API_URL=http://localhost:8030`, `FINANCE_API_EMAIL`, `FINANCE_API_PASSWORD`, `FINANCE_API_TIMEOUT_SECONDS=20`). `.env.example` mis à jour.
- Collection Mongo `finance_bridge_sync_events` (id unique, indexes (source, source_id, created_at) + (status, created_at)).

**P7 — Page admin frontend** :
- 🆕 `/app/frontend/src/pages/FinanceBridgeAdminPage.jsx` (~340 lignes) — page `/admin/finance-bridge` :
  - Carte santé (OK vert / DEGRADED ambre / DISABLED gris) + version + diagnostic config
  - 3 compteurs (Total / Succès / Erreurs)
  - **Actions rapides** : 2 inputs + boutons pour pousser un client KDM ou une commande LOLODRIVE vers finance-api
  - Filtres Statut + Source, tableau sync-events
  - Lien "Pont Finance" (icône CreditCard) ajouté dans NavBar admin

**Tests E2E (curl + Playwright)** :
- ✅ `/api/finance-bridge/health` (admin) → `bridge:OK, status:OK, external_finance: {bootstrap_done: true, version: 0.1.0}`
- ✅ `/parties/from-customer/user-buyer-pro` → SUCCESS ; 2ème appel → SUCCESS_IDEMPOTENT (party réutilisé)
- ✅ `/parties/from-customer/unknown` → 404
- ✅ `/receivables/from-order/order-lp-gerant-1` → créance "LD-LP-20260518-J1K2L3" 260€ créée + party résolu
- ✅ `/sync-events` → counts agrégés, 5 entrées SUCCESS
- ✅ `/health` sans auth → 403
- ✅ Page admin `/admin/finance-bridge` : badge OK vert "Opérationnel", boutons "Pousser" fonctionnels, toasts succès, **aucune erreur runtime** après fix du SyntheticEvent passing.


**Demande utilisateur** : ajouter un bouton de retour à la page précédente sur toutes les pages du back office.

**Implémenté** :
- 🆕 `/app/frontend/src/components/BackButton.jsx` (~50 lignes) — composant flottant unique :
  - Détecte la route courante via `useLocation()` et 15 patterns `BACK_OFFICE_PATTERNS` (admin*, super-admin, vendor, crm, lolodrive, lolo-point, pos, reporting-impact, etc.)
  - Clic → `navigate(-1)` ; si `window.history.length === 1` (onglet fraîchement ouvert sur une URL admin) → fallback `/admin`
  - `data-testid="back-office-back-btn"` pour les tests E2E
- 🆕 Style `.back-office-back-btn` dans `App.css` : pastille flottante glass-morphism bleu logistique (#1F4D87), position fixed top-left sous la NavBar, responsive (mobile : plus petit).
- 🆕 Monté **une seule fois** dans `App.js` à l'intérieur de `<BrowserRouter>` (avant `<Routes>`). Aucune modification des 14+ pages back-office individuelles.

**Tests E2E (playwright auto)** :
- ✅ Public : `/`, `/catalogue-lolodrive` → bouton **ABSENT** (pas de pollution UX)
- ✅ Back-office (7 routes testées) : `/admin`, `/admin/stripe-reconciliation`, `/admin/ged-bridge`, `/admin/lolo-points`, `/crm`, `/vendor`, `/lolodrive` → bouton **VISIBLE**
- ✅ Screenshot : pastille bleue lisible sous la NavBar, design conforme à la charte premium clair

**Total : 9/9 routes** conformes au comportement attendu.



**Demande utilisateur** : créer un microservice **séparé** du projet KDM pour la gestion financière. Ne PAS toucher au backend KDM tant que finance-api n'est pas validé en standalone.

**Architecture livrée** :
- 📂 `/app/finance-api/` — projet FastAPI indépendant, structure exacte demandée :
  - `main.py`, `requirements.txt`, `Dockerfile`, `.env.example`, `.env`, `README.md`
  - `app/core/{config,security}.py`
  - `app/db/session.py` (SQLAlchemy 2.x ; SQLite en dev, PostgreSQL prêt en prod)
  - `app/models/{user,party,receivable,payment,sepa_mandate,installment,ledger,webhook_event}.py`
  - `app/schemas/all.py` (Pydantic v2)
  - `app/routes/{auth,parties,receivables,payments,sepa,installment_plans,webhooks,reporting}.py`
  - `app/services/{psp_adapters,ledger_service,reconciliation_service,ged_connector,crm_connector}.py`

**Endpoints disponibles** :
- `GET /health`, `POST /setup/bootstrap`, `POST /auth/token`
- `POST/GET /parties`
- `POST/GET /receivables` (types : INVOICE, COTISATION, APPEL_CONTRIBUTION, PASS_CONSOMMATION, RECHARGE_UC, ORDER, OTHER)
- `POST /payments`, `POST /payments/{id}/mark-paid`, `POST /payments/{id}/refund`, `GET /payments`
- `POST /sepa/mandates`, `POST /sepa/mandates/{id}/activate`, `POST /sepa/mandates/{id}/revoke`
- `POST /installment-plans` (validation : Σ échéances = montant créance)
- `POST /webhooks/stripe`, `POST /webhooks/gocardless` (idempotents, signature à brancher)
- `GET /reporting/dashboard`, `GET /ledger/entries`, `GET /audit/verify-ledger-chain`

**Journal financier probant** :
- Table `ledger_entries` append-only avec `sequence` monotone + chaînage SHA-256 (`previous_hash` + `entry_hash`)
- Vérification chaîne via `GET /audit/verify-ledger-chain`
- ✅ **Tamper-test validé** : altération directe du `payload_json` (ex. amount_cents → 999999) détectée immédiatement avec le message `"entry_hash divergent — payload modifié après écriture"` à la séquence exacte.

**PSP adapters** (`psp_adapters.py`) :
- 3 backends : `manual` (toujours fonctionnel pour tests), `stripe`, `gocardless`
- Si secret PSP manquant : adaptateur renvoie `status=FAILED` avec message clair (pas de crash)
- `_stripe_checkout` et `_gocardless_billing_request` ont placeholders prêts pour brancher les vrais SDK

**Port** : Demandé 8010, mais ce port est utilisé par l'infra interne Emergent dans le pod preview → service exposé sur **8030 en sandbox** (8010 reste documenté pour la prod via Docker/k8s). Aucun impact fonctionnel.

**Base de données** :
- **Dev/sandbox** : SQLite `finance_api.db` (zéro setup)
- **Prod** : `DATABASE_URL=postgresql+psycopg2://finance_user:***@postgres-finance:5432/finance_api` (à activer dans `.env`)
- Auto-init des tables au startup (`Base.metadata.create_all`)

**Tests E2E (curl, scénario complet)** :
- ✅ `/health` → 200 + flags config (stripe_configured: false, gocardless_configured: false, etc.)
- ✅ `/setup/bootstrap` (1ère) → 200 + token JWT 120 min ; rejeu → **409 Conflict** ✓
- ✅ `/auth/token` (OAuth2 form) → JWT renvoyé, `/parties` sans token → **401**
- ✅ `POST /parties` (Restaurant La Caravelle, SIRET 555…) → 201
- ✅ `POST /receivables` (COTISATION 120€) → 201 + entrée ledger seq=1
- ✅ `POST /payments` (manual) → status PENDING + hosted_url + entrée ledger seq=2 PAYMENT_INITIATED
- ✅ `POST /payments/{id}/mark-paid` → status SUCCEEDED + receivable PAID + entrée ledger seq=3
- ✅ `POST /payments/{id}/refund` (30€) → status PARTIAL_REFUND + entrée ledger seq=4
- ✅ `POST /sepa/mandates` SEPA_B2B → 201, UMR auto-générée `UMR-20260523-0001`
- ✅ `POST /sepa/mandates/{id}/activate` → ACTIVE + entrée ledger seq=6
- ✅ `POST /installment-plans` (3×40€) → 3 installments créées
- ✅ `/reporting/dashboard` : KPIs cohérents (1 party, 1 receivable PAID, 12000 paid, 3000 refunded, 7 ledger entries)
- ✅ `/audit/verify-ledger-chain` initial → `ok: true, total_entries: 7`
- ✅ Tamper test : ledger chain casse à la bonne séquence après modification SQL directe

**État P1→P5** : OK. **P6 (bridge KDM)** sera traité dans une itération séparée, après validation utilisateur.



**Demande utilisateur** :
1. Rendre le badge "Client" visible (était quasi-invisible sur fond crème)
2. Créer compte vendeur pro fictif + parcours
3. Créer compte acheteur B2B fictif + parcours
4. Créer compte Lolo Point + parcours d'achat
5. Activer la GED

**Implémenté** :

#### 1. Badge Client (`LogisticsSection.jsx`)
- Couleur passée de `rgba(255,255,255,0.75)` (invisible sur fond crème) → **`#1F4D87` (Bleu logistique)** avec contour `rgba(31,77,135,0.45)` bien marqué.
- Pastille légende synchronisée (`background: #1F4D87`).
- Bonus : fix d'un `};` parasite après `.map()` qui pouvait poser des soucis.

#### 2. Seed personas (`/app/backend/seed_demo_personas.py`)
- 🆕 **Vendeur pro** : `vendor-pro@kdmarche.fr` / `Demo2026!`
  - Côté `users` : rôle `vendor`, lié à `vendor_id=vendor-demo-pro`
  - Côté `vendors` : Distillerie Damoiseau (status `approved`, SIRET 444…)
  - 3 produits : Rhum AOC blanc 1L (approuvé), Rhum VSOP 70cl (approuvé), Confiture goyave-rhum (en attente)
  - Parcours : `/vendor` → dashboard 2/3 actifs + 1 en attente, possibilité d'ajouter/éditer/soumettre
- 🆕 **Acheteur B2B pro** : `acheteur-pro@kdmarche.fr` / `Demo2026!`
  - Restaurant La Caravelle (SIRET 555…, 250 crédits)
  - Parcours : `/catalogue`, `/espace-acheteur`, `/wallet`
- ✅ **Gérant Lolo Point existant** enrichi d'une commande de réassort B2B `LD-LP-20260518-J1K2L3` FULFILLED (260 €) — parcours d'achat seedé
- `VendorSpacePage.jsx` : `DEMO_VENDOR_ID` mis à jour vers `vendor-demo-pro` pour exposer le seed.

#### 3. Activation GED interne
- Le script `seed_demo_personas.py` force l'init des 4 documents de référence via `initialize_default_documents()` si la collection est vide. À l'exécution : 4 documents trouvés (`convention`, `cg-oscop`, `cgv-kdmarche`, `note-preventive`), tous en statut `PUBLISHED`. Accessibles via `/documents` et `GET /api/ged/documents`.

**Tests E2E** :
- ✅ `POST /api/auth/login` vendor-pro → 200, company "Distillerie Damoiseau"
- ✅ `POST /api/auth/login` acheteur-pro → 200, 250 crédits, "Restaurant La Caravelle"
- ✅ `GET /api/vendor/dashboard/vendor-demo-pro` → 3 produits (2 approved + 1 pending), CA 0 € (pas encore de ventes)
- ✅ `GET /api/ged/documents` (admin) → 4 documents PUBLISHED
- ✅ Screenshot landing : badge Client bleu logistique parfaitement lisible, légende synchronisée
- ✅ Screenshot `/vendor` : dashboard Distillerie Damoiseau affiche 2 actifs / 1 en attente

**Credentials mis à jour** dans `/app/memory/test_credentials.md`.



**Demande utilisateur** : ne pas traiter les 502 comme bugs tant que la vraie GED ESS n'est pas déployée. Statut DEGRADED propre + page admin légère (sync-events + bouton re-push).

**Implémenté (backend, petit commit)** :
- `GET /api/ged-bridge/health` ré-écrit : renvoie **toujours HTTP 200** avec un statut lisible :
  - `OK` — URL configurée + microservice répond
  - `DEGRADED` — URL configurée mais microservice indisponible (404, timeout). Message explicite : *"Statut normal tant que la GED ESS n'est pas déployée."*
  - `DISABLED` — `GED_ESS_API_URL` non configurée (pont volontairement désactivé)
  - Renvoie en plus un objet `config` (url, token configuré ✔/—, HMAC configuré ✔/—, timeout) pour diagnostic admin.
- `GET /api/ged-bridge/sync-events` enrichi : retourne maintenant `{events, counts: {total, success, error}}` agrégés via `$group` Mongo. Filtre `status=SUCCESS|ERROR` ajouté.
- 🆕 `POST /api/ged-bridge/sync-events/{event_id}/retry` — rejoue un événement en échec (CRM dossier / LOLODRIVE order / PDF generate / create document). Trace une entrée `OUTBOUND_RETRY` en `ged_bridge_sync_events`.

**Implémenté (frontend, petit commit)** :
- 🆕 `/app/frontend/src/pages/GedBridgeAdminPage.jsx` — page admin minimaliste :
  - Carte santé avec badge coloré (OK vert / DEGRADED ambre / DISABLED gris) + panneau diagnostic config (URL, tokens, timeout).
  - 3 cartes de compteurs (Total / Succès / Erreurs).
  - Filtres Statut (par défaut "Erreurs" pour focus opérationnel) + Source.
  - Tableau des sync-events avec colonnes Date / Source / ID métier / Direction / Statut / Détail / Action.
  - Bouton **Re-pousser** sur chaque ligne en erreur (loader pendant le retry + refresh auto du tableau).
- 🆕 Route `/admin/ged-bridge` dans `App.js`, lien "Pont GED ESS" (icône Server) ajouté dans `NavBar.jsx` (section admin).

**Tests E2E (curl + screenshot UI)** :
- ✅ `GET /api/ged-bridge/health` → 200 + `status:"DEGRADED"` + diagnostic complet (avant : 502).
- ✅ `GET /api/ged-bridge/sync-events?status=ERROR` → 200 + `counts:{total:2, success:0, error:2}`.
- ✅ `POST /api/ged-bridge/sync-events/{id}/retry` → 502 propre + nouvelle entrée `OUTBOUND_RETRY` tracée.
- ✅ `POST /api/ged-bridge/sync-events/unknown/retry` → 404.
- ✅ Screenshot UI admin : page rend correctement, badge DEGRADED ambre, 2 lignes d'erreurs avec boutons "Re-pousser" actifs, design conforme à la charte premium light.


**Demande utilisateur** : intégrer le ZIP `KDM-main-V2-plus-CRM-OSCOP-main-GED-bridge.zip` en câblant le pont GED ESS externe sans remplacer la GED interne, et sans refactorer massivement `server.py`.

**Implémenté** :
- 🆕 `/app/backend/ged_external_client.py` — client async `httpx` vers le microservice GED ESS externe. Config depuis env (`GED_ESS_API_URL`, `GED_ESS_API_TOKEN`, `GED_ESS_WEBHOOK_SECRET`, `GED_ESS_TIMEOUT_SECONDS`). Header `Authorization: Bearer` + signature HMAC SHA256 `X-GED-ESS-Signature` sur le payload. Méthodes : `health`, `list_scopes`, `create_document`, `generate_pdf`, `push_to_external_connector`. Helpers : `SCOPE_BY_SOURCE`, `PDF_TEMPLATE_BY_SCOPE`, `resolve_scope_code`, `build_ged_business_metadata`.
- 🆕 `/app/backend/routes_ged_bridge.py` — routeur `/api/ged-bridge/*` protégé par admin (`get_current_user_id` + check `is_admin` ou role ∈ {SUPER_ADMIN, ADMIN, COOP_BOARD, GESTIONNAIRE_GED, oscop_super_admin, kdm_b2b_admin}). Routes :
  - `GET /health` — ping le microservice externe
  - `GET /scopes` — liste les périmètres
  - `GET /sync-events` — journal des syncs (paginé, filtre source/source_id)
  - `POST /documents` — crée un document directement côté GED externe
  - `POST /pdf/generate` — génère un PDF institutionnel
  - `POST /crm/dossiers/{id}/push` — pousse un dossier CRM O'SCOP → GED externe (template `OSCOP_CONTRAT_COOPERATIF`), met à jour `crm_dossiers.ged_external_document_id`
  - `POST /lolodrive/orders/{id}/push` — pousse une commande LOLODRIVE → GED externe (template `KDMARCHE_APPEL_CONTRIBUTION`)
- 🆕 Collection `ged_bridge_sync_events` : journal d'audit complet (id, source, source_id, direction, status SUCCESS/ERROR, payload, response, created_at). 3 indexes créés au démarrage.
- 🪶 `server.py` enrichi de **9 lignes seulement** (import + `set_database` + `include_router` + `ensure_indexes` au startup). **Aucun refactor**.
- 🆕 `/app/backend/.env` enrichi des 4 vars GED (valeurs fournies par l'utilisateur).
- 🆕 `/app/backend/.env.example` créé — documente toutes les vars critiques (Mongo, Stripe multi-comptes, Brevo, Mapbox, Google OAuth, GED ESS).
- 🆕 `/app/docs/GED_ESS_BRIDGE.md` copié depuis le ZIP.

**Tests E2E (curl)** :
- ✅ `GET /api/ged-bridge/health` sans token → **403** ; avec admin token → **502 + message clair** (`GED externe erreur 404` puisque l'URL pointe sur localhost:8001 qui n'expose pas `/health` — comportement attendu en l'absence d'un vrai microservice GED).
- ✅ `GET /api/ged-bridge/scopes` → 502 propre.
- ✅ `POST /api/ged-bridge/pdf/generate` → 502 propre + **événement tracé en `ged_bridge_sync_events`** avec `status=ERROR`, `direction=OUTBOUND`, payload + response.
- ✅ `POST /api/ged-bridge/crm/dossiers/unknown/push` → **404 "Dossier CRM introuvable"** (validation DB métier avant appel externe).
- ✅ `POST /api/ged-bridge/lolodrive/orders/unknown/push` → **404 "Commande LOLODRIVE introuvable"**.
- ✅ Audit : `GET /api/ged-bridge/sync-events?limit=5` renvoie bien la trace de la tentative PDF avec statut ERROR.
- ✅ **GED interne préservée** : `GET /api/ged/documents` → 200 (pont additif, pas un remplacement).

**Côté microservice GED ESS** (côté KDM, à fournir par l'admin GED) :
- URL cible : `http://localhost:8001` (placeholder) — à remplacer par la vraie URL du microservice
- Bearer token : `TON_TOKEN_GED` (placeholder)
- Webhook HMAC secret partagé : `SECRET_PARTAGE_GED` (placeholder)
- Timeout : 20 s


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


### 2026-02 — Intégration coordonnées bancaires KDMARCHE (myPOS)
- Clé Stripe LIVE KDMARCHE (`sk_live_51FqczfCo8u…`) confirmée et active dans `/app/backend/.env` → ligne `STRIPE_KDMARCHE_LIVE_KEY`.
- Mode `STRIPE_MODE=live` validé : `stripe_accounts.get_stripe_key('kdmarche')` retourne bien la clé live KDMARCHE et `get_account_for_checkout_kind('ORDER')` route correctement.
- Coordonnées bancaires KDMARCHE (myPOS Ltd, IE) ajoutées comme constante **serveur-only** dans `/app/backend/routes_payment.py` → `KDMARCHE_BANK_DETAILS` (titulaire PIPEROL FELIXIA VANESSA, IBAN `IE72MPOS99039052096773`, BIC `MPOSIE2D`).
- Endpoint public `/api/payments/bank-details` continue à exposer **uniquement** les coordonnées OSCOP (Crédit Mutuel) — pas de fuite des détails KDMARCHE (vérifié via curl).
- ⚠️ Sécurité : clé Stripe LIVE exposée en clair dans le chat → recommander à l'utilisateur de la **roter** dans Stripe Dashboard après le test E2E 1€.

### Test E2E LIVE Stripe (P0 — en attente utilisateur)
- L'utilisateur doit effectuer un paiement réel de 1€ (PASS ou produit ORDER) puis procéder à un refund depuis le dashboard Stripe.
- Vérifier les logs webhook : `tail -f /var/log/supervisor/backend.err.log | grep -iE 'stripe|webhook'`.

### 2026-02 — Endpoint `GET /api/admin/stripe/live-health` (go/no-go LIVE)
- Nouvel endpoint admin-only (403 sinon) qui retourne en un JSON :
  - `mode` : test | live
  - `accounts.{oscop,kdmarche}` : `key_configured`, `key_prefix` (masqué, jamais la clé complète), `webhook_secrets_count`
  - `last_webhook_received` : dernier webhook traité (via `applied_by=webhook:*`), avec compte, kind, session_id, flag `unsigned_test_mode`
  - `last_successful_payment` : dernier paiement OK (compte, kind, amount, session_id)
  - `stats_24h.{oscop,kdmarche}` : paid_count, paid_amount, refund_full/partial_count+amount, stale_pending_count (tx >15min sans applied)
  - `verdict` : `go` / `warn` / `no-go` + `reasons[]` humains (ex. "Aucun paiement LIVE encore observé — faire le test 1€ E2E")
- Aucune écriture, agrège uniquement `payment_transactions`.
- Contract tests : `/app/backend/tests/test_stripe_live_health.py` — 7/7 PASS (auth 403, shape, prefix masking, verdict logic).

### Backlog
- P1 : Wrapping i18n complet (FR/EN/ES) — après validation test LIVE.
- Future : brancher les vraies URLs de la GED ESS quand fournies (actuellement mode DEGRADED assumé).

### 2026-02 — Code Review Phase 1+2+3a (Critical + Low-Risk Cleanup)
**Backend (lint = 0 erreur bloquante) :**
- ✅ Fix circular import `routes_finance_bridge.py` ↔ `server.py` → import depuis `auth.py`
- ✅ Hardcoded passwords → env vars (`DEMO_SEED_PASSWORD`, `DEMO_USER_PASSWORD`) dans `seed_demo_personas.py` + `tests/test_iter10_*.py`
- ✅ Dynamic import sécurisé : `routes_stripe_reconciliation.py` (`__import__("os")` → `import os`)
- ✅ 2 ObjectId serialization bugs corrigés (`routes_lolodrive_oscoop.py`, `routes_notifications.py`)
- ✅ 9 bare `except:` → `except Exception:` / `except (ValueError, TypeError):`
- ✅ 11 E701 multi-statements aplatis (`routes_crm_oscoop.py`)
- ✅ 7 E712 == True/False → `is True/False` (tests)
- ✅ E741 `l` ambigu → `loc` (`routes_catalog.py`)
- ✅ 4 F841 local vars inutilisées nettoyées
- ✅ **Dead code supprimé** : `check_pricing_access`, `check_order_access`, `check_wallet_consume` (jamais appelés)

**Frontend (yarn build = clean) :**
- ✅ 41 unescaped entities corrigées (apostrophes/quotes → `&apos;` / `&quot;` / `&amp;`) dans : Footer, Header, ContactForm, LogisticsSection, DeliveryOptionsSelector, DynamicOrderForm, WalletPage, VendorSpacePage, StripeReconciliationPage, LegalPage, LandingPage, DashboardPage
- ✅ **Array index keys → IDs stables** (~15 instances) dans LegalPage / LandingPage / DashboardPage (utilise zone.code, point.label, slug content, etc.)
- ✅ Bloc `catch (_) {}` vide commenté dans LandingPage
- ✅ `setupTests.js` annoté `eslint-env jest` + `global jest`
- ✅ Trailing JSX corrupt cleanup dans LegalPage.jsx

**Restant en lint (acceptable) :**
- 5 false-positives `react-hooks/set-state-in-effect` / `static-components` — règles React 19 strictes sur patterns légitimes (useEffect→fetchData, useCallback+setState). Pas de bugs.

### 2026-02 — Code Review Phase 3b (Array Keys restants)
- ✅ **11 array-index-as-key remplacés par IDs stables** :
  - `ProductCardView.jsx` (6) : tier_pricing, allergens.contains/may_contain/free_from, technical_specs.norms, available_zones
  - `ProductCatalogManager.jsx` (1) : tags editor
  - `OrderFormPreview.jsx` (3) : hero tags, produits table, fees table
  - `AdminPlansPage.jsx` (1) : features list
- ⚠️ **Faux positif écarté** : le rapport "182 `is` au lieu de `==`" est incorrect — toutes les occurrences dans `/backend/tests/` sont des `is None` / `is True` / `is False`, usage PEP 8 correct.

**Non fait volontairement (risque de régression avant test LIVE) :**
- localStorage → httpOnly cookies (36 instances) — casserait l'auth E2E
- Split composants massifs (BuyerSpacePage 1237L, ProductCatalogManager 965L, etc.)
- Refactor email/pdf/auto-renew (fonctionnels, refactor = risque silencieux)

### Test E2E LIVE Stripe (P0 — en attente utilisateur)
- L'utilisateur doit effectuer un paiement réel de 1€ (PASS ou produit ORDER) puis procéder à un refund depuis le dashboard Stripe.
- Vérifier les logs webhook : `tail -f /var/log/supervisor/backend.err.log | grep -iE 'stripe|webhook'`.
