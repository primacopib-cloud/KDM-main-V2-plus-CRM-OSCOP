"""Journal d'audit consultable (territoires, campagnes, consultations) — lecture seule admin."""
from typing import Optional

from fastapi import APIRouter, Depends

from lolodrive_helpers import require_admin

audit_router = APIRouter(prefix="/api/admin/audit", tags=["audit"])

db = None


def set_audit_database(database):
    global db
    db = database


@audit_router.get("")
async def list_audit(event_type: Optional[str] = None, q: Optional[str] = None,
                     limit: int = 100, admin: dict = Depends(require_admin)):
    query = {}
    if event_type:
        query["event_type"] = event_type
    if q:
        query["$or"] = [
            {"actor": {"$regex": q, "$options": "i"}},
            {"event_type": {"$regex": q, "$options": "i"}},
            {"consultation_id": {"$regex": q, "$options": "i"}},
        ]
    items = await db.audit_journal.find(query, {"_id": 0, "sha256_prev": 0}) \
        .sort("seq", -1).limit(min(limit, 500)).to_list(500)
    types = await db.audit_journal.distinct("event_type")
    return {"items": items, "event_types": sorted(types)}


@audit_router.get("/verify")
async def verify_audit(admin: dict = Depends(require_admin)):
    from consultation_audit import verify_chain
    return await verify_chain()
