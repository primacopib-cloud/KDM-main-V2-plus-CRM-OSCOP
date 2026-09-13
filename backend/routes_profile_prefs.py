"""Préférences de profil : langue mémorisée sur le compte (multi-appareils)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core_deps import get_current_user
from db import get_database

profile_prefs_router = APIRouter(prefix="/api/profile", tags=["profile"])

LANGS = ["fr", "en", "es", "gcf"]


class LanguageBody(BaseModel):
    language: str


class FirstNameBody(BaseModel):
    first_name: str


@profile_prefs_router.post("/first-name")
async def set_first_name(body: FirstNameBody, current_user: dict = Depends(get_current_user)):
    """Prénom d'affichage du membre (salutation personnalisée)."""
    name = " ".join(body.first_name.split())
    if not name or len(name) > 40:
        raise HTTPException(status_code=422, detail="Prénom requis (40 caractères max)")
    await get_database().users.update_one(
        {"id": current_user["id"]}, {"$set": {"first_name": name}})
    return {"ok": True, "first_name": name}


@profile_prefs_router.get("/language")
async def get_language(current_user: dict = Depends(get_current_user)):
    return {"language": current_user.get("preferred_language")}


@profile_prefs_router.post("/language")
async def set_language(body: LanguageBody, current_user: dict = Depends(get_current_user)):
    if body.language not in LANGS:
        raise HTTPException(status_code=422, detail="Langue non supportée")
    await get_database().users.update_one(
        {"id": current_user["id"]}, {"$set": {"preferred_language": body.language}})
    return {"ok": True, "language": body.language}
