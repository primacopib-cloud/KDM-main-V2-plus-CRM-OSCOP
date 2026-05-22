"""
Stripe Checkout (hosted) for LOLODRIVE flows.
Uses emergentintegrations.payments.stripe.checkout for PASS, recharge UC, and order payments.

Security:
- Amounts are FIXED on backend (PASS=60€, packs RECHARGE, order = order.total_cents)
- Frontend only sends origin_url
- payment_transactions collection tracks status (idempotent webhook + polling)
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user_id
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)
from brevo_service import notify_pass_activated

logger = logging.getLogger(__name__)

checkout_router = APIRouter(prefix="/api/lolodrive/checkout", tags=["LOLODRIVE Stripe Checkout"])
webhook_router = APIRouter(tags=["Stripe Webhook"])

db = None
PASS_PRICE_EUR = 60.0
PASS_DAYS = 30
PASS_UC = 600
RECHARGE_PACKS = {
    "MINI": {"amount_eur": 20.0, "uc": 200},
    "STANDARD": {"amount_eur": 40.0, "uc": 400},
    "MAXI": {"amount_eur": 70.0, "uc": 720},
}


def set_checkout_database(database):
    global db
    db = database


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


def _stripe_api_key() -> Optional[str]:
    """Returns the active Stripe API key based on STRIPE_MODE.

    STRIPE_MODE=live → uses STRIPE_LIVE_KEY (real charges).
    Anything else (test, unset, ...) → uses STRIPE_API_KEY (test/sandbox).
    """
    mode = (os.environ.get("STRIPE_MODE") or "test").strip().lower()
    if mode == "live":
        return os.environ.get("STRIPE_LIVE_KEY") or os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    return os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")


def _stripe_client(http_request: Request) -> StripeCheckout:
    api_key = _stripe_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


def _build_urls(origin_url: str, kind: str, ref: str = "") -> Dict[str, str]:
    origin = origin_url.rstrip("/")
    return {
        "success_url": f"{origin}/paiement/retour?session_id={{CHECKOUT_SESSION_ID}}&kind={kind}&ref={ref}",
        "cancel_url": f"{origin}/paiement/annule?kind={kind}&ref={ref}",
    }


class OriginPayload(BaseModel):
    origin_url: str


class RechargePayload(BaseModel):
    origin_url: str
    pack: str  # MINI/STANDARD/MAXI


class OrderPayload(BaseModel):
    origin_url: str
    order_id: str


# ====================== PASS ACTIVATION ======================

@checkout_router.post("/pass-session")
async def create_pass_session(payload: OriginPayload, http_request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for PASS Vie Chère 60€."""
    sc = _stripe_client(http_request)
    urls = _build_urls(payload.origin_url, "PASS", user["id"])
    metadata = {"kind": "PASS", "user_id": user["id"]}
    req = CheckoutSessionRequest(
        amount=PASS_PRICE_EUR,
        currency="eur",
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
    )
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "kind": "PASS",
        "amount_cents": int(PASS_PRICE_EUR * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return {"url": session.url, "session_id": session.session_id}


@checkout_router.post("/recharge-session")
async def create_recharge_session(payload: RechargePayload, http_request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for UC recharge pack."""
    pack = RECHARGE_PACKS.get(payload.pack)
    if not pack:
        raise HTTPException(status_code=400, detail="Pack invalide")
    # Check PASS active
    pass_doc = await db.lolodrive_passes.find_one({"user_id": user["id"], "status": "ACTIVE"})
    if not pass_doc or pass_doc.get("ends_at") < datetime.utcnow():
        raise HTTPException(status_code=400, detail="PASS inactif : activation requise")
    sc = _stripe_client(http_request)
    urls = _build_urls(payload.origin_url, "RECHARGE", user["id"])
    metadata = {"kind": "RECHARGE", "user_id": user["id"], "pack": payload.pack, "uc": str(pack["uc"])}
    req = CheckoutSessionRequest(
        amount=pack["amount_eur"],
        currency="eur",
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
    )
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "kind": "RECHARGE",
        "amount_cents": int(pack["amount_eur"] * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return {"url": session.url, "session_id": session.session_id, "pack": payload.pack}


@checkout_router.post("/order-session")
async def create_order_session(payload: OrderPayload, http_request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for an existing order."""
    order = await db.lolodrive_orders.find_one({"id": payload.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in ["DRAFT", "PENDING_PAYMENT"]:
        raise HTTPException(status_code=400, detail="Commande non payable")
    amount_eur = order["total_cents"] / 100.0
    sc = _stripe_client(http_request)
    urls = _build_urls(payload.origin_url, "ORDER", order["id"])
    metadata = {"kind": "ORDER", "user_id": user["id"], "order_id": order["id"]}
    req = CheckoutSessionRequest(
        amount=amount_eur,
        currency="eur",
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
    )
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "kind": "ORDER",
        "amount_cents": order["total_cents"],
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    await db.lolodrive_orders.update_one({"id": order["id"]}, {"$set": {"status": "PENDING_PAYMENT", "stripe_checkout_session_id": session.session_id, "updated_at": datetime.utcnow()}})
    return {"url": session.url, "session_id": session.session_id, "amount_cents": order["total_cents"]}


# ====================== STATUS (polling) ======================

@checkout_router.get("/status/{session_id}")
async def checkout_status(session_id: str, http_request: Request, user: dict = Depends(get_current_user)):
    """Poll Stripe Checkout session status and apply business logic if paid (idempotent)."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if tx["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    sc = _stripe_client(http_request)
    status = await sc.get_checkout_status(session_id)
    new_payment_status = status.payment_status
    # Update tx
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": new_payment_status, "updated_at": datetime.utcnow()}},
    )
    # Apply business logic ONCE (idempotent)
    if new_payment_status == "paid" and not tx.get("applied"):
        await _apply_payment_success(tx)
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"applied": True}})
    return {
        "session_id": session_id,
        "status": status.status,
        "payment_status": new_payment_status,
        "amount_total": getattr(status, "amount_total", tx.get("amount_cents")),
        "currency": getattr(status, "currency", tx.get("currency", "eur")),
        "kind": tx["kind"],
        "applied": tx.get("applied") or new_payment_status == "paid",
    }


# ====================== WEBHOOK ======================

@webhook_router.post("/api/webhook/stripe")
async def stripe_webhook(http_request: Request):
    """Stripe webhook endpoint. Applies business logic idempotently."""
    body = await http_request.body()
    signature = http_request.headers.get("Stripe-Signature", "")
    sc = _stripe_client(http_request)
    try:
        evt = await sc.handle_webhook(body, signature)
    except Exception as e:
        logger.warning(f"Stripe webhook invalid: {e}")
        raise HTTPException(status_code=400, detail="Webhook invalide")

    if evt.payment_status == "paid" and evt.session_id:
        tx = await db.payment_transactions.find_one({"session_id": evt.session_id})
        if tx and not tx.get("applied"):
            await _apply_payment_success(tx)
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"applied": True, "payment_status": "paid", "updated_at": datetime.utcnow()}},
            )
    return {"received": True}


# ====================== APPLY LOGIC ======================

async def _apply_payment_success(tx: dict):
    """Apply business effects when a checkout session is paid. Must be idempotent (called by polling and webhook)."""
    kind = tx["kind"]
    user_id = tx["user_id"]
    now = datetime.utcnow()

    if kind == "PASS":
        # Activate PASS + credit 600 UC
        starts_at = now
        ends_at = starts_at + timedelta(days=PASS_DAYS)
        await db.lolodrive_passes.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "status": "ACTIVE",
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "price_cents": int(PASS_PRICE_EUR * 100),
                    "uc_granted": PASS_UC,
                    "is_auto_renew": False,
                    "stripe_session_id": tx["session_id"],
                    "updated_at": now,
                },
                "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now},
            },
            upsert=True,
        )
        wallet = await _get_or_create_wallet(user_id)
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]},
            {"$inc": {"balance_uc": PASS_UC}, "$set": {"updated_at": now}},
        )
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
            "amount_uc": PASS_UC, "reason": "PASS_ACTIVATION",
            "stripe_session_id": tx["session_id"], "created_at": now,
        })
        await _emit_crm_event("pass.activated", {"user_id": user_id, "pass_price_cents": int(PASS_PRICE_EUR * 100), "uc_granted": PASS_UC, "ends_at": ends_at})
        # Brevo email + SMS (best-effort)
        try:
            user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
            if user_doc and user_doc.get("email"):
                pass_doc = await db.lolodrive_passes.find_one({"user_id": user_id}, {"_id": 0, "id": 1})
                await notify_pass_activated(
                    to_email=user_doc["email"],
                    to_name=user_doc.get("contact_name"),
                    to_phone=user_doc.get("phone"),
                    pass_id=(pass_doc or {}).get("id", "PASS"),
                    uc_granted=PASS_UC,
                    ends_at=ends_at,
                )
        except Exception as exc:
            logger.warning(f"Brevo PASS notification failed: {exc}")

    elif kind == "RECHARGE":
        pack_key = tx["metadata"].get("pack")
        pack = RECHARGE_PACKS.get(pack_key)
        if not pack:
            logger.warning(f"Recharge: pack inconnu {pack_key}")
            return
        wallet = await _get_or_create_wallet(user_id)
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]},
            {"$inc": {"balance_uc": pack["uc"]}, "$set": {"updated_at": now}},
        )
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
            "amount_uc": pack["uc"], "reason": "RECHARGE",
            "stripe_session_id": tx["session_id"], "created_at": now,
        })

    elif kind == "ORDER":
        order_id = tx["metadata"].get("order_id")
        if not order_id:
            return
        await db.lolodrive_orders.update_one(
            {"id": order_id},
            {"$set": {"status": "PAID", "stripe_session_id": tx["session_id"], "paid_at": now, "updated_at": now}},
        )
        await _emit_crm_event("order.paid", {"user_id": user_id, "order_id": order_id})
        # Best-effort POS broadcast
        try:
            from routes_websockets import manager
            await manager.broadcast_to_admins({
                "type": "lolodrive_pos_event",
                "payload": {"event": "order.paid", "data": {"order_id": order_id}, "timestamp": now.isoformat()},
            })
        except Exception:
            pass


async def _get_or_create_wallet(user_id: str) -> dict:
    w = await db.lolodrive_wallets.find_one({"user_id": user_id})
    if w:
        return w
    w = {"id": str(uuid.uuid4()), "user_id": user_id, "balance_uc": 0, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    await db.lolodrive_wallets.insert_one(w)
    return w


async def _emit_crm_event(event_type: str, payload: dict):
    try:
        from routes_crm_oscoop import crm_record_event
        await crm_record_event(db, event_type, payload)
    except Exception as e:
        logger.warning(f"CRM sync skipped for {event_type}: {e}")


async def setup_checkout_indexes(database):
    await database.payment_transactions.create_index("session_id", unique=True)
    await database.payment_transactions.create_index([("user_id", 1), ("created_at", -1)])
    await database.payment_transactions.create_index("payment_status")
