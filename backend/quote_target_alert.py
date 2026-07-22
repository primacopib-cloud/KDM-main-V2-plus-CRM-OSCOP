"""Alerte fin de mois si l'objectif de conversion des devis n'est pas atteint."""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
quote_target_alert_router = APIRouter(prefix="/api/admin/quotes", tags=["quote-target-alert"])

ALERT_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


async def check_quote_target_alert(db, force: bool = False) -> dict:
    """Cron quotidien : à J-3 de la fin du mois, alerte l'admin si l'objectif n'est pas atteint."""
    now = datetime.now(timezone.utc)
    next_month = (now.replace(day=28) + timedelta(days=4)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    days_left = (next_month - now).days
    if not force and days_left > 3:
        return {"sent": False, "reason": "not_end_of_month", "days_left": days_left}
    month_key = now.strftime("%Y-%m")
    if not force and await db.system_flags.find_one({"key": "quote_target_alert", "month": month_key}):
        return {"sent": False, "reason": "already_sent"}
    target = ((await db.system_flags.find_one({"key": "quote_monthly_target"})) or {}).get("target", 0)
    if target <= 0:
        return {"sent": False, "reason": "no_target"}

    month_iso = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    converted, open_quotes = 0, []
    async for q in db.quote_requests.find({}, {
            "_id": 0, "id": 1, "status": 1, "status_history": 1, "company": 1,
            "first_name": 1, "last_name": 1, "contact_name": 1, "email": 1, "phone": 1, "created_at": 1}):
        s = q.get("status")
        if s == "converted":
            hist = q.get("status_history") or []
            at = next((h.get("at") for h in reversed(hist) if h.get("to") == "converted"), None)
            if at and at >= month_iso:
                converted += 1
        elif s in (None, "pending", "contacted", "processed"):
            open_quotes.append(q)

    if converted >= target:
        await db.system_flags.update_one(
            {"key": "quote_target_alert", "month": month_key},
            {"$set": {"status": "reached", "converted": converted, "target": target,
                      "checked_at": now.isoformat()}}, upsert=True)
        return {"sent": False, "reason": "target_reached", "converted": converted, "target": target}

    rows = ""
    for q in open_quotes[:20]:
        contact = (f"{q.get('first_name') or ''} {q.get('last_name') or ''}".strip()
                   or q.get("contact_name") or "—")
        created = q.get("created_at")
        date_s = created.strftime("%d/%m/%Y") if hasattr(created, "strftime") else str(created or "")[:10]
        status_label = "Contacté" if q.get("status") in ("contacted", "processed") else "Nouveau"
        rows += (f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'><b>{q.get('company', '—')}</b><br>"
                 f"<span style='color:#777;font-size:12px'>{contact}</span></td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;font-size:12px'>{q.get('email', '')}<br>{q.get('phone') or ''}</td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;font-size:12px'>{status_label}<br>{date_s}</td></tr>")
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:620px'>"
        "<h2 style='color:#5B2E8C'>🎯 Objectif de conversion — alerte fin de mois</h2>"
        f"<p>À 3 jours de la fin du mois, l'objectif de conversion des devis n'est pas encore atteint : "
        f"<b style='color:#C0392B'>{converted} / {target}</b> devis converti(s) en membres ({month_key}).</p>"
        f"<p><b>{len(open_quotes)}</b> devis restent à relancer dans le pipeline :</p>"
        "<table style='width:100%;border-collapse:collapse;font-size:14px'>"
        "<tr style='background:#2A1045;color:#fff'><th style='padding:6px 10px;text-align:left'>Société</th>"
        "<th style='padding:6px 10px;text-align:left'>Contact</th><th style='padding:6px 10px;text-align:left'>Statut</th></tr>"
        + rows + "</table>"
        "<p style='color:#999;font-size:11px;margin-top:16px'>Alerte automatique KDMARCHÉ × O'SCOP — "
        "gérez le pipeline dans Super Admin → Demandes.</p></div>"
    )
    from brevo_service import send_email
    await send_email(to_email=ALERT_EMAIL, to_name="Équipe KDMARCHÉ",
                     subject=f"🎯 Objectif devis non atteint ({converted}/{target}) — {len(open_quotes)} devis à relancer",
                     html_content=html, tags=["quote-target-alert"])
    await db.system_flags.update_one(
        {"key": "quote_target_alert", "month": month_key},
        {"$set": {"status": "alert_sent", "converted": converted, "target": target,
                  "remaining": len(open_quotes), "sent_at": now.isoformat()}}, upsert=True)
    logger.info("Alerte objectif devis envoyée (%s/%s, %s devis ouverts)", converted, target, len(open_quotes))
    return {"sent": True, "converted": converted, "target": target, "remaining_quotes": len(open_quotes)}


@quote_target_alert_router.post("/target-alert/send")
async def trigger_target_alert(force: bool = True, current_user: dict = Depends(get_current_user)):
    """Déclenchement manuel de l'alerte objectif (admin)."""
    await check_admin(current_user)
    return await check_quote_target_alert(get_database(), force=force)
