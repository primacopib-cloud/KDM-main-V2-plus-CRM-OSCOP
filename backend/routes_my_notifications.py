"""Notifications personnelles du membre : liste, lu/non-lu — /api/notifications/mine."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from auth import get_current_user_id

my_notifications_router = APIRouter(prefix="/api/notifications", tags=["Mes notifications"])
db = None


def set_my_notifications_database(database):
    global db
    db = database


def _ser(n: dict) -> dict:
    if isinstance(n.get("created_at"), datetime):
        n["created_at"] = n["created_at"].isoformat()
    return n


@my_notifications_router.get("/mine")
async def my_notifications(user_id: str = Depends(get_current_user_id), limit: int = 100):
    items = [_ser(n) async for n in db.notifications.find(
        {"target_user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(min(limit, 100))]
    unread = await db.notifications.count_documents({"target_user_id": user_id, "is_read": False})
    return {"items": items, "unread_count": unread}


@my_notifications_router.put("/mine/{notification_id}/read")
async def mark_mine_read(notification_id: str, user_id: str = Depends(get_current_user_id)):
    await db.notifications.update_one(
        {"id": notification_id, "target_user_id": user_id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True}


@my_notifications_router.put("/mine-read-all")
async def mark_all_mine_read(user_id: str = Depends(get_current_user_id)):
    r = await db.notifications.update_many(
        {"target_user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "count": r.modified_count}
