"""Préférences vendeur : canaux de notifications par type d'événement + récap périodique personnalisé."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id

logger = logging.getLogger(__name__)

prefs_router = APIRouter(prefix="/api/prefs", tags=["prefs"])

db = None

EVENT_TYPES = ["referral_bonus", "referral_welcome", "closure_reminder", "report_available"]
CHANNEL_VALUES = ["both", "email", "inapp", "none"]
FREQUENCIES = ["weekly", "biweekly", "monthly"]


def set_prefs_database(database):
    global db
    db = database


async def channel_allowed(user_id: str, event: str, channel: str) -> bool:
    """channel ∈ {email, inapp}. Par défaut : les deux canaux actifs."""
    doc = await db.notification_prefs.find_one({"user_id": user_id}, {"_id": 0, "prefs": 1})
    value = ((doc or {}).get("prefs") or {}).get(event, "both")
    return value == "both" or value == channel


@prefs_router.get("/notifications")
async def get_notification_prefs(user_id: str = Depends(get_current_user_id)):
    doc = await db.notification_prefs.find_one({"user_id": user_id}, {"_id": 0, "prefs": 1})
    prefs = {e: "both" for e in EVENT_TYPES}
    prefs.update((doc or {}).get("prefs") or {})
    return {"prefs": prefs, "events": EVENT_TYPES}


class NotifPrefsBody(BaseModel):
    prefs: dict


@prefs_router.put("/notifications")
async def set_notification_prefs(body: NotifPrefsBody, user_id: str = Depends(get_current_user_id)):
    clean = {}
    for event, value in body.prefs.items():
        if event not in EVENT_TYPES or value not in CHANNEL_VALUES:
            raise HTTPException(status_code=400, detail=f"Préférence invalide : {event}={value}")
        clean[event] = value
    await db.notification_prefs.update_one(
        {"user_id": user_id},
        {"$set": {"prefs": clean, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True}


@prefs_router.get("/recap")
async def get_recap_settings(user_id: str = Depends(get_current_user_id)):
    doc = await db.recap_settings.find_one({"user_id": user_id}, {"_id": 0})
    return {"enabled": (doc or {}).get("enabled", True), "day": (doc or {}).get("day", 0),
            "frequency": (doc or {}).get("frequency", "weekly")}


class RecapBody(BaseModel):
    enabled: bool
    day: int
    frequency: str


@prefs_router.put("/recap")
async def set_recap_settings(body: RecapBody, user_id: str = Depends(get_current_user_id)):
    if body.day < 0 or body.day > 6 or body.frequency not in FREQUENCIES:
        raise HTTPException(status_code=400, detail="Jour (0-6) ou fréquence invalide")
    await db.recap_settings.update_one(
        {"user_id": user_id},
        {"$set": {**body.dict(), "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True}
