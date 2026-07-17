"""Surveillance santé des apps de l'écosystème — alerte email admin sur panne / rétablissement."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from connectors import base as connectors_base
from connectors import generic_app, oscop_crm

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 600

db = None


def set_health_watch_database(database) -> None:
    global db
    db = database


async def _check_one(conn: dict) -> tuple[str, str | None]:
    if not conn["enabled"]:
        return "DISABLED", None
    try:
        if conn["name"] in ("oscop-ged", "oscop-finance"):
            await asyncio.wait_for(oscop_crm.health(), timeout=15)
            return "OK", None
        result = await asyncio.wait_for(generic_app.health(conn["name"]), timeout=15)
        return result.get("status", "ERROR"), result.get("error")
    except asyncio.TimeoutError:
        return "ERROR", "Timeout (15s)"
    except Exception as exc:
        return "ERROR", str(exc)[:200]


async def _send_alert_email(subject_title: str, message_html: str, details: dict, priority: str) -> None:
    """Envoie l'alerte via Brevo (configuré) avec repli SendGrid via email_alerts."""
    import os
    from brevo_service import is_brevo_configured, send_email, _wrap_html
    from email_alerts import send_critical_alert_email, ADMIN_ALERT_EMAIL

    admin_email = os.environ.get("ADMIN_ALERT_EMAIL", ADMIN_ALERT_EMAIL)
    if is_brevo_configured():
        rows = "".join(
            f"<p style='margin:4px 0;font-size:13px;'><strong>{k}</strong> : {v}</p>"
            for k, v in details.items()
        )
        icon = "🚨" if priority == "critical" else "✅"
        html = _wrap_html(subject_title, f"<p>{message_html}</p>{rows}")
        await send_email(
            to_email=admin_email, to_name="Admin",
            subject=f"{icon} [{priority.upper()}] {subject_title}",
            html_content=html, tags=["connector-alert"],
        )
    else:
        await asyncio.to_thread(
            send_critical_alert_email,
            alert_type="connector_alert", title=subject_title,
            message=message_html, details=details, priority=priority,
        )


async def check_and_alert() -> dict:
    """Vérifie chaque app ; envoie un email admin uniquement sur transition OK→ERROR ou ERROR→OK."""
    alerts_sent = 0
    checked = 0
    for conn in connectors_base.connectors_registry():
        status, error = await _check_one(conn)
        if status == "DISABLED":
            continue
        checked += 1
        prev = await db.connector_health_status.find_one({"name": conn["name"]}, {"_id": 0})
        prev_status = prev.get("status") if prev else None
        now = datetime.now(timezone.utc).isoformat()

        update = {"status": status, "error": error, "checked_at": now, "label": conn["label"]}
        if status != prev_status:
            update["since"] = now
        await db.connector_health_status.update_one(
            {"name": conn["name"]}, {"$set": update}, upsert=True
        )
        if prev_status is not None and status != prev_status:
            await db.connector_health_events.insert_one({
                "id": str(uuid.uuid4()), "name": conn["name"], "label": conn["label"],
                "from_status": prev_status, "to_status": status,
                "error": error, "at": now,
            })

        if prev_status == "OK" and status == "ERROR":
            await _send_alert_email(
                f"Connecteur en panne : {conn['label'].split('—')[0].strip()}",
                (
                    f"L'application <strong>{conn['label']}</strong> de l'écosystème ne répond plus. "
                    "Les synchronisations vers cette app sont mises en file d'attente et seront rejouées."
                ),
                {
                    "Application": conn["label"],
                    "URL": conn.get("base_url", "N/A"),
                    "Erreur": error or "Inconnue",
                    "Détecté à": now,
                },
                "critical",
            )
            alerts_sent += 1
            logger.warning("Health watch: %s DOWN — alerte email envoyée", conn["name"])
        elif prev_status == "ERROR" and status == "OK":
            await _send_alert_email(
                f"Connecteur rétabli : {conn['label'].split('—')[0].strip()}",
                f"L'application <strong>{conn['label']}</strong> répond à nouveau normalement.",
                {"Application": conn["label"], "URL": conn.get("base_url", "N/A"), "Rétabli à": now},
                "medium",
            )
            alerts_sent += 1
            logger.info("Health watch: %s recovered — email envoyé", conn["name"])

    return {"checked": checked, "alerts_sent": alerts_sent}


async def health_watch_loop() -> None:
    await asyncio.sleep(90)
    while True:
        try:
            await check_and_alert()
        except Exception as exc:
            logger.error("Health watch loop error: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
