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

## 4. Backlog

### P1 — Internationalisation
- Wrapper toutes les chaînes UI restantes avec `t()` (scaffolding i18n déjà en place)
- Activer la vérification du token webhook Brevo (`X-Brevo-Token`) en production

### P2 — Auth Google
- Brancher Google Login (Emergent-managed) avec `GOOGLE_CLIENT_ID` / `SECRET` fournis par l'utilisateur

### P2 — Stripe LIVE
- Bascule `STRIPE_MODE=live` quand l'utilisateur valide la mise en production (clé Live déjà dans le pod)

## 5. Test credentials
Voir `/app/memory/test_credentials.md`

## 6. Integrations
| Service | Statut | Clé |
|---|---|---|
| Stripe **O'SCOP** (Checkout + Subscriptions PASS, recharges UC, auto-renew, livraisons) | ✅ TEST actif | `STRIPE_API_KEY` / `STRIPE_LIVE_KEY` |
| Stripe **KDMARCHE** (commandes produits DRIVE) | ✅ TEST actif, LIVE key configurée | `STRIPE_KDMARCHE_API_KEY` / `STRIPE_KDMARCHE_LIVE_KEY` |
| Brevo (Email + SMS) | ✅ Configuré | API key dans `.env` |
| Mapbox GL | ✅ Configuré | `REACT_APP_MAPBOX_TOKEN` |
| Google Login (Emergent) | 🟡 Scaffolding | En attente vrais CLIENT_ID/SECRET OAuth (pas une API key) |

### Architecture Stripe multi-comptes
Centralisée dans `/app/backend/stripe_accounts.py`. Routage automatique :
- `kind=PASS` / `RECHARGE` / `SUBSCRIPTION` → compte **oscop**
- `kind=ORDER` (commandes DRIVE) → compte **kdmarche**
- Le `stripe_account` est persisté dans `payment_transactions` pour que le `status` polling et le webhook retrouvent le bon compte.
- Le webhook unique `/api/webhook/stripe` essaie chaque compte (signature mismatch ignoré) → un seul endpoint pour les 2 dashboards Stripe.
- Bascule LIVE : `STRIPE_MODE=live` dans `.env`, redémarrer backend.
