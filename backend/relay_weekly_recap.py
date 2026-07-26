"""Récap hebdomadaire du lundi : gérants de relais + récap réseau global aux admins."""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
TEAM_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


async def _point_stats(db, point: dict, since) -> dict:
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "created_at": {"$gte": since},
         "status": {"$in": ["PAID_UC", "PAID", "READY", "FULFILLED"]}},
        {"_id": 0, "total_cents": 1, "total_uc": 1}).to_list(500)
    new_reviews = await db.relay_reviews.count_documents(
        {"point_code": point["code"], "created_at": {"$gte": since}})
    all_reviews = await db.relay_reviews.find(
        {"point_code": point["code"]}, {"_id": 0, "rating": 1}).to_list(500)
    avg = round(sum(r["rating"] for r in all_reviews) / len(all_reviews), 1) if all_reviews else None
    return {"nb": len(orders),
            "eur": sum(o.get("total_cents", 0) for o in orders) / 100,
            "uc": round(sum(o.get("total_uc", 0) or 0 for o in orders), 2),
            "new_reviews": new_reviews, "avg": avg, "total_reviews": len(all_reviews)}


async def _send_manager_recap(db, point: dict, s: dict) -> bool:
    mgr = await db.users.find_one({"id": point["manager_user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
    if not mgr or not mgr.get("email"):
        return False
    from brevo_service import send_email, _wrap_html
    gold = " 🏆 Relais d'Or" if s["avg"] and s["avg"] >= 4.5 else ""
    first = ((mgr.get("contact_name") or "").split() or [""])[0]
    subject = f"Votre semaine LOLODRIVE — {point.get('name')}"
    body = f"""
      <p>Bonjour{f' {first}' if first else ''},</p>
      <p>Voici le résumé de la semaine pour votre relais <strong>{point.get('name')}</strong>{gold} :</p>
      <div style='background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;'>
        <p style='margin:0;'>🛒 Commandes traitées : <strong>{s['nb']}</strong></p>
        <p style='margin:6px 0 0;'>💶 Volume encaissé : <strong>{s['eur']:.2f} €</strong>{f" · <strong>{s['uc']:g} UC</strong>" if s['uc'] else ''}</p>
        <p style='margin:6px 0 0;'>💬 Nouveaux avis reçus : <strong>{s['new_reviews']}</strong></p>
        <p style='margin:6px 0 0;'>⭐ Note moyenne : <strong>{s['avg'] if s['avg'] is not None else '—'}</strong> ({s['total_reviews']} avis au total)</p>
      </div>
      <p>Pensez à répondre aux avis depuis votre POS LOLODRIVE — un relais réactif inspire confiance.</p>
    """
    await send_email(
        to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"{point.get('name')} — {s['nb']} commandes, {s['eur']:.2f} €, {s['new_reviews']} nouveaux avis, note {s['avg']}.",
        tags=["relay_weekly_recap"],
    )
    return True


async def _weekly_volume_history(db, now, weeks: int = 8) -> list:
    """Volume réseau (€) par semaine ISO sur les N dernières semaines."""
    start = (now - timedelta(days=7 * weeks)).replace(tzinfo=None)
    orders = await db.lolodrive_orders.find(
        {"created_at": {"$gte": start}, "lolo_point_id": {"$ne": None},
         "status": {"$in": ["PAID_UC", "PAID", "READY", "FULFILLED"]}},
        {"_id": 0, "created_at": 1, "total_cents": 1}).to_list(5000)
    buckets = {}
    for o in orders:
        c = o.get("created_at")
        if not isinstance(c, datetime):
            continue
        iso = c.isocalendar()
        tag = f"{iso[0]}-W{iso[1]:02d}"
        buckets[tag] = buckets.get(tag, 0) + o.get("total_cents", 0)
    out = []
    for i in range(weeks, 0, -1):
        iso = (now - timedelta(days=7 * i)).isocalendar()
        tag = f"{iso[0]}-W{iso[1]:02d}"
        out.append((tag, buckets.get(tag, 0) / 100))
    return out


def _history_chart_html(hist: list) -> str:
    maxv = max((v for _, v in hist), default=0) or 1
    bars = "".join(
        f"<tr><td style='padding:3px 8px;font-size:11px;color:#888;white-space:nowrap'>{tag}</td>"
        f"<td style='width:100%;padding:3px 8px'><div style='background:linear-gradient(90deg,#D9B35A,#F5A623);"
        f"height:12px;border-radius:6px;width:{max(2, round(v / maxv * 100))}%'></div></td>"
        f"<td style='padding:3px 8px;font-size:11px;text-align:right;white-space:nowrap'><b>{v:.0f} €</b></td></tr>"
        for tag, v in hist)
    return ("<p style='margin:18px 0 6px;font-weight:bold'>📈 Évolution du volume réseau (8 dernières semaines)</p>"
            f"<table style='width:100%;border-collapse:collapse'>{bars}</table>")


async def _send_admin_network_recap(db, rows: list, now) -> int:
    """Récap global du réseau de relais envoyé aux admins."""
    if not rows:
        return 0
    from brevo_service import send_email, _wrap_html
    rows.sort(key=lambda r: (r["s"]["eur"], r["s"]["nb"]), reverse=True)
    tot_nb = sum(r["s"]["nb"] for r in rows)
    tot_eur = sum(r["s"]["eur"] for r in rows)
    tot_rev = sum(r["s"]["new_reviews"] for r in rows)
    rows_html = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{r['point'].get('name')} "
        f"<span style='color:#999;font-size:11px'>({r['point'].get('code')} · {r['point'].get('territory') or '—'})</span></td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{r['s']['nb']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{r['s']['eur']:.2f} €</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{r['s']['new_reviews']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>"
        f"{('⭐ ' + str(r['s']['avg'])) if r['s']['avg'] is not None else '—'}"
        f"{' 🏆' if r['s']['avg'] and r['s']['avg'] >= 4.5 else ''}</td></tr>"
        for r in rows)
    period_end = now - timedelta(days=1)
    period = f"du {(now - timedelta(days=7)).strftime('%d/%m')} au {period_end.strftime('%d/%m/%Y')}"
    subject = f"🌐 Récap réseau LOLODRIVE — semaine {period}"
    body = f"""
      <p>Vue d'ensemble du réseau de relais pour la semaine {period} :</p>
      <div style='background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:14px;margin:14px 0;'>
        <p style='margin:0;'>🛒 Commandes réseau : <strong>{tot_nb}</strong> · 💶 Volume : <strong>{tot_eur:.2f} €</strong> · 💬 Nouveaux avis : <strong>{tot_rev}</strong></p>
      </div>
      <table style='width:100%;border-collapse:collapse;font-size:13px'>
        <tr style='color:#888;font-size:11px;text-transform:uppercase'>
          <th style='text-align:left;padding:6px 10px'>Relais</th><th style='text-align:right;padding:6px 10px'>Cmd</th>
          <th style='text-align:right;padding:6px 10px'>Volume</th><th style='text-align:right;padding:6px 10px'>Avis</th>
          <th style='text-align:right;padding:6px 10px'>Note</th>
        </tr>
        {rows_html}
      </table>
      {_history_chart_html(await _weekly_volume_history(db, now))}
      <p style='color:#999;font-size:11px;margin-top:14px'>🏆 = Relais d'Or (note ≥ 4.5) — récap automatique du lundi.</p>
    """
    recipients = {TEAM_EMAIL}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    sent = 0
    for email in recipients:
        try:
            await send_email(to_email=email, to_name=None, subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Réseau LOLODRIVE — {tot_nb} commandes, {tot_eur:.2f} €, {tot_rev} nouveaux avis.",
                             tags=["relay_network_recap"])
            sent += 1
        except Exception as exc:
            logger.warning("Récap réseau admin %s échoué : %s", email, exc)
    return sent


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

    since = (now - timedelta(days=7)).replace(tzinfo=None)
    sent = 0
    network_rows = []
    async for point in db.lolodrive_points.find({}, {"_id": 0}):
        stats = await _point_stats(db, point, since)
        network_rows.append({"point": point, "s": stats})
        if not point.get("manager_user_id"):
            continue
        try:
            if await _send_manager_recap(db, point, stats):
                sent += 1
        except Exception as exc:
            logger.warning("Récap hebdo relais %s échoué : %s", point.get("code"), exc)
    admin_sent = await _send_admin_network_recap(db, network_rows, now)
    logger.info("Récap hebdo relais : %s gérant(s), %s admin(s)", sent, admin_sent)
    return sent
