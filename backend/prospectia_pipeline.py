"""PROSPECT'IA — Pipeline de vente : vue kanban des prospects par étape avec actions IA suggérées."""
from fastapi import APIRouter, Depends

from lolodrive_helpers import require_admin

pipeline_router = APIRouter(prefix="/api/admin/prospectia", tags=["prospectia-pipeline"])
db = None

STAGES = [
    {"key": "a_contacter", "label": "À contacter", "suggestion": "Vérifiez la qualité des emails importés puis laissez PROSPECT'IA envoyer par lots de 20."},
    {"key": "contacte", "label": "Contacté", "suggestion": "Aucune action requise : la relance J+3 partira automatiquement pour les non-cliqueurs."},
    {"key": "relance", "label": "Relancé", "suggestion": "Après la relance J+7 sans clic, retirez le prospect ou tentez un canal WhatsApp/LinkedIn."},
    {"key": "clique", "label": "A cliqué", "suggestion": "Prospect chaud : appelez-le sous 48h ou envoyez une offre d'adhésion personnalisée."},
    {"key": "converti", "label": "Converti ✅", "suggestion": "Invitez ce nouveau membre à témoigner (Preuve sociale) et proposez le parrainage."},
]


def set_pipeline_database(database):
    global db
    db = database


def _stage(p: dict) -> str:
    if p.get("converted"):
        return "converti"
    if p.get("clicked"):
        return "clique"
    if p.get("followups", 0) > 0:
        return "relance"
    if p.get("status") == "sent":
        return "contacte"
    return "a_contacter"


@pipeline_router.get("/pipeline")
async def pipeline(admin: dict = Depends(require_admin)):
    columns = {s["key"]: [] for s in STAGES}
    async for c in db.prospectia_campaigns.find({}, {"_id": 0, "name": 1, "prospects": 1}):
        for p in c.get("prospects", []):
            columns[_stage(p)].append({
                "email": p["email"], "company": p.get("company"), "first_name": p.get("first_name"),
                "campaign": c["name"], "variant": p.get("variant"), "sent_at": p.get("sent_at"),
            })
    total = sum(len(v) for v in columns.values())
    conv_rate = round(100 * len(columns["converti"]) / total, 1) if total else 0
    return {"total": total, "conversion_rate": conv_rate,
            "stages": [{**s, "count": len(columns[s["key"]]), "prospects": columns[s["key"]][:50]} for s in STAGES]}
