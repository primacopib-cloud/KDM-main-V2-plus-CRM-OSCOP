"""Archivages mensuels GEDESS (CSV emails + PDF conformité) avec alerte email et relance quotidienne."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def _alert_if_failed(db, kind: str, label: str, run: dict) -> None:
    """Alerte le Super Admin (1 email max/jour par archive) si l'archivage a échoué."""
    if run.get("status") != "ERROR":
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    coll = db.email_archive_runs if kind == "emails" else db.compliance_archive_runs
    doc = await coll.find_one({"month": run["month"]}, {"_id": 0, "alert_sent_on": 1})
    if doc and doc.get("alert_sent_on") == today:
        return
    from connectors.health_watch import _send_alert_email
    await _send_alert_email(
        f"Échec archivage GEDESS : {label} ({run['month']})",
        (
            f"L'archivage mensuel automatique <strong>{label}</strong> pour la période "
            f"<strong>{run['month']}</strong> a échoué. Une nouvelle tentative sera effectuée "
            "automatiquement demain jusqu'à réussite."
        ),
        {
            "Archive": label,
            "Période": run["month"],
            "Erreur": run.get("error") or "Inconnue",
            "Prochaine tentative": "Automatique (quotidienne)",
        },
        "critical",
    )
    await coll.update_one({"month": run["month"]}, {"$set": {"alert_sent_on": today}})
    logger.warning("Alerte archivage GEDESS envoyée (%s %s)", label, run["month"])


async def run_monthly_archives_with_alerts(db, month: str) -> None:
    """Tente les 2 archivages du mois écoulé (idempotents) + alerte sur échec."""
    from routes_email_previews import archive_email_logs_to_ged
    from routes_compliance_report import archive_compliance_report_to_ged

    result = await archive_email_logs_to_ged(db, month)
    if result.get("status") not in ("ALREADY_ARCHIVED",):
        logger.info("Archive GED journal emails (%s): %s", month, result.get("status"))
    await _alert_if_failed(db, "emails", "Journal des emails (CSV)", {**result, "month": month})

    result = await archive_compliance_report_to_ged(db, month)
    if result.get("status") not in ("ALREADY_ARCHIVED",):
        logger.info("Archive GED rapport conformité (%s): %s", month, result.get("status"))
    await _alert_if_failed(db, "compliance", "Rapport de conformité (PDF)", {**result, "month": month})
