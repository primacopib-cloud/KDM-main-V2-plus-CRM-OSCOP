"""Annonces & Communications + Promos flash avec compte à rebours — gérées par le Super Admin / Admin."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

announcements_router = APIRouter(prefix="/api", tags=["announcements"])

db = None


def set_announcements_database(database):
    global db
    db = database


# ---------- Annonces ----------

class AnnouncementBody(BaseModel):
    title: str
    body: str
    priority: str = "normale"  # normale | urgente
    audiences: List[str] = ["all"]  # all | vendor | buyer | cooper
    active: bool = True


@announcements_router.get("/announcements")
async def public_announcements(space: str = "all"):
    q = {"active": True}
    items = await db.announcements.find(q, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    out = [a for a in items if "all" in (a.get("audiences") or ["all"]) or space in (a.get("audiences") or [])]
    return {"items": out[:10]}


@announcements_router.post("/announcements/{aid}/view")
async def announcement_view(aid: str):
    await db.announcements.update_one({"id": aid}, {"$inc": {"views": 1}})
    return {"ok": True}


@announcements_router.get("/admin/announcements")
async def admin_announcements(admin: dict = Depends(require_admin)):
    items = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@announcements_router.post("/admin/announcements")
async def create_announcement(body: AnnouncementBody, admin: dict = Depends(require_admin)):
    doc = {**body.dict(), "id": str(uuid.uuid4()), "views": 0,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.announcements.insert_one({**doc})
    return doc


@announcements_router.put("/admin/announcements/{aid}")
async def update_announcement(aid: str, body: dict, admin: dict = Depends(require_admin)):
    allowed = {k: v for k, v in body.items() if k in ("title", "body", "priority", "audiences", "active")}
    r = await db.announcements.update_one({"id": aid}, {"$set": allowed})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    return {"ok": True}


@announcements_router.delete("/admin/announcements/{aid}")
async def delete_announcement(aid: str, admin: dict = Depends(require_admin)):
    await db.announcements.delete_one({"id": aid})
    return {"deleted": True}


# ---------- Promos flash (compte à rebours) ----------

PLACEMENTS = ["landing", "kdmarche", "member_spaces"]


class FlashPromoBody(BaseModel):
    title: str
    description: str = ""
    discount_pct: int = 0
    starts_at: str
    ends_at: str
    placements: List[str] = ["landing", "kdmarche", "member_spaces"]
    cta_url: Optional[str] = None
    active: bool = True


@announcements_router.get("/public/flash-promos")
async def public_flash_promos(placement: str = "landing"):
    now = datetime.now(timezone.utc).isoformat()
    items = await db.flash_promos.find(
        {"active": True, "starts_at": {"$lte": now}, "ends_at": {"$gte": now}},
        {"_id": 0}).sort("ends_at", 1).limit(5).to_list(5)
    return {"items": [p for p in items if placement in (p.get("placements") or PLACEMENTS)]}


@announcements_router.get("/admin/flash-promos")
async def admin_flash_promos(admin: dict = Depends(require_admin)):
    items = await db.flash_promos.find({}, {"_id": 0}).sort("ends_at", -1).limit(100).to_list(100)
    return {"items": items, "placements": PLACEMENTS}


@announcements_router.post("/admin/flash-promos")
async def create_flash_promo(body: FlashPromoBody, admin: dict = Depends(require_admin)):
    if body.ends_at <= body.starts_at:
        raise HTTPException(status_code=400, detail="La date de fin doit être après le début")
    doc = {**body.dict(), "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.flash_promos.insert_one({**doc})
    return doc


@announcements_router.put("/admin/flash-promos/{pid}")
async def update_flash_promo(pid: str, body: dict, admin: dict = Depends(require_admin)):
    allowed = {k: v for k, v in body.items()
               if k in ("title", "description", "discount_pct", "starts_at", "ends_at", "placements", "cta_url", "active")}
    r = await db.flash_promos.update_one({"id": pid}, {"$set": allowed})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Promo introuvable")
    return {"ok": True}


@announcements_router.delete("/admin/flash-promos/{pid}")
async def delete_flash_promo(pid: str, admin: dict = Depends(require_admin)):
    await db.flash_promos.delete_one({"id": pid})
    return {"deleted": True}
