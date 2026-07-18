"""Suggestions de produits complémentaires pour le panier (souvent commandés ensemble)."""

from fastapi import APIRouter, Depends
import logging

from schema_catalog import ProductStatus, CartStatus
from routes_catalog import get_current_user_catalog, get_selected_zone

logger = logging.getLogger(__name__)

suggestions_router = APIRouter(prefix="/api/v2/catalog")

db = None


def set_suggestions_database(database):
    global db
    db = database


async def _product_payload(product: dict, zone_code: str, reason: str):
    zone_price = await db.zone_prices.find_one({
        "product_id": product["id"], "zone_code": zone_code, "is_active": True,
    })
    if not zone_price:
        return None
    return {
        "id": product["id"],
        "name": product["name"],
        "sku": product["sku"],
        "image_url": product.get("image_url"),
        "unit": product["unit"],
        "category_id": product.get("category_id"),
        "min_order_qty": product.get("min_order_qty", 1),
        "price_ht_cents": zone_price["price_ht_cents"],
        "reason": reason,
    }


@suggestions_router.get("/cart/suggestions")
async def get_cart_suggestions(
    limit: int = 4,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Produits complémentaires basés sur les co-commandes, complétés par la même catégorie."""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        return {"suggestions": []}

    zone_code = await get_selected_zone(current_user)
    if not zone_code:
        return {"suggestions": []}

    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    cart_items = (cart or {}).get("items", [])
    if not cart_items:
        return {"suggestions": []}

    cart_product_ids = {i["product_id"] for i in cart_items}
    limit = max(1, min(limit, 8))
    suggestions = []
    seen = set(cart_product_ids)

    # 1. Co-occurrence dans les commandes passées (toutes organisations)
    pipeline = [
        {"$match": {"items.product_id": {"$in": list(cart_product_ids)}}},
        {"$unwind": "$items"},
        {"$match": {"items.product_id": {"$nin": list(cart_product_ids)}}},
        {"$group": {"_id": "$items.product_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    async for row in db.orders.aggregate(pipeline):
        if len(suggestions) >= limit:
            break
        product = await db.products.find_one({
            "id": row["_id"], "status": ProductStatus.ACTIVE.value,
        })
        if not product or product["id"] in seen:
            continue
        payload = await _product_payload(product, zone_code, "CO_ORDERED")
        if payload:
            suggestions.append(payload)
            seen.add(product["id"])

    # 2. Complément : produits actifs des mêmes catégories que le panier
    if len(suggestions) < limit:
        cart_products = await db.products.find(
            {"id": {"$in": list(cart_product_ids)}}, {"category_id": 1}
        ).to_list(50)
        category_ids = list({p.get("category_id") for p in cart_products if p.get("category_id")})
        if category_ids:
            cursor = db.products.find({
                "category_id": {"$in": category_ids},
                "status": ProductStatus.ACTIVE.value,
                "id": {"$nin": list(seen)},
            }).limit(20)
            async for product in cursor:
                if len(suggestions) >= limit:
                    break
                payload = await _product_payload(product, zone_code, "SAME_CATEGORY")
                if payload:
                    suggestions.append(payload)
                    seen.add(product["id"])

    # 3. Dernier recours : produits actifs populaires de la zone
    if len(suggestions) < limit:
        cursor = db.products.find({
            "status": ProductStatus.ACTIVE.value,
            "id": {"$nin": list(seen)},
        }).limit(20)
        async for product in cursor:
            if len(suggestions) >= limit:
                break
            payload = await _product_payload(product, zone_code, "POPULAR")
            if payload:
                suggestions.append(payload)
                seen.add(product["id"])

    return {"suggestions": suggestions}
