"""
LOLODRIVE by O'SCOP - API additionnelle connectable pour KDMARCHÉ.

Objectif : ajouter au backend KDM existant un moteur B2C / B2B2C pour :
- PASS Vie Chère 60€ = 600 UC, 30 jours, sans renouvellement auto
- Wallet UC avec ledger
- Catalogue ESSENTIELS(25) vs Hors25
- UC Hors25 sans avantage uniquement si PASS actif
- Drive / livraison / LOLO POINTS coopératifs
- POS, événements LOLO HOUR, partenaires sponsors
- KPI back-office
- Stripe PaymentIntents + Customers + Ephemeral Keys

Découpé en modules : lolodrive_models, lolodrive_helpers, routes_lolodrive_pos,
routes_lolodrive_points, routes_lolodrive_manager, routes_lolodrive_admin.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import uuid
import logging
import stripe

from lolodrive_models import (
    PASS_PRICE_CENTS, PASS_UC, PASS_DAYS, RECHARGE_PACKS,
    CatalogType, FulfillmentType, OrderStatus,
    QuoteRequest, OrderCreate, RechargeIntentRequest, OrderIntentRequest, QuoteLine,
)
from lolodrive_helpers import (
    get_current_user, require_admin, get_or_create_wallet, is_pass_active,
    cents_to_uc, logistics_config, quote_cart, ensure_customer, emit_crm_event,
    set_lolodrive_helpers_database,
)
from routes_lolodrive_pos import set_lolodrive_pos_database
from routes_lolodrive_points import set_lolodrive_points_database
from routes_lolodrive_manager import set_lolodrive_manager_database
from routes_lolodrive_admin import set_lolodrive_admin_database

logger = logging.getLogger(__name__)

lolodrive_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_database(database):
    global db
    db = database
    set_lolodrive_helpers_database(database)
    set_lolodrive_pos_database(database)
    set_lolodrive_points_database(database)
    set_lolodrive_manager_database(database)
    set_lolodrive_admin_database(database)

# =======================
# Public / user routes
# =======================

@lolodrive_router.get("/health")
async def health():
    return {"status": "healthy", "service": "LOLODRIVE by O'SCOP", "timestamp": datetime.utcnow()}

@lolodrive_router.get("/pass/me")
async def my_pass(user: dict = Depends(get_current_user)):
    p = await db.lolodrive_passes.find_one({"user_id": user["id"]}, {"_id": 0})
    w = await get_or_create_wallet(user["id"])
    return {"pass": p, "wallet": {"balance_uc": w.get("balance_uc", 0)}, "active": await is_pass_active(user["id"])}

@lolodrive_router.get("/wallet/me")
async def my_wallet(user: dict = Depends(get_current_user)):
    w = await get_or_create_wallet(user["id"])
    ledger = await db.lolodrive_wallet_ledger.find({"wallet_id": w["id"]}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"wallet": {"balance_uc": w.get("balance_uc", 0)}, "ledger": ledger}

@lolodrive_router.get("/catalog/teaser")
async def catalog_teaser():
    products = await db.lolodrive_products.find({"is_active": {"$ne": False}}, {"_id": 0, "price_pass_cents": 0}).limit(7).to_list(7)
    return {"products": products, "note": "Catalogue teaser public : prix PASS détaillés masqués."}

@lolodrive_router.get("/catalog/products")
async def catalog_products(catalog_type: Optional[CatalogType] = None, territory: Optional[str] = None, user: dict = Depends(get_current_user)):
    pass_active = await is_pass_active(user["id"])
    query = {"is_active": {"$ne": False}}
    if catalog_type:
        query["catalog_type"] = catalog_type.value
    if territory:
        # Product is available in territory if `territories` is missing/empty (=all) OR contains the requested code.
        territory = territory.upper()
        query["$or"] = [
            {"territories": {"$exists": False}},
            {"territories": {"$size": 0}},
            {"territories": territory},
        ]
    products = await db.lolodrive_products.find(query, {"_id": 0}).sort("name", 1).limit(200).to_list(200)

    out = []
    for p in products:
        is_essential = p.get("catalog_type") == CatalogType.ESSENTIAL.value
        price_cents = p.get("price_public_cents", 0)
        if is_essential and pass_active and p.get("price_pass_cents") is not None:
            price_cents = p["price_pass_cents"]
        out.append({
            **p,
            "display_price_cents": price_cents,
            "display_uc": cents_to_uc(price_cents if is_essential else p.get("price_public_cents", price_cents)) if pass_active else None,
            "payment_rule": "ESSENTIAL_PRICE_PASS" if is_essential else "NORMAL_PRICE_UC_WITHOUT_ADVANTAGE_IF_PASS_ACTIVE",
        })
    return {"pass_active": pass_active, "products": out}

@lolodrive_router.post("/catalog/quote")
async def catalog_quote(request: QuoteRequest, user: dict = Depends(get_current_user)):
    return await quote_cart(user["id"], request.items)

@lolodrive_router.post("/orders")
async def create_order(request: OrderCreate, user: dict = Depends(get_current_user)):
    q = await quote_cart(user["id"], request.items)
    cfg = await logistics_config()
    is_drive = request.fulfillment_type in [FulfillmentType.DRIVE, FulfillmentType.LOLO_POINT]
    fees_cents = cfg["drive_fee_min_cents"] if is_drive else cfg["delivery_fee_min_cents"]
    fees_uc = cfg["drive_fee_min_uc"] if is_drive else cfg["delivery_fee_min_uc"]

    point = None
    if request.lolo_point_code:
        point = await db.lolodrive_points.find_one({"code": request.lolo_point_code})

    order = {
        "id": str(uuid.uuid4()),
        "order_number": f"LD-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}",
        "user_id": user["id"],
        "lolo_point_id": point.get("id") if point else None,
        "fulfillment_type": request.fulfillment_type.value,
        "delivery_zone": request.delivery_zone,
        "delivery_slot_id": request.delivery_slot_id,
        "status": OrderStatus.DRAFT.value,
        "items": q["lines"],
        "subtotal_cents": q["subtotal_cents"],
        "fees_cents": fees_cents,
        "total_cents": q["subtotal_cents"] + fees_cents,
        "subtotal_uc": q["subtotal_uc"],
        "fees_uc": fees_uc,
        "total_uc": q["subtotal_uc"] + fees_uc if q["pass_active"] else 0,
        "pay_with_uc": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.lolodrive_orders.insert_one(order)
    order.pop("_id", None)
    return order

@lolodrive_router.get("/orders/me")
async def my_orders(user: dict = Depends(get_current_user)):
    orders = await db.lolodrive_orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"orders": orders}

@lolodrive_router.post("/orders/{order_id}/pay-uc")
async def pay_uc(order_id: str, user: dict = Depends(get_current_user)):
    if not await is_pass_active(user["id"]):
        raise HTTPException(status_code=403, detail="PASS inactif")
    order = await db.lolodrive_orders.find_one({"id": order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in [OrderStatus.DRAFT.value, OrderStatus.PENDING_PAYMENT.value]:
        raise HTTPException(status_code=400, detail="Commande non payable")

    # Requote server-side (anti-fraude)
    items = [QuoteLine(sku=i["sku"], qty=i["qty"]) for i in order.get("items", [])]
    q = await quote_cart(user["id"], items)
    required_uc = q["subtotal_uc"] + order.get("fees_uc", 0)

    wallet = await get_or_create_wallet(user["id"])
    if wallet.get("balance_uc", 0) < required_uc:
        raise HTTPException(status_code=403, detail="Solde UC insuffisant")

    await db.lolodrive_wallets.update_one(
        {"id": wallet["id"]},
        {"$inc": {"balance_uc": -required_uc}, "$set": {"updated_at": datetime.utcnow()}},
    )
    await db.lolodrive_wallet_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "wallet_id": wallet["id"],
        "type": "DEBIT",
        "amount_uc": required_uc,
        "reason": "ORDER_PAY_UC",
        "order_id": order_id,
        "created_at": datetime.utcnow(),
    })
    await db.lolodrive_orders.update_one(
        {"id": order_id},
        {"$set": {"status": OrderStatus.PAID.value, "pay_with_uc": True, "total_uc": required_uc, "updated_at": datetime.utcnow()}},
    )
    return {"ok": True, "order_id": order_id, "paid_with": "UC", "total_uc": required_uc}

# =======================
# Stripe PaymentIntents
# =======================

@lolodrive_router.post("/stripe/customer")
async def stripe_customer(user: dict = Depends(get_current_user)):
    customer_id = await ensure_customer(user)
    return {"customer_id": customer_id}

@lolodrive_router.post("/stripe/ephemeral-key")
async def stripe_ephemeral_key(user: dict = Depends(get_current_user)):
    customer_id = await ensure_customer(user)
    ek = stripe.EphemeralKey.create({"customer": customer_id}, api_version="2024-06-20")
    return {"customer_id": customer_id, "ephemeral_key_secret": ek.secret}

@lolodrive_router.post("/payments/pass-intent")
async def pass_intent(user: dict = Depends(get_current_user)):
    customer_id = await ensure_customer(user)
    pi = stripe.PaymentIntent.create(
        amount=PASS_PRICE_CENTS,
        currency="eur",
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
        setup_future_usage="off_session",
        metadata={"kind": "LOLO_PASS", "user_id": user["id"]},
    )
    await db.lolodrive_payments.insert_one({
        "id": str(uuid.uuid4()), "kind": "PASS", "user_id": user["id"], "amount_cents": PASS_PRICE_CENTS,
        "stripe_payment_intent_id": pi.id, "status": "CREATED", "created_at": datetime.utcnow(),
    })
    return {"client_secret": pi.client_secret, "payment_intent_id": pi.id, "customer_id": customer_id}

@lolodrive_router.post("/payments/recharge-intent")
async def recharge_intent(request: RechargeIntentRequest, user: dict = Depends(get_current_user)):
    pack = RECHARGE_PACKS.get(request.pack.upper())
    if not pack:
        raise HTTPException(status_code=400, detail="Pack invalide")
    customer_id = await ensure_customer(user)
    pi = stripe.PaymentIntent.create(
        amount=pack["amount_cents"], currency="eur", customer=customer_id,
        automatic_payment_methods={"enabled": True}, setup_future_usage="off_session",
        metadata={"kind": "LOLO_RECHARGE", "user_id": user["id"], "pack_uc": str(pack["uc"])},
    )
    await db.lolodrive_payments.insert_one({
        "id": str(uuid.uuid4()), "kind": "RECHARGE", "user_id": user["id"], "amount_cents": pack["amount_cents"],
        "pack_uc": pack["uc"], "stripe_payment_intent_id": pi.id, "status": "CREATED", "created_at": datetime.utcnow(),
    })
    return {"client_secret": pi.client_secret, "payment_intent_id": pi.id, "customer_id": customer_id}

@lolodrive_router.post("/payments/order-intent")
async def order_intent(request: OrderIntentRequest, user: dict = Depends(get_current_user)):
    order = await db.lolodrive_orders.find_one({"id": request.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    customer_id = await ensure_customer(user)
    pi = stripe.PaymentIntent.create(
        amount=order["total_cents"], currency="eur", customer=customer_id,
        automatic_payment_methods={"enabled": True}, setup_future_usage="off_session",
        metadata={"kind": "LOLO_ORDER", "user_id": user["id"], "order_id": order["id"]},
    )
    await db.lolodrive_orders.update_one({"id": order["id"]}, {"$set": {"status": OrderStatus.PENDING_PAYMENT.value, "stripe_payment_intent_id": pi.id}})
    await db.lolodrive_payments.insert_one({
        "id": str(uuid.uuid4()), "kind": "ORDER", "user_id": user["id"], "order_id": order["id"], "amount_cents": order["total_cents"],
        "stripe_payment_intent_id": pi.id, "status": "CREATED", "created_at": datetime.utcnow(),
    })
    return {"client_secret": pi.client_secret, "payment_intent_id": pi.id, "customer_id": customer_id}

@lolodrive_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if secret:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    else:
        event = stripe.Event.construct_from(await request.json(), stripe.api_key)

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        meta = pi.get("metadata", {})
        kind = meta.get("kind")
        user_id = meta.get("user_id")

        await db.lolodrive_payments.update_many(
            {"stripe_payment_intent_id": pi["id"]}, {"$set": {"status": "SUCCEEDED", "updated_at": datetime.utcnow()}}
        )

        if kind == "LOLO_PASS":
            starts_at = datetime.utcnow()
            ends_at = starts_at + timedelta(days=PASS_DAYS)
            await db.lolodrive_passes.update_one(
                {"user_id": user_id},
                {"$set": {"status": "ACTIVE", "starts_at": starts_at, "ends_at": ends_at, "price_cents": PASS_PRICE_CENTS, "uc_granted": PASS_UC, "is_auto_renew": False, "updated_at": datetime.utcnow()}, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
                upsert=True,
            )
            wallet = await get_or_create_wallet(user_id)
            await db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": PASS_UC}, "$set": {"updated_at": datetime.utcnow()}})
            await db.lolodrive_wallet_ledger.insert_one({"id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT", "amount_uc": PASS_UC, "reason": "PASS_ACTIVATION", "created_at": datetime.utcnow()})
            await emit_crm_event("pass.activated", {"user_id": user_id, "pass_price_cents": PASS_PRICE_CENTS, "uc_granted": PASS_UC, "ends_at": ends_at})

        elif kind == "LOLO_RECHARGE":
            pack_uc = int(meta.get("pack_uc", 0))
            wallet = await get_or_create_wallet(user_id)
            await db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": pack_uc}, "$set": {"updated_at": datetime.utcnow()}})
            await db.lolodrive_wallet_ledger.insert_one({"id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT", "amount_uc": pack_uc, "reason": "RECHARGE", "created_at": datetime.utcnow()})

        elif kind == "LOLO_ORDER":
            await db.lolodrive_orders.update_one({"id": meta.get("order_id")}, {"$set": {"status": OrderStatus.PAID.value, "updated_at": datetime.utcnow()}})
            await emit_crm_event("order.paid", {"user_id": user_id, "order_id": meta.get("order_id"), "payment_intent_id": pi["id"]})

    if event["type"] == "payment_intent.payment_failed":
        pi = event["data"]["object"]
        await db.lolodrive_payments.update_many({"stripe_payment_intent_id": pi["id"]}, {"$set": {"status": "FAILED", "updated_at": datetime.utcnow()}})

    return {"received": True}

