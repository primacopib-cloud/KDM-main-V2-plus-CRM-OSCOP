"""Alerte email J-7 avant expiration de l'abonnement Acheteur Pro d'un gérant de relais."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def run_pro_expiry_alerts(db) -> int:
    now = datetime.utcnow()
    sent = 0
    async for point in db.lolodrive_points.find(
            {"manager_user_id": {"$ne": None}}, {"_id": 0, "manager_user_id": 1, "name": 1}):
        uid = point["manager_user_id"]
        membership = await db.org_memberships.find_one({"user_id": uid})
        if not membership:
            continue
        sub = await db.subscriptions.find_one(
            {"org_id": membership["org_id"], "status": "ACTIVE"}, {"_id": 0, "current_period_end": 1})
        end = (sub or {}).get("current_period_end")
        if not end:
            continue
        days = (end - now).days
        if not (0 <= days <= 7):
            continue
        key = f"{uid}:{end.isoformat()}"
        if await db.pro_expiry_notified.find_one({"key": key}):
            continue
        user = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "contact_name": 1})
        if not user or not user.get("email"):
            continue
        try:
            from brevo_service import send_email, _wrap_html
            first = ((user.get("contact_name") or "").split() or [""])[0]
            subject = f"⏳ Votre abonnement Acheteur Pro expire dans {days} jour(s)"
            body = f"""
              <p>Bonjour{f' {first}' if first else ''},</p>
              <p>Votre abonnement <strong>Acheteur Pro</strong> arrive à échéance le
              <strong>{end.strftime('%d/%m/%Y')}</strong> (dans {days} jour(s)).</p>
              <p>Rappel de la règle coopérative : tout gérant de relais LOLODRIVE
              (<strong>{point.get('name')}</strong>) doit disposer d'un abonnement Acheteur Pro actif.
              Pensez à renouveler pour conserver votre statut de gérant et l'accès à votre POS.</p>
            """
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"Votre abonnement Acheteur Pro expire le {end.strftime('%d/%m/%Y')} — renouvelez pour rester gérant LOLODRIVE.",
                tags=["pro_expiry_alert"])
            await db.pro_expiry_notified.insert_one({"key": key, "user_id": uid, "notified_at": now})
            sent += 1
        except Exception as exc:
            logger.warning("Alerte expiration Pro %s : %s", uid, exc)
    if sent:
        logger.info("Alertes expiration Pro envoyées : %s", sent)
    return sent
