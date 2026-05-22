# KDMARCHÉ / LOLODRIVE by O'SCOP

Plateforme coopérative B2C/B2B2C pour la lutte contre la vie chère dans les Outre-Mer, opérée par O'SCOP avec KDMARCHÉ comme moteur commercial.

## Comprendre le projet en 5 lignes

| Composant | Rôle |
|-----------|------|
| **KDMARCHÉ** | Moteur commercial (catalogue B2B, marchandises, facturation EXW) |
| **LOLODRIVE by O'SCOP** | Réseau drive / livraison / relais coopératifs (POS, LOLO POINTS, événements) |
| **PASS Vie Chère** | 60€ = 600 UC, valable 30 jours, sans renouvellement automatique |
| **UC** | Unité interne d'usage (10 centimes = 1 UC). **Ce n'est pas une monnaie** |
| **CRM O'SCOP** | Couche relationnelle (contacts, partenaires, opportunités, dossiers, impact ESS) |
| **V2** | Moteur transactionnel (PASS, wallet UC, catalogue, commandes, paiement Stripe, drive, livraison, POS, LOLO POINTS, LOLO HOUR) |

## Règles métier non négociables

- **Les UC ne sont pas une monnaie.** Référence légale : le prix en euros.
- **PASS Vie Chère** : 60 € = 600 UC, valable 30 jours, **sans renouvellement automatique**.
- Produits **ESSENTIELS** (catalogue 25) : ont un prix PASS réduit (visible si PASS actif).
- Produits **Hors25** : au prix normal. Payables en UC **sans avantage** uniquement si PASS actif.
- **La V2 est la source de vérité transactionnelle.** Le CRM **ne duplique pas** le wallet UC.
- **CRM = couche relationnelle et impact**, jamais transactionnelle.

## Stack technique

- Backend : FastAPI + Motor (MongoDB)
- Frontend : React 19 + Tailwind + Shadcn/UI
- Paiement : Stripe (PaymentIntents, mode test)
- Auth : JWT custom multi-rôles

## Rôles

`SUPER_ADMIN`, `ADMIN`, `TITULAIRE_PASS`, `OPERATEUR_POS`, `GERANT_LOLO_POINT`, `PARTENAIRE_CRM`, `CONSEIL_COOPERATIF`

## Comptes démo

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Super Admin | `admin@kdmarche-oscop.fr` | `AdminKDM2025!` |
| Titulaire PASS | `marie@example.com` | `Demo2026!` |
| Opérateur POS | `pos@lolodrive.fr` | `Demo2026!` |
| Gérant Lolo Point | `gerant@lolopoint.fr` | `Demo2026!` |

## Démarrage

```bash
cd backend && pip install -r requirements.txt
python seed_lolodrive.py
sudo supervisorctl restart backend frontend
```

## API namespaces

| Préfixe | Rôle |
|---------|------|
| `/api/auth/*` | Auth JWT |
| `/api/lolodrive/*` | Moteur LOLODRIVE V2 (PASS, wallet, catalogue, orders, POS, LOLO POINTS, événements) |
| `/api/crm/*` | CRM O'SCOP Bridge (contacts, orgs, opportunités, dossiers, impact) |
| `/api/v1/b2b/*`, `/api/v2/*` | Compatibilité KDMARCHÉ B2B (catalogue multi-zones, LOGI'SCOP, OPA) |

## Écrans clés

- `/super-admin` — Dashboard super admin KDM + LOLODRIVE
- `/pass` — Espace titulaire PASS (activation, wallet UC, ledger, recharge)
- `/pos` — Interface POS LOLODRIVE (file commandes, scan, transitions)
- `/admin/lolo-points` — Gestion réseau LOLO POINTS
- `/admin/lolo-hour` — Gestion événements LOLO HOUR
- `/crm` — CRM partenaires (contacts, orgs, opportunités, dossiers)
- `/reporting-impact` — Reporting impact ESS

## Documents juridiques

CGV KDMARCHÉ, CG O'SCOP, Convention partenariat, Charte ESS, contrats LOGI'SCOP. Voir `/legal`.

---

Voir aussi : [`AI_CONTEXT.md`](./AI_CONTEXT.md)
