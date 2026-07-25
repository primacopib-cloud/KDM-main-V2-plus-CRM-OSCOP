"""Archivage automatique des dossiers d'adhésion B2B abandonnés (brouillons > 30 jours)."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ABANDON_DAYS = 30


async def archive_stale_draft_applications(db) -> int:
    """Passe en ARCHIVED les dossiers DRAFT créés il y a plus de 30 jours. Idempotent."""
    cutoff = datetime.utcnow() - timedelta(days=ABANDON_DAYS)
    apps = await db.b2b_applications.find(
        {"status": "DRAFT", "created_at": {"$lt": cutoff}},
        {"_id": 0, "id": 1, "org_id": 1},
    ).to_list(500)
    if not apps:
        return 0
    now = datetime.utcnow()
    archived = []
    for app in apps:
        res = await db.b2b_applications.update_one(
            {"id": app["id"], "status": "DRAFT"},
            {"$set": {
                "status": "ARCHIVED",
                "archived_at": now,
                "archive_reason": "AUTO_ABANDON_30J",
                "updated_at": now,
            }},
        )
        if res.modified_count:
            org = await db.orgs.find_one({"id": app.get("org_id")}, {"_id": 0, "legal_name": 1})
            archived.append((org or {}).get("legal_name") or app["id"])
    if archived:
        logger.info("Archivage auto : %d dossier(s) brouillon > %dj archivé(s) : %s",
                    len(archived), ABANDON_DAYS, ", ".join(archived))
        try:
            from core_deps import create_notification
            names = ", ".join(archived[:5]) + ("…" if len(archived) > 5 else "")
            await create_notification(
                notification_type="org_applications_archived",
                title=f"{len(archived)} dossier(s) d'adhésion archivé(s) automatiquement",
                message=f"Brouillons abandonnés depuis plus de {ABANDON_DAYS} jours : {names}",
                data={"link": "/admin-v2", "count": len(archived)},
            )
        except Exception as exc:
            logger.warning("Notification archivage auto non créée : %s", exc)
    return len(archived)
