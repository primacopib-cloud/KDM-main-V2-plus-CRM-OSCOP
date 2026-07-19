"""Modèles de consultations — bibliothèque admin pour industrialiser la création de lots récurrents."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

templates_router = APIRouter(prefix="/api/admin/consultation-templates", tags=["consultation-templates"])

db = None

DEFAULT_TEMPLATES = [
    {"id": "tpl-alimentaire-scellee", "name": "Alimentaire 1ère transformation — offres scellées",
     "title": "Approvisionnement alimentaire (offres scellées)", "type": "STANDARD", "procedure": "SCELLEE",
     "category": "alimentaire", "products": [], "territories": ["GUADELOUPE"],
     "specs": "Produits alimentaires de consommation courante — offres scellées obligatoires (art. L.442-8).",
     "max_rounds": 3, "duration_days": 7},
    {"id": "tpl-emballage-enchere", "name": "Emballage / consommables — enchère inversée",
     "title": "Fournitures d'emballage professionnel", "type": "STANDARD", "procedure": "ENCHERE_INVERSEE",
     "category": "emballage", "products": [], "territories": ["GUADELOUPE"],
     "specs": "Emballages et consommables non alimentaires — enchère inversée 3 tours.",
     "max_rounds": 3, "duration_days": 7},
    {"id": "tpl-transport-enchere", "name": "Transport / fret maritime — enchère inversée",
     "title": "Prestation de fret maritime interterritorial", "type": "INTERTERRITORIALE",
     "procedure": "ENCHERE_INVERSEE", "category": "transport", "products": [],
     "territories": ["GUADELOUPE", "MARTINIQUE"],
     "specs": "Fret conteneurisé inter-îles — prix rendu port, Incoterm CIF.", "max_rounds": 3, "duration_days": 10},
    {"id": "tpl-hygiene-enchere", "name": "Hygiène & entretien — enchère inversée",
     "title": "Produits d'hygiène et d'entretien professionnels", "type": "STANDARD",
     "procedure": "ENCHERE_INVERSEE", "category": "hygiene", "products": [], "territories": ["GUADELOUPE"],
     "specs": "Produits d'hygiène professionnelle — fiches de sécurité exigées.", "max_rounds": 3, "duration_days": 7},
]


def set_templates_database(database):
    global db
    db = database


async def ensure_default_templates():
    for t in DEFAULT_TEMPLATES:
        await db.consultation_templates.update_one(
            {"id": t["id"]},
            {"$setOnInsert": {**t, "active": True, "criteria": None, "sku_ean": None,
                              "created_by": "system", "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True)


class TemplateBody(BaseModel):
    name: str
    title: str
    type: str = "STANDARD"
    procedure: str = "SCELLEE"
    category: str
    sku_ean: Optional[str] = None
    products: List[dict] = []
    territories: List[str] = []
    specs: str = ""
    max_rounds: int = 3
    duration_days: int = 7
    criteria: Optional[List[dict]] = None


@templates_router.get("")
async def list_templates(admin: dict = Depends(require_admin)):
    await ensure_default_templates()
    items = await db.consultation_templates.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(100)
    return {"items": items}


@templates_router.post("")
async def create_template(body: TemplateBody, admin: dict = Depends(require_admin)):
    if not body.name.strip() or not body.category.strip():
        raise HTTPException(status_code=400, detail="Nom et catégorie obligatoires")
    doc = {**body.dict(), "id": f"tpl-{uuid.uuid4().hex[:8]}", "active": True,
           "category": body.category.strip().lower(),
           "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.consultation_templates.insert_one({**doc})
    return doc


@templates_router.put("/{tid}")
async def update_template(tid: str, body: TemplateBody, admin: dict = Depends(require_admin)):
    res = await db.consultation_templates.update_one(
        {"id": tid}, {"$set": {**body.dict(), "category": body.category.strip().lower(),
                               "updated_by": admin.get("email"),
                               "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return {"ok": True}


@templates_router.delete("/{tid}")
async def deactivate_template(tid: str, admin: dict = Depends(require_admin)):
    res = await db.consultation_templates.update_one({"id": tid}, {"$set": {"active": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return {"ok": True}


@templates_router.post("/{tid}/instantiate")
async def instantiate_template(tid: str, admin: dict = Depends(require_admin)):
    """Crée un lot BROUILLON en 1 clic depuis le modèle (statut juridique résolu, dates pré-remplies)."""
    t = await db.consultation_templates.find_one({"id": tid, "active": True}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    from routes_consultations import _next_ref, DEFAULT_CRITERIA
    from routes_cpc_admin import get_cpc_settings
    from routes_legal_matrix import resolve_legal_status
    settings = await get_cpc_settings()
    legal = await resolve_legal_status(t["category"], t.get("sku_ean"))
    procedure = "SCELLEE" if legal["status"] == "ROUGE" else t["procedure"]
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()), "ref": await _next_ref(), "version": 1,
        "title": t["title"], "type": t["type"], "procedure": procedure,
        "category": t["category"], "sku_ean": t.get("sku_ean"),
        "legal_status": legal["status"], "legal_matrix_id": legal.get("id"),
        "legal_matrix_version": legal.get("version"), "orange_validation": None,
        "products": t.get("products") or [], "territories": t.get("territories") or [],
        "specs": t.get("specs", ""),
        "cpc_cost": settings["interterritorial_cost"] if t["type"] == "INTERTERRITORIALE" else settings["standard_cost"],
        "max_rounds": t.get("max_rounds", 3), "criteria": t.get("criteria") or DEFAULT_CRITERIA,
        "tie_break_order": ["qualite", "logistique", "disponibilite", "tracabilite", "first_timestamp"],
        "opens_at": now.isoformat(),
        "closes_at": (now + timedelta(days=t.get("duration_days", 7))).isoformat(),
        "status": "BROUILLON", "validations": {}, "published_snapshot_hash": None,
        "template_id": tid, "created_by": admin.get("email"),
        "created_at": now.isoformat(), "updated_at": now.isoformat(),
    }
    await db.consultations.insert_one({**doc})
    await audit("LOT_CREATED", admin.get("email"), doc["id"],
                {"ref": doc["ref"], "from_template": tid, "legal_status": legal["status"], "procedure": procedure})
    return doc
