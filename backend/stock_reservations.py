"""Réservation temporaire des quantités du panier (30 min) — évite les ruptures au paiement."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

RESERVATION_MINUTES = 30


def _now():
    return datetime.now(timezone.utc)


async def cleanup_expired(db) -> int:
    """Libère les réservations expirées (appel paresseux à chaque accès panier/stock)."""
    expired = await db.stock_reservations.find({"expires_at": {"$lt": _now().isoformat()}}).to_list(200)
    for r in expired:
        await db.zone_stocks.update_one(
            {"product_id": r["product_id"], "zone_code": r["zone_code"]},
            [{"$set": {"quantity_reserved": {"$max": [0, {"$subtract": [{"$ifNull": ["$quantity_reserved", 0]}, r["quantity"]]}]}}}],
        )
        await db.stock_reservations.delete_one({"id": r["id"]})
    return len(expired)


async def available_for_org(db, org_id: str, zone_code: str, product_id: str):
    """Disponible en tenant compte des réservations des autres orgs. None = stock non suivi."""
    stock = await db.zone_stocks.find_one({"product_id": product_id, "zone_code": zone_code})
    if not stock:
        return None
    own = await db.stock_reservations.find_one({"org_id": org_id, "product_id": product_id, "zone_code": zone_code})
    own_qty = own["quantity"] if own else 0
    return stock.get("quantity_available", 0) - stock.get("quantity_reserved", 0) + own_qty


async def reserve_for_cart(db, org_id: str, zone_code: str, product_id: str, quantity: int):
    """Fixe la réservation de l'org à `quantity` (absolu) et rafraîchit les 30 min. None si stock non suivi."""
    stock = await db.zone_stocks.find_one({"product_id": product_id, "zone_code": zone_code})
    if not stock:
        return None
    existing = await db.stock_reservations.find_one({"org_id": org_id, "product_id": product_id, "zone_code": zone_code})
    prev = existing["quantity"] if existing else 0
    delta = quantity - prev
    expires = (_now() + timedelta(minutes=RESERVATION_MINUTES)).isoformat()
    if quantity <= 0:
        if existing:
            await db.stock_reservations.delete_one({"id": existing["id"]})
    else:
        await db.stock_reservations.update_one(
            {"org_id": org_id, "product_id": product_id, "zone_code": zone_code},
            {"$set": {"quantity": quantity, "expires_at": expires},
             "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": _now().isoformat()}},
            upsert=True,
        )
    if delta:
        await db.zone_stocks.update_one(
            {"product_id": product_id, "zone_code": zone_code},
            [{"$set": {"quantity_reserved": {"$max": [0, {"$add": [{"$ifNull": ["$quantity_reserved", 0]}, delta]}]}}}],
        )
    return expires


async def decrement_stock_for_order(db, org_id: str, zone_code: str, items: list, order_number: str, author_email: str = "") -> int:
    """Déduit le stock du territoire à la confirmation d'une commande, trace l'historique et libère les réservations."""
    decremented = 0
    now_iso = _now().isoformat()
    for it in items:
        if it.get("unavailable"):
            continue
        stock = await db.zone_stocks.find_one({"product_id": it["product_id"], "zone_code": zone_code})
        if not stock:
            continue
        old_qty = stock.get("quantity_available", 0)
        new_qty = max(0, old_qty - it["quantity"])
        await db.zone_stocks.update_one(
            {"product_id": it["product_id"], "zone_code": zone_code},
            {"$set": {"quantity_available": new_qty, "updated_at": _now()}},
        )
        await db.stock_adjustments.insert_one({
            "id": f"{it['product_id']}-{zone_code}-{int(_now().timestamp() * 1000)}",
            "product_id": it["product_id"],
            "product_name": it.get("product_name", ""),
            "zone_code": zone_code,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "author_id": None,
            "author_email": author_email or f"Commande {order_number}",
            "reason": f"Commande {order_number}",
            "created_at": now_iso,
        })
        decremented += 1
    await release_org_zone(db, org_id, zone_code)
    return decremented


async def release_org_zone(db, org_id: str, zone_code: str, product_id: str | None = None) -> int:
    """Libère les réservations de l'org sur la zone (toutes ou un produit)."""
    query = {"org_id": org_id, "zone_code": zone_code}
    if product_id:
        query["product_id"] = product_id
    reservations = await db.stock_reservations.find(query).to_list(100)
    for r in reservations:
        await db.zone_stocks.update_one(
            {"product_id": r["product_id"], "zone_code": r["zone_code"]},
            [{"$set": {"quantity_reserved": {"$max": [0, {"$subtract": [{"$ifNull": ["$quantity_reserved", 0]}, r["quantity"]]}]}}}],
        )
        await db.stock_reservations.delete_one({"id": r["id"]})
    return len(reservations)
