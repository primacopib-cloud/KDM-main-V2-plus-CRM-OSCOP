"""Rappel objectif mi-mois : point d'étape envoyé au gérant le 15 s'il est en retard sur son objectif."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
REMIND_DAYS = (15, 16, 17)


async def run_goal_midmonth_reminders(db, force: bool = False, ref_date=None) -> int:
    now = ref_date or datetime.utcnow()
    if not force and now.day not in REMIND_DAYS:
        return 0
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_tag = month_start.strftime("%Y-%m")
    expected_pct = round(now.day / 31 * 100)
    sent = 0
    async for point in db.lolodrive_points.find({"monthly_goal_cents": {"$gt": 0}}, {"_id": 0}):
        if await db.goal_midmonth_sent.find_one({"point_id": point["id"], "month": month_tag}):
            continue
        total = 0
        async for o in db.lolodrive_orders.find(
                {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": month_start}},
                {"_id": 0, "total_cents": 1}):
            total += o.get("total_cents", 0)
        goal = point["monthly_goal_cents"]
        pct = round(total / goal * 100, 1)
        if pct >= expected_pct:
            continue
        mgr = await db.users.find_one({"id": point.get("manager_user_id")},
                                      {"_id": 0, "email": 1, "contact_name": 1})
        if not mgr or not mgr.get("email"):
            continue
        try:
            from brevo_service import send_email, _wrap_html
            remaining = (goal - total) / 100
            subject = f"📍 Point d'étape objectif — {point['name']} ({pct}%)"
            body = f"""
              <p>Bonjour {(mgr.get('contact_name') or '').split(' ')[0]},</p>
              <p>Nous sommes à mi-parcours du mois et votre relais <strong>{point['name']} ({point['code']})</strong>
              est en retard sur son objectif de caisse :</p>
              <div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:14px;margin:12px 0'>
                <p style='margin:0;font-size:15px'><strong>{total / 100:.2f} €</strong> encaissés sur
                <strong>{goal / 100:.2f} €</strong> — soit <strong>{pct}%</strong>
                (attendu à ce stade : ~{expected_pct}%).</p>
                <p style='margin:6px 0 0;font-size:13px'>Il reste <strong>{remaining:.2f} €</strong> à réaliser d'ici la fin du mois.</p>
              </div>
              <p>Quelques pistes : promotions sur vos top produits, relance des paniers, ventes au comptoir. Vous pouvez y arriver ! 💪</p>
            """
            await send_email(to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Objectif : {pct}% à mi-mois ({total / 100:.2f}/{goal / 100:.2f} €).",
                             tags=["objectif_mi_mois"])
            await db.goal_midmonth_sent.insert_one({"point_id": point["id"], "month": month_tag, "sent_at": now})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel mi-mois %s : %s", point.get("code"), exc)
    if sent:
        logger.info("Rappels objectif mi-mois envoyés : %s", sent)
    return sent
