"""Facturation CREDI'SCOP des actions métier : 4 CPC par action, 8 CPC au-delà de 100 actions dans le mois."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)

CLICK_COST = 4
CLICK_COST_PREMIUM = 8
MONTHLY_THRESHOLD = 100


async def charge_click(db, user_id: str, action_label: str) -> int:
    """Débite le tarif du clic (4 CPC ≤ 100 actions/mois, 8 CPC au-delà).
    Lève 402 « Rechargez vos crédits » si le solde CPC est insuffisant. Retourne le montant débité."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    counter = await db.click_counters.find_one({"user_id": user_id, "month": month}, {"_id": 0, "count": 1})
    count = (counter or {}).get("count", 0) + 1
    rate = CLICK_COST if count <= MONTHLY_THRESHOLD else CLICK_COST_PREMIUM

    from cpc_ledger import add_cpc_movement
    try:
        await add_cpc_movement(
            user_id, "CLICK_ACTION", -rate,
            idempotency_key=f"click:{user_id}:{uuid.uuid4().hex[:16]}",
            reason=f"{action_label} — action n°{count} du mois ({rate} CPC)",
            author="click_billing")
    except HTTPException as exc:
        if exc.status_code == 402:
            from cpc_ledger import get_cpc_account
            acc = await get_cpc_account(user_id)
            raise HTTPException(
                status_code=402,
                detail=(f"Solde CREDI'SCOP insuffisant : {rate} crédits requis pour cette action, "
                        f"{acc.get('cpc_balance', 0)} disponible(s). Rechargez vos crédits."))
        raise

    await db.click_counters.update_one(
        {"user_id": user_id, "month": month},
        {"$inc": {"count": 1},
         "$set": {"updated_at": now.isoformat()},
         "$setOnInsert": {"id": uuid.uuid4().hex, "user_id": user_id, "month": month,
                          "created_at": now.isoformat()}},
        upsert=True)
    logger.info("Clic facturé %s : %s (action n°%d, %d CPC)", user_id, action_label, count, rate)
    return rate
