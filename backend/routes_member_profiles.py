"""Profils d'adhésion & espaces — gestion dynamique par le Super Admin."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

member_profiles_router = APIRouter(prefix="/api", tags=["member-profiles"])

db = None


def set_member_profiles_database(database):
    global db
    db = database


DEFAULT_PROFILES = [
    {
        "slug": "vendor",
        "titles": {"fr": "Vendeur Pro", "en": "Pro Seller", "es": "Vendedor Pro"},
        "descriptions": {
            "fr": "Je propose mes produits à la centrale et développe mes ventes B2B.",
            "en": "I offer my products to the purchasing hub and grow my B2B sales.",
            "es": "Ofrezco mis productos a la central y desarrollo mis ventas B2B.",
        },
        "space_route": "/espace-vendeur", "convention_template": "v1_5_vendor",
        "creates_vendor_record": True, "active": True, "sort_order": 1, "system": True,
    },
    {
        "slug": "buyer",
        "titles": {"fr": "Acheteur Pro", "en": "Pro Buyer", "es": "Comprador Pro"},
        "descriptions": {
            "fr": "J'achète aux prix mutualisés et j'accède à la centrale B2B.",
            "en": "I buy at pooled prices and access the B2B purchasing hub.",
            "es": "Compro a precios mutualizados y accedo a la central B2B.",
        },
        "space_route": "/espace-acheteur", "convention_template": "v2_0_buyer",
        "creates_vendor_record": False, "active": True, "sort_order": 2, "system": True,
    },
]

CONVENTION_TEMPLATES = ["v1_5_vendor", "v2_0_buyer"]


async def seed_member_profiles(database) -> int:
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for p in DEFAULT_PROFILES:
        if not await database.member_profiles.find_one({"slug": p["slug"]}):
            await database.member_profiles.insert_one({**p, "id": str(uuid.uuid4()), "created_at": now, "updated_at": now})
            inserted += 1
    return inserted


async def get_profile(slug: str) -> dict | None:
    return await db.member_profiles.find_one({"slug": slug}, {"_id": 0})


class ProfileBody(BaseModel):
    slug: Optional[str] = None
    titles: dict
    descriptions: dict = {}
    space_route: str = "/espace-acheteur"
    convention_template: str = "v2_0_buyer"
    creates_vendor_record: bool = False
    active: bool = True
    sort_order: int = 10


class ProfileUpdateBody(BaseModel):
    titles: Optional[dict] = None
    descriptions: Optional[dict] = None
    space_route: Optional[str] = None
    convention_template: Optional[str] = None
    creates_vendor_record: Optional[bool] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


def _slugify(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return "".join(c if c.isalnum() else "-" for c in t).strip("-")[:40]


@member_profiles_router.get("/public/member-profiles")
async def public_profiles():
    items = await db.member_profiles.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    return {"profiles": items}


@member_profiles_router.get("/admin/member-profiles")
async def admin_list_profiles(admin: dict = Depends(require_admin)):
    items = await db.member_profiles.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    counts = {}
    async for d in db.vendor_onboarding.aggregate([{"$group": {"_id": "$member_type", "n": {"$sum": 1}}}]):
        counts[d["_id"]] = d["n"]
    for it in items:
        it["adhesions_count"] = counts.get(it["slug"], 0)
    return {"profiles": items, "convention_templates": CONVENTION_TEMPLATES}


@member_profiles_router.post("/admin/member-profiles")
async def admin_create_profile(body: ProfileBody, admin: dict = Depends(require_admin)):
    if not body.titles.get("fr"):
        raise HTTPException(status_code=400, detail="Le titre FR est requis")
    slug = body.slug or _slugify(body.titles["fr"])
    if await db.member_profiles.find_one({"slug": slug}):
        raise HTTPException(status_code=409, detail=f"Le profil « {slug} » existe déjà")
    if body.convention_template not in CONVENTION_TEMPLATES:
        raise HTTPException(status_code=400, detail="Modèle de convention invalide")
    now = datetime.now(timezone.utc).isoformat()
    doc = {**body.dict(), "slug": slug, "id": str(uuid.uuid4()), "system": False,
           "created_at": now, "updated_at": now}
    await db.member_profiles.insert_one(doc)
    doc.pop("_id", None)
    return doc


@member_profiles_router.put("/admin/member-profiles/{slug}")
async def admin_update_profile(slug: str, body: ProfileUpdateBody, admin: dict = Depends(require_admin)):
    profile = await db.member_profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "convention_template" in updates and updates["convention_template"] not in CONVENTION_TEMPLATES:
        raise HTTPException(status_code=400, detail="Modèle de convention invalide")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.member_profiles.update_one({"slug": slug}, {"$set": updates})
    return {**profile, **updates}


@member_profiles_router.delete("/admin/member-profiles/{slug}")
async def admin_delete_profile(slug: str, admin: dict = Depends(require_admin)):
    profile = await db.member_profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    if profile.get("system"):
        raise HTTPException(status_code=400, detail="Profil système : désactivez-le plutôt que de le supprimer")
    used = await db.vendor_onboarding.count_documents({"member_type": slug})
    if used:
        raise HTTPException(status_code=400, detail=f"{used} adhésion(s) utilisent ce profil : désactivez-le plutôt")
    await db.member_profiles.delete_one({"slug": slug})
    return {"deleted": True}
