"""Fidélité UC : bonus CREDI'SCOP automatique tous les 10 achats au comptoir du relais."""
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LOYALTY_EVERY = 10
DEFAULT_BONUS_UC = 10


async def check_loyalty_bonus(db, customer: dict, point: dict, order_number: str):
    """Retourne le bonus UC offert (0 si l'achat n'est pas un multiple de 10)."""
    count = await db.lolodrive_orders.count_documents(
        {"channel": "COUNTER", "user_id": customer["id"], "lolo_point_id": point["id"]})
    if count == 0 or count % LOYALTY_EVERY != 0:
        return 0
    doc = await db.lolodrive_settings.find_one({"key": "loyalty_bonus_uc"}, {"_id": 0})
    try:
        bonus = max(0.0, float((doc or {}).get("value", DEFAULT_BONUS_UC)))
    except (TypeError, ValueError):
        bonus = DEFAULT_BONUS_UC
    if bonus == int(bonus):
        bonus = int(bonus)
    if bonus <= 0:
        return 0
    from lolodrive_helpers import get_or_create_wallet
    wallet = await get_or_create_wallet(customer["id"])
    now = datetime.utcnow()
    await db.lolodrive_wallets.update_one(
        {"id": wallet["id"]}, {"$inc": {"balance_uc": bonus}, "$set": {"updated_at": now}})
    await db.lolodrive_wallet_ledger.insert_one({
        "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
        "amount_uc": bonus, "reason": "LOYALTY_BONUS", "order_number": order_number,
        "point_id": point["id"], "created_at": now})
    fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
    from uc_receipt_email import send_uc_receipt
    await send_uc_receipt(db, customer["id"], bonus, (fresh or {}).get("balance_uc"), kind="CREDIT",
                          order_number=order_number, point_name=point.get("name"),
                          context=f"🎁 Fidélité : votre {count}e achat au comptoir — {bonus} UC offerts")
    logger.info("Bonus fidélité %s UC pour %s (%de achat, %s)", bonus, customer["id"], count, point.get("code"))
    return bonus
