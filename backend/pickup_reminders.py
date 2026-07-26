"""Relance SMS/email des commandes prêtes non retirées après 48 h."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_pickup_reminders(db) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=48)
    sent = 0
    async for order in db.lolodrive_orders.find(
            {"status": "READY", "ready_at": {"$lte": cutoff},
             "pickup_reminder_sent": {"$ne": True}}, {"_id": 0}):
        user = await db.users.find_one(
            {"id": order.get("user_id")}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        if not user:
            continue
        point_name = "votre relais LOLODRIVE"
        if order.get("lolo_point_id"):
            pt = await db.lolodrive_points.find_one(
                {"id": order["lolo_point_id"]}, {"_id": 0, "name": 1, "code": 1})
            if pt:
                point_name = pt.get("name") or pt.get("code") or point_name
        num = str(order.get("order_number") or order.get("id"))[:32]
        first = ((user.get("contact_name") or "").split() or [""])[0]
        try:
            from brevo_service import send_sms, send_email, _wrap_html
            if user.get("phone"):
                await send_sms(
                    user["phone"],
                    f"KDMARCHE x O'SCOP : rappel, votre commande #{num} vous attend toujours "
                    f"({point_name}). Pensez a la retirer avec votre QR-code.",
                    tag="pickup_reminder")
            if user.get("email"):
                subject = f"Rappel — votre commande {num} vous attend"
                body = f"""
                  <p>Bonjour{f' {first}' if first else ''},</p>
                  <p>Votre commande <strong>#{num}</strong> est prête depuis plus de 48 h à
                  <strong>{point_name}</strong>. Pensez à la retirer avec votre QR-code.</p>
                """
                await send_email(
                    to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                    html_content=_wrap_html(subject, body),
                    text_content=f"Rappel : commande #{num} à retirer ({point_name}).",
                    tags=["pickup_reminder"])
            await db.lolodrive_orders.update_one(
                {"id": order["id"]},
                {"$set": {"pickup_reminder_sent": True, "pickup_reminder_at": datetime.utcnow()}})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel retrait %s échoué : %s", num, exc)
    if sent:
        logger.info("Rappels retrait 48h envoyés : %s", sent)
    return sent
