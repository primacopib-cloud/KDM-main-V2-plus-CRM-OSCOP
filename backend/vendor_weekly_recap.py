"""Récap hebdomadaire vendeur (lundi) : consultations ouvertes, solde CREDI'SCOP, notifications non lues."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

db = None


async def send_weekly_recaps(database) -> int:
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc)
    if now.weekday() != 0:
        return 0
    week = now.strftime("%G-W%V")
    open_cons = await db.consultations.find(
        {"status": {"$in": ["INSCRIPTIONS_OUVERTES", "EN_COURS"]}},
        {"_id": 0, "ref": 1, "title": 1, "closes_at": 1, "cpc_cost": 1}).sort("closes_at", 1).to_list(20)
    cons_html = "".join(
        f"<li><strong>{c['ref']}</strong> — {c['title']} (clôture {str(c['closes_at'])[:16].replace('T', ' ')}, "
        f"accès {c['cpc_cost']} CREDI'SCOP)</li>" for c in open_cons) or "<li>Aucune consultation ouverte cette semaine.</li>"
    from brevo_service import send_email
    sent = 0
    async for acct in db.cpc_accounts.find({}, {"_id": 0, "user_id": 1, "cpc_balance": 1}):
        if await db.weekly_recap_sent.find_one({"user_id": acct["user_id"], "week": week}, {"_id": 0, "week": 1}):
            continue
        user = await db.users.find_one({"id": acct["user_id"]},
                                       {"_id": 0, "email": 1, "full_name": 1, "name": 1, "role": 1})
        if not user or not user.get("email") or user.get("role") != "vendor":
            continue
        unread = await db.notifications.count_documents(
            {"target_user_id": acct["user_id"], "read_by": {"$ne": acct["user_id"]}})
        try:
            await send_email(
                to_email=user["email"], to_name=user.get("full_name") or user.get("name"),
                subject=f"Votre récap KDMARCHÉ × O'SCOP — semaine {week.split('W')[1]}",
                html_content=f"""<h2 style="color:#451F6B;">Bonne semaine !</h2>
                <p>Votre situation au lundi matin :</p>
                <ul>
                  <li>Solde : <strong>{acct.get('cpc_balance', 0)} CREDI'SCOP</strong></li>
                  <li>Notifications non lues : <strong>{unread}</strong></li>
                </ul>
                <p><strong>Consultations ouvertes ({len(open_cons)}) :</strong></p>
                <ul>{cons_html}</ul>
                <p style="color:#777;font-size:12px;">Retrouvez tout dans votre Espace Vendeur — onglets Consultations et CREDI'SCOP.</p>""",
                tags=["weekly-recap"])
            sent += 1
        except Exception as exc:
            logger.warning("Récap hebdo %s : %s", user["email"], exc)
        await db.weekly_recap_sent.insert_one({
            "user_id": acct["user_id"], "week": week, "sent_at": now.isoformat()})
    if sent:
        logger.info("Récap hebdo : %d emails envoyés (semaine %s)", sent, week)
    return sent
