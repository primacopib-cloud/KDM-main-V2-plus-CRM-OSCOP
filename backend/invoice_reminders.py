"""Relance automatique par email des factures non réglées à J+15 (une relance par facture)."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def process_invoice_reminders(database) -> None:
    cutoff = datetime.utcnow() - timedelta(days=15)
    invoices = await database.invoices.find({
        "status": "ISSUED",
        "payment_status": "PENDING",
        "issue_date": {"$lt": cutoff},
        "reminder_sent_at": {"$exists": False},
    }).to_list(20)
    if not invoices:
        return
    from brevo_service import send_email
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    sent = 0
    for inv in invoices:
        amount = (inv.get("balance_due_cents") or inv.get("total_ttc_cents") or 0) / 100
        issue = inv.get("issue_date")
        issue_str = issue.strftime("%d/%m/%Y") if hasattr(issue, "strftime") else str(issue)[:10]
        members = await database.org_memberships.find({"org_id": inv.get("org_id")}).to_list(3)
        users = await database.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                          {"email": 1, "first_name": 1}).to_list(3)
        html = ("<div style='font-family:Arial,sans-serif;max-width:560px'>"
                f"<p>Bonjour,</p><p>Sauf erreur de notre part, la facture <b>{inv.get('invoice_number')}</b> "
                f"émise le {issue_str} (commande {inv.get('order_number')}) reste à régler : "
                f"<b>{amount:.2f} € TTC</b>.</p>"
                "<p>Merci de procéder au règlement dans les meilleurs délais, ou de nous contacter si un paiement est déjà en cours.</p>"
                f"<p><a href='{base}/espace-acheteur' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Voir mes factures</a></p>"
                "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p></div>")
        for u in users:
            try:
                await send_email(to_email=u["email"], to_name=u.get("first_name"),
                                 subject=f"⏰ Rappel — facture {inv.get('invoice_number')} en attente de règlement",
                                 html_content=html, tags=["invoice-reminder"])
                sent += 1
            except Exception as exc:
                logger.warning("Relance facture échouée %s : %s", u.get("email"), exc)
        await database.invoices.update_one({"id": inv["id"]},
                                           {"$set": {"reminder_sent_at": datetime.utcnow().isoformat()}})
    if sent:
        logger.info("Relance factures impayées : %s email(s) envoyés", sent)
