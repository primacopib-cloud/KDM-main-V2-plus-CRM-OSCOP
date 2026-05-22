"""
Stripe Subscriptions natives — true automatic recurring billing for the PASS.

Why a dedicated module : `emergentintegrations.payments.stripe.checkout` is a
one-shot Checkout flow. For real automatic rebill (no email link click required)
we use the Stripe SDK directly with `mode='subscription'` + Subscription Schedule
+ webhook listeners.

Workflow :
  1. User opts into auto-renew → POST /api/lolodrive/pass/subscription/checkout
  2. Backend creates a Stripe Subscription Checkout session (60 € / 12 months).
  3. Stripe runs the subscription; we listen to `customer.subscription.updated`
     and `invoice.paid` to extend the PASS automatically each cycle.
  4. User can cancel at portal → POST /api/lolodrive/pass/subscription/cancel.

The legacy "soft" auto-renew (one-time Checkout link via email) remains as a
fallback for users who don't want a recurring agreement.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lolodrive/pass/subscription", tags=["PASS Subscription"])

PASS_PRICE_EUR = 60.0
PASS_PERIOD_DAYS = 365
PASS_UC_PER_PERIOD = 600

db = None


def set_pass_subscription_database(database):
    global db
    db = database


def _stripe_key() -> Optional[str]:
    mode = (os.environ.get("STRIPE_MODE") or "test").strip().lower()
    if mode == "live":
        return os.environ.get("STRIPE_LIVE_KEY") or os.environ.get("STRIPE_API_KEY")
    return os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")


def _public_origin() -> str:
    return (
        os.environ.get("KDM_PUBLIC_ORIGIN")
        or os.environ.get("FRONTEND_URL")
        or "https://coop-dashboard-8.preview.emergentagent.com"
    ).rstrip("/")


async def _resolve_or_create_stripe_customer(user: dict) -> str:
    """Return Stripe customer id, creating it if missing."""
    if user.get("stripe_customer_id"):
        return user["stripe_customer_id"]
    stripe.api_key = _stripe_key()
    customer = stripe.Customer.create(
        email=user.get("email"),
        name=user.get("contact_name"),
        metadata={"user_id": user["id"]},
    )
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"stripe_customer_id": customer.id, "updated_at": datetime.now(timezone.utc)}},
    )
    return customer.id


async def _resolve_or_create_pass_price() -> str:
    """Return a Stripe Price id for the PASS subscription. Creates Product+Price on first run."""
    stripe.api_key = _stripe_key()
    cfg = await db.app_settings.find_one({"_id": "pass_subscription"}) or {}
    price_id = cfg.get("price_id")
    if price_id:
        try:
            stripe.Price.retrieve(price_id)
            return price_id
        except stripe.error.InvalidRequestError:
            logger.warning("Stored PASS Price %s not found in Stripe — recreating", price_id)
    # Create
    product = stripe.Product.create(
        name="PASS Vie Chère KDMARCHÉ x O'SCOP",
        description="Abonnement annuel coopératif — 600 UC + accès aux essentiels",
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=int(PASS_PRICE_EUR * 100),
        currency="eur",
        recurring={"interval": "year"},
    )
    await db.app_settings.update_one(
        {"_id": "pass_subscription"},
        {"$set": {
            "_id": "pass_subscription",
            "product_id": product.id,
            "price_id": price.id,
            "amount_cents": int(PASS_PRICE_EUR * 100),
            "currency": "eur",
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return price.id


# =======================
# Endpoints
# =======================

class StartSubscriptionIn(BaseModel):
    success_path: str = "/paiement/retour"
    cancel_path: str = "/pass"


@router.post("/checkout")
async def start_subscription(payload: StartSubscriptionIn, user_id: str = Depends(get_current_user_id)):
    """Create a Stripe Subscription Checkout session for the PASS."""
    if not _stripe_key():
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.pop("_id", None)

    stripe.api_key = _stripe_key()
    try:
        customer_id = await _resolve_or_create_stripe_customer(user)
        price_id = await _resolve_or_create_pass_price()
        origin = _public_origin()
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{origin}{payload.success_path}?session_id={{CHECKOUT_SESSION_ID}}&kind=PASS_SUBSCRIPTION",
            cancel_url=f"{origin}{payload.cancel_path}?canceled=1",
            metadata={"kind": "PASS_SUBSCRIPTION", "user_id": user_id},
            subscription_data={"metadata": {"user_id": user_id}},
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe Subscription session error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(exc)[:200]}")

    now = datetime.now(timezone.utc)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.id,
        "user_id": user_id,
        "kind": "PASS_SUBSCRIPTION",
        "amount_cents": int(PASS_PRICE_EUR * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "stripe_customer_id": customer_id,
        "metadata": {"kind": "PASS_SUBSCRIPTION", "user_id": user_id},
        "created_at": now,
        "updated_at": now,
    })
    return {"url": session.url, "session_id": session.id}


@router.post("/cancel")
async def cancel_subscription(user_id: str = Depends(get_current_user_id)):
    """Cancel the user's active PASS subscription at the end of the current period."""
    if not _stripe_key():
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    pass_doc = await db.lolodrive_passes.find_one({"user_id": user_id, "status": "ACTIVE"}, {"_id": 0})
    sub_id = (pass_doc or {}).get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=404, detail="Aucun abonnement Stripe actif")
    stripe.api_key = _stripe_key()
    try:
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(exc)[:200]}")
    await db.lolodrive_passes.update_one(
        {"id": pass_doc["id"]},
        {"$set": {"is_auto_renew": False, "subscription_cancel_at_period_end": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True, "cancel_at_period_end": True}


@router.get("/status")
async def subscription_status(user_id: str = Depends(get_current_user_id)):
    pass_doc = await db.lolodrive_passes.find_one({"user_id": user_id}, {"_id": 0})
    if not pass_doc:
        return {"has_subscription": False}
    sub_id = pass_doc.get("stripe_subscription_id")
    if not sub_id:
        return {
            "has_subscription": False,
            "is_auto_renew_soft": pass_doc.get("is_auto_renew", False),
        }
    return {
        "has_subscription": True,
        "stripe_subscription_id": sub_id,
        "cancel_at_period_end": pass_doc.get("subscription_cancel_at_period_end", False),
        "current_period_end": pass_doc.get("ends_at"),
    }


# =======================
# Stripe webhook handler — extends PASS on each successful invoice
# =======================

@router.post("/webhook")
async def stripe_subscription_webhook(request: Request):
    """Stripe webhook for subscription events (invoice.paid, customer.subscription.updated, .deleted).

    Idempotent: each invoice id is processed at most once via `lolodrive_subscription_events.invoice_id` unique.
    """
    if not _stripe_key():
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    stripe.api_key = _stripe_key()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

    # We support both signed (prod) and unsigned (test) modes.
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            import json as _json
            event = _json.loads(payload.decode("utf-8"))
    except Exception as exc:
        logger.warning("Subscription webhook parse failed: %s", exc)
        raise HTTPException(status_code=400, detail="invalid webhook payload")

    etype = event.get("type") if isinstance(event, dict) else event["type"]
    obj = (event.get("data") or {}).get("object") if isinstance(event, dict) else event["data"]["object"]
    if not etype or not obj:
        return {"ok": False, "reason": "missing fields"}

    now = datetime.now(timezone.utc)

    if etype == "invoice.paid":
        invoice_id = obj.get("id")
        sub_id = obj.get("subscription")
        customer_id = obj.get("customer")
        # Idempotency
        try:
            await db.lolodrive_subscription_events.insert_one({
                "id": str(uuid.uuid4()),
                "type": etype,
                "invoice_id": invoice_id,
                "subscription_id": sub_id,
                "customer_id": customer_id,
                "received_at": now,
            })
        except Exception:
            return {"ok": True, "duplicate": True}
        # Locate the user
        user = await db.users.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
        if not user:
            sub = stripe.Subscription.retrieve(sub_id)
            uid = (sub.get("metadata") or {}).get("user_id")
            user = await db.users.find_one({"id": uid}, {"_id": 0}) if uid else None
        if not user:
            logger.warning("invoice.paid: no user for sub %s / customer %s", sub_id, customer_id)
            return {"ok": False, "reason": "user not found"}
        # Extend PASS by 365 days
        existing = await db.lolodrive_passes.find_one({"user_id": user["id"]})
        if existing:
            current_end = existing.get("ends_at") or now.replace(tzinfo=None)
            if isinstance(current_end, datetime) and current_end.tzinfo is None:
                base = max(current_end, datetime.utcnow())
            else:
                base = max(current_end.replace(tzinfo=None) if isinstance(current_end, datetime) else datetime.utcnow(), datetime.utcnow())
            new_end = base + timedelta(days=PASS_PERIOD_DAYS)
            await db.lolodrive_passes.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "status": "ACTIVE",
                    "ends_at": new_end,
                    "stripe_subscription_id": sub_id,
                    "is_auto_renew": True,
                    "updated_at": now,
                }},
            )
        else:
            new_end = datetime.utcnow() + timedelta(days=PASS_PERIOD_DAYS)
            await db.lolodrive_passes.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "status": "ACTIVE",
                "starts_at": datetime.utcnow(),
                "ends_at": new_end,
                "stripe_subscription_id": sub_id,
                "is_auto_renew": True,
                "created_at": now,
                "updated_at": now,
            })
        # Credit wallet 600 UC (cycle)
        wallet = await db.lolodrive_wallets.find_one({"user_id": user["id"]})
        if wallet:
            await db.lolodrive_wallets.update_one(
                {"id": wallet["id"]},
                {"$inc": {"balance_uc": PASS_UC_PER_PERIOD}, "$set": {"updated_at": now}},
            )
            await db.lolodrive_wallet_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "wallet_id": wallet["id"],
                "type": "CREDIT",
                "amount_uc": PASS_UC_PER_PERIOD,
                "reason": "PASS_SUBSCRIPTION_CYCLE",
                "ref_id": invoice_id,
                "created_at": now,
            })
        return {"ok": True, "extended": True, "new_ends_at": new_end.isoformat()}

    if etype == "customer.subscription.deleted":
        sub_id = obj.get("id")
        await db.lolodrive_passes.update_many(
            {"stripe_subscription_id": sub_id},
            {"$set": {"is_auto_renew": False, "subscription_active": False, "updated_at": now}},
        )
        return {"ok": True, "subscription_deleted": True}

    # Other events ignored but logged
    return {"ok": True, "event_type": etype, "ignored": True}


async def setup_pass_subscription_indexes(database):
    await database.lolodrive_subscription_events.create_index("invoice_id", unique=True, sparse=True)
    await database.lolodrive_subscription_events.create_index([("received_at", -1)])
    try:
        await database.users.create_index("stripe_customer_id", sparse=True)
    except Exception:
        pass
    try:
        await database.lolodrive_passes.create_index("stripe_subscription_id", sparse=True)
    except Exception:
        pass
