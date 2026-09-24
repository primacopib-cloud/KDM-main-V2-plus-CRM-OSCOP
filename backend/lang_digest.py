"""Digest hebdomadaire des langues : envoye aux SUPER_ADMIN chaque lundi (UTC)."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
db = None

LANG_LABELS = {"fr": "Francais", "en": "English", "es": "Espanol", "gcf": "Kreyol", "ar": "Arabe"}


def set_lang_digest_database(database):
    global db
    db = database


async def _week_counts(start, end):
    counts = {}
    cur = db.lang_usage.find({"day": {"$gte": start, "$lt": end}}, {"_id": 0, "lang": 1, "count": 1})
    async for r in cur:
        counts[r["lang"]] = counts.get(r["lang"], 0) + r.get("count", 0)
    return counts


async def send_lang_digest(force: bool = False):
    now = datetime.now(timezone.utc)
    iso_week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    flag_id = f"lang_digest_{iso_week}"
    if not force:
        if now.weekday() != 0:
            return False
        if await db.system_flags.find_one({"id": flag_id}):
            return False
    today = now.date()
    cur_start = (today - timedelta(days=7)).isoformat()
    prev_start = (today - timedelta(days=14)).isoformat()
    cur = await _week_counts(cur_start, today.isoformat())
    prev = await _week_counts(prev_start, cur_start)
    total_cur = sum(cur.values()) or 0
    rows = []
    for lg in ["fr", "en", "es", "gcf", "ar"]:
        c, p = cur.get(lg, 0), prev.get(lg, 0)
        growth = "nouveau" if (p == 0 and c > 0) else (f"{((c - p) / p * 100):+.0f}%" if p else "—")
        share = f"{round(c / total_cur * 100)}%" if total_cur else "0%"
        rows.append(f"<tr><td style='padding:4px 10px'>{LANG_LABELS[lg]}</td>"
                    f"<td style='padding:4px 10px;text-align:center'><b>{c}</b></td>"
                    f"<td style='padding:4px 10px;text-align:center'>{p}</td>"
                    f"<td style='padding:4px 10px;text-align:center'>{growth}</td>"
                    f"<td style='padding:4px 10px;text-align:center'>{share}</td></tr>")
    top = max(cur, key=cur.get) if cur else None
    growers = [lg for lg in cur if cur.get(lg, 0) > prev.get(lg, 0)]
    summary = ""
    if top:
        summary = (f"<p>Langue dominante : <b>{LANG_LABELS.get(top, top)}</b>. "
                   + (f"Communautes en croissance : <b>{', '.join(LANG_LABELS.get(g, g) for g in growers)}</b>." if growers else "Pas de croissance cette semaine."))
        summary += "</p>"
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:600px'>"
        f"<h2 style='color:#5B2E8C'>Digest hebdo — langues des visiteurs ({iso_week})</h2>"
        f"{summary}"
        "<table style='border-collapse:collapse;font-size:13px;width:100%'>"
        "<tr style='background:#f3eee4'><th style='padding:6px 10px;text-align:left'>Langue</th>"
        "<th>7 derniers jours</th><th>7 jours prec.</th><th>Evolution</th><th>Part</th></tr>"
        + "".join(rows) + "</table>"
        "<p style='color:#999;font-size:11px;margin-top:16px'>KDMARCHE x O'SCOP — panneau Langues des visiteurs du dashboard superadmin.</p></div>")
    from brevo_service import send_email
    admins = await db.users.find({"role": "SUPER_ADMIN"}, {"_id": 0, "email": 1, "contact_name": 1}).to_list(10)
    sent = 0
    for a in admins:
        try:
            r = await send_email(to_email=a["email"], to_name=a.get("contact_name"),
                                 subject=f"🌍 Digest hebdo des langues — {iso_week}",
                                 html_content=html, tags=["lang-digest"])
            if r:
                sent += 1
        except Exception as exc:
            logger.warning("Digest langues vers %s : %s", a.get("email"), exc)
    if sent:
        await db.system_flags.update_one(
            {"id": flag_id},
            {"$set": {"id": flag_id, "sent_at": now.isoformat(), "recipients": sent}}, upsert=True)
        logger.info("Digest langues %s envoye a %s admin(s)", iso_week, sent)
    return sent > 0


async def lang_digest_loop():
    while True:
        try:
            await send_lang_digest()
        except Exception as exc:
            logger.warning("Boucle digest langues : %s", exc)
        await asyncio.sleep(6 * 3600)
