"""
Shopping Lists API
Allows buyers to create and manage reusable shopping lists for recurring orders
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Database connection
client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_shopping_lists_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database


shopping_lists_router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])


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


# ============== SHOPPING LISTS API ==============

@shopping_lists_router.get("", response_model=List[ShoppingListSummary])
async def get_shopping_lists(
    request: Request,
    frequency: Optional[ListFrequency] = None,
    sort_by: Literal["name", "created_at", "last_used_at", "use_count"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc"
):
    """
    GET /api/shopping-lists
    Get all shopping lists for the current user
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Build query
    query = {"user_id": user_id}
    if frequency:
        query["frequency"] = frequency.value
    
    # Sort direction
    sort_dir = 1 if sort_order == "asc" else -1
    
    # Fetch lists
    cursor = db.shopping_lists.find(query).sort(sort_by, sort_dir)
    lists = await cursor.to_list(100)
    
    # Build summaries
    summaries = []
    for lst in lists:
        items = lst.get("items", [])
        # NOTE: per-list total intentionally not computed in summary
        # (would require N price lookups). Front-end fetches detail when expanded.
        
        summaries.append(ShoppingListSummary(
            id=lst.get("id"),
            name=lst.get("name"),
            description=lst.get("description"),
            frequency=lst.get("frequency", "custom"),
            color=lst.get("color", "#D9B35A"),
            icon=lst.get("icon", "ShoppingCart"),
            items_count=len(items),
            total_ht_cents=lst.get("cached_total_ht"),
            last_used_at=lst.get("last_used_at"),
            use_count=lst.get("use_count", 0)
        ))
    
    return summaries


@shopping_lists_router.post("", response_model=ShoppingListResponse)
async def create_shopping_list(data: ShoppingListCreate, request: Request):
    """
    POST /api/shopping-lists
    Create a new shopping list
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    # Check for duplicate name
    existing = await db.shopping_lists.find_one({"user_id": user_id, "name": data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Une liste avec ce nom existe déjà")
    
    # Validate products exist
    if data.items:
        product_ids = [item.product_id for item in data.items]
        products = await db.products.find({"id": {"$in": product_ids}}).to_list(100)
        found_ids = {p["id"] for p in products}
        missing = set(product_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Produits non trouvés: {', '.join(missing)}"
            )
    
    now = datetime.now(timezone.utc).isoformat()
    list_id = str(uuid.uuid4())
    
    new_list = {
        "id": list_id,
        "user_id": user_id,
        "name": data.name,
        "description": data.description,
        "frequency": data.frequency.value,
        "color": data.color or "#D9B35A",
        "icon": data.icon or "ShoppingCart",
        "items": [item.model_dump(exclude_unset=True) for item in data.items],
        "created_at": now,
        "updated_at": now,
        "last_used_at": None,
        "use_count": 0
    }
    
    await db.shopping_lists.insert_one(new_list)
    
    # Enrich items for response
    enriched_items = await enrich_items_with_products(new_list["items"])
    total = calculate_total(enriched_items)
    
    # Cache the total
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"cached_total_ht": total}}
    )
    
    return ShoppingListResponse(
        id=list_id,
        name=data.name,
        description=data.description,
        frequency=data.frequency.value,
        color=data.color or "#D9B35A",
        icon=data.icon or "ShoppingCart",
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=now,
        updated_at=now,
        last_used_at=None,
        use_count=0
    )


@shopping_lists_router.get("/{list_id}", response_model=ShoppingListResponse)
async def get_shopping_list(list_id: str, request: Request):
    """
    GET /api/shopping-lists/{list_id}
    Get a specific shopping list with full details
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    # Enrich items
    enriched_items = await enrich_items_with_products(lst.get("items", []))
    total = calculate_total(enriched_items)
    
    return ShoppingListResponse(
        id=lst.get("id"),
        name=lst.get("name"),
        description=lst.get("description"),
        frequency=lst.get("frequency", "custom"),
        color=lst.get("color", "#D9B35A"),
        icon=lst.get("icon", "ShoppingCart"),
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=lst.get("created_at"),
        updated_at=lst.get("updated_at"),
        last_used_at=lst.get("last_used_at"),
        use_count=lst.get("use_count", 0)
    )


@shopping_lists_router.patch("/{list_id}", response_model=ShoppingListResponse)
async def update_shopping_list(list_id: str, data: ShoppingListUpdate, request: Request):
    """
    PATCH /api/shopping-lists/{list_id}
    Update shopping list metadata
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    # Check for duplicate name if name is being changed
    if data.name and data.name != lst.get("name"):
        existing = await db.shopping_lists.find_one({"user_id": user_id, "name": data.name})
        if existing:
            raise HTTPException(status_code=400, detail="Une liste avec ce nom existe déjà")
    
    # Build update
    update_data = data.model_dump(exclude_unset=True)
    if "frequency" in update_data:
        update_data["frequency"] = update_data["frequency"].value if hasattr(update_data["frequency"], 'value') else update_data["frequency"]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": update_data}
    )
    
    # Fetch updated list
    updated = await db.shopping_lists.find_one({"id": list_id})
    enriched_items = await enrich_items_with_products(updated.get("items", []))
    total = calculate_total(enriched_items)
    
    return ShoppingListResponse(
        id=updated.get("id"),
        name=updated.get("name"),
        description=updated.get("description"),
        frequency=updated.get("frequency", "custom"),
        color=updated.get("color", "#D9B35A"),
        icon=updated.get("icon", "ShoppingCart"),
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=updated.get("created_at"),
        updated_at=updated.get("updated_at"),
        last_used_at=updated.get("last_used_at"),
        use_count=updated.get("use_count", 0)
    )


@shopping_lists_router.delete("/{list_id}")
async def delete_shopping_list(list_id: str, request: Request):
    """
    DELETE /api/shopping-lists/{list_id}
    Delete a shopping list
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    result = await db.shopping_lists.delete_one({"id": list_id, "user_id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    return {"message": "Liste supprimée", "id": list_id}


# ============== ITEMS MANAGEMENT ==============

@shopping_lists_router.post("/{list_id}/items", response_model=ShoppingListResponse)
async def add_item_to_list(list_id: str, item: AddItemRequest, request: Request):
    """
    POST /api/shopping-lists/{list_id}/items
    Add a product to the shopping list
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    # Verify product exists
    product = await db.products.find_one({"id": item.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    items = lst.get("items", [])
    
    # Check if product already in list
    existing_idx = None
    for i, existing_item in enumerate(items):
        if existing_item.get("product_id") == item.product_id:
            existing_idx = i
            break
    
    if existing_idx is not None:
        # Update quantity
        items[existing_idx]["quantity"] = items[existing_idx].get("quantity", 1) + item.quantity
        if item.notes:
            items[existing_idx]["notes"] = item.notes
    else:
        # Add new item
        items.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "notes": item.notes
        })
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update list
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"items": items, "updated_at": now}}
    )
    
    # Return updated list
    enriched_items = await enrich_items_with_products(items)
    total = calculate_total(enriched_items)
    
    # Cache total
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"cached_total_ht": total}}
    )
    
    return ShoppingListResponse(
        id=lst.get("id"),
        name=lst.get("name"),
        description=lst.get("description"),
        frequency=lst.get("frequency", "custom"),
        color=lst.get("color", "#D9B35A"),
        icon=lst.get("icon", "ShoppingCart"),
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=lst.get("created_at"),
        updated_at=now,
        last_used_at=lst.get("last_used_at"),
        use_count=lst.get("use_count", 0)
    )


@shopping_lists_router.patch("/{list_id}/items/{product_id}", response_model=ShoppingListResponse)
async def update_item_in_list(list_id: str, product_id: str, data: UpdateItemRequest, request: Request):
    """
    PATCH /api/shopping-lists/{list_id}/items/{product_id}
    Update item quantity or notes
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    items = lst.get("items", [])
    item_found = False
    
    for item in items:
        if item.get("product_id") == product_id:
            if data.quantity is not None:
                item["quantity"] = data.quantity
            if data.notes is not None:
                item["notes"] = data.notes
            item_found = True
            break
    
    if not item_found:
        raise HTTPException(status_code=404, detail="Produit non trouvé dans la liste")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"items": items, "updated_at": now}}
    )
    
    enriched_items = await enrich_items_with_products(items)
    total = calculate_total(enriched_items)
    
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"cached_total_ht": total}}
    )
    
    return ShoppingListResponse(
        id=lst.get("id"),
        name=lst.get("name"),
        description=lst.get("description"),
        frequency=lst.get("frequency", "custom"),
        color=lst.get("color", "#D9B35A"),
        icon=lst.get("icon", "ShoppingCart"),
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=lst.get("created_at"),
        updated_at=now,
        last_used_at=lst.get("last_used_at"),
        use_count=lst.get("use_count", 0)
    )


@shopping_lists_router.delete("/{list_id}/items/{product_id}")
async def remove_item_from_list(list_id: str, product_id: str, request: Request):
    """
    DELETE /api/shopping-lists/{list_id}/items/{product_id}
    Remove a product from the shopping list
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    items = lst.get("items", [])
    original_count = len(items)
    items = [item for item in items if item.get("product_id") != product_id]
    
    if len(items) == original_count:
        raise HTTPException(status_code=404, detail="Produit non trouvé dans la liste")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.shopping_lists.update_one(
        {"id": list_id},
        {"$set": {"items": items, "updated_at": now}}
    )
    
    return {"message": "Produit retiré de la liste", "product_id": product_id}


# ============== ACTIONS ==============

@shopping_lists_router.post("/{list_id}/use")
async def use_shopping_list(list_id: str, request: Request):
    """
    POST /api/shopping-lists/{list_id}/use
    Mark list as used (increment counter, update last_used_at)
    Returns the list items ready to be added to cart
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.shopping_lists.update_one(
        {"id": list_id},
        {
            "$set": {"last_used_at": now},
            "$inc": {"use_count": 1}
        }
    )
    
    # Return enriched items for adding to cart
    enriched_items = await enrich_items_with_products(lst.get("items", []))
    
    return {
        "message": "Liste utilisée",
        "list_id": list_id,
        "list_name": lst.get("name"),
        "items": [item.model_dump() for item in enriched_items],
        "items_count": len(enriched_items)
    }


@shopping_lists_router.post("/{list_id}/duplicate", response_model=ShoppingListResponse)
async def duplicate_shopping_list(list_id: str, request: Request, new_name: Optional[str] = None):
    """
    POST /api/shopping-lists/{list_id}/duplicate
    Create a copy of an existing shopping list
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    lst = await db.shopping_lists.find_one({"id": list_id, "user_id": user_id})
    if not lst:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    # Generate new name
    base_name = new_name or f"{lst.get('name')} (copie)"
    final_name = base_name
    counter = 1
    
    while await db.shopping_lists.find_one({"user_id": user_id, "name": final_name}):
        counter += 1
        final_name = f"{base_name} {counter}"
    
    now = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())
    
    new_list = {
        "id": new_id,
        "user_id": user_id,
        "name": final_name,
        "description": lst.get("description"),
        "frequency": lst.get("frequency", "custom"),
        "color": lst.get("color", "#D9B35A"),
        "icon": lst.get("icon", "ShoppingCart"),
        "items": lst.get("items", []).copy(),
        "created_at": now,
        "updated_at": now,
        "last_used_at": None,
        "use_count": 0,
        "cached_total_ht": lst.get("cached_total_ht")
    }
    
    await db.shopping_lists.insert_one(new_list)
    
    enriched_items = await enrich_items_with_products(new_list["items"])
    total = calculate_total(enriched_items)
    
    return ShoppingListResponse(
        id=new_id,
        name=final_name,
        description=lst.get("description"),
        frequency=lst.get("frequency", "custom"),
        color=lst.get("color", "#D9B35A"),
        icon=lst.get("icon", "ShoppingCart"),
        items=enriched_items,
        items_count=len(enriched_items),
        total_ht_cents=total,
        created_at=now,
        updated_at=now,
        last_used_at=None,
        use_count=0
    )


# ============== FREQUENCY OPTIONS ==============

@shopping_lists_router.get("/options/frequencies")
async def get_frequency_options():
    """
    GET /api/shopping-lists/options/frequencies
    Get available frequency options with labels
    """
    return {
        "frequencies": [
            {"value": "weekly", "label": "Hebdomadaire", "icon": "Calendar", "description": "Commande chaque semaine"},
            {"value": "biweekly", "label": "Bi-mensuel", "icon": "Calendar", "description": "Commande toutes les 2 semaines"},
            {"value": "monthly", "label": "Mensuel", "icon": "CalendarDays", "description": "Commande chaque mois"},
            {"value": "quarterly", "label": "Trimestriel", "icon": "CalendarRange", "description": "Commande chaque trimestre"},
            {"value": "one_time", "label": "Ponctuel", "icon": "CalendarCheck", "description": "Commande unique"},
            {"value": "custom", "label": "Personnalisé", "icon": "Settings", "description": "Fréquence personnalisée"},
        ]
    }
