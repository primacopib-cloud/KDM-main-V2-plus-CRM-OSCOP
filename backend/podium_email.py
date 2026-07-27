"""Email podium mensuel : classement des relais par caisse comptoir envoyé aux gérants en début de mois."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SEND_UNTIL_DAY = 3

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


async def run_podium_email(db, force: bool = False, ref_date=None) -> int:
    now = ref_date or datetime.utcnow()
    if not force and now.day > SEND_UNTIL_DAY:
        return 0
    cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (cur_start - timedelta(days=1)).replace(day=1)
    month_tag = prev_start.strftime("%Y-%m")
    agg = {}
    async for o in db.lolodrive_orders.find(
            {"channel": "COUNTER", "created_at": {"$gte": prev_start, "$lt": cur_start}},
            {"_id": 0, "lolo_point_id": 1, "total_cents": 1}):
        e = agg.setdefault(o.get("lolo_point_id"), {"count": 0, "total_cents": 0})
        e["count"] += 1
        e["total_cents"] += o.get("total_cents", 0)
    if not agg:
        return 0
    points = {p["id"]: p async for p in db.lolodrive_points.find(
        {}, {"_id": 0, "id": 1, "code": 1, "name": 1, "city": 1, "manager_user_id": 1})}
    ranking = sorted(
        [{"point_id": pid, **vals} for pid, vals in agg.items()],
        key=lambda r: r["total_cents"], reverse=True)
    month_label = prev_start.strftime("%B %Y")
    try:
        import locale
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        month_label = prev_start.strftime("%B %Y")
    except Exception:
        pass
    rows = "".join(
        f"<tr><td style='padding:5px 8px;border-bottom:1px solid #eee;font-weight:bold'>{MEDALS.get(i + 1, f'#{i + 1}')}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee'>{points.get(r['point_id'], {}).get('code', '?')} — "
        f"{points.get(r['point_id'], {}).get('name', 'Relais')}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:center'>{r['count']}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:bold'>{r['total_cents'] / 100:.2f} €</td></tr>"
        for i, r in enumerate(ranking[:10]))
    sent = 0
    for point in points.values():
        uid = point.get("manager_user_id")
        if not uid:
            continue
        if await db.podium_email_sent.find_one({"month": month_tag, "user_id": uid}):
            continue
        mgr = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "contact_name": 1})
        if not mgr or not mgr.get("email"):
            continue
        my_rank = next((i + 1 for i, r in enumerate(ranking) if r["point_id"] == point["id"]), None)
        my_line = (f"<p style='margin:12px 0 0;font-size:15px'>Votre relais <strong>{point['name']}</strong> est classé "
                   f"<strong>{MEDALS.get(my_rank, f'#{my_rank}')}</strong> ce mois-ci. "
                   f"{'Bravo, continuez comme ça ! 🎉' if my_rank and my_rank <= 3 else 'Le podium est à votre portée le mois prochain !'}</p>"
                   if my_rank else
                   f"<p style='margin:12px 0 0;font-size:14px'>Votre relais <strong>{point['name']}</strong> n'a pas enregistré "
                   f"de vente au comptoir ce mois-ci — lancez votre caisse pour entrer au classement !</p>")
        try:
            from brevo_service import send_email, _wrap_html
            first = ((mgr.get("contact_name") or "").split() or [""])[0]
            subject = f"🏆 Podium des relais LOLODRIVE — {month_label}"
            body = f"""
              <p>Bonjour{f' {first}' if first else ''},</p>
              <p>Voici le classement des caisses comptoir du réseau LOLODRIVE pour <strong>{month_label}</strong> :</p>
              <table style='width:100%;border-collapse:collapse;font-size:13px;margin:10px 0'>
                <tr style='color:#888;font-size:11px;text-transform:uppercase'>
                  <td style='padding:4px 8px'></td><td style='padding:4px 8px'>Relais</td>
                  <td style='padding:4px 8px;text-align:center'>Ventes</td><td style='padding:4px 8px;text-align:right'>Caisse</td>
                </tr>
                {rows}
              </table>
              {my_line}
              <p style='color:#999;font-size:11px;margin-top:12px'>Classement automatique mensuel — Réseau LOLODRIVE by O'SCOP.</p>
            """
            await send_email(
                to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"Podium relais {month_label} — votre relais : {'#' + str(my_rank) if my_rank else 'non classé'}.",
                tags=["podium_mensuel"])
            await db.podium_email_sent.insert_one({"month": month_tag, "user_id": uid, "sent_at": now})
            sent += 1
        except Exception as exc:
            logger.warning("Podium mensuel %s : %s", point.get("code"), exc)
    if sent:
        logger.info("Emails podium mensuel envoyés : %s", sent)
    return sent
