"""LOLODRIVE by O'SCOP — Admin (partners, events, products, demo, KPI, notifications) routes (split from routes_lolodrive_oscoop.py)."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import uuid
import logging
import stripe

from brevo_service import notify_pass_expiry_j3
from lolodrive_models import (
    PASS_PRICE_CENTS, PASS_UC, PASS_DAYS, RECHARGE_PACKS,
    RegisterProduct, PartnerCreate, EventCreate, OrderStatus,
)
from lolodrive_helpers import (
    get_current_user, require_admin, get_or_create_wallet, logistics_config, emit_crm_event,
)

logger = logging.getLogger(__name__)

lolodrive_admin_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_admin_database(database):
    global db
    db = database


@lolodrive_admin_router.post("/admin/partners")
async def create_partner(request: PartnerCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "created_at": datetime.utcnow()})
    await db.lolodrive_partners.insert_one(doc)
    doc.pop("_id", None)
    await emit_crm_event("partner.created", doc)
    return doc

@lolodrive_admin_router.post("/admin/events")
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

@lolodrive_admin_router.post("/admin/products")
async def admin_create_product(request: RegisterProduct, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    await db.lolodrive_products.update_one({"sku": doc["sku"]}, {"$set": doc}, upsert=True)
    return {k: v for k, v in doc.items() if k != "_id"}


# =======================
# DEMO simulators (no Stripe webhook required)
# =======================

@lolodrive_admin_router.post("/demo/simulate-pass-activation")
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


@lolodrive_admin_router.post("/demo/simulate-order-payment/{order_id}")
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


@lolodrive_admin_router.get("/me/savings")
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


@lolodrive_admin_router.post("/admin/init-defaults")
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

@lolodrive_admin_router.get("/admin/kpi/overview")
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

# =======================
# Notifications Brevo (Email + SMS)
# =======================

@lolodrive_admin_router.post("/admin/notifications/pass-expiry-j3")
async def notify_pass_expiry_j3_batch(admin: dict = Depends(require_admin)):
    """Envoie un email + SMS de rappel J-3 à tous les titulaires de PASS qui expirent dans ~3 jours.
    Idempotent par jour : on ne renvoie qu'une fois par PASS via le marqueur `j3_notified_at`.
    """
    now = datetime.utcnow()
    window_start = now + timedelta(days=2, hours=12)
    window_end = now + timedelta(days=3, hours=12)
    cursor = db.lolodrive_passes.find({
        "status": "ACTIVE",
        "ends_at": {"$gte": window_start, "$lte": window_end},
        "$or": [{"j3_notified_at": {"$exists": False}}, {"j3_notified_at": None}],
    }, {"_id": 0})
    sent = 0
    failed = 0
    async for p in cursor:
        user = await db.users.find_one({"id": p["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        if not user or not user.get("email"):
            continue
        try:
            await notify_pass_expiry_j3(
                to_email=user["email"],
                to_name=user.get("contact_name"),
                to_phone=user.get("phone"),
                pass_id=p.get("id", "PASS"),
                ends_at=p["ends_at"],
            )
            await db.lolodrive_passes.update_one(
                {"id": p["id"]}, {"$set": {"j3_notified_at": now, "updated_at": now}}
            )
            sent += 1
        except Exception as exc:
            logger.warning(f"PASS expiry J-3 notification failed for {user.get('email')}: {exc}")
            failed += 1
    return {"ok": True, "sent": sent, "failed": failed, "window": {"from": window_start, "to": window_end}}


@lolodrive_admin_router.post("/admin/notifications/test")
async def admin_notifications_test(admin: dict = Depends(require_admin)):
    """Envoie une notification test (email + SMS) à l'admin courant pour vérifier la config Brevo."""
    from brevo_service import notify_pass_activated as _notify
    res = await _notify(
        to_email=admin.get("email"),
        to_name=admin.get("contact_name"),
        to_phone=admin.get("phone"),
        pass_id="TEST-" + datetime.utcnow().strftime("%H%M%S"),
        uc_granted=600,
        ends_at=datetime.utcnow() + timedelta(days=30),
    )
    return {"ok": True, "result": res}


@lolodrive_admin_router.post("/admin/notifications/auto-renew-batch")
async def admin_run_auto_renew_batch(admin: dict = Depends(require_admin)):
    """Force-run the soft auto-renew batch (Stripe link + Brevo email/SMS) for testing/ops."""
    from pass_auto_renew import run_auto_renew_batch
    return await run_auto_renew_batch(db)


@lolodrive_admin_router.get("/admin/stripe/mode")
async def admin_stripe_mode(admin: dict = Depends(require_admin)):
    """Returns the active Stripe mode (test|live). Critical info for ops dashboard.

    To switch to live charges: set STRIPE_MODE=live in /app/backend/.env then restart.
    """
    import os as _os
    mode = (_os.environ.get("STRIPE_MODE") or "test").strip().lower()
    test_key = _os.environ.get("STRIPE_API_KEY", "")
    live_key = _os.environ.get("STRIPE_LIVE_KEY", "")
    return {
        "mode": mode,
        "active_key_prefix": (live_key if mode == "live" else test_key)[:12] + "…" if (live_key if mode == "live" else test_key) else None,
        "live_key_configured": bool(live_key),
        "warning": "MODE LIVE: charges réelles" if mode == "live" else "Mode test/sandbox — aucune charge réelle",
    }


async def ensure_lolodrive_indexes(database):
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
    await database.lolodrive_reservations.create_index([("event_id", 1), ("status", 1)])
    await database.lolodrive_reservations.create_index([("user_id", 1), ("event_id", 1)])
