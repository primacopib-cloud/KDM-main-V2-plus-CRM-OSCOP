"""Récap périodique vendeur personnalisé (jour + fréquence choisis) :
consultations ouvertes, solde CREDI'SCOP, notifications non lues."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

db = None


def _period_key(freq: str, now: datetime) -> str:
    return now.strftime("%Y-%m") if freq == "monthly" else now.strftime("%G-W%V")


async def send_weekly_recaps(database) -> int:
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc)
    open_cons = await db.consultations.find(
        {"status": {"$in": ["INSCRIPTIONS_OUVERTES", "EN_COURS"]}},
        {"_id": 0, "ref": 1, "title": 1, "closes_at": 1, "cpc_cost": 1}).sort("closes_at", 1).to_list(20)
    cons_html = "".join(
        f"<li><strong>{c['ref']}</strong> — {c['title']} (clôture {str(c['closes_at'])[:16].replace('T', ' ')}, "
        f"accès {c['cpc_cost']} CREDI'SCOP)</li>" for c in open_cons) or "<li>Aucune consultation ouverte actuellement.</li>"
    from brevo_service import send_email
    sent = 0
    async for acct in db.cpc_accounts.find({}, {"_id": 0, "user_id": 1, "cpc_balance": 1}):
        uid = acct["user_id"]
        s = await db.recap_settings.find_one({"user_id": uid}, {"_id": 0}) or {}
        if not s.get("enabled", True):
            continue
        if now.weekday() != s.get("day", 0):
            continue
        freq = s.get("frequency", "weekly")
        if freq == "biweekly":
            last = await db.weekly_recap_sent.find_one({"user_id": uid}, {"_id": 0, "sent_at": 1},
                                                       sort=[("sent_at", -1)])
            if last:
                try:
                    delta = now - datetime.fromisoformat(last["sent_at"])
                    if delta.days < 13:
                        continue
                except ValueError:
                    pass
        period = _period_key(freq, now)
        if await db.weekly_recap_sent.find_one({"user_id": uid, "week": period}, {"_id": 0, "week": 1}):
            continue
        user = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "full_name": 1, "name": 1, "role": 1})
        if not user or not user.get("email") or user.get("role") != "vendor":
            continue
        unread = await db.notifications.count_documents({"target_user_id": uid, "read_by": {"$ne": uid}})
        try:
            await send_email(
                to_email=user["email"], to_name=user.get("full_name") or user.get("name"),
                subject=f"Votre récap KDMARCHÉ × O'SCOP — {now.strftime('%d/%m/%Y')}",
                html_content=f"""<h2 style="color:#451F6B;">Votre point périodique</h2>
                <p>Situation du {now.strftime('%d/%m/%Y')} :</p>
                <ul>
                  <li>Solde : <strong>{acct.get('cpc_balance', 0)} CREDI'SCOP</strong></li>
                  <li>Notifications non lues : <strong>{unread}</strong></li>
                </ul>
                <p><strong>Consultations ouvertes ({len(open_cons)}) :</strong></p>
                <ul>{cons_html}</ul>
                <p style="color:#777;font-size:12px;">Jour et fréquence modifiables dans votre Espace Vendeur — onglet CREDI'SCOP,
                panneau Préférences.</p>""",
                tags=["weekly-recap"])
            sent += 1
        except Exception as exc:
            logger.warning("Récap %s : %s", user["email"], exc)
        await db.weekly_recap_sent.insert_one({"user_id": uid, "week": period, "sent_at": now.isoformat()})
    if sent:
        logger.info("Récap périodique : %d emails envoyés", sent)
    return sent
