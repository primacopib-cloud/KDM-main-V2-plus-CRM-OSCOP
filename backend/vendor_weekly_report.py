"""Récapitulatif hebdomadaire (lundi) des adhérents en impayé ou suspendus, envoyé au Super Admin."""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def send_weekly_unpaid_report(db):
    now = datetime.now(timezone.utc)
    if now.weekday() != 0:  # lundi uniquement
        return
    week_key = now.strftime("%G-W%V")
    if await db.system_flags.find_one({"key": "weekly_unpaid_report", "week": week_key}):
        return
    items = await db.vendor_onboarding.find(
        {"$or": [{"subscription_status": {"$in": ["past_due", "unpaid"]}}, {"access_suspended": True}],
         "status": {"$in": ["SIGNED", "ACTIVATED"]}},
        {"_id": 0, "company": 1, "contact_name": 1, "email": 1, "plan_name": 1,
         "subscription_status": 1, "access_suspended": 1, "first_payment_failure_at": 1}
    ).to_list(200)
    await db.system_flags.insert_one({"key": "weekly_unpaid_report", "week": week_key,
                                      "count": len(items), "sent_at": now.isoformat()})
    if not items:
        logger.info("Rapport hebdo impayés : aucun impayé cette semaine (%s)", week_key)
        return
    rows = ""
    for ob in items:
        etat = "🔒 Suspendu" if ob.get("access_suspended") else "⚠ Impayé"
        depuis = (ob.get("first_payment_failure_at") or "")[:10]
        rows += (f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee;'>{ob.get('company')}</td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{ob.get('email')}</td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{ob.get('plan_name')}</td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{etat}</td>"
                 f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{depuis}</td></tr>")
    html = f"""<h2 style="color:#451F6B;">Récapitulatif hebdomadaire — impayés & suspensions</h2>
    <p>{len(items)} adhérent(s) en situation d'impayé ou suspendu(s) cette semaine :</p>
    <table style="border-collapse:collapse;font-size:13px;width:100%;">
    <tr style="background:#f4eefa;color:#451F6B;"><th style="padding:6px 10px;text-align:left;">Entreprise</th>
    <th style="padding:6px 10px;text-align:left;">Email</th><th style="padding:6px 10px;text-align:left;">Formule</th>
    <th style="padding:6px 10px;text-align:left;">État</th><th style="padding:6px 10px;text-align:left;">Impayé depuis</th></tr>
    {rows}</table>
    <p style="color:#777;font-size:12px;margin-top:16px;">Suivi détaillé : Super Admin → Conventions.</p>"""
    try:
        from brevo_service import send_email
        from email_alerts import ADMIN_ALERT_EMAIL
        admin_email = os.environ.get("ADMIN_ALERT_EMAIL", ADMIN_ALERT_EMAIL)
        await send_email(to_email=admin_email, to_name="Super Admin",
                         subject=f"📋 Récap hebdo impayés — {len(items)} adhérent(s) ({week_key})",
                         html_content=html, tags=["weekly-unpaid-report"])
        logger.info("Rapport hebdo impayés envoyé (%s, %d adhérents)", week_key, len(items))
    except Exception as exc:
        logger.warning("Rapport hebdo impayés : %s", exc)
