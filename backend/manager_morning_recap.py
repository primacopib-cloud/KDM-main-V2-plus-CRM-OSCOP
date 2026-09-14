"""Récap matinal gérant : email quotidien avec les commandes du jour par créneau."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FLAG_KEY = "manager_morning_recap"
WINDOW_START_UTC = 9   # ~5h Antilles (UTC-4)
WINDOW_END_UTC = 16


def _row(o, users):
    cust = users.get(o.get("user_id"), "Client")
    kind = "Livraison" if o.get("fulfillment_type") == "DELIVERY" else "Retrait"
    total = (o.get("total_cents") or 0) / 100
    return (f"<tr><td style='padding:4px 8px;'>{o.get('order_number')}</td>"
            f"<td style='padding:4px 8px;'>{cust}</td>"
            f"<td style='padding:4px 8px;'>{kind}</td>"
            f"<td style='padding:4px 8px;text-align:right;'>{total:.2f} €</td></tr>")


async def run_manager_morning_recaps(db) -> int:
    """Envoie chaque matin (fenêtre 9h-16h UTC) un email récap aux gérants ayant des commandes ce jour."""
    now = datetime.now(timezone.utc)
    if not (WINDOW_START_UTC <= now.hour < WINDOW_END_UTC):
        return 0
    today = now.date().strftime("%Y-%m-%d")
    flag = await db.system_flags.find_one({"key": FLAG_KEY, "date": today})
    if flag:
        return 0
    await db.system_flags.update_one(
        {"key": FLAG_KEY, "date": today},
        {"$set": {"sent_at": now.isoformat()}}, upsert=True)

    sent = 0
    async for point in db.lolodrive_points.find({"manager_user_id": {"$ne": None}}, {"_id": 0}):
        manager = await db.users.find_one({"id": point["manager_user_id"]},
                                          {"_id": 0, "email": 1, "first_name": 1})
        if not manager or not manager.get("email"):
            continue
        orders = await db.lolodrive_orders.find(
            {"$or": [{"lolo_point_id": point["id"]}, {"reference_point_id": point["id"]}],
             "pickup_date": today,
             "status": {"$in": ["PAID", "PREPARING", "READY"]}},
            {"_id": 0}).to_list(500)
        if not orders:
            continue
        uids = list({o.get("user_id") for o in orders if o.get("user_id")})
        users = {}
        async for u in db.users.find({"id": {"$in": uids}},
                                     {"_id": 0, "id": 1, "first_name": 1, "contact_name": 1, "email": 1}):
            users[u["id"]] = u.get("first_name") or u.get("contact_name") or u.get("email") or "Client"

        by_slot = {}
        for o in orders:
            by_slot.setdefault(o.get("pickup_slot_id") or "?", []).append(o)
        sections = ""
        for sid in sorted(by_slot):
            rows = "".join(_row(o, users) for o in by_slot[sid])
            sections += (f"<p style='margin:14px 0 4px;font-weight:bold;color:#D4AF37;'>Créneau {sid} — "
                         f"{len(by_slot[sid])} commande(s)</p>"
                         f"<table style='width:100%;border-collapse:collapse;font-size:13px;'>{rows}</table>")
        first = manager.get("first_name") or "gérant(e)"
        body = (f"<p>Bonjour {first},</p>"
                f"<p>Voici les <strong>{len(orders)} commande(s)</strong> attendues aujourd'hui "
                f"au relais <strong>{point['name']}</strong> :</p>{sections}"
                f"<p style='margin-top:16px;'>Bonne journée !<br/>LOLODRIVE</p>")
        from brevo_service import send_email, _wrap_html
        await send_email(manager["email"], manager.get("first_name"),
                         f"Récap du jour — {len(orders)} commande(s) au relais {point['name']}",
                         _wrap_html("Récap matinal LOLODRIVE", body),
                         tags=["lolodrive-morning-recap"])
        sent += 1
    logger.info("Récap matinal envoyé — %d gérant(s) notifié(s) (%s)", sent, today)
    return sent
