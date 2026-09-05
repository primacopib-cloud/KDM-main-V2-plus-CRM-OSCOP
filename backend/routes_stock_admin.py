"""Routes admin stock & prix par zone — déclenchent les alertes favoris."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from admin_guard import require_admin
from auth import get_current_user_id
from email_alerts import send_critical_alert_email
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
    reorder_point: int | None = Field(default=None, ge=0)


class PriceUpdateRequest(BaseModel):
    zone_code: str
    price_ht_cents: int = Field(gt=0)


def _now():
    return datetime.now(timezone.utc)


@stock_admin_router.get("/stock-products")
async def list_stock_products(_: dict = Depends(_admin)):
    """Produits du catalogue V2 (collection products) pour la gestion des stocks."""
    products = await db.products.find(
        {}, {"_id": 0, "id": 1, "name": 1, "sku": 1, "category": 1}
    ).sort("name", 1).to_list(500)
    stocks = await db.zone_stocks.find(
        {}, {"_id": 0, "product_id": 1, "zone_code": 1, "quantity_available": 1, "quantity_reserved": 1, "reorder_point": 1}
    ).to_list(5000)
    low_by_product: dict[str, list[str]] = {}
    for s in stocks:
        available = s.get("quantity_available", 0) - s.get("quantity_reserved", 0)
        if available <= s.get("reorder_point", 10):
            low_by_product.setdefault(s["product_id"], []).append(s["zone_code"])
    for p in products:
        p["low_stock_zones"] = sorted(low_by_product.get(p["id"], []))
    return {"products": products}


async def _find_product(product_id: str):
    proj = {"_id": 0, "id": 1, "name": 1}
    return (
        await db.products.find_one({"id": product_id}, proj)
        or await db.catalog_products.find_one({"id": product_id}, proj)
    )


@stock_admin_router.get("/stock/{product_id}")
async def get_zone_stocks(product_id: str, _: dict = Depends(_admin)):
    product = await _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    stocks = await db.zone_stocks.find({"product_id": product_id}, {"_id": 0}).to_list(50)
    zones = await db.zone_prices.distinct("zone_code", {"product_id": product_id})
    by_zone = {s["zone_code"]: s for s in stocks}
    all_zones = sorted(set(list(by_zone.keys()) + list(zones)))
    return {
        "product_id": product_id,
        "stocks": [
            {
                "zone_code": z,
                "quantity_available": by_zone.get(z, {}).get("quantity_available", 0),
                "quantity_reserved": by_zone.get(z, {}).get("quantity_reserved", 0),
                "reorder_point": by_zone.get(z, {}).get("reorder_point", 10),
            }
            for z in all_zones
        ],
    }


@stock_admin_router.get("/stock-history")
async def get_stock_history(
    product_id: str | None = None,
    zone_code: str | None = None,
    limit: int = 50,
    _: dict = Depends(_admin),
):
    query = {}
    if product_id:
        query["product_id"] = product_id
    if zone_code:
        query["zone_code"] = zone_code
    entries = await db.stock_adjustments.find(query, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 200))
    return {"entries": entries}


@stock_admin_router.put("/stock/{product_id}")
async def update_zone_stock(product_id: str, body: StockUpdateRequest, admin: dict = Depends(_admin)):
    product = await _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    existing = await db.zone_stocks.find_one({"product_id": product_id, "zone_code": body.zone_code})
    old_available = 0
    reorder_point = body.reorder_point if body.reorder_point is not None else 10
    if existing:
        old_available = existing.get("quantity_available", 0) - existing.get("quantity_reserved", 0)
        if body.reorder_point is None:
            reorder_point = existing.get("reorder_point", 10)

    set_fields = {"quantity_available": body.quantity_available, "updated_at": _now(),
                  "last_restock_at": _now() if body.quantity_available > 0 else None}
    if body.reorder_point is not None:
        set_fields["reorder_point"] = body.reorder_point
    await db.zone_stocks.update_one(
        {"product_id": product_id, "zone_code": body.zone_code},
        {
            "$set": set_fields,
            "$setOnInsert": {"id": f"{product_id}-{body.zone_code}", "quantity_reserved": 0,
                             **({} if body.reorder_point is not None else {"reorder_point": 10})},
        },
        upsert=True,
    )

    # Historique des ajustements
    await db.stock_adjustments.insert_one({
        "id": f"{product_id}-{body.zone_code}-{int(_now().timestamp() * 1000)}",
        "product_id": product_id,
        "product_name": product.get("name", ""),
        "zone_code": body.zone_code,
        "old_quantity": existing.get("quantity_available", 0) if existing else 0,
        "new_quantity": body.quantity_available,
        "author_id": admin.get("id"),
        "author_email": admin.get("email"),
        "created_at": _now().isoformat(),
    })

    restocked = old_available <= 0 and body.quantity_available > 0
    if restocked:
        asyncio.ensure_future(alert_favorites(product_id, body.zone_code, "restock"))
        from routes_restock_alerts import notify_restock_watchers
        asyncio.ensure_future(notify_restock_watchers(product_id, body.zone_code))

    # Alerte email admins si le stock passe sous le seuil de réassort
    new_available = body.quantity_available - (existing.get("quantity_reserved", 0) if existing else 0)
    low_stock_alerted = False
    if new_available <= reorder_point and old_available > reorder_point:
        low_stock_alerted = True
        asyncio.ensure_future(asyncio.to_thread(
            send_critical_alert_email,
            alert_type="low_stock",
            title=f"Stock sous seuil : {product.get('name', product_id)} ({body.zone_code})",
            message=(
                f"Le stock du produit <strong>{product.get('name', product_id)}</strong> "
                f"sur le territoire <strong>{body.zone_code}</strong> est passé sous son seuil de réassort."
            ),
            details={
                "Produit": product.get("name", product_id),
                "Territoire": body.zone_code,
                "Stock disponible": f"{new_available} unités",
                "Seuil de réassort": f"{reorder_point} unités",
                "Modifié par": admin.get("email", ""),
            },
            priority="high",
        ))

    return {
        "product_id": product_id,
        "zone_code": body.zone_code,
        "quantity_available": body.quantity_available,
        "restock_alert_triggered": restocked,
        "low_stock_alert_triggered": low_stock_alerted,
        "reorder_point": reorder_point,
    }


@stock_admin_router.get("/stock-history/export")
async def export_stock_history(
    product_id: str | None = None,
    zone_code: str | None = None,
    _: dict = Depends(_admin),
):
    """Export CSV de l'historique des ajustements de stock."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    query = {}
    if product_id:
        query["product_id"] = product_id
    if zone_code:
        query["zone_code"] = zone_code
    entries = await db.stock_adjustments.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Date", "Produit", "SKU produit (id)", "Territoire", "Ancienne quantité", "Nouvelle quantité", "Auteur"])
    for e in entries:
        writer.writerow([
            e.get("created_at", ""), e.get("product_name", ""), e.get("product_id", ""),
            e.get("zone_code", ""), e.get("old_quantity", ""), e.get("new_quantity", ""),
            e.get("author_email", ""),
        ])
    buf.seek(0)
    filename = f"historique_stocks_{_now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter(["\ufeff" + buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
