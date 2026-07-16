"""Centre d'alertes favoris — préférences par produit + historique des alertes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from user_prefs_common import get_current_user_from_request

favorites_alerts_center_router = APIRouter(prefix="/user-prefs", tags=["Favorites Alerts Center"])

db = None


def set_favorites_alerts_center_database(database):
    global db
    db = database


class AlertsToggleRequest(BaseModel):
    enabled: bool


@favorites_alerts_center_router.get("/favorites/alerts-center")
async def get_alerts_center(request: Request):
    """Produits favoris avec préférence d'alerte + historique des alertes reçues."""
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    user_id = user.get("id")

    doc = await db.user_favorites.find_one({"user_id": user_id}, {"_id": 0})
    raw_favorites = (doc or {}).get("favorites", [])

    product_ids = [f.get("product_id") for f in raw_favorites]
    products = await db.products.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(200)
    products_map = {p["id"]: p for p in products}

    items = []
    for fav in raw_favorites:
        product = products_map.get(fav.get("product_id")) or {}
        items.append({
            "product_id": fav.get("product_id"),
            "product_name": product.get("name"),
            "product_sku": product.get("sku"),
            "product_image": product.get("image_url"),
            "added_at": fav.get("added_at"),
            "alerts_enabled": fav.get("alerts_enabled", True),
        })

    alerts = await db.notifications.find(
        {"target_user_id": user_id, "type": {"$regex": "^favorite_"}},
        {"_id": 0, "id": 1, "type": 1, "title": 1, "message": 1, "created_at": 1, "data": 1, "read_by": 1},
    ).sort("created_at", -1).limit(50).to_list(50)
    for a in alerts:
        a["is_read"] = user_id in (a.pop("read_by", None) or [])

    return {"products": items, "alerts": alerts, "total_products": len(items), "total_alerts": len(alerts)}


@favorites_alerts_center_router.put("/favorites/{product_id}/alerts")
async def toggle_product_alerts(product_id: str, body: AlertsToggleRequest, request: Request):
    """Active/coupe les alertes (restock + promo) pour un produit favori."""
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    user_id = user.get("id")

    result = await db.user_favorites.update_one(
        {"user_id": user_id, "favorites.product_id": product_id},
        {"$set": {"favorites.$.alerts_enabled": body.enabled}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé dans vos favoris")

    return {"product_id": product_id, "alerts_enabled": body.enabled}
