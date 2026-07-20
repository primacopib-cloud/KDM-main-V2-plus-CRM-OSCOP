"""Notifications post-clôture (rapport d'analyse disponible) + clôture automatique planifiée."""
import logging
import os
from datetime import datetime, timezone

from consultation_audit import audit

logger = logging.getLogger(__name__)

db = None


def set_notify_database(database):
    global db
    db = database


async def notify_report_available(cid: str) -> int:
    """Email aux participants dès la clôture : rapport d'analyse débloquable (report_cost CPC). Idempotent."""
    res = await db.consultations.update_one(
        {"id": cid, "report_alert_sent": {"$ne": True},
         "status": {"$in": ["CLOTUREE", "EN_EVALUATION", "ATTRIBUEE"]}},
        {"$set": {"report_alert_sent": True, "report_alert_at": datetime.now(timezone.utc).isoformat()}})
    if res.modified_count == 0:
        return 0
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    from routes_cpc_admin import get_cpc_settings
    from brevo_service import send_email
    cost = (await get_cpc_settings())["report_cost"]
    base = os.environ.get("FRONTEND_PUBLIC_URL", "")
    sent = 0
    async for e in db.consultation_entries.find({"consultation_id": cid, "status": "INSCRIT"}, {"_id": 0}):
        u = await db.users.find_one({"id": e["vendor_user_id"]}, {"_id": 0, "email": 1, "full_name": 1, "name": 1})
        if not u or not u.get("email"):
            continue
        try:
            await send_email(
                to_email=u["email"], to_name=u.get("full_name") or u.get("name"),
                subject=f"Consultation {c['ref']} clôturée — votre rapport d'analyse est disponible",
                html_content=f"""<h2 style="color:#451F6B;">Consultation {c['ref']} — clôturée</h2>
                <p>Bonjour,</p>
                <p><strong>{c['title']}</strong> est désormais clôturée. En tant que participant, vous pouvez
                débloquer votre <strong>rapport d'analyse détaillé</strong> ({cost} CPC — débit unique) :
                meilleure offre, médiane du marché, votre écart, votre classement final et les pondérations.</p>
                <p style="margin:24px 0;"><a href="{base}/vendor?tab=consultations"
                style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Débloquer mon rapport ({cost} CPC)</a></p>
                <p style="color:#777;font-size:12px;">Service facultatif O'SCOP — les CPC n'interviennent jamais dans le classement des offres.</p>""",
                tags=["consultation-report-available"])
            sent += 1
        except Exception as exc:
            logger.warning("Alerte rapport %s → %s : %s", c["ref"], u["email"], exc)
        try:
            from core_deps import create_notification
            await create_notification("report_available", f"Rapport d'analyse disponible — {c['ref']}",
                                      f"{c['title']} est clôturée : débloquez votre rapport détaillé ({cost} CREDI'SCOP).",
                                      target_roles=["direct"], target_user_id=e["vendor_user_id"],
                                      data={"link": "/vendor?tab=consultations"})
        except Exception as exc:
            logger.warning("Notif rapport %s : %s", e["vendor_user_id"], exc)
    await audit("REPORT_ALERT_SENT", "system", cid, {"sent": sent, "report_cost": cost})
    logger.info("Consultation %s : alerte rapport envoyée à %d participants", c["ref"], sent)
    return sent


async def close_due_consultations(database) -> int:
    """Cron : clôture les consultations arrivées à échéance (même sans visite), ouvre les scellées, notifie."""
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc).isoformat()
    closed = 0
    async for c in db.consultations.find(
            {"status": {"$in": ["INSCRIPTIONS_OUVERTES", "EN_COURS"]}, "closes_at": {"$ne": None, "$lte": now}},
            {"_id": 0}):
        await db.consultations.update_one({"id": c["id"]}, {"$set": {"status": "CLOTUREE", "closed_at": now}})
        await audit("CLOSED", "system", c["id"], {"auto": True, "scheduler": True, "closes_at": c["closes_at"]})
        if c["procedure"] == "SCELLEE":
            from routes_bids import open_sealed_bids
            await open_sealed_bids(c["id"])
        await notify_report_available(c["id"])
        closed += 1
    return closed
