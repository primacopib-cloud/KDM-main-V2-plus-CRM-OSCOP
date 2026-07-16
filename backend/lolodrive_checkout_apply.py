"""LOLODRIVE Checkout — Constantes métier & logique d'application paiement/refund (split from routes_lolodrive_checkout.py)."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import logging

from brevo_service import notify_pass_activated

logger = logging.getLogger(__name__)

db = None

def set_checkout_apply_database(database):
    global db
    db = database

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


async def _apply_payment_refund(tx: dict):
    """Reverse business effects on a FULL refund. Must be idempotent.

    Strategy per kind:
      - PASS:     status → REFUNDED, wallet -= PASS_UC (ledger DEBIT, may go negative)
      - RECHARGE: wallet -= pack.uc (ledger DEBIT, may go negative)
      - ORDER:    order.status → REFUNDED

    Wallet can become negative (already-spent UC are not magically returned by
    the customer). An "wallet.negative_after_refund" CRM event is emitted in
    that case so admins can decide whether to reach out or chargeback.
    """
    kind = tx["kind"]
    user_id = tx["user_id"]
    session_id = tx.get("session_id")
    now = datetime.utcnow()

    if kind == "PASS":
        await db.lolodrive_passes.update_one(
            {"user_id": user_id, "stripe_session_id": session_id},
            {"$set": {"status": "REFUNDED", "refunded_at": now, "updated_at": now}},
        )
        wallet = await _get_or_create_wallet(user_id)
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]},
            {"$inc": {"balance_uc": -PASS_UC}, "$set": {"updated_at": now}},
        )
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "DEBIT",
            "amount_uc": PASS_UC, "reason": "PASS_REFUND",
            "stripe_session_id": session_id, "created_at": now,
        })
        await _emit_crm_event("pass.refunded", {"user_id": user_id, "session_id": session_id})
        # Check post-refund balance
        wallet_after = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
        if wallet_after and wallet_after.get("balance_uc", 0) < 0:
            logger.warning(
                "Wallet went negative after PASS refund: user=%s balance=%s UC",
                user_id, wallet_after.get("balance_uc"),
            )
            await _emit_crm_event("wallet.negative_after_refund", {
                "user_id": user_id, "balance_uc": wallet_after.get("balance_uc"),
                "kind": "PASS_REFUND",
            })

    elif kind == "RECHARGE":
        pack_key = (tx.get("metadata") or {}).get("pack")
        pack = RECHARGE_PACKS.get(pack_key)
        if not pack:
            logger.warning(f"Refund: pack inconnu {pack_key}")
            return
        wallet = await _get_or_create_wallet(user_id)
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]},
            {"$inc": {"balance_uc": -pack["uc"]}, "$set": {"updated_at": now}},
        )
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "DEBIT",
            "amount_uc": pack["uc"], "reason": "RECHARGE_REFUND",
            "stripe_session_id": session_id, "created_at": now,
        })
        await _emit_crm_event("recharge.refunded", {
            "user_id": user_id, "pack": pack_key, "uc": pack["uc"],
        })
        wallet_after = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
        if wallet_after and wallet_after.get("balance_uc", 0) < 0:
            logger.warning(
                "Wallet went negative after RECHARGE refund: user=%s balance=%s UC",
                user_id, wallet_after.get("balance_uc"),
            )
            await _emit_crm_event("wallet.negative_after_refund", {
                "user_id": user_id, "balance_uc": wallet_after.get("balance_uc"),
                "kind": "RECHARGE_REFUND",
            })

    elif kind == "ORDER":
        order_id = (tx.get("metadata") or {}).get("order_id")
        if not order_id:
            return
        await db.lolodrive_orders.update_one(
            {"id": order_id},
            {"$set": {"status": "REFUNDED", "refunded_at": now, "updated_at": now}},
        )
        await _emit_crm_event("order.refunded", {"user_id": user_id, "order_id": order_id})
        try:
            from routes_websockets import manager
            await manager.broadcast_to_admins({
                "type": "lolodrive_pos_event",
                "payload": {"event": "order.refunded", "data": {"order_id": order_id}, "timestamp": now.isoformat()},
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
