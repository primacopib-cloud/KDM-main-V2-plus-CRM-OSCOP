"""PROSPECT'IA — Bibliothèque de scripts : sauvegarde, réutilisation et comparaison des performances."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
library_router = APIRouter(prefix="/api/admin/prospectia/library", tags=["prospectia-library"])
db = None


def set_library_database(database):
    global db
    db = database


class SaveScriptBody(BaseModel):
    title: str
    content: str
    content_type: str = "email"
    target: str = "vendor"
    lang: str = "fr"


@library_router.post("")
async def save_script(body: SaveScriptBody, admin: dict = Depends(require_admin)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Contenu vide")
    doc = {
        "id": str(uuid.uuid4()), "title": body.title.strip() or "Script sans titre",
        "content": body.content, "content_type": body.content_type,
        "target": body.target, "lang": body.lang,
        "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.prospectia_library.insert_one({**doc})
    from consultation_audit import audit
    await audit("PROSPECTIA_SCRIPT_SAVED", admin.get("email"), None, {"title": doc["title"], "type": doc["content_type"]})
    return doc


@library_router.get("")
async def list_scripts(admin: dict = Depends(require_admin)):
    items = await db.prospectia_library.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    stats = {}
    pipeline = [
        {"$match": {"library_id": {"$ne": None}}},
        {"$group": {"_id": "$library_id",
                    "campaigns": {"$sum": 1},
                    "sent": {"$sum": "$sent_count"},
                    "clicks": {"$sum": "$click_count"},
                    "conversions": {"$sum": "$conversions_count"}}},
    ]
    async for row in db.prospectia_campaigns.aggregate(pipeline):
        stats[row["_id"]] = row
    for it in items:
        s = stats.get(it["id"], {})
        it["campaigns_count"] = s.get("campaigns", 0)
        it["total_sent"] = s.get("sent", 0)
        it["total_clicks"] = s.get("clicks", 0)
        it["total_conversions"] = s.get("conversions", 0)
        it["click_rate"] = round(100 * it["total_clicks"] / it["total_sent"], 1) if it["total_sent"] else None
    items.sort(key=lambda x: (x["click_rate"] is not None, x["click_rate"] or 0), reverse=True)
    return {"items": items}


@library_router.delete("/{script_id}")
async def delete_script(script_id: str, admin: dict = Depends(require_admin)):
    res = await db.prospectia_library.delete_one({"id": script_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Script introuvable")
    return {"ok": True}
