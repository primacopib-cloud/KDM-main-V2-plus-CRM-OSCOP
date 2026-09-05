"""
KDMARCHE × O'SCOP - Catalogue API Routes
Products, categories, pricing, cart, orders with ABAC gating
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, Query
from typing import List, Optional
from datetime import datetime
import asyncio
import uuid
import logging

from schema_catalog import (
    # Enums
    ProductStatus, PriceType, OrderStatus, CartStatus,
    # Categories
    CategoryCreate, CategoryResponse, CategoryInDB,
    # Products
    ProductCreate, ProductResponse, ProductInDB,
    # Pricing
    ZonePriceCreate, ZonePriceResponse, ZonePriceInDB,
    # Stock
    ZoneStockInDB,
    # Cart
    CartItemCreate, CartItemResponse, CartResponse, CartInDB,
    # Orders
    OrderCreate, OrderResponse, OrderInDB, OrderItemResponse,
    # Pickup
    PickupLocationResponse, PickupLocationInDB,
    # Defaults
    DEFAULT_CATEGORIES, DEFAULT_PICKUP_LOCATIONS, SAMPLE_PRODUCTS,
)
from schema_v2 import (
    OrgStatus, SubscriptionStatus, PartnerProvisionStatus,
    CustomerRole, LedgerDirection, LedgerStatus,
    AuditLogEntry, LedgerEntryInDB,
)
from abac_policy import ABACPolicyEngine, PolicyInput, PolicySubject, PolicyResource, PolicyData

logger = logging.getLogger(__name__)

# Router
cart_router = APIRouter(prefix="/api/v2/catalog")

db = None

def set_cart_database(database):
    global db
    db = database

from routes_catalog import get_current_user_catalog, get_user_org_context, check_price_access, get_selected_zone, ensure_member_active
from role_guards import ensure_can_buy
from stock_reservations import cleanup_expired, available_for_org, reserve_for_cart, release_org_zone

# ============== CART ==============

async def _resolve_zone(current_user: dict, org_id: str, zone_code: Optional[str] = None) -> Optional[str]:
    """Zone explicite du client (persistée) ou zone sélectionnée côté serveur"""
    if zone_code:
        zone = await db.zones_v2.find_one({"code": zone_code})
        if zone:
            await db.org_runtime_preferences.update_one(
                {"org_id": org_id},
                {"$set": {"org_id": org_id, "selected_zone_id": zone["id"], "updated_at": datetime.utcnow()}},
                upsert=True,
            )
            return zone_code
    return await get_selected_zone(current_user)


@cart_router.get("/cart", response_model=CartResponse)
async def get_cart(
    zone_code: Optional[str] = None,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Get current user's cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    
    zone_code = await _resolve_zone(current_user, membership["org_id"], zone_code)
    if not zone_code:
        raise HTTPException(status_code=400, detail="Sélectionnez une zone d'abord")
    
    # Get or create cart
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        cart = CartInDB(
            org_id=membership["org_id"],
            zone_code=zone_code,
        ).dict()
        await db.carts.insert_one(cart)
    
    alerts = await _refresh_cart_items(cart)
    await cleanup_expired(db)
    price_alerts = [a for a in alerts if a["type"] == "PRICE_CHANGED" and a.get("new")]
    if price_alerts and current_user.get("email"):
        asyncio.create_task(_send_price_alert_email(current_user, price_alerts))
    from promo_pricing import enrich_cart_response
    response = await enrich_cart_response(db, await _build_cart_response(cart, alerts), cart, current_user)
    soonest = await db.stock_reservations.find(
        {"org_id": membership["org_id"], "zone_code": zone_code}
    ).sort("expires_at", 1).to_list(1)
    if soonest:
        response.reserved_until = soonest[0]["expires_at"]
    if cart.get("return_code"):
        response.return_code = cart["return_code"]
        response.return_discount_cents = round(cart.get("subtotal_ht_cents", 0) * cart.get("return_discount_percent", 0) / 100)
    return response


@cart_router.post("/cart/items", response_model=CartResponse)
async def add_to_cart(
    item: CartItemCreate,
    zone_code: Optional[str] = None,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Add item to cart"""
    ensure_can_buy(current_user)
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    
    zone_code = await _resolve_zone(current_user, membership["org_id"], zone_code)
    if not zone_code:
        raise HTTPException(status_code=400, detail="Sélectionnez une zone d'abord")
    
    # Check price access
    if not current_user.get("is_admin") and not await check_price_access(current_user, zone_code):
        raise HTTPException(status_code=403, detail="Accès non autorisé à cette zone")
    
    # Get product
    product = await db.products.find_one({"id": item.product_id, "status": ProductStatus.ACTIVE.value})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Get price for zone
    zone_price = await db.zone_prices.find_one({
        "product_id": item.product_id,
        "zone_code": zone_code,
        "is_active": True,
    })
    if not zone_price:
        raise HTTPException(status_code=400, detail="Produit non disponible dans cette zone")
    
    # Check quantity
    if item.quantity < product["min_order_qty"]:
        raise HTTPException(
            status_code=400,
            detail=f"Quantité minimum: {product['min_order_qty']}"
        )
    
    if product.get("max_order_qty") and item.quantity > product["max_order_qty"]:
        raise HTTPException(
            status_code=400,
            detail=f"Quantité maximum: {product['max_order_qty']}"
        )
    
    # Get or create cart
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        cart = CartInDB(
            org_id=membership["org_id"],
            zone_code=zone_code,
        ).dict()
        await db.carts.insert_one(cart)
        cart = await db.carts.find_one({"id": cart["id"]})
    
    # Build cart item
    cart_item = {
        "id": str(uuid.uuid4()),
        "product_id": product["id"],
        "product_name": product["name"],
        "product_sku": product["sku"],
        "product_image": product.get("image_url"),
        "unit": product["unit"],
        "quantity": item.quantity,
        "price_ht_cents": zone_price["price_ht_cents"],
        "line_total_ht_cents": zone_price["price_ht_cents"] * item.quantity,
        "incoterms": (product.get("incoterms") or {}).get(zone_code) or [],
    }
    
    # Check if product already in cart
    items = cart.get("items", [])
    existing_idx = next((i for i, x in enumerate(items) if x["product_id"] == item.product_id), None)

    # Réservation panier : vérifie la disponibilité réelle (30 min, hors réservations des autres orgs)
    await cleanup_expired(db)
    prospective_qty = item.quantity + (items[existing_idx]["quantity"] if existing_idx is not None else 0)
    available = await available_for_org(db, membership["org_id"], zone_code, item.product_id)
    if available is not None and prospective_qty > available:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuffisant sur ce territoire : {max(available, 0)} unité(s) disponible(s)",
        )

    if existing_idx is not None:
        # Update quantity
        items[existing_idx]["quantity"] += item.quantity
        items[existing_idx]["line_total_ht_cents"] = (
            items[existing_idx]["price_ht_cents"] * items[existing_idx]["quantity"]
        )
    else:
        items.append(cart_item)
    
    # Recalculate totals
    subtotal = sum(i["line_total_ht_cents"] for i in items)
    tax = int(subtotal * 0.085)  # TVA réduite DOM
    total = subtotal + tax
    
    # Update cart
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {
            "items": items,
            "subtotal_ht_cents": subtotal,
            "tax_cents": tax,
            "total_ttc_cents": total,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_cart = await db.carts.find_one({"id": cart["id"]})
    reserved_until = await reserve_for_cart(db, membership["org_id"], zone_code, item.product_id, prospective_qty)
    response = await _build_cart_response(updated_cart)
    response.reserved_until = reserved_until
    return response


@cart_router.post("/cart/reservation/extend")
async def extend_cart_reservation(
    zone_code: Optional[str] = None,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Prolonge de 15 minutes les réservations panier de l'organisation."""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    zone_code = await _resolve_zone(current_user, membership["org_id"], zone_code)
    if not zone_code:
        raise HTTPException(status_code=400, detail="Sélectionnez une zone d'abord")
    await cleanup_expired(db)
    from datetime import timedelta, timezone
    reservations = await db.stock_reservations.find(
        {"org_id": membership["org_id"], "zone_code": zone_code}
    ).to_list(100)
    if not reservations:
        raise HTTPException(status_code=404, detail="Aucune réservation active à prolonger")
    MAX_EXTENSIONS = 2
    used = max((r.get("extend_count", 0) for r in reservations), default=0)
    if used >= MAX_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Limite de 2 prolongations atteinte pour ce panier")
    now = datetime.now(timezone.utc)
    latest = None
    for r in reservations:
        base = max(datetime.fromisoformat(r["expires_at"]), now)
        new_expires = (base + timedelta(minutes=15)).isoformat()
        await db.stock_reservations.update_one(
            {"id": r["id"]},
            {"$set": {"expires_at": new_expires, "extend_count": r.get("extend_count", 0) + 1}},
        )
        if latest is None or new_expires < latest:
            latest = new_expires
    return {"extended": len(reservations), "reserved_until": latest, "extensions_left": MAX_EXTENSIONS - used - 1}


@cart_router.post("/cart/apply-return-code", response_model=CartResponse)
async def apply_return_code(
    payload: dict,
    zone_code: Optional[str] = None,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Applique un bon de retour (relance panier abandonné) au panier actif."""
    code = (payload.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Code requis")
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    zone_code = await _resolve_zone(current_user, membership["org_id"], zone_code)
    promo = await db.cart_return_codes.find_one({"code": code, "org_id": membership["org_id"]})
    if not promo:
        raise HTTPException(status_code=404, detail="Code invalide pour votre organisation")
    if promo.get("used"):
        raise HTTPException(status_code=400, detail="Ce bon de retour a déjà été utilisé")
    if promo["expires_at"] < datetime.utcnow().isoformat():
        raise HTTPException(status_code=400, detail="Ce bon de retour a expiré")
    cart = await db.carts.find_one({
        "org_id": membership["org_id"], "zone_code": zone_code, "status": CartStatus.ACTIVE.value,
    })
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Panier vide")
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {"return_code": code, "return_discount_percent": promo["discount_percent"], "updated_at": datetime.utcnow()}},
    )
    cart = await db.carts.find_one({"id": cart["id"]})
    response = await _build_cart_response(cart)
    response.return_code = code
    response.return_discount_cents = round(cart.get("subtotal_ht_cents", 0) * promo["discount_percent"] / 100)
    return response


@cart_router.delete("/cart/items/{item_id}", response_model=CartResponse)
async def remove_from_cart(
    item_id: str,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Remove item from cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    
    zone_code = await get_selected_zone(current_user)
    
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    
    # Remove item
    removed = next((i for i in cart.get("items", []) if i["id"] == item_id), None)
    items = [i for i in cart.get("items", []) if i["id"] != item_id]
    if removed:
        await release_org_zone(db, membership["org_id"], cart["zone_code"], removed["product_id"])
    
    # Recalculate
    subtotal = sum(i["line_total_ht_cents"] for i in items)
    tax = int(subtotal * 0.085)
    total = subtotal + tax
    
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {
            "items": items,
            "subtotal_ht_cents": subtotal,
            "tax_cents": tax,
            "total_ttc_cents": total,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_cart = await db.carts.find_one({"id": cart["id"]})
    return await _build_cart_response(updated_cart)


@cart_router.delete("/cart", response_model=dict)
async def clear_cart(current_user: dict = Depends(get_current_user_catalog)):
    """Clear cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    
    zone_code = await get_selected_zone(current_user)
    if zone_code:
        await release_org_zone(db, membership["org_id"], zone_code)
    
    await db.carts.update_one(
        {
            "org_id": membership["org_id"],
            "zone_code": zone_code,
            "status": CartStatus.ACTIVE.value,
        },
        {"$set": {
            "items": [],
            "subtotal_ht_cents": 0,
            "tax_cents": 0,
            "total_ttc_cents": 0,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    return {"message": "Panier vidé"}


async def _send_price_alert_email(user: dict, price_alerts: list):
    """Email Brevo à l'acheteur quand un produit de son panier change de prix."""
    import brevo_service
    from brevo_service import _wrap_html
    rows = "".join(
        f"<tr><td style='padding:8px 12px;color:rgba(255,255,255,0.85);font-size:14px;'>{a['product_name']}</td>"
        f"<td style='padding:8px 12px;color:rgba(255,255,255,0.5);font-size:14px;text-decoration:line-through;'>{a['old_price_ht_cents']/100:.2f} €</td>"
        f"<td style='padding:8px 12px;color:#D9B35A;font-size:14px;font-weight:bold;'>{a['new_price_ht_cents']/100:.2f} € HT</td></tr>"
        for a in price_alerts
    )
    body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Changement de prix dans votre panier</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        Bonjour {user.get('contact_name') or ''},<br/><br/>
        Le prix de {len(price_alerts)} produit(s) de votre panier KDMARCHÉ a été mis à jour :
      </p>
      <table style=\"width:100%;border-collapse:collapse;background:rgba(255,255,255,0.05);border-radius:12px;\">{rows}</table>
      <p style=\"color:rgba(255,255,255,0.55);font-size:12px;margin-top:16px;\">
        Votre panier a été automatiquement recalculé avec les nouveaux prix coopératifs.
      </p>
    """
    try:
        await brevo_service.send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject="⚠ Prix mis à jour dans votre panier KDMARCHÉ",
            html_content=_wrap_html("Alerte prix panier", body),
            tags=["cart-price-alert"],
        )
        logger.info("Price alert email sent to %s (%d items)", user["email"], len(price_alerts))
    except Exception as e:
        logger.error("Price alert email failed: %s", e)


async def _refresh_cart_items(cart: dict) -> list:
    """Détecte les changements de prix / indisponibilités et met le panier à jour."""
    alerts = []
    items = cart.get("items", [])
    if not items:
        return alerts
    changed = False
    for it in items:
        product = await db.products.find_one({"id": it["product_id"]})
        zone_price = await db.zone_prices.find_one({
            "product_id": it["product_id"],
            "zone_code": cart["zone_code"],
            "is_active": True,
        })
        available = product and product.get("status") == ProductStatus.ACTIVE.value and zone_price
        if not available:
            if not it.get("unavailable"):
                it["unavailable"] = True
                changed = True
                alerts.append({"type": "UNAVAILABLE", "item_id": it["id"], "product_name": it["product_name"], "new": True})
            else:
                alerts.append({"type": "UNAVAILABLE", "item_id": it["id"], "product_name": it["product_name"], "new": False})
            continue
        if it.get("unavailable"):
            it["unavailable"] = False
            changed = True
            alerts.append({"type": "AVAILABLE_AGAIN", "item_id": it["id"], "product_name": it["product_name"], "new": True})
        # Sync silencieux des incoterms du produit pour la zone du panier
        inco = (product.get("incoterms") or {}).get(cart["zone_code"]) or []
        if inco != (it.get("incoterms") or []):
            it["incoterms"], changed = inco, True
        if zone_price["price_ht_cents"] != it["price_ht_cents"]:
            alerts.append({
                "type": "PRICE_CHANGED", "item_id": it["id"], "product_name": it["product_name"],
                "old_price_ht_cents": it["price_ht_cents"], "new_price_ht_cents": zone_price["price_ht_cents"],
                "new": True,
            })
            it["price_ht_cents"] = zone_price["price_ht_cents"]
            it["line_total_ht_cents"] = zone_price["price_ht_cents"] * it["quantity"]
            changed = True
    if changed:
        subtotal = sum(i["line_total_ht_cents"] for i in items if not i.get("unavailable"))
        tax = int(subtotal * 0.085)
        cart["subtotal_ht_cents"] = subtotal
        cart["tax_cents"] = tax
        cart["total_ttc_cents"] = subtotal + tax
        cart["updated_at"] = datetime.utcnow()
        await db.carts.update_one(
            {"id": cart["id"]},
            {"$set": {
                "items": items,
                "subtotal_ht_cents": subtotal,
                "tax_cents": tax,
                "total_ttc_cents": cart["total_ttc_cents"],
                "updated_at": cart["updated_at"],
            }}
        )
    return alerts


async def _build_cart_response(cart: dict, alerts: list = None) -> CartResponse:
    """Build cart response"""
    items = []
    for item in cart.get("items", []):
        items.append(CartItemResponse(
            id=item["id"],
            product_id=item["product_id"],
            product_name=item["product_name"],
            product_sku=item["product_sku"],
            product_image=item.get("product_image"),
            unit=item["unit"],
            quantity=item["quantity"],
            price_ht_cents=item["price_ht_cents"],
            line_total_ht_cents=item["line_total_ht_cents"],
            unavailable=bool(item.get("unavailable")),
            incoterms=item.get("incoterms") or [],
        ))
    
    return CartResponse(
        id=cart["id"],
        org_id=cart["org_id"],
        zone_code=cart["zone_code"],
        status=cart["status"],
        items=items,
        items_count=len(items),
        subtotal_ht_cents=cart.get("subtotal_ht_cents", 0),
        tax_cents=cart.get("tax_cents", 0),
        total_ttc_cents=cart.get("total_ttc_cents", 0),
        alerts=alerts or [],
        created_at=cart["created_at"],
        updated_at=cart["updated_at"],
    )


# ============== INSTALLMENT CALCULATION ==============

@cart_router.get("/installment/calculate")
async def calculate_installment_plan(
    amount_ht_cents: int = Query(..., description="Montant HT en centimes"),
    current_user: dict = Depends(get_current_user_catalog),
):
    """
    Calculate installment plan for a given amount
    
    Formula:
    - Frais = Montant HT × 20%
    - TVA sur frais = Frais × 8.50%
    - Total frais = Frais + TVA
    - Réparti sur 4 échéances mensuelles
    """
    MIN_INSTALLMENT_HT_CENTS = 550000  # 5500€
    
    if amount_ht_cents < MIN_INSTALLMENT_HT_CENTS:
        return {
            "eligible": False,
            "min_amount_ht_cents": MIN_INSTALLMENT_HT_CENTS,
            "min_amount_ht_eur": MIN_INSTALLMENT_HT_CENTS / 100,
            "provided_amount_ht_cents": amount_ht_cents,
            "provided_amount_ht_eur": amount_ht_cents / 100,
            "message": f"Le paiement échelonné est disponible à partir de {MIN_INSTALLMENT_HT_CENTS/100:.0f}€ HT"
        }
    
    # Calculate fees
    fees_ht_cents = int(amount_ht_cents * 0.20)  # 20%
    fees_tva_cents = int(fees_ht_cents * 0.085)  # 8.50% TVA
    total_fees_cents = fees_ht_cents + fees_tva_cents
    
    # Total with original TVA (8.50%) + fees
    product_tva_cents = int(amount_ht_cents * 0.085)
    total_ttc_cents = amount_ht_cents + product_tva_cents
    total_with_fees_cents = total_ttc_cents + total_fees_cents
    
    # Calculate installments
    installment_amount = total_with_fees_cents // 4
    remainder = total_with_fees_cents % 4
    
    from dateutil.relativedelta import relativedelta
    base_date = datetime.utcnow()
    
    installments = []
    for i in range(4):
        due_date = base_date + relativedelta(months=i)
        amount = installment_amount + (1 if i < remainder else 0)
        installments.append({
            "number": i + 1,
            "amount_cents": amount,
            "amount_eur": amount / 100,
            "due_date": due_date.strftime("%Y-%m-%d"),
            "label": f"Échéance {i+1}/4 - {due_date.strftime('%B %Y')}"
        })
    
    return {
        "eligible": True,
        "subtotal_ht_cents": amount_ht_cents,
        "subtotal_ht_eur": amount_ht_cents / 100,
        "product_tva_cents": product_tva_cents,
        "product_tva_eur": product_tva_cents / 100,
        "total_ttc_cents": total_ttc_cents,
        "total_ttc_eur": total_ttc_cents / 100,
        "fee_rate": 0.20,
        "fee_rate_percent": "20%",
        "fee_tva_rate": 0.085,
        "fee_tva_rate_percent": "8.50%",
        "fees_ht_cents": fees_ht_cents,
        "fees_ht_eur": fees_ht_cents / 100,
        "fees_tva_cents": fees_tva_cents,
        "fees_tva_eur": fees_tva_cents / 100,
        "total_fees_cents": total_fees_cents,
        "total_fees_eur": total_fees_cents / 100,
        "total_with_fees_cents": total_with_fees_cents,
        "total_with_fees_eur": total_with_fees_cents / 100,
        "installment_count": 4,
        "installments": installments,
        "savings_vs_full_payment": 0,  # No savings, fees are additional
        "message": f"Paiement en 4× de {installment_amount/100:.2f}€/mois (frais inclus)"
    }


