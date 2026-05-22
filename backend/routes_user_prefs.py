"""
User Preferences API - Shortcuts and Settings
Manages user-specific preferences like navbar shortcuts
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from bson import ObjectId

# Import from main server
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Database connection
client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_user_prefs_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database


user_prefs_router = APIRouter(prefix="/user-prefs", tags=["User Preferences"])


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


# ============== SHORTCUTS API ==============

from fastapi import Header, Request

@user_prefs_router.get("/shortcuts", response_model=ShortcutsResponse)
async def get_shortcuts(request: Request):
    """
    GET /api/user-prefs/shortcuts
    Get user's pinned shortcuts
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
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


# ============== FAVORITES API ==============

class FavoriteItem(BaseModel):
    """A favorite product item"""
    product_id: str
    added_at: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    product_price_ht: Optional[int] = None  # cents


class FavoritesResponse(BaseModel):
    """Response with user's favorites"""
    favorites: List[FavoriteItem]
    total: int


class FavoriteToggleResponse(BaseModel):
    """Response for add/remove favorite"""
    product_id: str
    is_favorite: bool
    message: str


@user_prefs_router.get("/favorites", response_model=FavoritesResponse)
async def get_favorites(request: Request, include_details: bool = True):
    """
    GET /api/user-prefs/favorites
    Get user's favorite products
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Get favorites from collection
    doc = await db.user_favorites.find_one({"user_id": user_id})
    
    favorites = []
    if doc and "favorites" in doc:
        raw_favorites = doc["favorites"]
        
        if include_details:
            # Enrich with product details
            product_ids = [f.get("product_id") for f in raw_favorites]
            products_cursor = db.products.find({"id": {"$in": product_ids}})
            products = await products_cursor.to_list(100)
            products_map = {p["id"]: p for p in products}
            
            for fav in raw_favorites:
                product = products_map.get(fav.get("product_id"))
                if product:
                    favorites.append(FavoriteItem(
                        product_id=fav.get("product_id"),
                        added_at=fav.get("added_at", datetime.now(timezone.utc).isoformat()),
                        product_name=product.get("name"),
                        product_sku=product.get("sku"),
                        product_image=product.get("image_url"),
                        product_price_ht=product.get("price_ht_cents")
                    ))
                else:
                    # Product might have been deleted
                    favorites.append(FavoriteItem(
                        product_id=fav.get("product_id"),
                        added_at=fav.get("added_at", datetime.now(timezone.utc).isoformat())
                    ))
        else:
            favorites = [FavoriteItem(
                product_id=f.get("product_id"),
                added_at=f.get("added_at", datetime.now(timezone.utc).isoformat())
            ) for f in raw_favorites]
    
    return FavoritesResponse(favorites=favorites, total=len(favorites))


@user_prefs_router.get("/favorites/ids")
async def get_favorite_ids(request: Request):
    """
    GET /api/user-prefs/favorites/ids
    Get just the list of favorite product IDs (lightweight)
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    doc = await db.user_favorites.find_one({"user_id": user_id})
    
    ids = []
    if doc and "favorites" in doc:
        ids = [f.get("product_id") for f in doc["favorites"]]
    
    return {"product_ids": ids, "count": len(ids)}


@user_prefs_router.post("/favorites/{product_id}", response_model=FavoriteToggleResponse)
async def add_favorite(product_id: str, request: Request):
    """
    POST /api/user-prefs/favorites/{product_id}
    Add a product to favorites
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Verify product exists
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Check if already in favorites
    doc = await db.user_favorites.find_one({"user_id": user_id})
    if doc:
        existing_ids = [f.get("product_id") for f in doc.get("favorites", [])]
        if product_id in existing_ids:
            return FavoriteToggleResponse(
                product_id=product_id,
                is_favorite=True,
                message="Produit déjà dans les favoris"
            )
    
    # Add to favorites
    new_favorite = {
        "product_id": product_id,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.user_favorites.update_one(
        {"user_id": user_id},
        {
            "$push": {"favorites": new_favorite},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return FavoriteToggleResponse(
        product_id=product_id,
        is_favorite=True,
        message="Produit ajouté aux favoris"
    )


@user_prefs_router.delete("/favorites/{product_id}", response_model=FavoriteToggleResponse)
async def remove_favorite(product_id: str, request: Request):
    """
    DELETE /api/user-prefs/favorites/{product_id}
    Remove a product from favorites
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Check if exists in favorites
    doc = await db.user_favorites.find_one({"user_id": user_id})
    if not doc or "favorites" not in doc:
        return FavoriteToggleResponse(
            product_id=product_id,
            is_favorite=False,
            message="Produit non présent dans les favoris"
        )
    
    existing_ids = [f.get("product_id") for f in doc.get("favorites", [])]
    if product_id not in existing_ids:
        return FavoriteToggleResponse(
            product_id=product_id,
            is_favorite=False,
            message="Produit non présent dans les favoris"
        )
    
    # Remove from favorites
    await db.user_favorites.update_one(
        {"user_id": user_id},
        {
            "$pull": {"favorites": {"product_id": product_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return FavoriteToggleResponse(
        product_id=product_id,
        is_favorite=False,
        message="Produit retiré des favoris"
    )


@user_prefs_router.post("/favorites/{product_id}/toggle", response_model=FavoriteToggleResponse)
async def toggle_favorite(product_id: str, request: Request):
    """
    POST /api/user-prefs/favorites/{product_id}/toggle
    Toggle favorite status (add if not present, remove if present)
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Check current status
    doc = await db.user_favorites.find_one({"user_id": user_id})
    existing_ids = []
    if doc and "favorites" in doc:
        existing_ids = [f.get("product_id") for f in doc.get("favorites", [])]
    
    if product_id in existing_ids:
        # Remove
        await db.user_favorites.update_one(
            {"user_id": user_id},
            {
                "$pull": {"favorites": {"product_id": product_id}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        return FavoriteToggleResponse(
            product_id=product_id,
            is_favorite=False,
            message="Produit retiré des favoris"
        )
    else:
        # Verify product exists
        product = await db.products.find_one({"id": product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        # Add
        new_favorite = {
            "product_id": product_id,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.user_favorites.update_one(
            {"user_id": user_id},
            {
                "$push": {"favorites": new_favorite},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
        return FavoriteToggleResponse(
            product_id=product_id,
            is_favorite=True,
            message="Produit ajouté aux favoris"
        )


@user_prefs_router.delete("/favorites")
async def clear_all_favorites(request: Request):
    """
    DELETE /api/user-prefs/favorites
    Clear all favorites
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    result = await db.user_favorites.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "favorites": [],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Tous les favoris ont été supprimés", "cleared": result.modified_count > 0}

