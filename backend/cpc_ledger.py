"""Registre CPC append-only — solde = somme des écritures, aucune modification/suppression."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

db = None

MOVEMENT_TYPES = [
    "PACK_PURCHASE", "PROMO_GRANT", "CONSULTATION_ENTRY", "REPORT_PURCHASE",
    "REFUND_CANCELLATION", "REFUND_INCIDENT", "EXPIRY", "ADMIN_CORRECTION", "STRIPE_REVERSAL",
]


def set_cpc_ledger_database(database):
    global db
    db = database


async def ensure_cpc_indexes():
    await db.cpc_ledger.create_index("idempotency_key", unique=True)
    await db.cpc_ledger.create_index([("user_id", 1), ("created_at", -1)])
    await db.cpc_accounts.create_index("user_id", unique=True)


async def get_cpc_account(user_id: str) -> dict:
    acc = await db.cpc_accounts.find_one({"user_id": user_id}, {"_id": 0})
    return acc or {"user_id": user_id, "status": "ACTIF", "cpc_balance": 0}


async def add_cpc_movement(user_id: str, mtype: str, qty: int, idempotency_key: str,
                           reason: str = "", author: str = "system",
                           consultation_id: str = None, pack_id: str = None,
                           stripe_session_id: str = None, stripe_event_id: str = None,
                           allow_frozen: bool = False) -> dict | None:
    """Écriture atomique et idempotente. Retourne None si la clé a déjà été traitée (no-op)."""
    if mtype not in MOVEMENT_TYPES:
        raise ValueError(f"Type de mouvement CPC inconnu : {mtype}")
    if qty == 0:
        raise HTTPException(status_code=400, detail="Quantité nulle")
    existing = await db.cpc_ledger.find_one({"idempotency_key": idempotency_key}, {"_id": 0, "id": 1})
    if existing:
        logger.info("CPC idempotence : clé %s déjà traitée — no-op", idempotency_key)
        return None
    acc = await get_cpc_account(user_id)
    if qty < 0 and not allow_frozen:
        if acc.get("status") == "GELE":
            raise HTTPException(status_code=403, detail="Compte CPC gelé — contactez l'administrateur")
        if acc.get("cpc_balance", 0) + qty < 0:
            raise HTTPException(status_code=402, detail="Solde CPC insuffisant")
    now = datetime.now(timezone.utc).isoformat()
    updated = await db.cpc_accounts.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"cpc_balance": qty}, "$set": {"updated_at": now},
         "$setOnInsert": {"status": "ACTIF", "created_at": now}},
        upsert=True, return_document=ReturnDocument.AFTER)
    balance_after = updated["cpc_balance"]
    entry = {
        "id": str(uuid.uuid4()), "user_id": user_id, "type": mtype, "qty": qty,
        "balance_before": balance_after - qty, "balance_after": balance_after,
        "consultation_id": consultation_id, "pack_id": pack_id,
        "stripe_session_id": stripe_session_id, "stripe_event_id": stripe_event_id,
        "idempotency_key": idempotency_key, "reason": reason, "author": author,
        "created_at": now,
    }
    try:
        await db.cpc_ledger.insert_one({**entry})
    except DuplicateKeyError:
        await db.cpc_accounts.update_one({"user_id": user_id}, {"$inc": {"cpc_balance": -qty}})
        logger.info("CPC idempotence (course) : clé %s — écriture compensée", idempotency_key)
        return None
    logger.info("CPC %s %+d pour %s (solde %d) [%s]", mtype, qty, user_id, balance_after, reason[:60])
    return entry


async def freeze_cpc_account(user_id: str, reason: str):
    await db.cpc_accounts.update_one(
        {"user_id": user_id},
        {"$set": {"status": "GELE", "frozen_reason": reason,
                  "frozen_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    logger.warning("Compte CPC %s GELÉ : %s", user_id, reason)


async def expire_cpc_purchases(database):
    """Cron : expire les crédits des packs arrivés au terme de leur validité (approximation FIFO)."""
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.cpc_purchases.find(
        {"status": "SETTLED", "expires_at": {"$lt": now}, "expiry_processed": {"$ne": True}}, {"_id": 0})
    async for p in cursor:
        acc = await get_cpc_account(p["user_id"])
        qty = min(acc.get("cpc_balance", 0), p["credits"])
        if qty > 0:
            await add_cpc_movement(
                p["user_id"], "EXPIRY", -qty, idempotency_key=f"exp:{p['id']}",
                reason=f"Expiration pack {p['pack_label']} (validité {p.get('validity_months', 12)} mois)",
                pack_id=p.get("pack_id"), allow_frozen=True)
        await db.cpc_purchases.update_one({"id": p["id"]}, {"$set": {"expiry_processed": True}})
