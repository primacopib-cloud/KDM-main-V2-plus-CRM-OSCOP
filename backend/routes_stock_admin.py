"""Routes admin stock & prix par zone — déclenchent les alertes favoris."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from admin_guard import require_admin
from auth import get_current_user_id
from favorites_alerts import alert_favorites

logger = logging.getLogger(__name__)

stock_admin_router = APIRouter(prefix="/api/catalog/admin", tags=["Stock Admin"])

db = None


def set_stock_admin_database(database) -> None:
    global db
    db = database


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class StockUpdateRequest(BaseModel):
    zone_code: str
    quantity_available: int = Field(ge=0)


class PriceUpdateRequest(BaseModel):
    zone_code: str
    price_ht_cents: int = Field(gt=0)


def _now():
    return datetime.now(timezone.utc)


@stock_admin_router.put("/stock/{product_id}")
async def update_zone_stock(product_id: str, body: StockUpdateRequest, _: dict = Depends(_admin)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    existing = await db.zone_stocks.find_one({"product_id": product_id, "zone_code": body.zone_code})
    old_available = 0
    if existing:
        old_available = existing.get("quantity_available", 0) - existing.get("quantity_reserved", 0)

    await db.zone_stocks.update_one(
        {"product_id": product_id, "zone_code": body.zone_code},
        {
            "$set": {"quantity_available": body.quantity_available, "updated_at": _now(),
                     "last_restock_at": _now() if body.quantity_available > 0 else None},
            "$setOnInsert": {"id": f"{product_id}-{body.zone_code}", "quantity_reserved": 0, "reorder_point": 10},
        },
        upsert=True,
    )

    restocked = old_available <= 0 and body.quantity_available > 0
    if restocked:
        asyncio.ensure_future(alert_favorites(product_id, body.zone_code, "restock"))

    return {
        "product_id": product_id,
        "zone_code": body.zone_code,
        "quantity_available": body.quantity_available,
        "restock_alert_triggered": restocked,
    }


@stock_admin_router.put("/price/{product_id}")
async def update_zone_price(product_id: str, body: PriceUpdateRequest, _: dict = Depends(_admin)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    existing = await db.zone_prices.find_one({"product_id": product_id, "zone_code": body.zone_code})
    old_price = existing.get("price_ht_cents") if existing else None

    await db.zone_prices.update_one(
        {"product_id": product_id, "zone_code": body.zone_code},
        {
            "$set": {"price_ht_cents": body.price_ht_cents, "updated_at": _now(), "is_active": True},
            "$setOnInsert": {"id": f"{product_id}-{body.zone_code}-price", "price_type": "STANDARD",
                             "original_price_ht_cents": old_price or body.price_ht_cents},
        },
        upsert=True,
    )

    promo = old_price is not None and body.price_ht_cents < old_price
    if promo:
        asyncio.ensure_future(alert_favorites(
            product_id, body.zone_code, "promo",
            {"new_price_cents": body.price_ht_cents, "old_price_cents": old_price},
        ))

    return {
        "product_id": product_id,
        "zone_code": body.zone_code,
        "price_ht_cents": body.price_ht_cents,
        "promo_alert_triggered": promo,
    }
