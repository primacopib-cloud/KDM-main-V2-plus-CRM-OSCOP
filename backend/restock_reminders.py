"""Relance gérant : bon de commande fournisseur sans réception pointée après REMINDER_DAYS jours."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
REMINDER_DAYS = 5


async def run_restock_reminders(db, now=None) -> int:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=REMINDER_DAYS)
    sent = 0
    async for o in db.restock_orders.find(
            {"received_at": None, "reminder_sent_at": None, "created_at": {"$lte": cutoff}}, {"_id": 0}):
        await db.restock_orders.update_one({"id": o["id"]}, {"$set": {"reminder_sent_at": now}})
        try:
            if await _notify_manager(db, o, now):
                sent += 1
                logger.info("Relance bon de commande %s envoyée", o["order_number"])
        except Exception as exc:
            logger.warning("Relance bon %s : %s", o.get("order_number"), exc)
    return sent


async def _notify_manager(db, o, now):
    point = await db.lolodrive_points.find_one(
        {"id": o["point_id"]}, {"_id": 0, "name": 1, "code": 1, "manager_user_id": 1})
    mgr = point and await db.users.find_one(
        {"id": point.get("manager_user_id")}, {"_id": 0, "email": 1, "contact_name": 1})
    if not (mgr and mgr.get("email")):
        return False
    days = max(REMINDER_DAYS, (now - o["created_at"]).days)
    items = "".join(f"<li>{l['name']} × {l['qty']}"
                    f"{' — ' + l['supplier'] if l.get('supplier') else ''}</li>" for l in o.get("lines", []))
    from brevo_service import send_email, _wrap_html
    subject = f"⏰ Bon de commande {o['order_number']} sans réception depuis {days} jours"
    body = f"""
      <p>Bonjour {mgr.get('contact_name') or ''},</p>
      <p>Votre bon de commande <strong>{o['order_number']}</strong> (relais {point.get('name')})
      a été envoyé il y a <strong style='color:#d97706'>{days} jours</strong> et sa réception n'a pas encore été pointée.</p>
      <ul style='font-size:13px'>{items}</ul>
      <p>Relancez le fournisseur si la livraison n'est pas arrivée, ou pointez la réception dans
      votre espace POS → « Bons de commande fournisseur » pour remettre les stocks à jour.</p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Relance automatique — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Bon {o['order_number']} sans reception depuis {days} jours.",
                     tags=["restock_order_reminder"])
    return True
