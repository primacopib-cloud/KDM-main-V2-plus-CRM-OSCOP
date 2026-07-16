"""Core notifications routes (split from server.py)."""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from models import NotificationResponse, NotificationsListResponse
from db import get_database
from core_deps import get_current_user

logger = logging.getLogger(__name__)

notifications_core_router = APIRouter(prefix="/api")


@notifications_core_router.get("/notifications", response_model=NotificationsListResponse)
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    unread_only: bool = False
):
    """Get notifications for current user (admin only or targeted)."""
    db = get_database()
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)

    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}

    if unread_only:
        query["read_by"] = {"$ne": user_id}

    notifications = await db.notifications.find(query).sort("created_at", -1).limit(limit).to_list(limit)

    unread_query = query.copy()
    unread_query["read_by"] = {"$ne": user_id}
    unread_count = await db.notifications.count_documents(unread_query)

    return NotificationsListResponse(
        notifications=[
            NotificationResponse(
                id=n["id"],
                type=n["type"],
                title=n["title"],
                message=n["message"],
                data=n.get("data", {}),
                is_read=user_id in n.get("read_by", []),
                created_at=n["created_at"]
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=len(notifications)
    )


@notifications_core_router.post("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    db = get_database()
    user_id = current_user["id"]

    result = await db.notifications.update_one(
        {"id": notification_id},
        {"$addToSet": {"read_by": user_id}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification non trouvée")

    return {"message": "Notification marquée comme lue"}


@notifications_core_router.post("/notifications/read-all", response_model=dict)
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read for current user."""
    db = get_database()
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)

    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}

    await db.notifications.update_many(query, {"$addToSet": {"read_by": user_id}})

    return {"message": "Toutes les notifications marquées comme lues"}


@notifications_core_router.get("/notifications/poll", response_model=dict)
async def poll_notifications(
    current_user: dict = Depends(get_current_user),
    since: str = None  # ISO timestamp
):
    """Poll for new notifications (for 30s polling)."""
    db = get_database()
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)

    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query["created_at"] = {"$gt": since_dt}
        except (ValueError, TypeError):
            pass

    new_notifications = await db.notifications.find(query).sort("created_at", -1).limit(10).to_list(10)

    unread_query = {
        "$or": [
            {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
            {"target_user_id": user_id}
        ] if is_admin else {"target_user_id": user_id},
        "read_by": {"$ne": user_id}
    }
    unread_count = await db.notifications.count_documents(unread_query)

    return {
        "has_new": len(new_notifications) > 0,
        "unread_count": unread_count,
        "new_notifications": [
            {
                "id": n["id"],
                "type": n["type"],
                "title": n["title"],
                "message": n["message"],
                "created_at": n["created_at"].isoformat()
            }
            for n in new_notifications
        ],
        "server_time": datetime.utcnow().isoformat()
    }
