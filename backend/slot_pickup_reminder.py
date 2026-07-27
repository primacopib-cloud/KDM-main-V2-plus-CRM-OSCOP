"""Rappel au client 1h avant le début de son créneau de retrait Drive / livraison (email + SMS)."""
import logging
import uuid
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


async def run_no_pickup_reminders(db, now=None) -> int:
    """Relance le client si sa commande prête n'a pas été retirée après la fin de son créneau,
    en l'informant de la pénalité (UC par article × catégorie, 1 UC = 0,10 €)."""
    now = now or datetime.utcnow()
    from routes_lolodrive_taxonomy import get_fees_config_doc, compute_penalty_uc
    cfg = await get_fees_config_doc()
    slots = {s["id"]: s for s in cfg.get("pickup_slots", [])}
    sent = 0
    async for o in db.lolodrive_orders.find({
            "status": "READY",
            "pickup_slot_id": {"$nin": [None, ""]},
            "ready_at": {"$gte": now - timedelta(days=7)},
            "no_pickup_reminder_sent_at": {"$exists": False}}, {"_id": 0}):
        slot = slots.get(o["pickup_slot_id"])
        hm = _parse_hhmm((slot or {}).get("end"))
        if not slot or not hm:
            continue
        try:
            day = datetime.strptime(o.get("pickup_date") or now.strftime("%Y-%m-%d"), "%Y-%m-%d")
        except ValueError:
            continue
        slot_end = day.replace(hour=hm[0], minute=hm[1])
        if now < slot_end:
            continue
        user = await db.users.find_one({"id": o.get("user_id")},
                                       {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        if not user or not user.get("email"):
            continue
        penalty = await compute_penalty_uc(o.get("items", []))
        num, label = o.get("order_number"), slot.get("label")
        point_name = "votre relais LOLODRIVE"
        if o.get("lolo_point_id"):
            pt = await db.lolodrive_points.find_one({"id": o["lolo_point_id"]}, {"_id": 0, "name": 1})
            if pt:
                point_name = pt["name"]
        # Débit automatique de la pénalité sur le CREDI'SCOP du client (ligne tracée au ledger)
        new_balance = None
        if penalty > 0:
            from lolodrive_helpers import get_or_create_wallet
            wallet = await get_or_create_wallet(o["user_id"])
            await db.lolodrive_wallets.update_one(
                {"id": wallet["id"]}, {"$inc": {"balance_uc": -penalty}, "$set": {"updated_at": now}})
            await db.lolodrive_wallet_ledger.insert_one({
                "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "DEBIT",
                "amount_uc": penalty, "reason": "NO_PICKUP_PENALTY",
                "order_number": num, "created_at": now})
            fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
            new_balance = (fresh or {}).get("balance_uc")
        await db.lolodrive_orders.update_one(
            {"id": o["id"]},
            {"$set": {"no_pickup_reminder_sent_at": now, "no_pickup_penalty_uc": penalty,
                      "no_pickup_penalty_debited": penalty > 0}})
        balance_html = ""
        if new_balance is not None:
            balance_html = (f"<p style='margin:6px 0 0'>Elle a été débitée de votre CREDI'SCOP — "
                            f"nouveau solde : <strong>{new_balance:g} UC</strong>.</p>")
        try:
            from brevo_service import send_email, send_sms, _wrap_html
            subject = f"⚠️ Commande {num} non retirée — pénalité {penalty:g} UC"
            body = f"""
              <p>Bonjour {((user.get('contact_name') or '').split() or [''])[0]},</p>
              <p>Votre commande <strong>{num}</strong> était prête au retrait chez <strong>{point_name}</strong>
              pendant votre créneau <strong>{label}</strong>, mais elle n'a pas été retirée.</p>
              <div style='background:rgba(255,77,77,0.07);border:1px solid rgba(255,77,77,0.3);border-radius:12px;padding:14px;margin:12px 0'>
                <p style='margin:0'>Une pénalité de non-retrait s'applique :
                <strong style='color:#dc2626'>{penalty:g} UC ({penalty / 10:.2f} €)</strong>
                <span style='color:#777;font-size:12px'>(1 UC par article selon la catégorie)</span></p>
                {balance_html}
              </div>
              <p>Merci de passer retirer votre commande dès que possible — elle vous attend toujours.</p>
              <p style='color:#999;font-size:11px;margin-top:12px'>Réseau LOLODRIVE by O'SCOP.</p>
            """
            await send_email(to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Commande {num} non retirée (créneau {label}). "
                                          f"Pénalité : {penalty:g} UC ({penalty / 10:.2f} EUR) débitée de votre CREDI'SCOP. "
                                          f"Merci de la retirer au plus vite.",
                             tags=["no_pickup_penalty"])
            if user.get("phone"):
                try:
                    debit_txt = f" Debit CREDI'SCOP, solde {new_balance:g} UC." if new_balance is not None else ""
                    await send_sms(user["phone"],
                                   f"LOLODRIVE : commande {num} non retiree ({label}). "
                                   f"Penalite {penalty:g} UC ({penalty / 10:.2f} EUR).{debit_txt} "
                                   f"Elle vous attend chez {point_name}.",
                                   tag="no_pickup_penalty")
                except Exception as exc:
                    logger.warning("SMS pénalité %s : %s", num, exc)
            sent += 1
        except Exception as exc:
            logger.warning("Relance non-retrait %s : %s", num, exc)
    if sent:
        logger.info("Relances non-retrait envoyées : %d", sent)
    return sent
