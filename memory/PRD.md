# PRD — KDMARCHÉ / LOLODRIVE by O'SCOP

## Plateforme coopérative B2B2C — Centrale d'achats ESS Outre-mer

---

## 0. RÈGLE D'OR (édictée par l'utilisateur le 16 juin 2026)
**Aucun fichier ne doit dépasser 500 lignes de code.**
- Tout NOUVEAU code doit être découpé en modules < 500 lignes dès sa création.
- ~40 fichiers existants dépassent la limite (pires : `server.py` 1664, `routes_lolodrive_oscoop.py` 1397, `ProductCatalogManager.jsx` 1345, `BuyerSpacePage.jsx` 1314, `AdminPlansPage.jsx` 1191, `WalletPage.jsx` 1090, `api.js` 1031…). Refactoring progressif à planifier, MAIS ne pas toucher aux fichiers du tunnel de paiement (`routes_payment.py`, `CheckoutPage.jsx`, `StripeCheckoutButton.jsx`) avant la validation du test Stripe LIVE 1€.

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
- **MISE À JOUR (16 juin 2026)** : charte globale basculée en **Violet KDMARCHE (#5B2E8C / #2A1045 / #451F6B) + Or O'SCOP (#D4AF37)** sur TOUTES les pages (remplacement des bleus marine #0B4D87/#0B1F3B et du vert #57D19A dans 37 fichiers). Logos officiels : `/logos/kdmarche-pro.webp` (KD Marché Pro) et `/logos/oscop.webp` (Objectif SCOP Outremer), trimés et servis localement via `partners` dans `mock.js`. Menu « Tarifs » renommé « Accès Pro Mutualisé » (navbar + footer + titre page /tarifs). Classes CSS utilitaires : `.on-dark` (restaure le texte blanc sur panneaux violets) et `.force-white` (texte blanc sur boutons à fond dégradé inline).
- **MISE À JOUR (16 juin 2026 — bis)** : section « API Coopérative B2B2C » de la landing passée en `on-dark` (texte blanc sur violet), bloc JSON « Accès sécurisé » remplacé par un visuel high-tech généré (`/images/api-hightech.webp`, réseau de membres pros convergeant vers un hub mutualisé). CTA « Découvrir l'Accès Pro Mutualisé » ajouté dans le hero (boutons « Découvrir les offres » et « Télécharger l'offre PDF » supprimés). Bloc « Conditions d'accès au dispositif coopératif d'achats mutualisés » reformulé. Email de bienvenue (`send_welcome_email`) rebrandé violet-or avec logos (`FRONTEND_URL/logos/*.png`, variable `FRONTEND_URL` ajoutée au backend/.env). Badge « Made with Emergent » supprimé (index.html + CSS kill-switch).
- **MISE À JOUR (16 juillet 2026 — LOT 7 FINAL + SEED ACHETEUR : RÈGLE D'OR 100% ATTEINTE)** : (1) **Seed acheteur** : script idempotent `/app/backend/seed_buyer_org.py` — org `org-demo-achats` (APPROVED) + membership CUSTOMER_ORG_OWNER pour acheteur-pro@kdmarche.fr + subscription ACTIVE (ESS_ACCES) + partner_account KDMARCHE ACCESS_ENABLED + entitlements zones GUADELOUPE/MARTINIQUE + préférence zone + wallet. Panier & commandes fonctionnent (commande test KDM-20260716 créée via API et tunnel UI vérifié). (2) **Lot 7 paiement** : `routes_payment` (815→~410 + `payment_models.py` + `routes_payment_sepa.py`), `routes_checkout` (621→~440 + `checkout_common.py` + `checkout_handlers.py`), `routes_checkout_v1` (546→~315 + `checkout_v1_models.py`), `routes_stripe_reconciliation` (584→313 + `routes_stripe_health.py`), `routes_lolodrive_checkout` (659→~450 + `lolodrive_checkout_apply.py`), `CheckoutPage.jsx` (981→449 + `components/checkout/` : checkoutUtils, CheckoutProgress, CheckoutSteps, CheckoutPayment), `StripeReconciliationPage.jsx` (666→454 + `components/reconciliation/`). (3) **Sécurité webhook** : `/api/v2/checkout/webhook` exige désormais une signature en mode LIVE (fallback dev sans signature supprimé en live, secrets par compte STRIPE_WEBHOOK_SECRETS_KDMARCHE pris en charge) → 400 propre au lieu de 500. (4) Régressions frontend trouvées par testing_agent iteration_17 puis corrigées : icônes lucide dans checkoutUtils STEPS + import partners (fixés par testing agent), prop `nextStep` OrderSummarySidebar + export/import `ByKindCard` (fixés par main agent). Validé : pytest 142/142 (lots 4-7 + shopping lists), CI build vert, tunnel checkout UI vérifié navigateur jusqu'à l'étape Livraison (zones + 3 modes + point retrait) sans erreur JS, page Réconciliation Stripe LIVE rend (cartes OSCOP/KDMARCHE, CSV, graphe). **SCAN FINAL : 0 fichier > 500 lignes dans tout le projet.** Reste à faire par l'utilisateur : test Stripe LIVE 1€ + remboursement pour valider le tunnel refactorisé de bout en bout.
- **MISE À JOUR (16 juillet 2026 — LOT 6, REFACTORING <500 lignes TERMINÉ hors paiement)** : (1) Backend, 15 fichiers découpés (mêmes URLs, setters en cascade) : `routes_shopping_lists` (723→`shopping_lists_common`+`routes_shopping_lists_items`), `routes_user_prefs` (617→`user_prefs_common`+`routes_user_prefs_favorites`), `routes_pod` (676→`pod_models`+`routes_pod_sign`), `routes_logiscop` (676→`logiscop_models`), `routes_ess` (654→`ess_models`), `abac_policy` (623→`abac_engine`+façade), `schema_catalog` (615→`schema_catalog_enums`+`schema_catalog_cart`+façade star), `routes_websockets` (558→`ws_manager` avec `manager` ré-exporté), `routes_admin_zones` (557→`admin_zones_common`+`routes_admin_zones_public`), `routes_pdf` (552→`pdf_generators`), `schema_preparation` (546→`schema_preparation_defaults`), `routes_contracts` (546→`contracts_models`), `routes_export` (513→`export_common`), `schema_product_card` (567→`schema_product_card_parts`), tests shopping_lists scindés en 2 + TEST_PRODUCT_ID résolu dynamiquement depuis la DB. Nouveaux routers inclus dans server.py : shopping_lists_items, user_prefs_favorites, pod_sign, admin_zones_public. (2) Frontend, 12 fichiers découpés : `ProductCardView` (945→`components/product-card/` x3), `DeliveryOptionsSelector` (752→`components/delivery/` x3), `DynamicOrderForm` (747→`components/order-form/` x2), `OnboardingPage` (728→`components/onboarding/OnboardingSteps.jsx`), `ShoppingListsPage` (715→`components/shopping-lists/` x3), `SMSSignatureModal` (682→`components/signature/` x2), `LegalPage` (616→`components/legal/LegalDocument.jsx`), `AdminProductsPage` (585→`components/admin/ProductDetailModal.jsx`), `NotificationsHistoryPage` (582→`components/notifications/` x2), `NavBar` (528→`components/navbar/` x2), `QuickShortcuts` (503→`components/shortcuts/` x2), `ShoppingListDetailPage` (501→import frequencyLabels partagé). (3) Régressions trouvées par testing_agent (iteration_16) puis TOUTES corrigées + audit automatique de props manquantes sur les 18 fichiers extraits : filterFrequency/setFilterFrequency (ShoppingListFilters), import Button (LegalDocument + PreparationOptionsSection), unreadCount (UserMenu), showDeleteConfirm (ShoppingListDialogs), Calendar (ShoppingListFilters), setPage (NotificationFilters), documentRef (SignatureSteps), weightKg/volumeM3/itemsCount (StandardDeliverySection), zoneCode (PreparationOptionsSection). Validé : pytest 81/81 (lot4+lot5+shopping_lists) + test_lot6 34/34, CI build vert, /legal + /listes-achats + dialogs vérifiés navigateur. ⚠️ RESTENT >500 lignes UNIQUEMENT les 7 fichiers PAIEMENT gelés jusqu'au test Stripe LIVE 1€ : CheckoutPage (981), routes_payment (815), StripeReconciliationPage (666), routes_lolodrive_checkout (659), routes_checkout (621), routes_stripe_reconciliation (584), routes_checkout_v1 (546) → à découper en Lot 7 APRÈS validation du paiement.
- **MISE À JOUR (16 juillet 2026 — LOT 5, REFACTORING <500 lignes + fix régressions Lot 4)** : (1) Régressions Lot 4 corrigées : `REJECTION_REASONS` importé dans `adminv2/ApplicationsTab.jsx`, `MIN_INSTALLMENT_CENTS` centralisé dans `catalog/catalogUtils.js` (importé par CheckoutDialog + CatalogPage), 8 warnings eslint `exhaustive-deps` neutralisés → `CI=true yarn build` passe à 100%. (2) Backend découpé : `routes_lolodrive_oscoop.py` (1397→309 + `lolodrive_models.py`, `lolodrive_helpers.py`, `routes_lolodrive_pos.py`, `routes_lolodrive_points.py`, `routes_lolodrive_manager.py`, `routes_lolodrive_admin.py` — setter `set_lolodrive_database` cascade vers les sous-modules), `routes_signature.py` (739→421 + `signature_models.py` + `routes_signature_admin.py`), `email_service.py` (678→415 + `email_alerts.py`, imports routes_websockets mis à jour), `routes_v1_logiscop.py` (960→305 + `logiscop_v1_models.py`, `logiscop_v1_pricing.py`, `routes_v1_logiscop_orders.py`), `routes_opa_bundle.py` (902→309 + `opa_defaults.py`, `opa_bundle_gen.py`), `routes_admin_plans.py` (853→409 + `admin_plans_common.py`, `routes_admin_plans_credits.py`), `schema_v2.py` (802→211, façade star re-exports + `schema_v2_enums.py`, `schema_v2_billing.py`, `schema_v2_zones.py`), `routes_ged.py` (757→340 + `ged_models.py`, `routes_ged_admin.py`). (3) Frontend : `data/legalDocuments.js` (1069→47, façade + `data/legal/{variables,cgv,convention,ess,logiscop}.js`). Mêmes prefixes URL, zéro changement de contrat API. Validé : pyflakes clean, pytest Lot4 15/15 + Lot5 33/33 (`test_lot5_refactor_regression.py`), frontend /legal + /admin-v2 + /catalogue + /espace-vendeur clean (iteration_15.json). Restent >500 lignes pour Lot 6 (hors paiement) : ProductCardView (945), DeliveryOptionsSelector (752), DynamicOrderForm (747), OnboardingPage (728), routes_shopping_lists (723), ShoppingListsPage (715), SMSSignatureModal (682), routes_pod (676), routes_logiscop (676), routes_ess (654), abac_policy (623), routes_user_prefs (617), LegalPage (616), schema_catalog (615), AdminProductsPage (585), NotificationsHistoryPage (582), schema_product_card (567), routes_websockets (558), routes_admin_zones (557), routes_pdf (552), schema_preparation (546), routes_contracts (546), NavBar (528), routes_export (513), QuickShortcuts (503), ShoppingListDetailPage (501), tests/test_shopping_lists_api (743). Fichiers PAIEMENT gelés jusqu'au test Stripe LIVE 1€ : CheckoutPage (981), routes_payment (815), StripeReconciliationPage (666), routes_lolodrive_checkout (659), routes_checkout (621), routes_stripe_reconciliation (584), routes_checkout_v1 (546).
- **MISE À JOUR (16 juin 2026 — LOT 3, REFACTORING <500 lignes)** : Backend — `routes_catalog.py` (1054→389, cart→`routes_cart_v2.py`, orders→`routes_orders_v2.py`), `routes_v2.py` (996→294, →`routes_v2_applications.py` + `routes_v2_billing.py`), `routes_admin_ess.py` (999→487, →`routes_admin_ess_rules.py` + `routes_admin_ess_capacity.py`) — mêmes prefixes URL, zéro changement de contrat API. Frontend — `BuyerSpacePage.jsx` (1314→477, →`components/buyer/`), `ProductCatalogManager.jsx` (1345→460, →`components/catalog-manager/`). Bug latent corrigé : bouton « Détails » des commandes acheteur désormais câblé (ouvre le modal). Fonction morte `downloadOrderPDF` supprimée. Régression validée testing agent 100% (iteration_13.json, pytest `test_lot3_refactor_regression.py`). ⚠️ Issue seed découverte (pré-existante) : `acheteur-pro@kdmarche.fr` n'a pas d'`organization_id` → cart/orders v2 retournent 400 pour ce compte (à corriger dans le seed). Restent >500 lignes pour Lot 4 (hors paiement) : legalDocuments.js (1069), routes_v1_logiscop (960), ProductCardView (945), routes_opa_bundle (902), VendorSpacePage (889), routes_vendor (872), AdminV2Page (862), routes_admin_plans (853), CatalogPage (801), routes_superadmin (800), routes_ged (757)… Fichiers paiement (routes_payment 815, CheckoutPage 981, routes_checkout 621, routes_lolodrive_*) : APRÈS le test Stripe LIVE.
- **MISE À JOUR (16 juin 2026 — LOT 2, REFACTORING <500 lignes)** : `server.py` (1664→435) découpé — routes déplacées verbatim dans `routes_core_auth.py`, `routes_core_users.py`, `routes_core_admin.py`, `routes_core_notifications.py`, `routes_core_orgs.py` + helpers partagés `core_deps.py` (get_current_user, check_admin, create_notification via `db.get_database()`). Bug latent corrigé : l'alias `/api/admin/products/pending` était déclaré après `include_router` (jamais enregistré) — désormais actif dans routes_core_admin. `SuperAdminPage.jsx` (740→137) découpé avec `components/superadmin/` (widgets, SuperAdminHeader, DashboardTab, UsersOrdersTabs). Régression validée par testing agent : 22/22 backend + smoke frontend 100% (iteration_12.json, suite pytest `test_lot2_refactor_regression.py`). Restent >500 lignes (Lot 3) : routes_lolodrive_oscoop (1397, contient du paiement), routes_catalog (1054), routes_admin_ess (999), routes_v2 (996), routes_v1_logiscop (960), routes_opa_bundle (902), routes_vendor (872), routes_admin_plans (853), schema_v2 (802), routes_superadmin (800), routes_ged (757), etc. + frontend BuyerSpacePage (1314), ProductCatalogManager (1345), CheckoutPage (paiement — après test Stripe LIVE).
- **MISE À JOUR (16 juin 2026 — LOT 1, REFACTORING <500 lignes)** : `services/api.js` (1031→76) découpé en barrel + 5 modules (`http.js`, `api.core.js`, `api.v2.js`, `api.lolodrive.js`, `api.crm.js`) — tous les imports existants inchangés, default export supprimé (aucun consommateur). `WalletPage.jsx` (1090→460) découpé avec `components/wallet/` (walletUtils, WalletOrgTabs, WalletDialogs, BuyCreditsDialog). `AdminPlansPage.jsx` (1191→306) découpé avec `components/admin/plans/` (shared, PlanFormModal, OptionFormModal, CreditAdjustModal, PlansTab, OptionsTab, CreditsTab). Régression frontend validée par testing agent (100% pass, iteration_11.json). Issue pré-existante notée : WebSocket notifications 400 (user_id vide dans la query string).

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

### 2026-07-18 — Factures PDF crédits + Alerte solde faible : VALIDÉS
- ✅ **Facture PDF** (`pdf_credit_invoice.py`) : générée après paiement d'un pack (reportlab, en-tête FACTURE, n° CR-YYYYMMDD-xxx, table pack/bonus/total). Testé : PDF 2435 octets valide.
- ✅ **Email facture Brevo** (`routes_credit_packs._send_invoice_email`) : envoyé au vendeur avec le PDF en pièce jointe après crédit du pack (via polling `/status/{session_id}`). Testé : Brevo 201 Created.
- ✅ **Alerte crédits faibles** (`vendor_credits._send_low_credit_alert`, seuil `LOW_CREDIT_THRESHOLD=10`) : email envoyé une fois au franchissement du seuil dans `consume_credits`. Testé : franchissement 12→2, Brevo 201. Fix : `asyncio.create_task` (API dépréciée remplacée).
- ✅ **Non-régression achat crédits** : testing_agent iteration_35 → 13/13 pass (packs, purchase Stripe LIVE session, status 403 autre user, analytics admin, refund vidéo auto, logins). Suite pytest : `/app/backend/tests/test_iter35_credit_packs_regression.py`. Script manuel : `/app/backend/tests/manual_test_invoice_and_alerts.py`.
- ❌ **Fal.ai vidéo TOUJOURS BLOQUÉ** : 3 jobs testés (dont 1 après le rechargement annoncé par l'utilisateur) → erreur fal.ai « User is locked. Reason: Exhausted balance ». Clé configurée : `FAL_KEY=bc07ae08-7fa4-…`. Le remboursement automatique des 50 crédits fonctionne (solde vendeur intact à 152). **Action utilisateur requise** : vérifier sur fal.ai/dashboard/billing que le rechargement porte bien sur le compte de CETTE clé, ou fournir une nouvelle clé.

### 2026-07-18 — Vidéo Fal.ai VALIDÉE en réel + Galerie spots vidéo /kdmarche
- ✅ **Nouvelle clé FAL_KEY** fournie par l'utilisateur (compte rechargé) installée dans backend/.env.
- ✅ **Spot vidéo réel généré** (Veo3 fast, ~6 min) : `https://v3b.fal.media/files/b/0aa2b08f/sPX6u-mBQgx31ZBifUu57_….mp4` — job DONE, vidéo liée au produit (`vendor_products.video_url` + `products.video_url` pour le catalogue B2B). 50 crédits consommés (solde vendeur 102).
- ✅ **Résilience jobs vidéo** (`routes_vendor_ai.py` + `ai_media_service.py`) : le `fal_request_id` est désormais persisté dans `ai_video_jobs` ; `GET /video-jobs/{id}` s'auto-répare si le backend a redémarré pendant la génération (re-interroge fal.ai, finalise ou échoue+rembourse). Cause racine du job bloqué : hot-reload tuait la tâche asyncio en vol.
- ✅ **Galerie publique spots vidéo** : `GET /api/public/kdmarche-videos` (jobs DONE + nom produit + vendeur) + section `VideoShowcase` sur `/kdmarche` (`components/kdmarche/VideoShowcase.jsx`, lecteurs vidéo, data-testid `kdm-video-showcase`). Screenshot validé.

### 2026-07-18 — Vidéo sur catalogue B2B + Génération depuis photo (VALIDÉS avec screenshots)
- ✅ **Vidéo sur fiche catalogue B2B** : `video_url` ajouté à `ProductResponse` (schema_catalog) + `_build_product_response` (routes_catalog). Badge or "Spot vidéo" (Play) sur la carte produit (`ProductsGrid.jsx`) → modal lecteur (`components/catalog/ProductVideoModal.jsx`, data-testid `product-video-modal`). Screenshot validé côté acheteur (`/catalogue`).
- ✅ **Spot vidéo depuis photo (image-to-video)** : testé en RÉEL — job `c7492609` DONE via `fal-ai/veo3/fast/image-to-video` avec la photo du produit (URL publique `/api/uploads/products/...`). UI Studio IA améliorée : sélecteur de photo avec option "Sans photo (100% IA)" et hint "rendu fidèle" (`AIStudioModal.jsx`). Screenshot validé.
- ✅ Galerie `/kdmarche` affiche désormais 2 spots réels (Rhum VSOP + Rhum blanc). Solde vendeur : 52 crédits (2×50 consommés légitimement).

### 2026-07-18 — Partage/téléchargement des spots + Sauvegarde locale des vidéos (VALIDÉS testing_agent iteration_36 : 100%)
- ✅ **Sauvegarde locale** : `ai_media_service.download_video_locally()` copie chaque vidéo fal.media dans `/app/backend/uploads/videos/` (servie via `/api/uploads/videos/{job_id}.mp4`). `_finalize_video_job` stocke l'URL locale (+ `fal_video_url` d'origine). Migration one-shot `migrate_videos_local.py` exécutée : 2 vidéos existantes migrées (2.6 + 3.8 Mo).
- ✅ **Boutons partage vendeur** : `components/vendor/VideoShareButtons.jsx` (Télécharger, Copier le lien, WhatsApp, Facebook, Partager natif) affichés sous la vidéo dans le Studio IA ET dans la nouvelle modal "Spot vidéo" de l'Espace Vendeur.
- ✅ **Refactor Règle d'Or** : colonne d'actions produit vendeur extraite dans `components/vendor/ProductActions.jsx` (avec bouton "Spot vidéo" conditionnel + VendorVideoModal) → `VendorSpacePage.jsx` repasse à 486 lignes (<500).
- ✅ Testing_agent iteration_36 : 7/7 flows frontend + 2/2 curl backend PASS (actions vendeur, modal partage, badge catalogue acheteur, galerie /kdmarche, add-to-cart régression).
- ℹ️ Note : la lecture vidéo en Chromium headless de test échoue (codecs H.264 absents) — FAUX POSITIF, les fichiers sont H.264/AAC standard (lisibles sur tous les vrais navigateurs), servis en 200 video/mp4.

### 2026-07-18 — Spot sur vitrine produit + Notification "spot prêt" (VALIDÉS)
- ✅ **Modal "Voir" vendeur** (`VendorProductViewModal.jsx`) : section "Spot vidéo du produit" avec lecteur + boutons de partage (testid `view-product-video-section`). Screenshot validé.
- ✅ **Fiche PDF produit** (`pdf_product_sheet.py`) : bloc "🎬 SPOT VIDÉO" avec lien cliquable + **QR code** (reportlab QrCodeWidget) vers la vidéo — uniquement si `video_url`. Testé curl : PDF 7,5 Ko, /URI + lien présents.
- ✅ **Email Brevo "spot prêt"** (`routes_vendor_ai._send_video_ready_email`, appelé par `_finalize_video_job`) : bouton "▶ Regarder le spot" + lien Espace Vendeur, tag `video-ready`. Testé réel : Brevo 201 Created.

### 2026-07-18 — Spots multi-langues (FR/EN/ES) + Stats de vues (VALIDÉS)
- ✅ **Voix off multi-langues** : sélecteur 🇫🇷/🇬🇧/🇪🇸 dans le Studio IA (onglet vidéo). Le prompt Veo3 force la langue de narration (`ai_media_service.submit_product_video(language)`). Variantes stockées dans `video_urls.{lang}` sur `vendor_products` + `products` (migration `video_urls.fr` faite pour l'existant). **Testé réel** : spot EN généré (job `8aa3c90e`, image-to-video, voix off anglaise), les 2 variantes FR/EN coexistent.
- ✅ **Chips de langue** dans la modal vidéo catalogue acheteur (`ProductVideoModal`) et la modal vendeur (`VendorVideoModal`) — bascule instantanée entre variantes (screenshot validé, src change bien).
- ✅ **Stats de vues** : `POST /api/public/kdmarche-video-view {product_id}` incrémente `video_views` (vendor_products + products). Tracking au 1er play dans la galerie publique et la modal catalogue (pas côté vendeur). Affichage : compteur 👁 dans les cartes galerie + "X vues" dans la modal vendeur. Testé curl : compteur passe à 1.
- ✅ Galerie `/kdmarche` dédupliquée (une carte par produit, spot le plus récent) + champ `language` et `views` exposés.
- ℹ️ Solde vendeur démo re-crédité à 102 par admin_grant (2 générations réelles consommées dans la session).

### 2026-07-18 — Widget "Mes spots" vendeur + Variante auto selon langue interface (VALIDÉS)
- ✅ **Endpoint** `GET /api/vendor/ai/spots/{vendor_id}` (routes_vendor_ai) : total_spots, total_views, best (meilleur spot par vues), liste par produit avec langues disponibles.
- ✅ **Widget "Mes spots vidéo"** (`components/vendor/MySpotsWidget.jsx`, monté dans l'onglet Dashboard de VendorSpacePage) : 3 mini-stats (Spots créés / Vues cumulées / Meilleur spot 🏆) + liste des spots avec drapeaux langues et vues. Screenshot validé (3 spots, 1 vue, best = Rhum blanc).
- ✅ **Variante auto export** : `ProductVideoModal` (catalogue acheteur) sélectionne la variante correspondant à `i18n.language` (fallback FR → première dispo). Testé : interface `?lang=en` → vidéo EN chargée par défaut (chip EN active).

### 2026-07-18 — Spot Espagnol + Top des spots /kdmarche (VALIDÉS)
- ✅ **Trio export complet** : variante 🇪🇸 générée en réel (job `62419e17`, image-to-video, voix off espagnole) → le Rhum blanc dispose des 3 variantes `video_urls: {fr, en, es}`, exposées au catalogue B2B et servies localement (200 video/mp4). Solde vendeur : 52.
- ✅ **Top des spots** : classement 🥇🥈🥉 des spots les plus vus (filtre views > 0, calcul client depuis `/api/public/kdmarche-videos`) affiché au-dessus de la galerie `/kdmarche` (`TopSpots` dans `VideoShowcase.jsx`, testid `kdm-top-spots`). Screenshot validé.

### 2026-07-18 — Plans (programmation/masquage) + Crédits par profil + Broadcast spots + Rapport mensuel (VALIDÉS testing_agent iteration_37 : 100%)
- ✅ **Programmation des plans** : champs `visible`, `visible_from`, `visible_until` sur les plans (admin_plans_common + routes_admin_plans). Nouvel endpoint public `GET /api/public/plans` (filtre actif+visible+fenêtre). UI : toggle œil sur les cartes (`toggle-visible-plan-{slug}`), badges Masqué/Programmé/Expiré, switch + dates dans PlanFormModal. `/tarifs` (PricingPage) filtre ses cartes via l'API publique.
- ✅ **Crédits par profil** : `POST /api/admin/plans/credits/grant-by-profile {profile, amount}` — vendor → vendors.credits, autres rôles → wallets.balance_credits (fix DuplicateKeyError : org_id `user-{id}` dans $setOnInsert, aussi corrigé dans adjust_user_credits). UI : bloc `ProfileGrantBar` dans l'onglet Crédits utilisateurs de /admin/plans.
- ✅ **Diffusion spots vers l'écosystème** : `POST /api/connectors/broadcast-spots` — push du payload spots (produit, vendeur, vues, vidéos multilingues en URLs absolues) vers les 4 apps génériques via le hub, journalisé dans connector_sync_events (retry possible). Bouton "Diffuser les spots vidéo" sur /admin/connecteurs. ⚠️ Les apps externes doivent implémenter le récepteur `POST /api/kdmarche/spots` (404 attendus pour l'instant).
- ✅ **Rapport mensuel vendeur** : `vendor_monthly_report.py` — email Brevo (spots, vues cumulées, meilleur spot, commandes, CA HT), idempotent par mois (`monthly_report_sent`), envoyé le 1er du mois par le scheduler + déclenchement manuel `POST /api/admin/vendor-reports/send?force=true` (testé réel : 1 email Brevo).
- Testing_agent iteration_37 : 3/3 backend + 4/4 UI flows PASS, état des plans restauré.

### 2026-07-18 — CREDI'SCOP + Historique rapports + Promos programmées (VALIDÉS self-test)
- ✅ **Renommage Wallet → CREDI'SCOP** (KDMARCHÉ uniquement — les autres apps de l'écosystème sont externes) : toutes les valeurs i18n FR/EN/ES (15 fichiers locales), textes en dur (Breadcrumb, QuickNav, CatalogHeader, DashboardPage, DocumentsPage, cgv.js, mock.js, useNavigationHistory). Page /wallet : titre "Mon CREDI'SCOP", signature "Mes droits coopératifs mobilisables", définition institutionnelle (capital d'usage coopératif) et **mention juridique** en pied de page (droits d'usage internes, ni parts sociales ni monnaie électronique). Screenshot validé.
- ✅ **Historique rapports mensuels** : collection `vendor_report_log` alimentée à chaque envoi. Endpoints `GET /api/admin/vendor-reports/history` + `POST /api/admin/vendor-reports/resend/{vendor_id}`. UI : panneau "Rapports mensuels vendeurs" (`VendorReportsPanel.jsx`) dans SuperAdmin > Crédits & IA avec boutons "Envoyer à tous" et "Renvoyer" par ligne (badge renvoyé). Testé réel : resend Brevo SENT.
- ✅ **Promotions programmées (offres flash)** : champs `starts_at`/`ends_at` sur les promotions crédits + filtre fenêtre dans `_matches` (credit_promotions.py). UI : champs dates "Du/Au" dans le formulaire + badge ⏱ fenêtre sur les lignes. Testé : promo future → 0%, fenêtre active → 50%, expirée → 0%.

### 2026-07-18 — Config Prod Connecteurs + Spec CREDI'SCOP écosystème (VALIDÉS testing_agent iteration_38 : 100%)
- ✅ **Blockers déploiement corrigés** (trouvés par deployment_agent) : (1) .gitignore bloquait `.env`/`.env.*`/`*.env` → lignes supprimées, (2) 5 mots de passe avec `!` non quotés dans backend/.env (FINANCE_API, IABOIS, OSCOPGE, COPPAM, CRMESS) → quotés. Re-scan deployment_agent : **PASS, prêt à publier**.
- ✅ **Pont OSCOP vérifié fonctionnel** après corrections : 6/6 connecteurs OK (oscop-ged, oscop-finance, oscop-ia-bois, oscop-ge, coppam, crm-ess) avec les identifiants fournis par l'utilisateur (déjà en .env, tous MATCH). Testing_agent iteration_38 : 100% (santé connecteurs, auth 3 rôles, régressions publiques).
- ✅ **Spécification CREDI'SCOP écosystème** : document prêt à copier-coller dans chaque app externe → `/app/memory/CREDISCOP_RENOMMAGE_ECOSYSTEME.md` (libellés, signature, définition, mention juridique, règles techniques — ne pas toucher clés/routes/collections).
- ℹ️ Identifiants apps externes fournis : IA Bois (admin@oscop.local), GE (admin@oscopge.fr), COPPAM (admin@coppam.local), CRM ESS (admin@objectifscop.com) — tous vérifiés OK via health-status.

### 2026-07-18 — Badge CREDI'SCOP nav (tous profils) + Spec récepteur spots (VALIDÉS self-test)
- ✅ **Endpoint unifié** `GET /api/me/crediscop` (`routes_crediscop.py`) : vendeur → vendors.credits (href /espace-vendeur), membre org → wallets.balance_credits par org_membership (href /wallet), autres profils → wallet perso user_id (grant-by-profile). Testé curl 3 profils : acheteur 500 (org), vendeur 62, COOPER 30 (user).
- ✅ **Badge doré `CrediscopBadge`** (rafraîchi toutes les 60 s, cliquable) monté dans : NavBar principale (desktop + menu mobile, couvre COOPER/Expert via RoleSpaceLayout), header Espace Acheteur (`BuyerSpacePage`), header Catalogue (`CatalogHeader`). Header Espace Vendeur : badge crédits existant rebadgé "62 CREDI'SCOP". Screenshots validés (acheteur, catalogue, vendeur).
- ✅ **Spec récepteur spots** : `/app/memory/RECEPTEUR_SPOTS_ECOSYSTEME.md` — endpoint `POST /api/kdmarche/spots` à implémenter dans les 4 apps externes (payload exact, auth Bearer admin, upsert par product_id, test de validation via bouton Diffuser).

### 2026-07-18 — Badge Accès galerie + Recharge directe + Relevé CREDI'SCOP unifié (VALIDÉS self-test)
- ✅ **Badge "Accès" galerie vidéo** (/kdmarche, `AccessBadge` dans VideoShowcase) : non connecté → `/connexion?next=/catalogue` (LoginPage supporte désormais le param `next`), connecté → `/catalogue` direct. Testé E2E : login avec next atterrit bien au catalogue.
- ✅ **Recharge depuis badge CREDI'SCOP** : clic → vendeur `/espace-vendeur?recharge=1` (ouvre CreditPacksModal automatiquement), autres profils `/wallet?topup=1` (ouvre TopupDialog automatiquement). Modal renommée "Recharger mon CREDI'SCOP". Testé E2E les deux profils.
- ✅ **Relevé CREDI'SCOP unifié** : `GET /api/me/crediscop/statement` (JSON) + `/statement.pdf` (PDF reportlab avec soldes par compartiment — Crédits IA Vendeur / CREDI'SCOP Organisation / Personnel —, 40 derniers mouvements unifiés, mention juridique). Bouton "Relevé CREDI'SCOP (PDF)" sur la page /wallet (téléchargement blob authentifié). Testé : PDF 2,7 Ko valide, vendeur 19 mouvements, acheteur solde org 500.

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

### 2026-02 — Redesign Login / Landing / Tarifs (UX coopérative)
- ✅ **`/connexion` refonte totale** : split panel dark navy (KDMARCHE) + white form. Badge "ESPACE MEMBRES", storytelling coopératif, 3 bénéfices (Centrale B2B2C, Conditions mutualisées, Cadre sécurisé), footer RGPD/SSL. Bouton bleu profond, Google OAuth intégré, lien "Adhérer à la Centrale", et **callout "Vous êtes administrateur ? Connexion admin"** en bas.
- ✅ **`/admin/connexion` nouvelle page** : split panel dark purple (#4a1776) + gold (#F5A623). Badge "ESPACE ADMINISTRATEUR", warning journalisation, formulaire distinct. Enforcement `is_admin` : login refusé + logout automatique + toast erreur si le compte n'est pas admin. Redirect vers `/superadmin` sur succès.
- ✅ **`NavBar` simplifié** : top bar publique = Accueil, LOGI'SCOP, O'SCOP, Tarifs + (si connecté) Mon Espace + Catalogue. Tout le reste (Wallet, Commandes, Documents, Espace Vendeur, Super Admin, Plans, Admin Orgs, Validation Produits, Recon Stripe, GED, Finance) passe dans le dropdown avatar structuré en 3 sections (Compte / Vendeur / Administration).
- ✅ **`/tarifs` nouvelle page** : 3 abonnements ESS ACCÈS PRO 149€ (bleu), ESS VOLUME PRO 349€ (or, badge RECOMMANDÉ), ESS IMPACT PRO 749€ (violet). Trust strip (Sécurisé / Mutualisé / Coopératif / Performant) + FAQ courte + CTAs adhésion.
- ✅ **Landing : bandeau `CooperativeApiSection`** ajouté (violet + or) avec message institutionnel "API Coopérative B2B2C — Accès Pro Mutualisé", 4 piliers, et bloc code JSON reprenant la formulation API cooperative (`service_name: "CommunityPlace Pro Cooperative API"`, etc.).
- Palette appliquée : violet profond `#4a1776` + jaune `#F5A623` (charte KD MARCHÉ Pro) + bleu KDMARCHE `#0B4D87` + or O'SCOP `#D9B35A`.
- Build frontend clean (yarn build OK), aucune régression sur les routes existantes.

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

### 2026-06 — i18n Phase A COMPLÈTE (FR/EN/ES) — Vitrine & Parcours Client
**Architecture i18n :**
- 9 fichiers de locales (< 500 lignes chacun) : `{fr,en,es}.json` (common/nav/footer/auth), `{fr,en,es}-site.json` (landing/partners/logistics/contact/offers/pricing/logiscop/oscop/catalog), `{fr,en,es}-app.json` (buyer/checkout/favorites/lists/lolodrive/onboarding/orders/pass/relay/wallet)
- Merge par spread dans `i18n/index.js` ; détection `?lang=` > localStorage > navigator > FR
- `LanguageSwitcher` : changeLanguage + reload (les pages utilisent `i18n.t()` hors hook)
- ~490 clés × 3 langues

**Bugs corrigés :**
- ✅ NavBar plantait tout le site : `useTranslation` importé mais hook jamais appelé → `t is not defined` (crash React total)
- ✅ Clés `auth.*`, `footer.*`, `nav.*` référencées mais absentes des JSON (pages auth affichaient les clés brutes)
- ✅ LanguageSwitcher ne rechargeait pas la page (i18n.t hors hook non réactif)

**Pages traduites (Phase A)** : Landing (+ PricingSection, PartnersSection, LogisticsSection, ContactForm), Header, Footer, Breadcrumb, Login, Register, ForgotPassword, Tarifs, Offres, LOGI'SCOP, O'SCOP, Catalog, Checkout (+ CheckoutSteps/Payment/Dialog + toasts), Orders, Wallet, Favorites, ShoppingLists, Onboarding, PassSpace, BuyerSpace (+ Dashboard/Invoices/Orders tabs, buyerUtils statuts/dates via getters i18n)
- Dates : `toLocaleDateString(i18n.language)` partout dans le parcours client

**Tests** : iteration_18 (6 issues détectées) + iteration_19 (6/6 fixes PASS) + vérif visuelle finale (breadcrumb + recent orders EN OK). ~90-100% frontend PASS.

**Restant (Phase B — P1)** : Espaces Admin, SuperAdmin, Vendor, Dashboard Lolodrive (namespaces à créer). Les catégories produits viennent de la DB (données FR, non couvertes par i18n UI).
**Note testing agent** : préférer `<Trans>` aux clés prefix/suffix pour les futures locales.

### 2026-06 — i18n Phase B (Admin/SuperAdmin/Vendeur/Lolodrive) + Devise locale — TERMINÉ
**Devise & dates locales :**
- 37+ fichiers : `Intl.NumberFormat('fr-FR')` / `toLocaleDateString('fr-FR')` → `i18n.language` (EN : €1,234.56 · Jul 16 ; FR : 1 234,56 € · 16 juil.). `fmtEUR` de LolodriveLayout localisé aussi.

**Phase B i18n (~420 clés, namespace `adm`) :**
- Nouveaux fichiers : `{fr,en,es}-admin.json` (~420 lignes chacun, < 500 ✅), mergés dans i18n/index.js
- Pages : AdminLoginPage, AdminPage, AdminPlansPage (+plans/*), AdminProductsPage (+ProductDetailModal), AdminV2Page (+adminv2/*), SuperAdminPage (+superadmin/*), VendorSpacePage (+vendor/*), LolodriveAdminDashboardPage (+LolodriveLayout), BackButton, NotificationToast (Connecté/Déconnecté)
- Extraction automatisée par scripts regex (texte JSX, placeholder/title/label/sub, toasts, labels JS) + passes manuelles multilignes

**Tests** : iteration_20 (1 CRITICAL trouvé : import i18n manquant dans PlansTab → crash /admin/plans — corrigé ; + résidus FR Lolodrive/Vendor/AdminProducts/BackButton — tous corrigés et vérifiés par screenshots EN/ES post-fix)
**Notes** : la route Lolodrive admin est `/lolodrive`. Textes générés côté serveur (alertes type "11 commande(s) payée(s) en attente >2h", noms de catégories DB, features des plans en DB) non couverts par i18n frontend — nécessiterait i18n des données backend (backlog).
**i18n est désormais COMPLET (Phase A + B) sur ~910 clés × 3 langues.**

### 2026-06 — Fix P0 crash /catalogue (post-migration cookies httpOnly) — TERMINÉ
- Cause: `tData()` utilisé sans import dans `CatalogPage.jsx` et `components/catalog/ProductsGrid.jsx` → ReferenceError.
- Fixes: imports `tData` ajoutés; WebSocket notifications ne se connecte plus avec `user_id` vide (`NotificationToast.jsx` guard `if (!userId)`); `SuperAdminPage.jsx` lit l'id via `JSON.parse(localStorage.getItem('user'))?.id`; localisation `+N autres` via `adm.plus_more` / `buyer.plus_more_items` (fr/en/es).
- Validé par testing_agent iteration_22: 100% (6/6 flows) — catalogue, add-to-cart, favoris, i18n EN, WebSocket user_id réel, logout/régression. 0 erreur console.
- Restant: Test Stripe LIVE 1€ (attente utilisateur), pont GED ESS externe, microservice finance-api.

### 2026-06 — Socle Connecteurs multi-apps + Connecteur n°1 O'SCOP + Alertes favoris — TERMINÉ
- **Socle connecteurs** (`/app/backend/connectors/`): file unifiée `connector_sync_events` (retry, journal), registre extensible (8+ apps prévues). Routes `/api/connectors/*` (admin). Page admin `/admin/connecteurs` (cartes santé, push manuel, file avec retry + compteur tentatives). Lien menu ADMINISTRATION.
- **Connecteur oscop-ged / oscop-finance** vers CRM réel https://objectifscopoutremer.com (login Bearer via OSCOP_CRM_URL/EMAIL/PASSWORD dans .env, token cache + relogin 401). Health OK live. Push paiement `/api/paiements` : SUCCESS live (paiement test créé puis supprimé côté CRM). Push GED `/api/ged/documents/upload` : ERROR — **bug côté CRM distant** ("Path parameters cannot have a default value"), à corriger dans le projet objectifscopoutremer ; l'événement reste en file avec retry.
- **Sync auto** : commande payée (checkout_handlers) → facture PDF vers GED + paiement vers Finance ; contrat signé (routes_contracts) → document vers GED. Non bloquant (asyncio).
- **Alertes favoris** (`favorites_alerts.py` + `routes_stock_admin.py`): PUT /api/catalog/admin/stock/{id} (restock 0→>0) et /price/{id} (baisse prix) → notification in-app + email Brevo (201 vérifiés), anti-spam 24h.
- **Fix bug pré-existant** : `UserMenu` crashait (`nav is not defined`) au clic sur l'avatar — prop `nav` désormais passée depuis NavBar.
- Testé iteration_23 : backend 10/10, frontend 7/7 (100%).
- Compte de service `bridge@kdmarche.fr` à créer côté CRM par l'utilisateur (login refusé actuellement, admin@felixia.fr utilisé en attendant — basculer via .env).
- Restant : corriger upload GED côté CRM distant, connecter les 7 autres apps (1 adaptateur + .env chacune), test Stripe LIVE 1€ (attente utilisateur).

### 2026-06 — Centre d'alertes favoris (acheteur) — TERMINÉ
- Page `/alertes-favoris` (FavoriteAlertsPage.jsx) : liste des favoris avec switch alertes ON/OFF par produit + historique des alertes reçues (restock/promo). Lien menu acheteur « Alertes favoris ».
- Backend `routes_favorites_alerts_center.py` : GET /api/user-prefs/favorites/alerts-center, PUT /api/user-prefs/favorites/{product_id}/alerts. `favorites_alerts.py` respecte `alerts_enabled` (testé : OFF → 0 notifié).
- i18n fr/en/es (`fav_alerts.*` + nav.favorite_alerts).
- Auto-testé (curl e2e + screenshot). Les 7 autres apps à connecter : l'utilisateur fournira la liste plus tard.

### 2026-06 — Corrections revue de code externe — TERMINÉ (iteration_24 : 100%)
- Backend : wildcard imports remplacés par imports explicites (routes_checkout, routes_checkout_v1, abac_policy) ; 6 vrais NameError `generate_id` corrigés (routes_admin_ess_capacity/_rules — les créations ESS crashaient en 500) ; credentials tests via env vars ; refactor favorites_alerts (helpers _already_alerted/_notify_user).
- Frontend : DOMPurify sur dangerouslySetInnerHTML (LegalDocument) ; keys stables au lieu d'index (6 fichiers) ; http.js ne lit plus jamais de token localStorage ; export CSV admin via cookies.
- Vérifié : « 122 missing hook deps » du rapport = FAUX POSITIF (eslint react-hooks/exhaustive-deps = 0 warning sur tout src/). « Circular imports » déjà atténués par imports in-function (serveur démarre sans erreur).
- REPORTÉ (risque régression > gain, code legacy testé) : refactor des fonctions legacy complexes (logiscop_v1_pricing, lolodrive_checkout_apply, ess_models...) et découpage des 5 composants 400-460 lignes (tous < règle d'or 500).
- Non-régression validée par testing_agent iteration_24 : backend 10/10, frontend 7/7.

### 2026-06 — Revue de code externe, 2e passe — TERMINÉ (iteration_25 : 100%)
- Backend : wildcard imports → explicites dans routes_logiscop (avec TRANSPORT_RATES_PER_M3), routes_payment, schema_catalog (ré-exports explicites enums+cart).
- Frontend : catches silencieux → console.debug (PosLolodrive, Onboarding, Landing, useLolodriveWebSocket ×3) ; keys index → stables (ApplicationsTab, PricingSection, PartnersSection ×4, LogisticsSection, AdvancedStatsCharts).
- Régression introduite puis corrigée : LogisticsSection avait perdu le paramètre `index` encore utilisé (landing blanche) — corrigé par testing agent (restauré `(step, index)`), + 2 keys PartnersSection restantes corrigées ensuite (blocs dupliqués).
- Validé iteration_25 : backend 10/10, frontend 7/7. Landing vérifiée visuellement après le dernier fix.
- Toujours reporté (décision maintenue) : refactor fonctions legacy complexes + découpage composants 400-460 lignes (< règle d'or 500). Suggestion testing agent en backlog : ErrorBoundary autour des sections landing.

### 2026-06 — Revue de code externe, 3e passe — TERMINÉ (iteration_26 + pytest 20/20)
- Backend : wildcard imports → ré-exports explicites (schema_catalog_cart, schema_product_card, schema_v2 — attention: schema_v2_zones exporte aussi PartnerAccountInDB, AuditLogEntry, OutboxEvent*, DEFAULT_ZONES/PLANS) ; secrets test_iter25 → env vars. Auto-testé : pytest iter23+iter25 = 20/20.
- Frontend : objets chart inline → constantes module (StripeReconciliationPage, LoloPointManagerPage, SignatureDemoPage) ; useNavigationHistory : localStorage → sessionStorage.
- Régression détectée par testing agent (iter26) et corrigée : import i18n manquant dans reconciliationUtils.js (page stripe-reconciliation cassée) — vérifiée visuellement après fix.
- Points redondants du rapport (déjà traités passes 1-2) : XSS/DOMPurify en place, hook deps faux positif (ESLint 0 warning), circular imports en lazy imports.
- Toujours reporté : refactor fonctions legacy complexes + découpage composants <500 lignes.
NOTE DEPLOIEMENT : un déploiement production a échoué le 17/07 (timeout readiness). Si l'utilisateur en parle → lancer deployment_agent pour scanner les blockers.

### 2026-06 — Fix déploiement production « impossible de publier » — TERMINÉ (iteration_27 : 100%)
- Cause : `load_dotenv(override=True)` dans server.py écrasait en prod le MONGO_URL injecté par la plateforme avec `localhost:27017` du .env packagé → crash startup (ServerSelectionTimeoutError). En plus, le probe de readiness tapait GET /health (racine) → 404.
- Fix : load_dotenv SANS override + override sélectif des seules clés STRIPE_* depuis le .env (placeholder pod sk_test_emergent doit rester écrasé en preview) + route racine GET /health → 200.
- Validé : simulation prod (MONGO_URL plateforme préservé, clé Stripe projet prioritaire), deployment_agent PASS sans blocker, testing_agent 9/9 backend + smoke frontend 100%.
- L'utilisateur peut relancer le déploiement (bouton Deploy).

### 2026-06 — Connecteurs des 4 apps supplémentaires + vérif prod — TERMINÉ
- Vérification PRODUCTION (https://coop-dashboard-8.emergent.host) : login admin OK, connecteurs oscop enabled, health oscop-ged OK — les variables OSCOP sont bien reprises en prod. ✅
- Nouveau `connectors/generic_app.py` : adaptateur générique (login → Bearer token ou cookie session, health). 4 apps branchées :
  - oscop-ia-bois (https://oscop-ia-bois.emergent.host, token, /api/health) — OK
  - oscop-ge (https://ge-outremer-hub.emergent.host, access_token, /api/auth/me) — OK
  - coppam (https://treasury-dash-4.emergent.host, cookie session, /api/auth/session) — OK
  - crm-ess (https://fastapi-react-crm-4.emergent.host, ws_token, /api/health) — OK (= app du zip CRM-ESS-main)
- Registre étendu (6 connecteurs), dispatch health dans routes_connectors. Page admin affiche les 6 cartes, test santé COPPAM vérifié via UI (badge OK).
- Config .env : IABOIS_*, OSCOPGE_*, COPPAM_*, CRMESS_* (URL/EMAIL/PASSWORD ×4).
- ⚠️ Ces nouvelles variables ne seront en PRODUCTION qu'au prochain déploiement.
- FLUX MÉTIER PAR APP : à définir avec l'utilisateur (actuellement : santé + socle prêt, pas encore de push automatique pour ces 4 apps).

### 2026-06 — Flux COPPAM + CRM ESS + préparation test Stripe Live — TERMINÉ (iteration_28 : 100%)
- `sync_order_paid` pousse maintenant vers 4 connecteurs : oscop-ged (facture PDF), oscop-finance (paiement), coppam (encaissement POST /api/invoices — API distante en 500, événements en file avec retry = comportement attendu), crm-ess (facture PDF via POST /api/documents/upload, VALIDÉ live). `sync_contract_signed` → ged + crm-ess.
- `generic_app.request()` : client authentifié réutilisable (Bearer ou cookie session). COPPAM_MEMBER_ID dans .env.
- Nettoyage effectué : paiement test oscop + doc test crm-ess supprimés des apps de prod.
- Stripe PROD vérifié : mode LIVE, 2 clés configurées (oscop sk_live_51ScyA…, kdmarche sk_live_51Fqcz…). ⚠️ last_webhook_received=null → l'utilisateur doit vérifier dans le dashboard Stripe que les webhooks pointent vers https://coop-dashboard-8.emergent.host (endpoints: /api/checkout/webhook, /api/webhook/stripe, /api/lolodrive/stripe/webhook).
- TEST 1€ LIVE : à exécuter PAR L'UTILISATEUR avec sa carte sur l'app publiée ; ensuite l'agent vérifie la réconciliation et procède au remboursement.
- ⚠️ Redéploiement nécessaire pour activer les nouveaux flux + variables (IABOIS_*, OSCOPGE_*, COPPAM_*, CRMESS_*) en production.

## 2026-07-17 — Renommage de marque
- "Centrale d'achat(s)" remplacé par "Communityplace" dans toute l'app (26 fichiers : frontend FR/EN/ES i18n, textes légaux, backend emails/PDF/API). Équivalents EN ("purchasing hub") et ES ("central de compras") également remplacés par la marque Communityplace.
- Badge "Communityplace" (pastille dorée avec icône Store) ajouté dans les 2 en-têtes : Header.jsx (site vitrine) et NavBar.jsx (application). Composant réutilisable : frontend/src/components/CommunityplaceBadge.jsx.

## 2026-07-17 — Validation Écosystème + Page Marque
- Section "Pourquoi Communityplace ?" ajoutée sur la landing (composant WhyCommunityplaceSection.jsx, i18n FR/EN/ES, 3 cartes Community/Place/Coopérative).
- Validation complète (iteration_29.json) : backend connecteurs 7/7 (ecosystem, sync IA Bois ~44 projets, sync-events, health), frontend 100% (EcosystemPanel /admin, section Communityplace, badge en-tête, aucun résidu "centrale d'achat", non-régression /catalogue). Scheduler confirmé actif (IA Bois 15 min, PASS 6h). 6 apps externes en santé OK.
- Note testing agent : EcosystemPanel dépend du cookie httpOnly (pas de header Bearer) et n'affiche pas d'état d'erreur en cas de 401/500 (amélioration possible).
- Reste à faire (P0) : Test Stripe LIVE 1€ + remboursement en production (action utilisateur guidée).

## 2026-07-17 — Alerte Panne Connecteur + Devis IA Bois
- Health watch écosystème : boucle scheduler toutes les 10 min (connectors/health_watch.py) → email admin (Brevo, repli SendGrid) uniquement sur transition OK→ERROR (critical) ou ERROR→OK (medium). Statuts stockés dans connector_health_status, exposés via GET /api/connectors/health-status. Destinataire : ADMIN_ALERT_EMAIL (défaut admin@kdmarche-oscop.fr).
- Devis IA Bois 1-clic : POST /api/connectors/iabois/projects/{id}/quote (idempotent) génère un devis matériaux pré-rempli depuis les paramètres du projet (surface, chambres, toit, terrasse, garage) — lignes ossature/isolation/bardage/couverture/menuiseries, TVA 8.5%. Collection iabois_quotes, projet passe en statut QUOTED. UI : boutons "Créer le devis"/"Voir le devis" dans IaboisProjectsPanel + modal IaboisQuoteModal (i18n FR/EN/ES).
- Testé : curl backend (création + idempotence), simulation transitions health watch (alerts_sent=1 via Brevo), flux UI e2e validé par screenshot (modal devis 57 003,73 € TTC).

## 2026-07-17 — Historique pannes + Header/Footer + Drapeaux + Droits & Rôles
- Historique pannes : transitions enregistrées dans connector_health_events, GET /api/connectors/health-history, modal timeline au clic sur une carte du panneau Écosystème (EcosystemHistoryModal.jsx).
- Liens LOGI'SCOP et O'SCOP retirés du header (navItems.js) et ajoutés au footer (Footer.jsx, data-testid footer-link-logiscop/oscop).
- Sélecteur de langue : drapeaux images flagcdn (fr/gb/es) à la place des codes texte (LanguageSwitcher.jsx).
- Droits & Rôles (super admin) : routes_team_roles.py (/api/admin/team — list/search/grant/revoke/create), rôles ADMIN/COOPER/EXPERT + 7 rôles techniques. Création de membre = mdp temporaire affiché + email Brevo. Revoke restaure le rôle d'origine (snapshot previous_role). Guard : mutations réservées SUPER_ADMIN/OSCOP_SUPER_ADMIN/is_admin. UI : onglet "Droits & Rôles" sur /superadmin (TeamRolesTab.jsx + TeamMemberForms.jsx), i18n FR/EN/ES.
- Validation : iteration_30.json — backend 3/3, frontend 4/4 PASS. Fix post-test : revoke restaure previous_role (re-testé curl : buyer restauré). Compte test : cooper-test@kdmarche.fr (COOPER, voir test_credentials.md).

## 2026-07-17/18 — Espaces rôles + Espace Acheteur + Vendeur fix + Taxonomie + Photos produits
- Espaces COOPER (/espace-cooper) et EXPERT (/espace-expert) : KPIs via GET /api/team/overview (guard staff), RoleSpaceLayout partagé, liens dans le menu selon rôle.
- Onglet "Espace Acheteur" (/superadmin) : GET /api/admin/buyers + PATCH credits/suspend, tableau avec crédits éditables et suspension (BuyersTab.jsx).
- Espace Vendeur : boutons Voir (VendorProductViewModal + fiche), Modifier (formulaire pré-rempli, PUT), Fiche PDF (GET /api/vendor/products/{v}/{p}/pdf via pdf_product_sheet.py reportlab).
- Onglet "Catégories & Taxes" (/superadmin) : routes_taxonomy.py (collections product_categories + tva_rates, seed 8 cat/6 taux au démarrage), CRUD instantané, formulaire produit vendeur hydraté depuis l'API.
- Photos produits : POST upload-image (multipart PNG/JPEG, max 3, 5 Mo, 1 principale), fichiers dans /app/backend/uploads/products servis via StaticFiles /api/uploads. UI ProductPhotoUploader (préviews, étoile principale).
- Validation iteration_31.json : backend 11/11, frontend 100% PASS. Post-test : slug vide rejeté (taxonomy), DialogDescription a11y, note champs modifiables en édition.

## 2026-07-18 — Page vitrine KDMARCHÉ + Studio IA + Crédits vendeurs
- Page publique /kdmarche (KdmarchePage.jsx) : hero Communityplace B2B2C, 5 stats EN DIRECT (GET /api/public/kdmarche-stats), piliers Vendeurs/Acheteurs, CTA inscription. Liens menu topbar + footer.
- Studio IA vendeur (AIStudioModal.jsx, bouton par produit) : génération d'image studio par prompt + amélioration de photo (Gemini Nano Banana via EMERGENT_LLM_KEY, module llm copié dans le package vendored /app/backend/emergentintegrations — NE PAS écraser payments qui est patché pour Stripe). Spot vidéo Veo 3 via fal.ai : code prêt (routes_vendor_ai.py, job async ai_video_jobs) mais EN ATTENTE de FAL_KEY utilisateur (503 + warning UI tant que non configurée).
- Crédits vendeurs (vendor_credits.py) : barème credit_pricing seedé (fiche 5, photo 1, image IA 10, amélioration 8, vidéo 50), consume/refund + transactions, consommation branchée sur submit_product/upload-image/IA. Admin : onglet "Crédits & IA" /superadmin (barème éditable + attribution soldes). Solde affiché dans l'espace vendeur. vendor-demo-pro seedé à ~152 crédits.
- Validation iteration_33.json : backend 9/9, frontend 4/4 PASS. Génération/amélioration IA réelles validées par main agent (images attachées au produit rhum, crédits décomptés, remboursement sur échec).
- EN ATTENTE UTILISATEUR : clé FAL_KEY (fal.ai/dashboard/keys) pour activer la vidéo ; test Stripe Live 1€ en production.

## 2026-07-18 — Packs Stripe + Promotions + Analytics + Historiques + FAL_KEY
- FAL_KEY configurée dans backend/.env (video:true). ⚠️ Compte fal.ai SANS SOLDE — jobs vidéo → ERROR "Exhausted balance" + remboursement auto. L'utilisateur doit recharger sur fal.ai/dashboard/billing.
- Packs de crédits Stripe (routes_credit_packs.py) : starter 50/9,90€, pro 200/29,90€, studio 500/59,90€ (collection credit_packs). Achat via _create_checkout_session (compte RECHARGE), crédit idempotent au polling /api/credit-packs/status/{sid} avec bonus promo. UI : badge crédits cliquable → CreditPacksModal (packs + historique), polling ?credit_session= au retour Stripe.
- Promotions (credit_promotions.py) : bonus_purchase / discount_action en %, scopes profil/territoire/catégorie/action, CRUD + archivage admin (/api/admin/credit-promotions). Discount appliqué dans consume_credits (arrondi ceil). UI : CreditPromotionsPanel dans l'onglet Crédits & IA.
- Analytics (/api/admin/credit-analytics) : totaux achetés/consommés/remboursés/revenus € + ventilation service/vendeur/territoire/catégorie (transactions enrichies category/territory/owner_type). UI : CreditAnalyticsPanel.
- Historiques : vendeur (50 dernières transactions dans le modal), acheteur pro (GET /api/team/my-credits + section repliable BuyerCreditHistory sur /dashboard, ajustements admin loggés).
- Validation iteration_34.json : backend 7/7, frontend 3/3 PASS. Stripe LIVE : session créée jamais payée.
- EN ATTENTE : solde fal.ai (vidéos), test Stripe Live 1€ prod, 2 dernières apps écosystème.

## 2026-07-18 — Correction bugs UI signalés ("l'app bugg")
- Sweep frontend testing_agent (iteration_40.json) suite au signalement utilisateur "un bouton ne fait rien".
- FIX DashboardPage.jsx : 3 boutons morts → "Paramètres" = Link /changer-mot-de-passe, "Changer de formule" = Link /tarifs, "Contacter le support" = mailto:contact@centrale-ess.fr.
- FIX prix panier "---" : mismatch de champs API (price_ht_cents/line_total_ht_cents/subtotal_ht_cents) vs frontend (unit_price_ht_cents/total_ht_cents). Corrigé dans CatalogHeader.jsx + CatalogPage.jsx (+ product_sku).
- FIX CrediscopBadge : variante publique pour visiteurs non connectés → badge "GALERIE SPOTS" (Link /kdmarche), ajouté au NavBar branche non-authentifiée. Skip du fetch /me/crediscop si non connecté.
- Faux positif rapport : /kdmarche fonctionne (vérifié par screenshot).
- Vérifications screenshot : boutons naviguent, panier affiche 128,00 € HT / Total 144,59 €, badge public cliquable → /kdmarche.

## 2026-07-18 — Formulaire Contact Support (Brevo) + Alertes Panier
- Page /contact (+ alias /support) : SupportContactPage.jsx — formulaire (nom, email, catégorie, sujet, message), préremplissage user connecté, écran de confirmation avec n° de ticket.
- Backend routes_support.py : POST /api/support/contact → ticket en base (support_tickets, n° SUP-YYYYMMDD-XXXXXX) + 2 emails Brevo (équipe support via SUPPORT_CONTACT_EMAIL=contact@centrale-ess.fr dans .env, confirmation à l'expéditeur). Validé E2E (201 Brevo, ticket créé).
- Bouton "Contacter le support" du dashboard acheteur pointe désormais vers /contact.
- Alertes panier : _refresh_cart_items() dans routes_cart_v2.py au GET /api/v2/catalog/cart — détecte PRICE_CHANGED (met à jour prix + totaux, alerte one-shot), UNAVAILABLE (flag persistant item.unavailable, exclu du sous-total), AVAILABLE_AGAIN. CartResponse.alerts + CartItemResponse.unavailable.
- Frontend : toasts au chargement du catalogue, bannière data-testid=cart-alerts-banner dans le drawer, badge INDISPONIBLE rouge sur l'item, bouton checkout désactivé si item indisponible.
- Validé par curl (3 scénarios) + screenshots UI (toast prix, bannière indisponible, checkout désactivé, formulaire contact soumis avec succès).
