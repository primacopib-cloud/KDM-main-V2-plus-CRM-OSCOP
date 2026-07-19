"""Suspension automatique des espaces vendeurs : avertissement à J+7 d'impayé, suspension à J+15, réactivation au paiement."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from auth import get_current_user_id
from vendor_emails import send_warning_email, send_suspended_email, send_reactivated_email

logger = logging.getLogger(__name__)

vendor_suspension_router = APIRouter(prefix="/api/vendor-onboarding", tags=["vendor-suspension"])

db = None
WARNING_DAYS = 7
SUSPEND_DAYS = 15


def set_vendor_suspension_database(database):
    global db
    db = database


def _days_since(iso: str) -> float:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except Exception:
        return 0.0


@vendor_suspension_router.get("/my-subscription")
async def my_subscription(user_id: str = Depends(get_current_user_id)):
    """Statut d'abonnement/suspension du compte vendeur connecté (espace vendeur)."""
    ob = await db.vendor_onboarding.find_one(
        {"user_id": user_id},
        {"_id": 0, "subscription_status": 1, "access_suspended": 1,
         "hosted_invoice_url": 1, "plan_name": 1, "first_payment_failure_at": 1})
    if not ob:
        return {"suspended": False, "subscription_status": None}
    return {"suspended": bool(ob.get("access_suspended")),
            "subscription_status": ob.get("subscription_status"),
            "plan_name": ob.get("plan_name"),
            "hosted_invoice_url": ob.get("hosted_invoice_url"),
            "first_payment_failure_at": ob.get("first_payment_failure_at")}


async def suspend_vendor_access(ob: dict):
    now = datetime.now(timezone.utc).isoformat()
    await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {
        "access_suspended": True, "suspended_at": now}})
    if ob.get("user_id"):
        await db.vendors.update_one({"id": ob["user_id"]}, {"$set": {"status": "SUSPENDED", "suspended_at": now}})
    await send_suspended_email(ob)
    try:
        from core_deps import create_notification
        await create_notification(
            "vendor_suspended", "Espace vendeur suspendu",
            f"{ob['company']} suspendu pour impayé de plus de {SUSPEND_DAYS} jours.",
            {"onboarding_id": ob["id"]})
    except Exception:
        pass
    logger.info("Espace vendeur %s suspendu (impayé > %sj)", ob["company"], SUSPEND_DAYS)


async def reactivate_vendor_access(ob: dict):
    """Appelée sur invoice.paid : lève la suspension et remet le vendeur en APPROVED."""
    await db.vendor_onboarding.update_one({"id": ob["id"]}, {
        "$set": {"access_suspended": False, "reactivated_at": datetime.now(timezone.utc).isoformat()},
        "$unset": {"suspension_warning_sent_at": "", "suspended_at": "", "first_payment_failure_at": ""}})
    if ob.get("user_id"):
        await db.vendors.update_one({"id": ob["user_id"], "status": "SUSPENDED"}, {"$set": {"status": "APPROVED"}})
    if ob.get("access_suspended"):
        await send_reactivated_email(ob)
        logger.info("Espace vendeur %s réactivé après paiement", ob["company"])


async def check_vendor_suspensions(database):
    """Cron journalier : avertit à J+7 et suspend à J+15 d'impayé Stripe."""
    global db
    if db is None:
        db = database
    cursor = db.vendor_onboarding.find({
        "subscription_status": {"$in": ["past_due", "unpaid"]},
        "status": {"$in": ["SIGNED", "ACTIVATED"]},
    }, {"_id": 0})
    async for ob in cursor:
        try:
            ref = ob.get("first_payment_failure_at") or ob.get("last_payment_failure_at")
            if not ref:
                continue
            days = _days_since(ref)
            if days >= SUSPEND_DAYS and not ob.get("access_suspended"):
                await suspend_vendor_access(ob)
            elif days >= WARNING_DAYS and not ob.get("suspension_warning_sent_at") and not ob.get("access_suspended"):
                await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {
                    "suspension_warning_sent_at": datetime.now(timezone.utc).isoformat()}})
                await send_warning_email(ob, int(days), max(SUSPEND_DAYS - int(days), 1))
        except Exception as exc:
            logger.warning("Suspension check %s : %s", ob.get("id"), exc)
