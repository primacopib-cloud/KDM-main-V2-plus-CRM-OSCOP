"""
Shopping Lists API
Allows buyers to create and manage reusable shopping lists for recurring orders

Découpé en modules : shopping_lists_common, routes_shopping_lists_items.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from shopping_lists_common import (
    get_current_user_from_request,
    ListFrequency, ShoppingListItem, ShoppingListCreate, ShoppingListUpdate,
    ShoppingListResponse, ShoppingListSummary,
    get_current_user_from_token, enrich_items_with_products, calculate_total,
    set_shopping_lists_common_database,
)
from routes_shopping_lists_items import set_shopping_lists_items_database

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_shopping_lists_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database
    set_shopping_lists_common_database(database)
    set_shopping_lists_items_database(database)


shopping_lists_router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])

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
    user = await get_current_user_from_request(request)
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
    user = await get_current_user_from_request(request)
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
    user = await get_current_user_from_request(request)
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
    user = await get_current_user_from_request(request)
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
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    
    result = await db.shopping_lists.delete_one({"id": list_id, "user_id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Liste non trouvée")
    
    return {"message": "Liste supprimée", "id": list_id}


