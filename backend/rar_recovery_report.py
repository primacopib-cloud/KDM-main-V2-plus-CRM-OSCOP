"""Rapport mensuel de recouvrement RàR : synthèse impayés / suspensions / régularisations (cron)."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _month_bounds(month: str):
    y, m = int(month[:4]), int(month[5:7])
    start = datetime(y, m, 1)
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    return start, end


async def run_monthly_recovery_report(db, force_month: str = None) -> int:
    """Début de mois : envoie aux admins la synthèse recouvrement du mois écoulé (idempotent)."""
    now = datetime.utcnow()
    if force_month:
        month = force_month
    else:
        if now.day > 5:
            return 0
        month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    if await db.rar_recovery_report_log.find_one({"month": month}):
        return 0
    start, end = _month_bounds(month)

    collected = await db.orders.find(
        {"rar": True, "payment_status": "succeeded", "paid_at": {"$gte": start, "$lt": end}},
        {"_id": 0, "cod_amount_due_cents": 1}).to_list(500)
    reminded = await db.orders.count_documents(
        {"rar": True, "rar_last_reminder_at": {"$gte": start, "$lt": end}})
    final_notices = await db.orders.count_documents(
        {"rar": True, "rar_overdue_alert_at": {"$gte": start, "$lt": end}})
    suspensions = await db.audit_journal.count_documents(
        {"event_type": "RAR_ACCOUNT_AUTO_SUSPENDED", "ts": {"$gte": start.isoformat(), "$lt": end.isoformat()}})
    reactivations = await db.audit_journal.count_documents(
        {"event_type": "RAR_ACCOUNT_REACTIVATED", "ts": {"$gte": start.isoformat(), "$lt": end.isoformat()}})
    unpaid = await db.orders.find(
        {"rar": True, "payment_status": "cod_pending", "cod_amount_due_cents": {"$gt": 0}},
        {"_id": 0, "cod_amount_due_cents": 1, "rar_proof_at": 1, "confirmed_at": 1}).to_list(200)
    unpaid_total = sum(o.get("cod_amount_due_cents") or 0 for o in unpaid)
    ages = [(now - (o.get("rar_proof_at") or o.get("confirmed_at"))).days
            for o in unpaid if o.get("rar_proof_at") or o.get("confirmed_at")]
    collected_total = sum(o.get("cod_amount_due_cents") or 0 for o in collected)

    rows = [
        ("Encaissements RàR du mois", f"{len(collected)} commande(s) — {collected_total / 100:.2f} €"),
        ("Commandes relancées (J+3/72 h)", str(reminded)),
        ("Derniers rappels J+14 envoyés", str(final_notices)),
        ("Suspensions automatiques de plafond", str(suspensions)),
        ("Réactivations après régularisation", str(reactivations)),
        ("Impayés en cours à date", f"{len(unpaid)} commande(s) — {unpaid_total / 100:.2f} €"),
        ("Impayé le plus ancien", f"J+{max(ages)}" if ages else "—"),
    ]
    table = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee'>{k}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right'><b>{v}</b></td></tr>"
        for k, v in rows)
    subject = f"📊 Rapport recouvrement RàR — {month}"
    body = (f"<p>Bonjour,</p><p>Synthèse mensuelle du recouvrement <b>Règlement à Réception Pro</b> "
            f"pour <b>{month}</b> :</p><table style='border-collapse:collapse;width:100%'>{table}</table>"
            f"<p style='font-size:11px;color:#888'>Pipeline automatique : relances J+3 (max 3), dernier rappel J+14 "
            f"avec alerte admin, suspension du plafond 72 h après sans encaissement. "
            f"Détail temps réel dans la console admin, panneau « Impayés RàR ».</p>")
    from brevo_service import send_email, _wrap_html
    admin_email = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    try:
        await send_email(to_email=admin_email, to_name="Équipe KDMARCHÉ", subject=subject,
                         html_content=_wrap_html(subject, body), text_content=subject,
                         tags=["rar_recovery_report"])
    except Exception as exc:
        logger.warning("Rapport recouvrement non envoyé : %s", exc)
        return 0
    await db.rar_recovery_report_log.insert_one({
        "month": month, "sent_at": now, "collected": len(collected), "collected_cents": collected_total,
        "reminded": reminded, "final_notices": final_notices, "suspensions": suspensions,
        "reactivations": reactivations, "unpaid": len(unpaid), "unpaid_cents": unpaid_total})
    logger.info("Rapport recouvrement RàR envoyé (%s)", month)
    return 1
