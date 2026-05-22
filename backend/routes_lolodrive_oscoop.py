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

Stack compatible : FastAPI + Motor MongoDB + auth.py existant.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import os
import uuid
import logging
import stripe

from auth import get_current_user_id

logger = logging.getLogger(__name__)

lolodrive_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

# Database reference injected by server.py
db = None

def set_lolodrive_database(database):
    global db
    db = database

async def emit_crm_event(event_type: str, payload: dict):
    """Best-effort CRM bridge; never blocks transactional flow."""
    try:
        from routes_crm_oscoop import crm_record_event
        await crm_record_event(db, event_type, payload)
    except Exception as e:
        logger.warning(f"CRM sync skipped for {event_type}: {e}")

stripe.api_key = os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")

# =======================
# Constants / business rules
# =======================

PASS_PRICE_CENTS = 6000
PASS_UC = 600
PASS_DAYS = 30

RECHARGE_PACKS = {
    "MINI": {"amount_cents": 2000, "uc": 200},
    "STANDARD": {"amount_cents": 4000, "uc": 400},
    "MAXI": {"amount_cents": 7000, "uc": 720},
}

DEFAULT_LOGISTICS_CONFIG = {
    "id": "default",
    "drive_open_time": "08:00",
    "drive_close_time": "21:30",
    "drive_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
    "drive_fee_min_cents": 200,
    "drive_fee_min_uc": 20,
    "drive_fee_max_cents": 300,
    "drive_fee_max_uc": 30,
    "delivery_fee_min_cents": 500,
    "delivery_fee_max_cents": 1000,
    "delivery_fee_min_uc": 50,
    "delivery_fee_max_uc": 100,
    "allow_uc_for_normal_if_pass_active": True,
}

# =======================
# Schemas
# =======================

class CatalogType(str, Enum):
    ESSENTIAL = "ESSENTIAL"
    NORMAL = "NORMAL"

class FulfillmentType(str, Enum):
    DRIVE = "DRIVE"
    DELIVERY = "DELIVERY"
    LOLO_POINT = "LOLO_POINT"

class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PREPARING = "PREPARING"
    READY = "READY"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class EventType(str, Enum):
    LOLO_HOUR = "LOLO_HOUR"
    FLASH_PASS = "FLASH_PASS"
    FLASH_PUBLIC = "FLASH_PUBLIC"
    LOLO_BIG_DEAL = "LOLO_BIG_DEAL"
    PARTNER = "PARTNER"

class RegisterProduct(BaseModel):
    sku: str
    name: str
    category: str = "Épicerie"
    brand: Optional[str] = None
    size_label: Optional[str] = None
    catalog_type: CatalogType = CatalogType.NORMAL
    price_public_cents: int
    price_pass_cents: Optional[int] = None
    image_url: Optional[str] = None
    stock_qty: Optional[int] = None

class QuoteLine(BaseModel):
    sku: str
    qty: int = Field(..., ge=1)

class QuoteRequest(BaseModel):
    items: List[QuoteLine]

class OrderCreate(BaseModel):
    fulfillment_type: FulfillmentType
    items: List[QuoteLine]
    lolo_point_code: Optional[str] = None
    delivery_zone: Optional[str] = None
    delivery_slot_id: Optional[str] = None

class RechargeIntentRequest(BaseModel):
    pack: str = Field(..., description="MINI | STANDARD | MAXI")

class OrderIntentRequest(BaseModel):
    order_id: str

class LoloPointCreate(BaseModel):
    name: str
    code: str
    city: Optional[str] = None
    address: Optional[str] = None
    zone_name: Optional[str] = None
    manager_user_id: Optional[str] = None
    payout_cap_cents_monthly: int = 120000
    payout_cap_percent_bps: int = 600

class EventCreate(BaseModel):
    type: EventType
    title: str
    starts_at: datetime
    ends_at: datetime
    is_pass_only: bool = True
    partner_id: Optional[str] = None
    sponsor_pack: Optional[str] = None
    stock_limit: Optional[int] = None
    per_user_limit: int = 1
    drive_only: bool = True

class PartnerCreate(BaseModel):
    name: str
    type: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

class CoopContributionCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    estimated_value_cents: Optional[int] = None
    user_id: Optional[str] = None

class StatusUpdate(BaseModel):
    status: OrderStatus

class PayoutPreviewRequest(BaseModel):
    from_date: datetime
    to_date: datetime

# =======================
# Helpers
# =======================

async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    role = user.get("role") or user.get("user_role") or user.get("role_v2")
    is_admin = user.get("is_admin", False) or role in ["oscop_super_admin", "kdm_b2b_admin", "admin", "SUPER_ADMIN", "ADMIN"]
    if not is_admin:
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user

async def get_or_create_wallet(user_id: str) -> dict:
    wallet = await db.lolodrive_wallets.find_one({"user_id": user_id})
    if wallet:
        return wallet
    wallet = {"id": str(uuid.uuid4()), "user_id": user_id, "balance_uc": 0, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    await db.lolodrive_wallets.insert_one(wallet)
    return wallet

async def is_pass_active(user_id: str) -> bool:
    doc = await db.lolodrive_passes.find_one({"user_id": user_id})
    return bool(doc and doc.get("status") == "ACTIVE" and doc.get("ends_at") and doc["ends_at"] > datetime.utcnow())

def cents_to_uc(cents: int) -> int:
    # Règle interne : 10 centimes = 1 UC. Ne pas afficher comme taux public.
    return round(cents / 10)

async def logistics_config() -> dict:
    cfg = await db.lolodrive_logistics_config.find_one({"id": "default"})
    if cfg:
        return cfg
    await db.lolodrive_logistics_config.insert_one({**DEFAULT_LOGISTICS_CONFIG, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    return DEFAULT_LOGISTICS_CONFIG

async def quote_cart(user_id: str, items: List[QuoteLine]) -> dict:
    pass_active = await is_pass_active(user_id)
    cfg = await logistics_config()
    allow_normal_uc = cfg.get("allow_uc_for_normal_if_pass_active", True)

    skus = [i.sku for i in items]
    products = await db.lolodrive_products.find({"sku": {"$in": skus}, "is_active": {"$ne": False}}).to_list(200)
    products_by_sku = {p["sku"]: p for p in products}

    subtotal_cents = 0
    subtotal_uc = 0
    lines = []

    for item in items:
        p = products_by_sku.get(item.sku)
        if not p:
            continue
        is_essential = p.get("catalog_type") == CatalogType.ESSENTIAL.value
        unit_cents = p.get("price_public_cents", 0)
        if is_essential and pass_active and p.get("price_pass_cents") is not None:
            unit_cents = p["price_pass_cents"]

        unit_uc = None
        if pass_active:
            if is_essential:
                unit_uc = cents_to_uc(unit_cents)
            elif allow_normal_uc:
                # Hors25 payable en UC sans avantage : UC sur prix normal
                unit_uc = cents_to_uc(p.get("price_public_cents", unit_cents))

        subtotal_cents += unit_cents * item.qty
        subtotal_uc += (unit_uc or 0) * item.qty
        lines.append({
            "sku": p["sku"],
            "name": p["name"],
            "qty": item.qty,
            "catalog_type": p.get("catalog_type"),
            "unit_cents": unit_cents,
            "unit_uc": unit_uc,
        })

    return {"pass_active": pass_active, "subtotal_cents": subtotal_cents, "subtotal_uc": subtotal_uc, "lines": lines}

async def ensure_customer(user: dict) -> str:
    if user.get("stripe_customer_id"):
        return user["stripe_customer_id"]
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    customer = stripe.Customer.create(
        email=user.get("email"),
        phone=user.get("phone"),
        metadata={"user_id": user["id"]},
    )
    await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer.id}})
    return customer.id

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
async def catalog_products(catalog_type: Optional[CatalogType] = None, user: dict = Depends(get_current_user)):
    pass_active = await is_pass_active(user["id"])
    query = {"is_active": {"$ne": False}}
    if catalog_type:
        query["catalog_type"] = catalog_type.value
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

# =======================
# Logistics / POS
# =======================

@lolodrive_router.get("/logistics/config")
async def get_logistics_config():
    return await logistics_config()

@lolodrive_router.get("/logistics/zones")
async def get_delivery_zones():
    zones = await db.lolodrive_delivery_zones.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return {"zones": zones}

@lolodrive_router.get("/pos/orders")
async def pos_orders(status_filter: Optional[OrderStatus] = Query(None, alias="status"), lolo_point_code: Optional[str] = None, user: dict = Depends(get_current_user)):
    query: Dict[str, Any] = {}
    if status_filter:
        query["status"] = status_filter.value
    if lolo_point_code:
        point = await db.lolodrive_points.find_one({"code": lolo_point_code})
        query["lolo_point_id"] = point.get("id") if point else "__missing__"
    orders = await db.lolodrive_orders.find(query, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"orders": orders}

@lolodrive_router.post("/pos/orders/{order_id}/status")
async def pos_update_order_status(order_id: str, request: StatusUpdate, user: dict = Depends(get_current_user)):
    now = datetime.utcnow()
    extra = {"updated_at": now}
    if request.status == OrderStatus.PREPARING:
        extra["prepared_at"] = now
    if request.status == OrderStatus.READY:
        extra["ready_at"] = now
    if request.status == OrderStatus.FULFILLED:
        extra["fulfilled_at"] = now
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": request.status.value, **extra}})
    await _broadcast_pos_event("order.status_changed", {"order_id": order_id, "status": request.status.value})
    return {"ok": True, "order_id": order_id, "status": request.status.value}

@lolodrive_router.post("/pos/orders/{order_id}/scan")
async def pos_scan(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.lolodrive_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in [OrderStatus.READY.value, OrderStatus.PAID.value]:
        raise HTTPException(status_code=400, detail="Commande non prête")
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": OrderStatus.FULFILLED.value, "fulfilled_at": datetime.utcnow(), "updated_at": datetime.utcnow()}})
    await _broadcast_pos_event("order.fulfilled", {"order_id": order_id})
    return {"ok": True, "order_id": order_id, "status": OrderStatus.FULFILLED.value}


@lolodrive_router.post("/pos/orders/{order_id}/cancel")
async def pos_cancel_order(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Annulation / signalement d'un problème par l'opérateur POS.
    payload = {"reason": "...", "refund_uc": bool}. Si refund_uc=True et commande payée en UC, recrédite le wallet.
    """
    order = await db.lolodrive_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] in [OrderStatus.FULFILLED.value, OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value]:
        raise HTTPException(status_code=400, detail="Commande déjà finalisée")
    reason = (payload or {}).get("reason", "Annulation POS")
    refund_uc = (payload or {}).get("refund_uc", False)
    new_status = OrderStatus.CANCELLED.value
    extra = {"cancelled_at": datetime.utcnow(), "cancel_reason": reason}
    # Refund UC if requested and applicable
    if refund_uc and order.get("pay_with_uc") and order.get("total_uc"):
        wallet = await db.lolodrive_wallets.find_one({"user_id": order["user_id"]})
        if wallet:
            await db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": order["total_uc"]}, "$set": {"updated_at": datetime.utcnow()}})
            await db.lolodrive_wallet_ledger.insert_one({"id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT", "amount_uc": order["total_uc"], "reason": "ORDER_REFUND", "order_id": order_id, "created_at": datetime.utcnow()})
            new_status = OrderStatus.REFUNDED.value
            extra["refunded_at"] = datetime.utcnow()
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": new_status, "updated_at": datetime.utcnow(), **extra}})
    await _broadcast_pos_event("order.cancelled", {"order_id": order_id, "status": new_status, "reason": reason})
    return {"ok": True, "order_id": order_id, "status": new_status, "reason": reason}


async def _broadcast_pos_event(event_type: str, payload: dict):
    """Broadcast LOLODRIVE POS events to all admin WebSocket clients."""
    try:
        from routes_websockets import manager
        await manager.broadcast_to_admins({
            "type": "lolodrive_pos_event",
            "payload": {"event": event_type, "data": payload, "timestamp": datetime.utcnow().isoformat()},
        })
    except Exception:
        pass


@lolodrive_router.get("/admin/kpi/dashboard")
async def admin_kpi_dashboard(admin: dict = Depends(require_admin)):
    """Tableau de bord enrichi : UC en circulation, top produits, alertes, CA jour/mois."""
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    # UC en circulation
    pipeline = [{"$group": {"_id": None, "total_uc": {"$sum": "$balance_uc"}}}]
    uc_circ_doc = await db.lolodrive_wallets.aggregate(pipeline).to_list(1)
    uc_in_circulation = uc_circ_doc[0]["total_uc"] if uc_circ_doc else 0
    # UC consommées (DEBIT all-time)
    pipeline_consumed = [{"$match": {"type": "DEBIT"}}, {"$group": {"_id": None, "total": {"$sum": "$amount_uc"}}}]
    consumed_doc = await db.lolodrive_wallet_ledger.aggregate(pipeline_consumed).to_list(1)
    uc_consumed = consumed_doc[0]["total"] if consumed_doc else 0
    # CA jour & mois (statut PAID/PREPARING/READY/FULFILLED)
    paid_statuses = [OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.READY.value, OrderStatus.FULFILLED.value]
    ca_today = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": today}}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total_cents"}, "uc_orders": {"$sum": {"$cond": ["$pay_with_uc", 1, 0]}}}},
    ]).to_list(1)
    ca_today_data = ca_today[0] if ca_today else {"count": 0, "revenue": 0, "uc_orders": 0}
    ca_month = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total_cents"}}},
    ]).to_list(1)
    ca_month_data = ca_month[0] if ca_month else {"count": 0, "revenue": 0}
    # Top produits (30 derniers jours)
    from_30d = now - timedelta(days=30)
    top_products = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": from_30d}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.sku",
            "name": {"$first": "$items.name"},
            "qty": {"$sum": "$items.qty"},
            "revenue_cents": {"$sum": {"$multiply": ["$items.unit_cents", "$items.qty"]}},
            "catalog_type": {"$first": "$items.catalog_type"},
        }},
        {"$sort": {"qty": -1}},
        {"$limit": 5},
    ]).to_list(5)
    # Alertes
    alerts = []
    # PASS expirant J-3
    j3 = now + timedelta(days=3)
    pass_expiring = await db.lolodrive_passes.count_documents({"status": "ACTIVE", "ends_at": {"$lte": j3, "$gte": now}})
    if pass_expiring > 0:
        alerts.append({"severity": "warning", "icon": "alert-triangle", "message": f"{pass_expiring} PASS expirent dans moins de 3 jours"})
    # Commandes anciennes (PAID > 2h sans préparation)
    stale_paid = await db.lolodrive_orders.count_documents({"status": "PAID", "created_at": {"$lt": now - timedelta(hours=2)}})
    if stale_paid > 0:
        alerts.append({"severity": "critical", "icon": "clock", "message": f"{stale_paid} commande(s) payée(s) en attente >2h"})
    # Stock bas
    low_stock = await db.lolodrive_products.count_documents({"is_active": True, "stock_qty": {"$lt": 10}})
    if low_stock > 0:
        alerts.append({"severity": "warning", "icon": "package", "message": f"{low_stock} produit(s) avec stock < 10"})
    if not alerts:
        alerts.append({"severity": "ok", "icon": "check-circle", "message": "Aucune alerte. Tout est en ordre."})
    return {
        "uc_in_circulation": uc_in_circulation,
        "uc_consumed": uc_consumed,
        "ca_today": {"orders": ca_today_data["count"], "revenue_cents": ca_today_data["revenue"], "uc_orders": ca_today_data.get("uc_orders", 0)},
        "ca_month": {"orders": ca_month_data["count"], "revenue_cents": ca_month_data["revenue"]},
        "top_products": [{k: v for k, v in p.items() if k != "_id"} | {"sku": p["_id"]} for p in top_products],
        "alerts": alerts,
    }

# =======================
# LOLO POINTS cooperatifs
# =======================

@lolodrive_router.get("/lolo-points")
async def list_lolo_points(city: Optional[str] = None):
    query = {"status": "ACTIVE"}
    if city:
        query["city"] = city
    points = await db.lolodrive_points.find(query, {"_id": 0}).sort("name", 1).to_list(200)
    return {"points": points}

@lolodrive_router.post("/admin/lolo-points")
async def create_lolo_point(request: LoloPointCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "status": "ACTIVE", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    await db.lolodrive_points.insert_one(doc)
    doc.pop("_id", None)
    await emit_crm_event("lolo_point.created", doc)
    return doc

@lolodrive_router.post("/admin/lolo-points/{point_id}/contributions")
async def create_contribution(point_id: str, request: CoopContributionCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "lolo_point_id": point_id, "created_at": datetime.utcnow()})
    await db.lolodrive_contributions.insert_one(doc)
    doc.pop("_id", None)
    return doc

@lolodrive_router.post("/admin/lolo-points/{point_id}/payout-preview")
async def payout_preview(point_id: str, request: PayoutPreviewRequest, admin: dict = Depends(require_admin)):
    point = await db.lolodrive_points.find_one({"id": point_id})
    if not point:
        raise HTTPException(status_code=404, detail="Point introuvable")
    orders = await db.lolodrive_orders.find({
        "lolo_point_id": point_id,
        "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
        "created_at": {"$gte": request.from_date, "$lte": request.to_date},
    }).to_list(10000)

    volume = sum(o.get("subtotal_cents", 0) for o in orders)
    withdrawals = len(orders)
    pass_activations = await db.lolodrive_passes.count_documents({"source_lolo_point_id": point_id, "created_at": {"$gte": request.from_date, "$lte": request.to_date}})

    withdrawal_comm = withdrawals * point.get("withdrawal_commission_cents", 70)
    pass_comm = pass_activations * point.get("pass_activation_commission_cents", 400)
    volume_comm = round(volume * point.get("essential_volume_bps", 200) / 10000)
    calculated = withdrawal_comm + pass_comm + volume_comm
    percent_cap = round(volume * point.get("payout_cap_percent_bps", 600) / 10000)
    monthly_cap = point.get("payout_cap_cents_monthly", 120000)
    capped = min(calculated, percent_cap, monthly_cap)

    return {
        "point": {"id": point["id"], "name": point["name"], "code": point["code"]},
        "period": {"from": request.from_date, "to": request.to_date},
        "consumption_volume_cents": volume,
        "withdrawals": withdrawals,
        "pass_activations": pass_activations,
        "components": {"withdrawal_commission_cents": withdrawal_comm, "pass_commission_cents": pass_comm, "volume_commission_cents": volume_comm},
        "calculated_cents": calculated,
        "caps": {"percent_cap_cents": percent_cap, "monthly_cap_cents": monthly_cap},
        "capped_cents": capped,
    }

# =======================
# Events / partners / sponsors
# =======================

@lolodrive_router.get("/events/active")
async def active_events():
    now = datetime.utcnow()
    events = await db.lolodrive_events.find({"is_active": True, "ends_at": {"$gte": now}}, {"_id": 0}).sort("starts_at", 1).limit(100).to_list(100)
    return {"events": events}

@lolodrive_router.post("/admin/partners")
async def create_partner(request: PartnerCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "created_at": datetime.utcnow()})
    await db.lolodrive_partners.insert_one(doc)
    doc.pop("_id", None)
    await emit_crm_event("partner.created", doc)
    return doc

@lolodrive_router.post("/admin/events")
async def create_event(request: EventCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": datetime.utcnow()})
    await db.lolodrive_events.insert_one(doc)
    doc.pop("_id", None)
    await emit_crm_event("event.created", doc)
    return doc

# =======================
# Admin products / default seed
# =======================

@lolodrive_router.post("/admin/products")
async def admin_create_product(request: RegisterProduct, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    await db.lolodrive_products.update_one({"sku": doc["sku"]}, {"$set": doc}, upsert=True)
    return {k: v for k, v in doc.items() if k != "_id"}


# =======================
# DEMO simulators (no Stripe webhook required)
# =======================

@lolodrive_router.post("/demo/simulate-pass-activation")
async def demo_simulate_pass_activation(user: dict = Depends(get_current_user)):
    """DEMO ONLY: simulate webhook payment_intent.succeeded for PASS activation.
    Active le PASS pour l'utilisateur courant + crédite 600 UC sans passer par Stripe.
    Aucune valeur fiscale. À utiliser uniquement en mode démo/test.
    """
    user_id = user["id"]
    starts_at = datetime.utcnow()
    ends_at = starts_at + timedelta(days=PASS_DAYS)
    await db.lolodrive_passes.update_one(
        {"user_id": user_id},
        {"$set": {"status": "ACTIVE", "starts_at": starts_at, "ends_at": ends_at, "price_cents": PASS_PRICE_CENTS, "uc_granted": PASS_UC, "is_auto_renew": False, "demo_activation": True, "updated_at": datetime.utcnow()}, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    wallet = await get_or_create_wallet(user_id)
    await db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": PASS_UC}, "$set": {"updated_at": datetime.utcnow()}})
    await db.lolodrive_wallet_ledger.insert_one({"id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT", "amount_uc": PASS_UC, "reason": "PASS_ACTIVATION_DEMO", "created_at": datetime.utcnow()})
    await emit_crm_event("pass.activated", {"user_id": user_id, "pass_price_cents": PASS_PRICE_CENTS, "uc_granted": PASS_UC, "ends_at": ends_at, "demo": True})
    return {"ok": True, "ends_at": ends_at, "uc_granted": PASS_UC, "demo": True}


@lolodrive_router.post("/demo/simulate-order-payment/{order_id}")
async def demo_simulate_order_payment(order_id: str, user: dict = Depends(get_current_user)):
    """DEMO ONLY: passe une commande à PAID sans déclencher Stripe webhook."""
    order = await db.lolodrive_orders.find_one({"id": order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in [OrderStatus.DRAFT.value, OrderStatus.PENDING_PAYMENT.value]:
        raise HTTPException(status_code=400, detail="Commande non payable")
    await db.lolodrive_orders.update_one(
        {"id": order_id},
        {"$set": {"status": OrderStatus.PAID.value, "demo_paid": True, "updated_at": datetime.utcnow()}},
    )
    await emit_crm_event("order.paid", {"user_id": user["id"], "order_id": order_id, "demo": True})
    return {"ok": True, "order_id": order_id, "status": OrderStatus.PAID.value, "demo": True}


@lolodrive_router.get("/me/savings")
async def my_savings(user: dict = Depends(get_current_user)):
    """Calcule les économies réalisées par l'utilisateur grâce au PASS sur ses commandes ESSENTIELS."""
    orders = await db.lolodrive_orders.find({
        "user_id": user["id"],
        "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
    }).to_list(1000)
    skus = {it["sku"] for o in orders for it in (o.get("items") or [])}
    products = await db.lolodrive_products.find({"sku": {"$in": list(skus)}}, {"_id": 0}).to_list(1000)
    prices = {p["sku"]: p for p in products}
    savings = 0
    essential_items = 0
    for o in orders:
        for it in (o.get("items") or []):
            p = prices.get(it["sku"])
            if not p:
                continue
            if p.get("catalog_type") != "ESSENTIAL":
                continue
            pub = p.get("price_public_cents", 0)
            paid = it.get("unit_cents", pub)
            qty = it.get("qty", 1)
            diff = max(0, pub - paid) * qty
            savings += diff
            essential_items += qty
    return {"savings_cents": savings, "essential_items": essential_items, "orders_count": len(orders)}


@lolodrive_router.post("/admin/init-defaults")
async def init_defaults(admin: dict = Depends(require_admin)):
    """Initialise config, zones, produits exemples et indexes si nécessaire."""
    await ensure_lolodrive_indexes(db)
    await logistics_config()

    zones = [
        {"id": "zone-gt", "name": "Grande-Terre", "days": "MON,WED,FRI", "slots": [
            {"id": "gt-am", "label": "Matin 9h–12h30", "start": "09:00", "end": "12:30"},
            {"id": "gt-pm", "label": "Après-midi 14h–18h", "start": "14:00", "end": "18:00"},
        ]},
        {"id": "zone-bt", "name": "Basse-Terre", "days": "TUE,THU,FRI", "slots": [
            {"id": "bt-am", "label": "Matin 9h–12h30", "start": "09:00", "end": "12:30"},
            {"id": "bt-pm", "label": "Après-midi 14h–18h", "start": "14:00", "end": "18:00"},
        ]},
    ]
    for z in zones:
        await db.lolodrive_delivery_zones.update_one({"id": z["id"]}, {"$set": z}, upsert=True)

    products = [
        {"sku":"RIZ-5KG","name":"Riz long grain","category":"Épicerie","catalog_type":"ESSENTIAL","price_public_cents":650,"price_pass_cents":490},
        {"sku":"LAIT-1L","name":"Lait UHT","category":"Épicerie","brand":"Candia","catalog_type":"ESSENTIAL","price_public_cents":140,"price_pass_cents":110},
        {"sku":"HUILE-1L","name":"Huile végétale","category":"Épicerie","catalog_type":"ESSENTIAL","price_public_cents":450,"price_pass_cents":320},
        {"sku":"FARINE-1KG","name":"Farine de blé T45","category":"Épicerie","brand":"Francine","catalog_type":"ESSENTIAL","price_public_cents":200,"price_pass_cents":160},
        {"sku":"TOMACOULI-500G","name":"Tomacouli","category":"Cuisine","brand":"Panzani","catalog_type":"NORMAL","price_public_cents":220,"price_pass_cents":None},
    ]
    for p in products:
        p.update({"id": p.get("id") or str(uuid.uuid4()), "is_active": True, "updated_at": datetime.utcnow()})
        await db.lolodrive_products.update_one({"sku": p["sku"]}, {"$set": p, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)

    return {"ok": True, "message": "LOLODRIVE defaults initialized", "products": len(products), "zones": len(zones)}

# =======================
# KPI / reporting
# =======================

@lolodrive_router.get("/admin/kpi/overview")
async def kpi_overview(from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, admin: dict = Depends(require_admin)):
    f = from_date or (datetime.utcnow() - timedelta(days=30))
    t = to_date or datetime.utcnow()

    orders = await db.lolodrive_orders.find({"created_at": {"$gte": f, "$lte": t}, "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]}}).to_list(10000)
    pass_active = await db.lolodrive_passes.count_documents({"status": "ACTIVE", "ends_at": {"$gt": datetime.utcnow()}})
    points_active = await db.lolodrive_points.count_documents({"status": "ACTIVE"})
    events_active = await db.lolodrive_events.count_documents({"is_active": True, "ends_at": {"$gt": datetime.utcnow()}})
    wallet_debits = await db.lolodrive_wallet_ledger.aggregate([
        {"$match": {"created_at": {"$gte": f, "$lte": t}, "type": "DEBIT"}},
        {"$group": {"_id": None, "total_uc": {"$sum": "$amount_uc"}}},
    ]).to_list(1)

    return {
        "period": {"from": f, "to": t},
        "pass_active": pass_active,
        "orders": {
            "count": len(orders),
            "revenue_cents": sum(o.get("total_cents", 0) for o in orders),
            "drive": sum(1 for o in orders if o.get("fulfillment_type") == "DRIVE"),
            "delivery": sum(1 for o in orders if o.get("fulfillment_type") == "DELIVERY"),
            "lolo_point": sum(1 for o in orders if o.get("fulfillment_type") == "LOLO_POINT"),
            "paid_uc": sum(1 for o in orders if o.get("pay_with_uc")),
        },
        "wallet": {"debited_uc": wallet_debits[0]["total_uc"] if wallet_debits else 0},
        "lolo_points_active": points_active,
        "events_active": events_active,
    }

async def ensure_lolodrive_indexes(database):
    """Indexes essentiels pour performance et anti-scans sur collections LOLODRIVE."""
    await database.lolodrive_passes.create_index("user_id", unique=True)
    await database.lolodrive_passes.create_index([("status", 1), ("ends_at", -1)])
    await database.lolodrive_wallets.create_index("user_id", unique=True)
    await database.lolodrive_wallet_ledger.create_index([("wallet_id", 1), ("created_at", -1)])
    await database.lolodrive_products.create_index("sku", unique=True)
    await database.lolodrive_products.create_index([("catalog_type", 1), ("is_active", 1)])
    await database.lolodrive_products.create_index([("name", "text"), ("brand", "text"), ("category", "text")])
    await database.lolodrive_orders.create_index("id", unique=True)
    await database.lolodrive_orders.create_index([("user_id", 1), ("created_at", -1)])
    await database.lolodrive_orders.create_index([("lolo_point_id", 1), ("status", 1), ("created_at", -1)])
    await database.lolodrive_orders.create_index([("status", 1), ("created_at", -1)])
    await database.lolodrive_points.create_index("code", unique=True)
    await database.lolodrive_points.create_index([("status", 1), ("city", 1)])
    await database.lolodrive_events.create_index([("is_active", 1), ("starts_at", 1), ("ends_at", 1)])
    await database.lolodrive_partners.create_index("name")
    await database.lolodrive_payments.create_index("stripe_payment_intent_id", unique=True)
    await database.lolodrive_payments.create_index([("user_id", 1), ("created_at", -1)])
