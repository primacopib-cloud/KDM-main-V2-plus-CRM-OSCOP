"""User Preferences — Favorites API (split from routes_user_prefs.py)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from user_prefs_common import get_current_user_from_token

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_user_prefs_favorites_database(database):
    global db
    db = database

user_prefs_favorites_router = APIRouter(prefix="/user-prefs", tags=["User Preferences"])

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


@user_prefs_favorites_router.get("/favorites", response_model=FavoritesResponse)
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


@user_prefs_favorites_router.get("/favorites/ids")
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


@user_prefs_favorites_router.post("/favorites/{product_id}", response_model=FavoriteToggleResponse)
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


@user_prefs_favorites_router.delete("/favorites/{product_id}", response_model=FavoriteToggleResponse)
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


@user_prefs_favorites_router.post("/favorites/{product_id}/toggle", response_model=FavoriteToggleResponse)
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


@user_prefs_favorites_router.delete("/favorites")
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

