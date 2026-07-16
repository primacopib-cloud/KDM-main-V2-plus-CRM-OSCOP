"""User Preferences — Models & auth helper (split from routes_user_prefs.py)."""
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_user_prefs_common_database(database):
    global db
    db = database

# ============== MODELS ==============

class ShortcutItem(BaseModel):
    """A single shortcut/pinned link"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str = Field(..., min_length=1, max_length=50)
    href: str = Field(..., min_length=1)
    icon: Optional[str] = None  # lucide icon name
    color: Optional[str] = None  # hex color
    order: int = 0


class ShortcutCreate(BaseModel):
    """Create a new shortcut"""
    label: str = Field(..., min_length=1, max_length=50)
    href: str = Field(..., min_length=1)
    icon: Optional[str] = "Star"
    color: Optional[str] = "#D9B35A"


class ShortcutUpdate(BaseModel):
    """Update an existing shortcut"""
    label: Optional[str] = Field(None, min_length=1, max_length=50)
    href: Optional[str] = Field(None, min_length=1)
    icon: Optional[str] = None
    color: Optional[str] = None
    order: Optional[int] = None


class ShortcutsResponse(BaseModel):
    """Response with user's shortcuts"""
    shortcuts: List[ShortcutItem]
    max_shortcuts: int = 6


class ReorderRequest(BaseModel):
    """Reorder shortcuts"""
    shortcut_ids: List[str]


# ============== HELPER: Get Current User ==============

async def get_current_user_from_token(authorization: str = None):
    """Extract user from token - simplified version"""
    if not authorization:
        return None
    
    try:
        from jose import jwt
        token = authorization.replace("Bearer ", "")
        secret = os.environ.get("JWT_SECRET_KEY", "kdmarche-oscop-b2b-ess-secret-key-2025")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            return user
    except Exception as e:
        print(f"Auth error: {e}")
    return None


