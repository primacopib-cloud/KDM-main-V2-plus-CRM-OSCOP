# SPÉCIFICATION — RÉCEPTEUR DE SPOTS VIDÉO KDMARCHÉ

> Document à copier-coller dans l'agent Emergent de chaque application de l'écosystème O'SCOP :
> - OSCOP IA Bois — https://oscop-ia-bois.emergent.host
> - O'SCOP GE — https://ge-outremer-hub.emergent.host
> - COPPAM — https://treasury-dash-4.emergent.host
> - CRM ESS — https://fastapi-react-crm-4.emergent.host

---

## PROMPT À COLLER DANS CHAQUE APP

Ajouter un endpoint récepteur qui accepte la diffusion des spots vidéo publicitaires
envoyés par le hub de connecteurs KDMARCHÉ.

### Endpoint à créer
- **Méthode/Route** : `POST /api/kdmarche/spots`
- **Authentification** : Bearer token de l'utilisateur admin (le hub KDMARCHÉ s'authentifie
  d'abord via `POST /api/auth/login` avec le compte admin existant, puis appelle l'endpoint
  avec `Authorization: Bearer <token>`). Protéger l'endpoint par l'auth existante de l'app.

### Payload reçu (JSON)
```json
{
  "count": 2,
  "spots": [
    {
      "product_id": "vp-damoiseau-rhum-blanc",
      "product_name": "Rhum blanc agricole AOC 1L",
      "vendor_name": "Distillerie Damoiseau",
      "views": 12,
      "videos": {
        "fr": "https://<kdmarche-prod>/api/uploads/videos/<job>.mp4",
        "en": "https://<kdmarche-prod>/api/uploads/videos/<job>.mp4",
        "es": "https://<kdmarche-prod>/api/uploads/videos/<job>.mp4"
      },
      "source": "kdmarche"
    }
  ]
}
```
- `videos` : URLs absolues des spots MP4 (H.264/AAC), une entrée par langue disponible (fr/en/es).
- Le hub renvoie régulièrement la liste complète : traiter en **upsert par `product_id`**
  (pas d'insertion en doublon).

### Comportement attendu
1. Upsert de chaque spot dans une collection/table `kdmarche_spots`
   (clé : `product_id`, champs : product_name, vendor_name, views, videos, source, received_at).
2. Réponse : `200 {"status": "OK", "received": <count>}`.
3. (Optionnel mais recommandé) Afficher les spots reçus dans l'interface :
   une section "Spots vidéo KDMARCHÉ" (lecteurs vidéo avec le nom du produit et du vendeur),
   par exemple sur le tableau de bord ou une page dédiée.

### Test de validation
Depuis KDMARCHÉ (page /admin/connecteurs), le super admin clique sur
« Diffuser les spots vidéo » : l'événement doit passer de ERROR (404) à SUCCESS
dans la file de synchronisation du hub.
