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


async def _confirmed_promo_mention(database) -> str:
    """« Promo -X% appliquee, expire dans Zh. » si une promo flash discount est active."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    best, best_left = None, None
    async for promo in database.credit_promotions.find(
            {"promo_type": "discount_action", "active": True, "archived": {"$ne": True}}, {"_id": 0}):
        pct = float(promo.get("value_percent") or 0)
        if pct <= 0:
            continue
        left = None
        if promo.get("ends_at"):
            try:
                end = datetime.fromisoformat(str(promo["ends_at"]).replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                left = (end - now).total_seconds()
                if left <= 0:
                    continue
            except ValueError:
                left = None
        if not best or pct > float(best.get("value_percent") or 0):
            best, best_left = promo, left
    if not best:
        return ""
    pct = int(float(best["value_percent"]))
    if best_left:
        h = int(best_left // 3600)
        left_txt = f"{h}h" if h >= 1 else f"{int(best_left // 60)}min"
        return f"Promo -{pct}% appliquee, expire dans {left_txt}."
    return f"Promo -{pct}% appliquee."


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
        # Confirmation : mention de la promo flash appliquée et de son expiration
        if new_status == "CONFIRMED":
            try:
                promo_txt = await _confirmed_promo_mention(database)
                if promo_txt:
                    text = (f"KDMARCHE : votre commande {order.get('order_number')} est {label}. "
                            f"{promo_txt} Suivi : {base}/commandes")
            except Exception as exc:
                logger.debug("Mention promo SMS ignorée : %s", exc)
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
