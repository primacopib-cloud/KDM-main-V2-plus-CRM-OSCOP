# finance-api — Microservice financier coopératif

> Service **séparé** du projet KDM. Tourne sur le port **8010** avec sa propre base (SQLite en dev, PostgreSQL `finance_api` en prod). Aucune dépendance directe au backend KDM : KDM appellera ce service via un client HTTP léger (`finance_external_client.py`) plus tard.

## Démarrer en dev (testable seule, sans KDM)

```bash
cd /app/finance-api
pip install -r requirements.txt
cp .env.example .env   # déjà fait dans ce repo
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

Swagger UI : <http://localhost:8010/docs>

## Endpoints clés (étape P1 → P5 OK)

| Méthode | Route                                            | Auth | Description |
|---------|--------------------------------------------------|------|-------------|
| GET     | `/health`                                        | non  | Liveness + flags config |
| POST    | `/setup/bootstrap`                               | non* | Crée l'admin initial (refuse si users > 0) |
| POST    | `/auth/token`                                    | non  | OAuth2 password — renvoie un JWT |
| POST    | `/parties`                                       | JWT  | Crée un tiers (client/adhérent/fournisseur) |
| GET     | `/parties`                                       | JWT  | Liste paginée + recherche |
| POST    | `/receivables`                                   | JWT  | Crée une créance (INVOICE / PASS / COTISATION / APPEL_CONTRIBUTION) |
| GET     | `/receivables`                                   | JWT  | Liste filtrable |
| POST    | `/payments`                                      | JWT  | Initie un paiement (PSP Stripe/GoCardless/manual) |
| POST    | `/payments/{id}/mark-paid`                       | JWT  | Confirme manuellement (cash, sandbox, virement) |
| POST    | `/payments/{id}/refund`                          | JWT  | Remboursement (partiel ou total) |
| POST    | `/sepa/mandates`                                 | JWT  | Crée un mandat SEPA Core ou B2B |
| POST    | `/sepa/mandates/{id}/activate`                   | JWT  | Activation après signature |
| POST    | `/sepa/mandates/{id}/revoke`                     | JWT  | Révocation |
| POST    | `/installment-plans`                             | JWT  | Échéancier multi-versements |
| POST    | `/webhooks/stripe` / `/webhooks/gocardless`      | non  | Intake PSP (idempotent, HMAC à brancher) |
| GET     | `/reporting/dashboard`                           | JWT  | KPI consolidés |
| GET     | `/ledger/entries`                                | JWT  | Journal financier (lecture seule) |
| GET     | `/audit/verify-ledger-chain`                     | JWT  | Vérifie la chaîne de hash du journal (audit probant) |

*\* `/setup/bootstrap` est ouvert puis se refuse seul une fois exécuté.*

## Journal financier probant

Chaque mutation métier (créance créée, paiement réussi, remboursement, mandat activé…) ajoute une ligne dans `ledger_entries` :

- `sequence` monotone (1, 2, 3, …)
- `previous_hash` = SHA-256 de l'entrée précédente
- `entry_hash` = SHA-256 du payload canonical + previous_hash
- **Append-only** : aucune route ne fait `UPDATE` / `DELETE` sur cette table

Toute altération est détectable via `GET /audit/verify-ledger-chain` qui re-marche la chaîne et renvoie la première rupture.

## Mapping KDM → Finance

| KDM / LOLODRIVE        | Finance API                                |
|------------------------|--------------------------------------------|
| client / adhérent      | `Party`                                    |
| commande               | `Receivable` (`receivable_type=ORDER`)     |
| PASS Vie Chère         | `Receivable` (`PASS_CONSOMMATION`)         |
| cotisation             | `Receivable` (`COTISATION`)                |
| appel à contribution   | `Receivable` (`APPEL_CONTRIBUTION`)        |
| paiement immédiat      | `Payment`                                  |
| paiement en N fois     | `InstallmentPlan` + `Installment[]`        |
| mandat bancaire        | `SepaMandate`                              |
| journal financier      | `LedgerEntry` (chaîné)                     |

## Étape suivante (P6) — Bridge côté KDM

À faire **après** validation E2E de ce service seul :
- `/app/backend/finance_external_client.py` (HTTP client → finance-api)
- `/app/backend/routes_finance_bridge.py` (routes `/api/finance-bridge/*` admin-only)
- 9 lignes dans `server.py` (import + include_router).
