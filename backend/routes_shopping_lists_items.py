"""Shopping Lists — Items, actions & frequency endpoints (split from routes_shopping_lists.py)."""
from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from shopping_lists_common import (
    ListFrequency, ShoppingListItem, ShoppingListResponse, AddItemRequest, UpdateItemRequest,
    get_current_user_from_token, enrich_items_with_products, calculate_total,
)

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_shopping_lists_items_database(database):
    global db
    db = database

shopping_lists_items_router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])

# ============== ITEMS MANAGEMENT ==============

@shopping_lists_items_router.post("/{list_id}/items", response_model=ShoppingListResponse)
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


@shopping_lists_items_router.patch("/{list_id}/items/{product_id}", response_model=ShoppingListResponse)
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


@shopping_lists_items_router.delete("/{list_id}/items/{product_id}")
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

@shopping_lists_items_router.post("/{list_id}/use")
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


@shopping_lists_items_router.post("/{list_id}/duplicate", response_model=ShoppingListResponse)
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

@shopping_lists_items_router.get("/options/frequencies")
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
