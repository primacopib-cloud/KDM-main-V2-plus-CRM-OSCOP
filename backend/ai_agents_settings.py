"""Agents IA (PROSPECT'IA / ENCHÈR'IA) — interrupteurs et réglages Super Admin."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

ai_agents_router = APIRouter(prefix="/api/admin/ai-agents", tags=["ai-agents"])

db = None

DEFAULTS = {"id": "default", "prospectia_enabled": False, "encheria_enabled": False, "ventia_enabled": False}


def set_ai_agents_database(database):
    global db
    db = database


async def get_agents_settings(database=None) -> dict:
    d = database if database is not None else db
    s = await d.ai_agents_settings.find_one({"id": "default"}, {"_id": 0})
    return {**DEFAULTS, **(s or {})}


class AgentsBody(BaseModel):
    prospectia_enabled: Optional[bool] = None
    encheria_enabled: Optional[bool] = None
    ventia_enabled: Optional[bool] = None


@ai_agents_router.get("")
async def read_settings(admin: dict = Depends(require_admin)):
    return await get_agents_settings()


@ai_agents_router.put("")
async def update_settings(body: AgentsBody, admin: dict = Depends(require_admin)):
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if upd:
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.ai_agents_settings.update_one({"id": "default"}, {"$set": upd}, upsert=True)
        from consultation_audit import audit
        await audit("AI_AGENT_TOGGLED", admin.get("email"), None, upd)
        logger.info("Agents IA mis à jour par %s : %s", admin.get("email"), upd)
    return await get_agents_settings()


@ai_agents_router.get("/encheria/reports")
async def encheria_reports(admin: dict = Depends(require_admin)):
    items = await db.encheria_reports.find({}, {"_id": 0}).sort("created_at", -1).to_list(30)
    return {"items": items}
