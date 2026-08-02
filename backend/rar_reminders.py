"""Relances automatiques des impayés RàR : réception confirmée mais paiement en retard (cron)."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_rar_payment_reminders(db) -> int:
    """J+3 après confirmation de réception, toutes les 72 h, max 3 relances par commande."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=3)
    orders = await db.orders.find({
        "rar": True, "payment_status": "cod_pending",
        "rar_proof_at": {"$lt": cutoff},
        "cod_amount_due_cents": {"$gt": 0},
        "rar_reminder_count": {"$not": {"$gte": 3}},
        "$or": [{"rar_last_reminder_at": {"$exists": False}}, {"rar_last_reminder_at": {"$lt": cutoff}}],
    }).to_list(20)
    if not orders:
        return 0
    from brevo_service import send_email, _wrap_html
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    sent = 0
    for o in orders:
        amount = (o.get("cod_amount_due_cents") or 0) / 100
        n = (o.get("rar_reminder_count") or 0) + 1
        members = await db.org_memberships.find({"org_id": o["org_id"]}).to_list(3)
        users = await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                    {"email": 1, "contact_name": 1}).to_list(3)
        subject = f"⏰ Relance {n}/3 — facture de la commande {o.get('order_number')} en attente de règlement"
        body = (f"<p>Bonjour,</p><p>Vous avez confirmé la réception de la commande "
                f"<b>{o.get('order_number')}</b> le {str(o.get('rar_proof_at'))[:10]}, mais son règlement "
                f"de <b>{amount:.2f} € TTC</b> n'a pas encore été encaissé.</p>"
                f"<p><a href='{base}/espace-acheteur?tab=invoices' style='background:#D9B35A;color:#000;"
                f"padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Régler ma facture</a></p>"
                f"<p style='font-size:11px;color:#888'>Votre plafond Règlement à Réception Pro reste mobilisé "
                f"tant que le paiement n'est pas définitivement encaissé. Un incident de paiement peut entraîner "
                f"la réduction ou la suspension de votre plafond.</p>")
        ok = False
        for u in users:
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_payment_reminder"])
                ok = True
            except Exception as exc:
                logger.warning("Relance RàR échouée %s : %s", u.get("email"), exc)
        if ok:
            sent += 1
            await db.orders.update_one({"id": o["id"]},
                                       {"$set": {"rar_last_reminder_at": now},
                                        "$inc": {"rar_reminder_count": 1}})
    if sent:
        logger.info("Relances impayés RàR envoyées : %s", sent)
    return sent
