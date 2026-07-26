"""Récap hebdomadaire envoyé chaque lundi aux gérants de relais LOLODRIVE."""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def run_relay_weekly_recap(db, force: bool = False) -> int:
    now = datetime.now(timezone.utc)
    if not force and now.weekday() != 0:
        return 0
    week_tag = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    if not force:
        flag = await db.system_flags.find_one({"key": "relay_recap_week"}, {"_id": 0, "value": 1})
        if flag and flag.get("value") == week_tag:
            return 0
        await db.system_flags.update_one(
            {"key": "relay_recap_week"}, {"$set": {"value": week_tag}}, upsert=True)

    from brevo_service import send_email, _wrap_html
    since = (now - timedelta(days=7)).replace(tzinfo=None)
    sent = 0
    async for point in db.lolodrive_points.find({"manager_user_id": {"$ne": None}}, {"_id": 0}):
        mgr = await db.users.find_one({"id": point["manager_user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if not mgr or not mgr.get("email"):
            continue
        orders = await db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "created_at": {"$gte": since},
             "status": {"$in": ["PAID_UC", "PAID", "READY", "FULFILLED"]}},
            {"_id": 0, "total_cents": 1, "total_uc": 1}).to_list(500)
        nb = len(orders)
        total_eur = sum(o.get("total_cents", 0) for o in orders) / 100
        total_uc = round(sum(o.get("total_uc", 0) or 0 for o in orders), 2)
        new_reviews = await db.relay_reviews.count_documents(
            {"point_code": point["code"], "created_at": {"$gte": since}})
        all_reviews = await db.relay_reviews.find({"point_code": point["code"]}, {"_id": 0, "rating": 1}).to_list(500)
        avg = round(sum(r["rating"] for r in all_reviews) / len(all_reviews), 1) if all_reviews else None
        gold = " 🏆 Relais d'Or" if avg and avg >= 4.5 else ""
        first = ((mgr.get("contact_name") or "").split() or [""])[0]
        subject = f"Votre semaine LOLODRIVE — {point.get('name')}"
        body = f"""
          <p>Bonjour{f' {first}' if first else ''},</p>
          <p>Voici le résumé de la semaine pour votre relais <strong>{point.get('name')}</strong>{gold} :</p>
          <div style='background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;'>
            <p style='margin:0;'>🛒 Commandes traitées : <strong>{nb}</strong></p>
            <p style='margin:6px 0 0;'>💶 Volume encaissé : <strong>{total_eur:.2f} €</strong>{f' · <strong>{total_uc:g} UC</strong>' if total_uc else ''}</p>
            <p style='margin:6px 0 0;'>💬 Nouveaux avis reçus : <strong>{new_reviews}</strong></p>
            <p style='margin:6px 0 0;'>⭐ Note moyenne : <strong>{avg if avg is not None else '—'}</strong> ({len(all_reviews)} avis au total)</p>
          </div>
          <p>Pensez à répondre aux avis depuis votre POS LOLODRIVE — un relais réactif inspire confiance.</p>
        """
        try:
            await send_email(
                to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"{point.get('name')} — {nb} commandes, {total_eur:.2f} €, {new_reviews} nouveaux avis, note {avg}.",
                tags=["relay_weekly_recap"],
            )
            sent += 1
        except Exception as exc:
            logger.warning("Récap hebdo relais %s échoué : %s", point.get("code"), exc)
    logger.info("Récap hebdo relais envoyé à %s gérant(s)", sent)
    return sent
