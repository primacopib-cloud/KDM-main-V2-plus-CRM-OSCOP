"""Archivage automatique des dossiers d'adhésion B2B abandonnés (brouillons > 30 jours)
+ relance de dernière chance à J+25 avant archivage."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ABANDON_DAYS = 30
WARN_DAYS = 25

_WARN_I18N = {
    "fr": {
        "subject": "Dernière chance — votre dossier d'adhésion sera archivé dans 5 jours",
        "title": "Votre dossier va être archivé",
        "hello": "Bonjour",
        "body": "Le dossier d'adhésion de <strong>{org}</strong> est resté en brouillon depuis plus de {warn} jours. "
                "Sans action de votre part, il sera <strong>archivé automatiquement dans {left} jours</strong>.",
        "cta": "Finalisez votre dossier dès maintenant en quelques clics :",
        "btn": "Reprendre mon dossier",
        "footer": "La coopérative KDMARCHÉ × O'SCOP",
    },
    "en": {
        "subject": "Last chance — your membership application will be archived in 5 days",
        "title": "Your application is about to be archived",
        "hello": "Hello",
        "body": "The membership application for <strong>{org}</strong> has been in draft for over {warn} days. "
                "Without action, it will be <strong>automatically archived in {left} days</strong>.",
        "cta": "Complete your application now in a few clicks:",
        "btn": "Resume my application",
        "footer": "The KDMARCHÉ × O'SCOP cooperative",
    },
    "es": {
        "subject": "Última oportunidad — su solicitud de adhesión se archivará en 5 días",
        "title": "Su solicitud está a punto de archivarse",
        "hello": "Hola",
        "body": "La solicitud de adhesión de <strong>{org}</strong> lleva más de {warn} días en borrador. "
                "Sin acción por su parte, se <strong>archivará automáticamente en {left} días</strong>.",
        "cta": "Complete su solicitud ahora en unos clics:",
        "btn": "Reanudar mi solicitud",
        "footer": "La cooperativa KDMARCHÉ × O'SCOP",
    },
    "gcf": {
        "subject": "Dènyé chans — dosyé adézyon a'w ké achivé adan 5 jou",
        "title": "Dosyé a'w ké achivé talè",
        "hello": "Bonjou",
        "body": "Dosyé adézyon a <strong>{org}</strong> rété an bouyon dépi plis ki {warn} jou. "
                "Si ou pa fè ayen, i ké <strong>achivé otomatikman adan {left} jou</strong>.",
        "cta": "Fini dosyé a'w atchèlman an dé klik :",
        "btn": "Rouvè dosyé an mwen",
        "footer": "Koopérativ KDMARCHÉ × O'SCOP",
    },
}


async def _resolve_recipient(db, app: dict):
    """Email + nom + langue du destinataire (org contact, sinon user déposant)."""
    org = await db.orgs.find_one({"id": app.get("org_id")}) or {}
    user = None
    if app.get("submitted_by_user_id"):
        user = await db.users.find_one({"id": app["submitted_by_user_id"]},
                                       {"_id": 0, "email": 1, "contact_name": 1, "preferred_language": 1})
    email = org.get("contact_email") or (user or {}).get("email")
    name = org.get("contact_name") or (user or {}).get("contact_name") or ""
    lang = (user or {}).get("preferred_language") or "fr"
    return org, email, name, (lang if lang in _WARN_I18N else "fr")


async def send_pre_archive_warnings(db) -> int:
    """Dernier email à J+25 avant archivage auto (idempotent via archive_warning_sent_at)."""
    cutoff = datetime.utcnow() - timedelta(days=WARN_DAYS)
    apps = await db.b2b_applications.find({
        "status": "DRAFT",
        "created_at": {"$lt": cutoff},
        "$or": [{"archive_warning_sent_at": {"$exists": False}}, {"archive_warning_sent_at": None}],
    }).to_list(200)
    base = os.environ.get("PUBLIC_BASE_URL") or "https://kdmarche-oscop.fr"
    sent = 0
    for app in apps:
        org, email, name, lang = await _resolve_recipient(db, app)
        if not email:
            await db.b2b_applications.update_one(
                {"id": app["id"]}, {"$set": {"archive_warning_sent_at": datetime.utcnow()}})
            continue
        t = _WARN_I18N[lang]
        left = ABANDON_DAYS - WARN_DAYS
        link = f"{base}/adhesion"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#451F6B;">{t['title']}</h2>
          <p>{t['hello']} {name},</p>
          <p>{t['body'].format(org=org.get('legal_name') or '', warn=WARN_DAYS, left=left)}</p>
          <p>{t['cta']}</p>
          <p><a href="{link}" style="display:inline-block;background:#D9B35A;color:#2A1045;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">{t['btn']}</a></p>
          <p style="color:#777;margin-top:24px;">{t['footer']}</p>
        </div>
        """
        try:
            from brevo_service import send_email
            await send_email(to_email=email, to_name=name or None, subject=t["subject"],
                             html_content=html, tags=["adhesion-pre-archive"])
            await db.b2b_applications.update_one(
                {"id": app["id"]}, {"$set": {"archive_warning_sent_at": datetime.utcnow()}})
            sent += 1
            logger.info("Relance pré-archivage J+%d envoyée à %s (app %s, %s)", WARN_DAYS, email, app["id"], lang)
        except Exception as exc:
            logger.warning("Relance pré-archivage dossier %s : %s", app["id"], exc)
    return sent


async def run_adhesion_archiving(db) -> dict:
    """Point d'entrée scheduler : relance J+25 puis archivage J+30."""
    warned = await send_pre_archive_warnings(db)
    archived = await archive_stale_draft_applications(db)
    return {"warned": warned, "archived": archived}


async def archive_stale_draft_applications(db) -> int:
    """Passe en ARCHIVED les dossiers DRAFT créés il y a plus de 30 jours,
    au moins 3 jours après la relance de dernière chance. Idempotent."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=ABANDON_DAYS)
    apps = await db.b2b_applications.find(
        {"status": "DRAFT", "created_at": {"$lt": cutoff},
         "archive_warning_sent_at": {"$lt": now - timedelta(days=3)}},
        {"_id": 0, "id": 1, "org_id": 1},
    ).to_list(500)
    if not apps:
        return 0
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
