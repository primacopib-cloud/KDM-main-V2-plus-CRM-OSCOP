"""Récap hebdomadaire d'acquisition envoyé aux admins chaque lundi."""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

TEAM_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


async def _week_stats(db, start_iso: str, end_iso: str) -> dict:
    rng = {"$gte": start_iso, "$lt": end_iso}
    return {
        "clicks": await db.cta_clicks.count_documents({"at": rng}),
        "paid": await db.vendor_onboarding.count_documents({"status": {"$ne": "PAYMENT_PENDING"}, "created_at": rng}),
        "referrals": await db.referral_links.count_documents({"created_at": rng}),
        "pass": await db.pass_registrations.count_documents({"created_at": rng}),
    }


def _delta(cur: int, prev: int) -> str:
    if prev == 0:
        return "" if cur == 0 else " (nouveau)"
    pct = round((cur - prev) / prev * 100)
    return f" ({'+' if pct >= 0 else ''}{pct} % vs sem. précédente)"


async def run_acquisition_weekly_recap(db) -> bool:
    now = datetime.now(timezone.utc)
    if now.weekday() != 0:
        return False
    week_tag = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    flag = await db.system_flags.find_one({"key": "acquisition_recap_week"}, {"_id": 0, "value": 1})
    if flag and flag.get("value") == week_tag:
        return False
    await db.system_flags.update_one(
        {"key": "acquisition_recap_week"}, {"$set": {"value": week_tag}}, upsert=True)

    monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_start, last_end = monday - timedelta(weeks=1), monday
    cur = await _week_stats(db, last_start.isoformat(), last_end.isoformat())
    prev = await _week_stats(db, (monday - timedelta(weeks=2)).isoformat(), last_start.isoformat())

    rows = [
        ("🖱️ Clics sur les boutons d'adhésion", cur["clicks"], prev["clicks"]),
        ("✅ Adhésions payées", cur["paid"], prev["paid"]),
        ("🤝 Nouveaux parrainages", cur["referrals"], prev["referrals"]),
        ("🎫 Inscriptions PASS LOLODRIVE", cur["pass"], prev["pass"]),
    ]
    rows_html = "".join(
        f"<tr><td style='padding:8px 12px;border-bottom:1px solid #eee'>{label}</td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right'><b>{c}</b>"
        f"<span style='color:#888;font-size:11px'>{_delta(c, p)}</span></td></tr>"
        for label, c, p in rows)
    period = f"du {last_start.strftime('%d/%m')} au {(last_end - timedelta(days=1)).strftime('%d/%m/%Y')}"
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:560px'>"
        f"<h2 style='color:#451F6B'>📊 Récap acquisition — semaine {period}</h2>"
        f"<table style='width:100%;border-collapse:collapse'>{rows_html}</table>"
        "<p style='margin-top:14px'>Détail par bouton, taux de conversion et tendance : "
        "Superadmin → Conventions.</p>"
        "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — récap automatique du lundi</p></div>")

    recipients = {TEAM_EMAIL}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    from brevo_service import send_email
    sent = 0
    for email in recipients:
        try:
            await send_email(to_email=email, to_name=None,
                             subject=f"📊 Récap acquisition — semaine {period}",
                             html_content=html, tags=["acquisition-weekly-recap"])
            sent += 1
        except Exception as exc:
            logger.warning("Récap acquisition → %s : %s", email, exc)
    logger.info("Récap hebdo acquisition envoyé à %d destinataire(s) (%s)", sent, week_tag)
    return True
