"""Shopping Lists — Models & shared helpers (split from routes_shopping_lists.py)."""
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_shopping_lists_common_database(database):
    global db
    db = database

# ============== MODELS ==============

class ListFrequency(str, Enum):
    """Frequency/category for shopping lists"""
    WEEKLY = "weekly"           # Hebdomadaire
    BIWEEKLY = "biweekly"       # Bi-mensuel
    MONTHLY = "monthly"         # Mensuel
    QUARTERLY = "quarterly"     # Trimestriel
    ONE_TIME = "one_time"       # Ponctuel
    CUSTOM = "custom"           # Personnalisé


class ShoppingListItem(BaseModel):
    """A product item in a shopping list"""
    product_id: str
    quantity: int = Field(ge=1, default=1)
    notes: Optional[str] = None
    # Enriched fields (filled when fetching)
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    price_ht_cents: Optional[int] = None


class ShoppingListCreate(BaseModel):
    """Create a new shopping list"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    frequency: ListFrequency = ListFrequency.CUSTOM
    color: Optional[str] = "#D9B35A"
    icon: Optional[str] = "ShoppingCart"
    items: List[ShoppingListItem] = []


class ShoppingListUpdate(BaseModel):
    """Update an existing shopping list"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    frequency: Optional[ListFrequency] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ShoppingListResponse(BaseModel):
    """Full shopping list response"""
    id: str
    name: str
    description: Optional[str] = None
    frequency: str
    color: str
    icon: str
    items: List[ShoppingListItem]
    items_count: int
    total_ht_cents: Optional[int] = None
    created_at: str
    updated_at: str
    last_used_at: Optional[str] = None
    use_count: int = 0


class ShoppingListSummary(BaseModel):
    """Summary for list view"""
    id: str
    name: str
    description: Optional[str] = None
    frequency: str
    color: str
    icon: str
    items_count: int
    total_ht_cents: Optional[int] = None
    last_used_at: Optional[str] = None
    use_count: int = 0


class AddItemRequest(BaseModel):
    """Add item to list"""
    product_id: str
    quantity: int = Field(ge=1, default=1)
    notes: Optional[str] = None


class UpdateItemRequest(BaseModel):
    """Update item in list"""
    quantity: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


# ============== HELPER: Auth ==============

async def get_current_user_from_token(authorization: str = None):
    """Extract user from token"""
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


async def enrich_items_with_products(items: List[dict]) -> List[ShoppingListItem]:
    """Enrich shopping list items with product details"""
    if not items:
        return []
    
    product_ids = [item.get("product_id") for item in items]
    products_cursor = db.products.find({"id": {"$in": product_ids}})
    products = await products_cursor.to_list(100)
    products_map = {p["id"]: p for p in products}
    
    enriched = []
    for item in items:
        product = products_map.get(item.get("product_id"))
        enriched.append(ShoppingListItem(
            product_id=item.get("product_id"),
            quantity=item.get("quantity", 1),
            notes=item.get("notes"),
            product_name=product.get("name") if product else None,
            product_sku=product.get("sku") if product else None,
            product_image=product.get("image_url") if product else None,
            price_ht_cents=product.get("price_ht_cents") if product else None
        ))
    
    return enriched


def calculate_total(items: List[ShoppingListItem]) -> int:
    """Calculate total HT in cents"""
    total = 0
    for item in items:
        if item.price_ht_cents:
            total += item.price_ht_cents * item.quantity
    return total


