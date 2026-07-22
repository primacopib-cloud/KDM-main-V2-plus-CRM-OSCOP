"""SMS Brevo de suivi de commande à chaque changement de statut."""
import logging
import os

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "PENDING": "en attente de validation",
    "CONFIRMED": "confirmée",
    "PREPARING": "en préparation",
    "READY_FOR_PICKUP": "prête pour enlèvement",
    "PICKED_UP": "enlevée",
    "SHIPPED": "expédiée",
    "DELIVERED": "livrée",
    "INVOICED": "facturée",
    "PAID": "payée",
    "CANCELED": "annulée",
    "CANCELLED": "annulée",
}


async def send_order_status_sms(database, order_id: str, new_status: str) -> None:
    """Fire-and-forget : SMS au(x) membre(s) de l'org avec le lien de suivi."""
    try:
        order = await database.orders.find_one({"id": order_id}, {"order_number": 1, "org_id": 1})
        if not order:
            return
        members = await database.org_memberships.find({"org_id": order.get("org_id")}).to_list(3)
        users = await database.users.find(
            {"id": {"$in": [m["user_id"] for m in members]}, "phone": {"$exists": True, "$nin": ["", None]}},
            {"phone": 1}).to_list(2)
        if not users:
            return
        base = os.environ.get("FRONTEND_URL", "").rstrip("/")
        label = STATUS_LABELS.get(new_status, new_status.lower())
        text = (f"KDMARCHE : votre commande {order.get('order_number')} est {label}. "
                f"Suivi : {base}/commandes")
        from brevo_service import send_sms
        for u in users:
            phone = (u.get("phone") or "").replace(" ", "")
            if not phone:
                continue
            try:
                await send_sms(phone, text, tag="order-status")
                logger.info("SMS statut commande envoyé à %s (%s → %s)", phone, order.get("order_number"), new_status)
            except Exception as exc:
                logger.warning("SMS statut commande échoué %s : %s", phone, exc)
    except Exception as exc:
        logger.warning("send_order_status_sms erreur : %s", exc)


async def process_pickup_reminders(database) -> None:
    """SMS de rappel pour les commandes prêtes pour enlèvement depuis plus de 48h (un seul rappel)."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=48)
    orders = await database.orders.find({
        "status": "READY_FOR_PICKUP",
        "ready_at": {"$lt": cutoff},
        "pickup_reminder_sent": {"$ne": True},
    }).to_list(20)
    if not orders:
        return
    from brevo_service import send_sms
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    sent = 0
    for o in orders:
        members = await database.org_memberships.find({"org_id": o.get("org_id")}).to_list(3)
        users = await database.users.find(
            {"id": {"$in": [m["user_id"] for m in members]}, "phone": {"$exists": True, "$nin": ["", None]}},
            {"phone": 1}).to_list(2)
        text = (f"KDMARCHE : rappel, votre commande {o.get('order_number')} vous attend toujours "
                f"au point d'enlevement. Suivi : {base}/commandes")
        for u in users:
            phone = (u.get("phone") or "").replace(" ", "")
            try:
                await send_sms(phone, text, tag="pickup-reminder")
                sent += 1
            except Exception as exc:
                logger.warning("SMS rappel enlèvement échoué %s : %s", phone, exc)
        await database.orders.update_one({"id": o["id"]}, {"$set": {"pickup_reminder_sent": True}})
    if sent:
        logger.info("Rappel enlèvement : %s SMS envoyés", sent)
