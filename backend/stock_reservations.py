"""Réservation temporaire des quantités du panier (30 min) — évite les ruptures au paiement."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

RESERVATION_MINUTES = 30


def _now():
    return datetime.now(timezone.utc)


async def cleanup_expired(db) -> int:
    """Libère les réservations expirées, trace les paniers abandonnés et relance l'acheteur."""
    expired = await db.stock_reservations.find({"expires_at": {"$lt": _now().isoformat()}}).to_list(200)
    abandoned_by_org: dict[tuple, list] = {}
    for r in expired:
        await db.zone_stocks.update_one(
            {"product_id": r["product_id"], "zone_code": r["zone_code"]},
            [{"$set": {"quantity_reserved": {"$max": [0, {"$subtract": [{"$ifNull": ["$quantity_reserved", 0]}, r["quantity"]]}]}}}],
        )
        await db.reservation_history.insert_one({
            "id": str(uuid.uuid4()),
            "org_id": r["org_id"],
            "product_id": r["product_id"],
            "zone_code": r["zone_code"],
            "quantity": r["quantity"],
            "reserved_at": r.get("created_at"),
            "expired_at": _now().isoformat(),
            "extend_count": r.get("extend_count", 0),
            "outcome": "EXPIRED_ABANDONED",
        })
        await db.stock_reservations.delete_one({"id": r["id"]})
        abandoned_by_org.setdefault((r["org_id"], r["zone_code"]), []).append(r)
    if abandoned_by_org:
        import asyncio
        asyncio.ensure_future(send_abandoned_cart_reminders(db, abandoned_by_org))
    return len(expired)


async def send_abandoned_cart_reminders(db, abandoned_by_org: dict) -> int:
    """Email de relance à l'acheteur dont la réservation panier a expiré (max 1 par org/zone/24 h)."""
    import logging
    from datetime import timedelta

    logger = logging.getLogger(__name__)
    sent = 0
    cutoff = (_now() - timedelta(hours=24)).isoformat()
    for (org_id, zone_code), reservations in abandoned_by_org.items():
        already = await db.abandoned_cart_reminders.find_one(
            {"org_id": org_id, "zone_code": zone_code, "sent_at": {"$gte": cutoff}}
        )
        if already:
            continue
        owner = await db.org_memberships.find_one({"org_id": org_id, "role": {"$regex": "OWNER"}})
        user = await db.users.find_one({"id": owner["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "name": 1}) if owner else None
        if not user or not user.get("email"):
            continue
        product_ids = [r["product_id"] for r in reservations]
        names = {p["id"]: p["name"] for p in await db.products.find({"id": {"$in": product_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(50)}
        rows = "".join(
            f"<li style='color:rgba(255,255,255,0.85);font-size:14px;margin-bottom:4px;'>"
            f"{names.get(r['product_id'], r['product_id'])} — {r['quantity']} unité(s)</li>"
            for r in reservations
        )
        body = f"""
          <h2 style="color:#D9B35A;margin:0 0 12px;font-size:18px;">Votre panier vous attend</h2>
          <p style="color:rgba(255,255,255,0.8);font-size:14px;">
            Bonjour {user.get('contact_name') or user.get('name') or ''},<br/><br/>
            La réservation de votre panier KDMARCHÉ ({zone_code}) a expiré sans commande.
            Les articles restent dans votre panier, mais les quantités ne sont plus garanties :
          </p>
          <ul style="padding-left:18px;">{rows}</ul>
          <p style="color:rgba(255,255,255,0.55);font-size:12px;margin-top:16px;">
            Reconnectez-vous au catalogue Pro pour finaliser votre commande — un nouvel ajout réactive la réservation de 30 minutes.
          </p>
        """
        try:
            from brevo_service import send_email, _wrap_html
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"),
                subject=f"🛒 Votre panier KDMARCHÉ vous attend ({zone_code})",
                html_content=_wrap_html("Relance panier", body),
                tags=["abandoned-cart-reminder"],
            )
            sent += 1
            await db.abandoned_cart_reminders.insert_one({
                "id": str(uuid.uuid4()), "org_id": org_id, "zone_code": zone_code,
                "email": user["email"], "products": product_ids, "sent_at": _now().isoformat(),
            })
            await db.reservation_history.update_many(
                {"org_id": org_id, "zone_code": zone_code, "outcome": "EXPIRED_ABANDONED", "reminded": {"$exists": False}},
                {"$set": {"reminded": True}},
            )
            logger.info("Abandoned cart reminder sent to %s (org %s, zone %s)", user["email"], org_id, zone_code)
        except Exception as exc:
            logger.error("Abandoned cart reminder failed for org %s: %s", org_id, exc)
    return sent


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


async def restock_for_cancellation(db, zone_code: str, items: list, order_number: str, author_email: str = "") -> int:
    """Ré-injecte les quantités au stock du territoire quand une commande est annulée."""
    restocked = 0
    now_iso = _now().isoformat()
    for it in items:
        if it.get("unavailable"):
            continue
        stock = await db.zone_stocks.find_one({"product_id": it["product_id"], "zone_code": zone_code})
        if not stock:
            continue
        old_qty = stock.get("quantity_available", 0)
        old_available = old_qty - stock.get("quantity_reserved", 0)
        new_qty = old_qty + it["quantity"]
        await db.zone_stocks.update_one(
            {"product_id": it["product_id"], "zone_code": zone_code},
            {"$set": {"quantity_available": new_qty, "updated_at": _now(), "last_restock_at": _now()}},
        )
        await db.stock_adjustments.insert_one({
            "id": f"{it['product_id']}-{zone_code}-{int(_now().timestamp() * 1000)}",
            "product_id": it["product_id"],
            "product_name": it.get("product_name", ""),
            "zone_code": zone_code,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "author_id": None,
            "author_email": author_email or f"Annulation {order_number}",
            "reason": f"Annulation commande {order_number}",
            "created_at": now_iso,
        })
        if old_available <= 0 and new_qty > 0:
            import asyncio
            from favorites_alerts import alert_favorites
            from routes_restock_alerts import notify_restock_watchers
            asyncio.ensure_future(alert_favorites(it["product_id"], zone_code, "restock"))
            asyncio.ensure_future(notify_restock_watchers(it["product_id"], zone_code))
        restocked += 1
    return restocked


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
