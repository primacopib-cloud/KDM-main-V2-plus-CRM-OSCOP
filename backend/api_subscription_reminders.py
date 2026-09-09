"""Rappel d'expiration des abonnements API annuels — email J-30 avec lien de renouvellement (idempotent)."""
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def run_api_subscription_expiry_reminders(db) -> int:
    now = datetime.now(timezone.utc)
    limit = (now + timedelta(days=30)).isoformat()
    sent = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE",
        "expiry_reminder_sent": {"$ne": True},
        "valid_until": {"$gt": now.isoformat(), "$lte": limit},
    })
    async for sub in cursor:
        try:
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            vu = str(sub.get("valid_until") or "")
            days_left = max((datetime.fromisoformat(vu) - now).days, 0)
            await send_email(
                to_email=sub["email"], to_name=sub.get("contact_name"),
                subject=f"⏳ Votre abonnement API expire dans {days_left} jour(s) — renouvelez en un clic",
                html_content=_wrap_html("Renouvellement de votre abonnement API", (
                    f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Votre abonnement annuel à l'API coopérative "
                    f"(<b>{sub['reference']}</b>) arrive à échéance le "
                    f"<b>{vu[8:10]}/{vu[5:7]}/{vu[:4]}</b>.</p>"
                    "<p style='font-size:14px;'>Renouvelez dès maintenant pour conserver votre accès sans "
                    "interruption : votre nouvelle année démarrera à la fin de la période en cours.</p>"
                    f"<p style='text-align:center;'><a href='{base}/coop-api' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Renouveler mon abonnement — "
                    f"{float(sub.get('amount_eur') or 2500):,.0f} €</a></p>")),
                tags=["api-subscription-renewal"])
            await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {
                "expiry_reminder_sent": True, "expiry_reminder_at": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel expiration abonnement API %s : %s", sub.get("reference"), exc)
    if sent:
        logger.info("Rappels expiration abonnement API envoyés : %s", sent)
    return sent


async def run_api_subscription_expirations(db) -> int:
    """Désactive la clé API des abonnements arrivés à expiration sans renouvellement (idempotent)."""
    now = datetime.now(timezone.utc).isoformat()
    deactivated = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE",
        "valid_until": {"$lt": now},
        "key_deactivated_at": {"$exists": False},
        "api_key_id": {"$exists": True},
    })
    async for sub in cursor:
        await db.api_keys.update_one({"id": sub["api_key_id"]}, {"$set": {"is_active": False}})
        await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {
            "status": "EXPIRED", "key_deactivated_at": now}})
        deactivated += 1
        logger.info("Clé API désactivée (abonnement expiré) : %s (%s)", sub.get("reference"), sub.get("email"))
    return deactivated
