"""Shared dependencies & helpers for core API routes (split from server.py)."""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import Depends, HTTPException, status

from auth import get_current_user_id
from db import get_database

logger = logging.getLogger(__name__)


async def get_user_by_email(email: str):
    """Get user by email from database."""
    db = get_database()
    user = await db.users.find_one({"email": email})
    return user


async def get_user_by_id(user_id: str):
    """Get user by ID from database."""
    db = get_database()
    user = await db.users.find_one({"id": user_id})
    return user


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Get the current user from database."""
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return user


async def check_admin(current_user: dict):
    """Check if user is admin."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    return current_user


async def create_notification(
    notification_type: str,
    title: str,
    message: str,
    target_roles: List[str] = None,
    target_user_id: str = None,
    data: dict = None
):
    """Helper to create a notification."""
    db = get_database()
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "target_roles": target_roles or ["oscop_super_admin", "oscop_compliance_admin"],
        "target_user_id": target_user_id,
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow()
    }
    await db.notifications.insert_one(notification)
    logger.info(f"Notification created: {notification_type} - {title}")
    return notification
