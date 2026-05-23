# Connexion GED ESS externe — KDMARCHE × O'SCOP

Ce patch ajoute un pont backend vers un microservice GED ESS externe sans supprimer la GED interne existante.

## Routes ajoutées

Base URL backend KDM :

```txt
/api/ged-bridge
```

Routes principales :

```txt
GET  /api/ged-bridge/health
GET  /api/ged-bridge/scopes
GET  /api/ged-bridge/sync-events
POST /api/ged-bridge/documents
POST /api/ged-bridge/pdf/generate
POST /api/ged-bridge/crm/dossiers/{dossier_id}/push
POST /api/ged-bridge/lolodrive/orders/{order_id}/push
```

## Variables d'environnement à ajouter au backend KDM

```env
GED_ESS_API_URL=http://ged-ess-api:8000
GED_ESS_API_TOKEN=<token_jwt_ou_token_machine>
GED_ESS_WEBHOOK_SECRET=<secret_hmac_partage>
GED_ESS_TIMEOUT_SECONDS=20
```

`GED_ESS_API_URL` peut pointer vers :

```txt
http://localhost:8001
https://ged.votre-domaine.fr
http://ged-ess-api:8000 dans Docker Compose
```

## Principe d'architecture

Le projet KDM conserve :

- MongoDB comme base applicative opérationnelle ;
- la GED interne actuelle `/api/ged` pour les documents HTML publics ;
- le CRM O'SCOP ;
- les commandes LOLODRIVE ;
- la facturation, les signatures et le paiement.

Le microservice GED ESS externe reçoit :

- les dossiers CRM structurés ;
- les commandes LOLODRIVE transformées en appels à contribution ;
- les documents PDF institutionnels ;
- les métadonnées de traçabilité ;
- les références externes CRM / commande / projet ;
- les événements synchronisés.

## Exemples d'appels

### Vérifier la connexion

```bash
curl -H "Authorization: Bearer <token_kdm>" \
  http://localhost:8000/api/ged-bridge/health
```

### Pousser un dossier CRM vers la GED externe

```bash
curl -X POST \
  -H "Authorization: Bearer <token_kdm>" \
  "http://localhost:8000/api/ged-bridge/crm/dossiers/<dossier_id>/push?entity_id=<ged_entity_id>&scope_id=<ged_scope_id>&generate_pdf=true"
```

### Pousser une commande LOLODRIVE vers la GED externe

```bash
curl -X POST \
  -H "Authorization: Bearer <token_kdm>" \
  "http://localhost:8000/api/ged-bridge/lolodrive/orders/<order_id>/push?entity_id=<ged_entity_id>&scope_id=<ged_scope_id>"
```

### Générer un PDF institutionnel directement

```bash
curl -X POST http://localhost:8000/api/ged-bridge/pdf/generate \
  -H "Authorization: Bearer <token_kdm>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Convention OSCOP - Coopérateur contributeur",
    "source": "oscop",
    "entity_id": "<ged_entity_id>",
    "scope_id": "<ged_scope_id>",
    "family": "CONTRAT_COOPERATIF",
    "context": {
      "contributor_name": "Entreprise Exemple",
      "object": "Intégration au périmètre coopératif"
    }
  }'
```

## Mapping métier

| Source KDM | Périmètre GED | Modèle PDF par défaut |
|---|---|---|
| coppam | COPPAM | COPPAM_ATTESTATION_CAPACITE |
| oscop / o_scop | OSCOP | OSCOP_CONTRAT_COOPERATIF |
| kdmarche / lolodrive | KDMARCHE | KDMARCHE_APPEL_CONTRIBUTION |
| fogedom | FOGEDOM | FOGEDOM_CONVENTION_FINANCEMENT |
| ftpe | FTPE | GENERIQUE_ESS |
| general | GENERAL | GENERIQUE_ESS |

## Fichiers ajoutés

```txt
backend/ged_external_client.py
backend/routes_ged_bridge.py
docs/GED_ESS_BRIDGE.md
```

## Fichier modifié

```txt
backend/server.py
```

Le serveur charge maintenant automatiquement le routeur `ged_bridge_router` et crée les index MongoDB de synchronisation.
