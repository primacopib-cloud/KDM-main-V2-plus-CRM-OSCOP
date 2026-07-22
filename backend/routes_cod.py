"""Paiement à la livraison (COD) — réservé aux acheteurs Pro avec abonnement actif."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from checkout_common import get_current_user_checkout, get_order_with_access_check

logger = logging.getLogger(__name__)
cod_router = APIRouter(prefix="/api/v2/checkout", tags=["cod"])
db = None


def set_cod_database(database):
    global db
    db = database


async def _is_cod_eligible(user: dict) -> bool:
    from routes_catalog import get_user_org_context
    org, subscription, _, _, _ = await get_user_org_context(user)
    return bool(org and org.get("status") == "APPROVED" and subscription and subscription.get("status") == "ACTIVE")


@cod_router.get("/cod-eligibility")
async def cod_eligibility(current_user: dict = Depends(get_current_user_checkout)):
    eligible = await _is_cod_eligible(current_user)
    return {"eligible": eligible,
            "reason": None if eligible else "Réservé aux acheteurs Pro avec abonnement actif"}


@cod_router.post("/confirm-cod")
async def confirm_cod(order_id: str = Query(...), current_user: dict = Depends(get_current_user_checkout)):
    if not await _is_cod_eligible(current_user):
        raise HTTPException(status_code=403, detail="Paiement à la livraison réservé aux acheteurs Pro avec abonnement actif")
    order, _ = await get_order_with_access_check(order_id, current_user)
    if order["status"] not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(status_code=400, detail="Commande non éligible")
    amount = order["total_ttc_cents"]
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "CONFIRMED",
            "payment_status": "cod_pending",
            "payment_method": "cod",
            "cod": True,
            "cod_amount_due_cents": amount,
            "confirmed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }})
    from consultation_audit import audit
    await audit("ORDER_COD_CONFIRMED", current_user.get("email"), None,
                {"order_id": order_id, "order_number": order.get("order_number"), "amount_due_cents": amount})
    try:
        from erp_webhooks import dispatch_order_event
        fresh = await db.orders.find_one({"id": order_id})
        await dispatch_order_event(db, "order.status_changed", fresh)
    except Exception as exc:
        logger.warning("Webhook ERP COD non envoyé : %s", exc)
    logger.info("Commande %s confirmée en paiement à la livraison (%s cents)", order.get("order_number"), amount)
    return {"success": True, "order_id": order_id, "order_number": order.get("order_number"),
            "amount_due_cents": amount, "message": "Commande confirmée — règlement à la livraison"}
