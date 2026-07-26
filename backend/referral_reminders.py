"""Relance des filleuls inactifs : inscrits avec un code parrain mais sans première action après 7 jours."""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def run_referral_filleul_reminders(database) -> int:
    """Email + notification in-app aux filleuls dont le bonus n'est pas encore déclenché (une seule relance)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    links = await database.referral_links.find(
        {"bonus_paid": False, "reminder_sent_at": {"$exists": False}, "created_at": {"$lt": cutoff}},
        {"_id": 0}).to_list(200)
    sent = 0
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    for link in links:
        now_iso = datetime.now(timezone.utc).isoformat()
        res = await database.referral_links.update_one(
            {"filleul_id": link["filleul_id"], "reminder_sent_at": {"$exists": False}},
            {"$set": {"reminder_sent_at": now_iso}})
        if res.modified_count == 0:
            continue
        user = await database.users.find_one(
            {"id": link["filleul_id"]}, {"_id": 0, "email": 1, "full_name": 1, "first_name": 1})
        email = (user or {}).get("email") or link.get("filleul_email")
        try:
            from core_deps import create_notification
            await create_notification(
                "referral_filleul_reminder", "🎁 Votre bonus de parrainage vous attend",
                "Passez votre première commande ou inscrivez-vous à une consultation pour débloquer "
                "votre bonus de bienvenue CREDI'SCOP (et celui de votre parrain).",
                target_roles=["direct"], target_user_id=link["filleul_id"],
                data={"link": "/catalogue"})
        except Exception as exc:
            logger.warning("Notif relance filleul %s : %s", link["filleul_id"], exc)
        if email:
            try:
                from brevo_service import send_email
                await send_email(
                    to_email=email, to_name=(user or {}).get("full_name") or (user or {}).get("first_name"),
                    subject="🎁 Votre bonus de parrainage vous attend toujours",
                    html_content=(
                        "<div style='font-family:Arial,sans-serif;max-width:560px'>"
                        "<h2 style='color:#451F6B;'>Votre parrainage n'est pas encore finalisé</h2>"
                        "<p>Vous vous êtes inscrit avec un code parrain il y a quelques jours, mais votre "
                        "première action se fait attendre.</p>"
                        "<p>Passez votre <b>première commande</b> ou inscrivez-vous à une <b>consultation</b> "
                        "pour débloquer votre <b>bonus de bienvenue CREDI'SCOP</b> — votre parrain recevra le sien "
                        "au même moment.</p>"
                        f"<p><a href='{base}/catalogue' style='background:#5B2E8C;color:#fff;padding:10px 18px;"
                        "border-radius:8px;text-decoration:none'>Découvrir le catalogue</a></p>"
                        "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — programme de parrainage</p></div>"),
                    tags=["referral-filleul-reminder"])
            except Exception as exc:
                logger.warning("Email relance filleul %s : %s", email, exc)
        sent += 1
    if sent:
        logger.info("Relance filleuls inactifs : %d relance(s) envoyée(s)", sent)
    return sent
