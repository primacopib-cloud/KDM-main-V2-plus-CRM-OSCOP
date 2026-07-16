"""
User Preferences API - Shortcuts and Settings
Manages user-specific preferences like navbar shortcuts

Découpé en modules : user_prefs_common, routes_user_prefs_favorites.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from user_prefs_common import (
    get_current_user_from_request,
    ShortcutItem, ShortcutCreate, ShortcutUpdate, ShortcutsResponse, ReorderRequest,
    get_current_user_from_token, set_user_prefs_common_database,
)
from routes_user_prefs_favorites import set_user_prefs_favorites_database

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_user_prefs_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database
    set_user_prefs_common_database(database)
    set_user_prefs_favorites_database(database)


user_prefs_router = APIRouter(prefix="/user-prefs", tags=["User Preferences"])

# ============== SHORTCUTS API ==============

from fastapi import Header, Request

@user_prefs_router.get("/shortcuts", response_model=ShortcutsResponse)
async def get_shortcuts(request: Request):
    """
    GET /api/user-prefs/shortcuts
    Get user's pinned shortcuts
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Get shortcuts from user_shortcuts collection
    doc = await db.user_shortcuts.find_one({"user_id": user_id})
    
    shortcuts = []
    if doc and "shortcuts" in doc:
        shortcuts = doc["shortcuts"]
    
    return ShortcutsResponse(
        shortcuts=[ShortcutItem(**s) for s in shortcuts],
        max_shortcuts=6
    )


@user_prefs_router.post("/shortcuts", response_model=ShortcutItem)
async def create_shortcut(shortcut: ShortcutCreate, request: Request):
    """
    POST /api/user-prefs/shortcuts
    Create a new pinned shortcut
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Get current shortcuts
    doc = await db.user_shortcuts.find_one({"user_id": user_id})
    current_shortcuts = doc.get("shortcuts", []) if doc else []
    
    # Check max shortcuts
    if len(current_shortcuts) >= 6:
        raise HTTPException(
            status_code=400, 
            detail="Nombre maximum de raccourcis atteint (6)"
        )
    
    # Check for duplicate href
    if any(s.get("href") == shortcut.href for s in current_shortcuts):
        raise HTTPException(
            status_code=400,
            detail="Ce raccourci existe déjà"
        )
    
    # Create new shortcut
    new_shortcut = ShortcutItem(
        label=shortcut.label,
        href=shortcut.href,
        icon=shortcut.icon or "Star",
        color=shortcut.color or "#D9B35A",
        order=len(current_shortcuts)
    )
    
    # Upsert into collection
    await db.user_shortcuts.update_one(
        {"user_id": user_id},
        {
            "$push": {"shortcuts": new_shortcut.model_dump()},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return new_shortcut


@user_prefs_router.patch("/shortcuts/{shortcut_id}", response_model=ShortcutItem)
async def update_shortcut(shortcut_id: str, update: ShortcutUpdate, request: Request):
    """
    PATCH /api/user-prefs/shortcuts/{shortcut_id}
    Update an existing shortcut
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Get current shortcuts
    doc = await db.user_shortcuts.find_one({"user_id": user_id})
    if not doc or "shortcuts" not in doc:
        raise HTTPException(status_code=404, detail="Raccourci non trouvé")
    
    shortcuts = doc["shortcuts"]
    shortcut_index = None
    
    for i, s in enumerate(shortcuts):
        if s.get("id") == shortcut_id:
            shortcut_index = i
            break
    
    if shortcut_index is None:
        raise HTTPException(status_code=404, detail="Raccourci non trouvé")
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        shortcuts[shortcut_index][key] = value
    
    # Save
    await db.user_shortcuts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "shortcuts": shortcuts,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return ShortcutItem(**shortcuts[shortcut_index])


@user_prefs_router.delete("/shortcuts/{shortcut_id}")
async def delete_shortcut(shortcut_id: str, request: Request):
    """
    DELETE /api/user-prefs/shortcuts/{shortcut_id}
    Remove a shortcut
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # First check if shortcut exists
    doc = await db.user_shortcuts.find_one({"user_id": user_id})
    if not doc or "shortcuts" not in doc:
        raise HTTPException(status_code=404, detail="Raccourci non trouvé")
    
    shortcut_exists = any(s.get("id") == shortcut_id for s in doc["shortcuts"])
    if not shortcut_exists:
        raise HTTPException(status_code=404, detail="Raccourci non trouvé")
    
    # Remove shortcut
    await db.user_shortcuts.update_one(
        {"user_id": user_id},
        {
            "$pull": {"shortcuts": {"id": shortcut_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Raccourci supprimé"}


@user_prefs_router.post("/shortcuts/reorder")
async def reorder_shortcuts(reorder_data: ReorderRequest, request: Request):
    """
    POST /api/user-prefs/shortcuts/reorder
    Reorder shortcuts by providing the new order of IDs
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Get current shortcuts
    doc = await db.user_shortcuts.find_one({"user_id": user_id})
    if not doc or "shortcuts" not in doc:
        raise HTTPException(status_code=404, detail="Aucun raccourci trouvé")
    
    shortcuts = doc["shortcuts"]
    shortcuts_map = {s["id"]: s for s in shortcuts}
    
    # Reorder
    reordered = []
    for i, sid in enumerate(reorder_data.shortcut_ids):
        if sid in shortcuts_map:
            shortcuts_map[sid]["order"] = i
            reordered.append(shortcuts_map[sid])
    
    # Save
    await db.user_shortcuts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "shortcuts": reordered,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Ordre mis à jour", "count": len(reordered)}


# ============== SUGGESTED SHORTCUTS ==============

@user_prefs_router.get("/shortcuts/suggestions")
async def get_shortcut_suggestions(request: Request):
    """
    GET /api/user-prefs/shortcuts/suggestions
    Get suggested shortcuts based on user's navigation history
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    # Predefined suggestions based on common pages
    suggestions = [
        {"label": "Catalogue", "href": "/catalogue", "icon": "ShoppingCart", "color": "#D9B35A"},
        {"label": "Commandes", "href": "/commandes", "icon": "Package", "color": "#57D19A"},
        {"label": "Wallet", "href": "/wallet", "icon": "Wallet", "color": "#3B82F6"},
        {"label": "Documents", "href": "/documents", "icon": "FileText", "color": "#8B5CF6"},
        {"label": "Mon Espace", "href": "/espace-acheteur", "icon": "LayoutDashboard", "color": "#EC4899"},
        {"label": "Documents légaux", "href": "/legal", "icon": "Scale", "color": "#F59E0B"},
    ]
    
    # Get user's existing shortcuts to filter out
    doc = await db.user_shortcuts.find_one({"user_id": user.get("id")})
    existing_hrefs = set()
    if doc and "shortcuts" in doc:
        existing_hrefs = {s.get("href") for s in doc["shortcuts"]}
    
    # Filter out existing shortcuts
    available = [s for s in suggestions if s["href"] not in existing_hrefs]
    
    return {"suggestions": available}


