"""
Stripe Checkout (hosted) for LOLODRIVE flows — Multi-account.

Two Stripe accounts coexist on this platform:
  • O'SCOP OUTREMER (account="oscop") → PASS / RECHARGE / SUBSCRIPTION
  • KDMARCHE        (account="kdmarche") → ORDER (DRIVE)

We deliberately use the official `stripe` SDK directly (no
`emergentintegrations.payments.stripe.checkout` wrapper) so that real test/live
sessions are created on Stripe's real `api.stripe.com` endpoint — the Emergent
integration proxy was unexpectedly intercepting the call chain and returning
stub URLs (`https://checkout.stripe.test/...`) which cannot be opened in a
browser to validate a real payment flow.

Security:
- Amounts are FIXED on backend (PASS=60€, packs RECHARGE, order = order.total_cents)
- Frontend only sends origin_url
- payment_transactions collection tracks status (idempotent webhook + polling)
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user_id
from brevo_service import notify_pass_activated
from stripe_accounts import (
    AccountName,
    get_account_for_checkout_kind,
    get_stripe_key,
)

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

# Webhook signing secrets (configure when configuring webhooks in each Stripe
# dashboard). Each entry is a comma-separated list — useful when you have one
# secret per mode (TEST + LIVE) on the same Stripe account.
# When None, signature is NOT verified — fine for TEST development but MUST
# be set in production.
_WEBHOOK_SECRETS_ENV = {
    "oscop": "STRIPE_WEBHOOK_SECRETS_OSCOP",
    "kdmarche": "STRIPE_WEBHOOK_SECRETS_KDMARCHE",
}


def _webhook_secrets_for(account: str) -> list:
    """Return the list of webhook signing secrets configured for an account."""
    raw = os.environ.get(_WEBHOOK_SECRETS_ENV.get(account, ""), "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def set_checkout_database(database):
    global db
    db = database


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


def _api_key_for(account: AccountName) -> str:
    api_key = get_stripe_key(account)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe non configuré (account={account})",
        )
    return api_key


def _build_urls(origin_url: str, kind: str, ref: str = "") -> Dict[str, str]:
    origin = origin_url.rstrip("/")
    return {
        "success_url": f"{origin}/paiement/retour?session_id={{CHECKOUT_SESSION_ID}}&kind={kind}&ref={ref}",
        "cancel_url": f"{origin}/paiement/annule?kind={kind}&ref={ref}",
    }


def _create_checkout_session(
    account: AccountName,
    amount_eur: float,
    success_url: str,
    cancel_url: str,
    metadata: Dict[str, str],
    product_name: str,
) -> Dict[str, Any]:
    """Create a Stripe Checkout Session using the official SDK with the per-account key."""
    api_key = _api_key_for(account)
    # Reset api_base to the real Stripe endpoint — the emergentintegrations wrapper
    # may have pinned `stripe.api_base` to its proxy via a side-effect during startup.
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=api_key,
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": product_name},
                    "unit_amount": int(round(amount_eur * 100)),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    return {"id": session.id, "url": session.url}


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
    """Create Stripe Checkout session for PASS Vie Chère 60€ (O'SCOP account)."""
    account: AccountName = get_account_for_checkout_kind("PASS")
    urls = _build_urls(payload.origin_url, "PASS", user["id"])
    metadata = {"kind": "PASS", "user_id": user["id"], "stripe_account": account}
    session = _create_checkout_session(
        account=account,
        amount_eur=PASS_PRICE_EUR,
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
        product_name="KDMARCHÉ x O'SCOP — PASS Vie Chère",
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session["id"],
        "user_id": user["id"],
        "kind": "PASS",
        "stripe_account": account,
        "amount_cents": int(PASS_PRICE_EUR * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return {"url": session["url"], "session_id": session["id"], "stripe_account": account}


@checkout_router.post("/recharge-session")
async def create_recharge_session(payload: RechargePayload, http_request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for UC recharge pack (O'SCOP account)."""
    pack = RECHARGE_PACKS.get(payload.pack)
    if not pack:
        raise HTTPException(status_code=400, detail="Pack invalide")
    # Check PASS active — handle both naive and aware datetimes coming from Mongo
    pass_doc = await db.lolodrive_passes.find_one({"user_id": user["id"], "status": "ACTIVE"})
    if not pass_doc:
        raise HTTPException(status_code=400, detail="PASS inactif : activation requise")
    ends_at = pass_doc.get("ends_at")
    if ends_at is not None:
        ends_at_naive = ends_at.replace(tzinfo=None) if getattr(ends_at, "tzinfo", None) else ends_at
        if ends_at_naive < datetime.utcnow():
            raise HTTPException(status_code=400, detail="PASS inactif : activation requise")
    account: AccountName = get_account_for_checkout_kind("RECHARGE")
    urls = _build_urls(payload.origin_url, "RECHARGE", user["id"])
    metadata = {"kind": "RECHARGE", "user_id": user["id"], "pack": payload.pack, "uc": str(pack["uc"]), "stripe_account": account}
    session = _create_checkout_session(
        account=account,
        amount_eur=pack["amount_eur"],
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
        product_name=f"Recharge UC — Pack {payload.pack}",
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session["id"],
        "user_id": user["id"],
        "kind": "RECHARGE",
        "stripe_account": account,
        "amount_cents": int(pack["amount_eur"] * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return {"url": session["url"], "session_id": session["id"], "pack": payload.pack, "stripe_account": account}


@checkout_router.post("/order-session")
async def create_order_session(payload: OrderPayload, http_request: Request, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session for an existing order (KDMARCHE account)."""
    order = await db.lolodrive_orders.find_one({"id": payload.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in ["DRAFT", "PENDING_PAYMENT"]:
        raise HTTPException(status_code=400, detail="Commande non payable")
    amount_eur = order["total_cents"] / 100.0
    account: AccountName = get_account_for_checkout_kind("ORDER")
    urls = _build_urls(payload.origin_url, "ORDER", order["id"])
    metadata = {"kind": "ORDER", "user_id": user["id"], "order_id": order["id"], "stripe_account": account}
    session = _create_checkout_session(
        account=account,
        amount_eur=amount_eur,
        success_url=urls["success_url"],
        cancel_url=urls["cancel_url"],
        metadata=metadata,
        product_name=f"KDMARCHÉ — Commande #{order['id'][:8]}",
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session["id"],
        "user_id": user["id"],
        "kind": "ORDER",
        "stripe_account": account,
        "amount_cents": order["total_cents"],
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    await db.lolodrive_orders.update_one(
        {"id": order["id"]},
        {"$set": {
            "status": "PENDING_PAYMENT",
            "stripe_checkout_session_id": session["id"],
            "stripe_account": account,
            "updated_at": datetime.utcnow(),
        }},
    )
    return {"url": session["url"], "session_id": session["id"], "amount_cents": order["total_cents"], "stripe_account": account}


# ====================== STATUS (polling) ======================

@checkout_router.get("/status/{session_id}")
async def checkout_status(session_id: str, http_request: Request, user: dict = Depends(get_current_user)):
    """Poll Stripe Checkout session status and apply business logic if paid (idempotent)."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if tx["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    account: AccountName = tx.get("stripe_account") or get_account_for_checkout_kind(tx.get("kind", ""))
    api_key = _api_key_for(account)
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.retrieve(session_id, api_key=api_key)
    new_payment_status = session.payment_status
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": new_payment_status, "updated_at": datetime.utcnow()}},
    )
    if new_payment_status == "paid":
        claim = await db.payment_transactions.update_one(
            {"session_id": session_id, "applied": {"$ne": True}},
            {"$set": {"applied": True, "applied_at": datetime.utcnow(), "applied_by": "polling"}},
        )
        if claim.modified_count == 1:
            await _apply_payment_success(tx)
    return {
        "session_id": session_id,
        "status": session.status,
        "payment_status": new_payment_status,
        "amount_total": session.amount_total,
        "currency": session.currency,
        "kind": tx["kind"],
        "stripe_account": account,
        "applied": tx.get("applied") or new_payment_status == "paid",
    }


# ====================== WEBHOOK ======================

@webhook_router.post("/api/webhook/stripe")
async def stripe_webhook(http_request: Request):
    """Stripe webhook endpoint. Idempotent (atomic claim).

    Both Stripe accounts (KDMARCHE + O'SCOP) post here. We try to construct
    the event with each account's webhook secret; whichever validates wins.
    If no webhook secrets are configured yet (TEST env), we accept the event
    body without signature verification (logged warning).
    """
    body = await http_request.body()
    signature = http_request.headers.get("Stripe-Signature", "")
    event = None
    verified_account: Optional[str] = None
    any_secret_configured = False

    for account_name in ("oscop", "kdmarche"):
        secrets_list = _webhook_secrets_for(account_name)
        if secrets_list:
            any_secret_configured = True
        for secret in secrets_list:
            try:
                event = stripe.Webhook.construct_event(body, signature, secret)
                verified_account = account_name
                logger.info(
                    "Stripe webhook verified with account=%s event_id=%s",
                    account_name, event.get("id"),
                )
                break
            except (stripe.error.SignatureVerificationError, ValueError) as exc:
                logger.debug(
                    "Stripe webhook signature mismatch for account=%s: %s",
                    account_name, exc,
                )
                continue
        if event is not None:
            break

    if event is None:
        if not any_secret_configured:
            # No webhook secret configured — accept without verification (DEV/TEST only)
            try:
                import json
                event = stripe.Event.construct_from(json.loads(body.decode()), api_key=get_stripe_key("oscop"))
                verified_account = "unsigned-test"
                logger.warning("Stripe webhook NOT verified (no STRIPE_WEBHOOK_SECRETS_* configured)")
            except Exception as exc:
                logger.warning("Stripe webhook unsigned-parse failed: %s", exc)
                raise HTTPException(status_code=400, detail="Webhook invalide")
        else:
            logger.warning("Stripe webhook invalid for both accounts (signature mismatch)")
            raise HTTPException(status_code=400, detail="Webhook invalide")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        if session.get("payment_status") == "paid" and session_id:
            tx = await db.payment_transactions.find_one({"session_id": session_id})
            if tx:
                claim = await db.payment_transactions.update_one(
                    {"session_id": session_id, "applied": {"$ne": True}},
                    {"$set": {
                        "applied": True,
                        "applied_at": datetime.utcnow(),
                        "applied_by": f"webhook:{verified_account}",
                        "payment_status": "paid",
                        "updated_at": datetime.utcnow(),
                    }},
                )
                if claim.modified_count == 1:
                    await _apply_payment_success(tx)
                else:
                    logger.info("Stripe webhook: tx %s already applied — no-op", session_id)
    return {"received": True}


# ====================== APPLY LOGIC ======================

async def _apply_payment_success(tx: dict):
    """Apply business effects when a checkout session is paid. Must be idempotent."""
    kind = tx["kind"]
    user_id = tx["user_id"]
    now = datetime.utcnow()

    if kind == "PASS":
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
