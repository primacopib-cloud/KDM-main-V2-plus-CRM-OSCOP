"""Rappel au client 1h avant le début de son créneau de retrait Drive / livraison (email + SMS)."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _parse_hhmm(s):
    try:
        h, m = map(int, (s or "").split(":"))
        return h, m
    except (ValueError, AttributeError):
        return None


async def run_slot_reminders(db, now=None) -> int:
    now = now or datetime.utcnow()
    from routes_lolodrive_taxonomy import get_fees_config_doc
    cfg = await get_fees_config_doc()
    slots = {("pickup", s["id"]): s for s in cfg.get("pickup_slots", [])}
    slots.update({("delivery", s["id"]): s for s in cfg.get("delivery_slots", [])})
    since = now - timedelta(days=7)
    sent = 0
    async for o in db.lolodrive_orders.find({
            "status": {"$in": ["PAID", "PREPARING", "READY"]},
            "created_at": {"$gte": since},
            "$or": [{"pickup_slot_id": {"$nin": [None, ""]}}, {"delivery_slot_id": {"$nin": [None, ""]}}],
            "slot_reminder_sent_at": {"$exists": False}}, {"_id": 0}):
        kind = "pickup" if o.get("pickup_slot_id") else "delivery"
        if o.get("pickup_date") and o["pickup_date"] != now.strftime("%Y-%m-%d"):
            continue
        slot = slots.get((kind, o.get("pickup_slot_id") or o.get("delivery_slot_id")))
        hm = _parse_hhmm((slot or {}).get("start"))
        if not slot or not hm:
            continue
        start_today = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
        if not (start_today - timedelta(hours=1) <= now < start_today):
            continue
        user = await db.users.find_one({"id": o.get("user_id")},
                                       {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        if not user or not user.get("email"):
            continue
        point_name = "votre relais LOLODRIVE"
        if o.get("lolo_point_id"):
            pt = await db.lolodrive_points.find_one({"id": o["lolo_point_id"]}, {"_id": 0, "name": 1})
            if pt:
                point_name = pt["name"]
        num = o.get("order_number")
        label = slot.get("label")
        is_delivery = kind == "delivery"
        try:
            from brevo_service import send_email, send_sms, _wrap_html
            subject = f"⏰ Rappel — votre {'livraison' if is_delivery else 'commande'} {num} ({label})"
            body = f"""
              <p>Bonjour {((user.get('contact_name') or '').split() or [''])[0]},</p>
              <p>Votre créneau {'de livraison' if is_delivery else 'de retrait'} approche : <strong>{label}</strong> (dans moins d'une heure).</p>
              <p>Commande <strong>{num}</strong>{'' if is_delivery else f" — à retirer au point <strong>{point_name}</strong>"}.</p>
              <p style='color:#999;font-size:11px;margin-top:12px'>À tout de suite — Réseau LOLODRIVE by O'SCOP.</p>
            """
            await send_email(to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Rappel : commande {num}, créneau {label} dans moins d'une heure.",
                             tags=["slot_reminder"])
            if user.get("phone"):
                try:
                    await send_sms(user["phone"],
                                   f"LOLODRIVE : rappel, votre commande {num} est a retirer ({label}) - {point_name}.",
                                   tag="slot_reminder")
                except Exception as exc:
                    logger.warning("SMS rappel créneau %s : %s", num, exc)
            await db.lolodrive_orders.update_one(
                {"id": o["id"]}, {"$set": {"slot_reminder_sent_at": now}})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel créneau %s : %s", num, exc)
    if sent:
        logger.info("Rappels de créneau envoyés : %d", sent)
    return sent
