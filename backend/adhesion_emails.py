"""Emails de suivi des demandes d'adhésion B2B (multilingues)."""
import logging

logger = logging.getLogger(__name__)

_T = {
    "fr": {
        "subject": "Votre dossier d'adhésion a bien été reçu — KDMARCHÉ × O'SCOP",
        "title": "Dossier d'adhésion reçu",
        "hello": "Bonjour",
        "body": "Nous confirmons la bonne réception du dossier d'adhésion B2B de <strong>{org}</strong>.",
        "next": "Prochaines étapes",
        "step1": "Notre équipe conformité examine vos documents (24-48 h ouvrées).",
        "step2": "Vous recevrez une notification de décision par email.",
        "step3": "Si approuvé, vous accéderez au catalogue B2B et pourrez commander.",
        "footer": "La coopérative KDMARCHÉ × O'SCOP",
    },
    "en": {
        "subject": "Your membership application has been received — KDMARCHÉ × O'SCOP",
        "title": "Application received",
        "hello": "Hello",
        "body": "We confirm receipt of the B2B membership application for <strong>{org}</strong>.",
        "next": "Next steps",
        "step1": "Our compliance team reviews your documents (24-48 business hours).",
        "step2": "You will receive a decision notification by email.",
        "step3": "If approved, you will access the B2B catalog and can place orders.",
        "footer": "The KDMARCHÉ × O'SCOP cooperative",
    },
    "es": {
        "subject": "Su solicitud de adhesión ha sido recibida — KDMARCHÉ × O'SCOP",
        "title": "Solicitud recibida",
        "hello": "Hola",
        "body": "Confirmamos la recepción de la solicitud de adhesión B2B de <strong>{org}</strong>.",
        "next": "Próximos pasos",
        "step1": "Nuestro equipo de conformidad examina sus documentos (24-48 h laborables).",
        "step2": "Recibirá una notificación de decisión por correo electrónico.",
        "step3": "Si se aprueba, accederá al catálogo B2B y podrá realizar pedidos.",
        "footer": "La cooperativa KDMARCHÉ × O'SCOP",
    },
    "gcf": {
        "subject": "Dosyé adézyon a'w rivé bien — KDMARCHÉ × O'SCOP",
        "title": "Dosyé adézyon rivé",
        "hello": "Bonjou",
        "body": "Nou ka konfirmé nou risivwè dosyé adézyon B2B a <strong>{org}</strong>.",
        "next": "Sa ki ka vin apré",
        "step1": "Ekip konfòmité an nou ka gadé dokiman a'w (24-48 è ouvrab).",
        "step2": "Ou ké risivwè on notifikasyon désizyon pa imel.",
        "step3": "Si yo apwouvé'y, ou ké ni aksè a katalòg B2B-la é ou ké pé komandé.",
        "footer": "Koopérativ KDMARCHÉ × O'SCOP",
    },
}


async def send_adhesion_submitted_email(org: dict, lang: str = "fr"):
    """Accusé de réception envoyé au contact de l'organisation à la soumission."""
    email = (org or {}).get("contact_email")
    if not email:
        logger.info("Adhésion soumise sans contact_email — email de confirmation ignoré")
        return
    t = _T.get(lang if lang in _T else "fr", _T["fr"])
    name = org.get("contact_name") or org.get("legal_name") or ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#451F6B;">{t['title']}</h2>
      <p>{t['hello']} {name},</p>
      <p>{t['body'].format(org=org.get('legal_name') or '')}</p>
      <h3 style="color:#451F6B;">{t['next']}</h3>
      <ol>
        <li>{t['step1']}</li>
        <li>{t['step2']}</li>
        <li>{t['step3']}</li>
      </ol>
      <p style="color:#777;margin-top:24px;">{t['footer']}</p>
    </div>
    """
    try:
        from brevo_service import send_email
        await send_email(
            to_email=email,
            to_name=name or None,
            subject=t["subject"],
            html_content=html,
            tags=["adhesion-submitted"],
        )
        logger.info("Email confirmation adhésion envoyé à %s (%s)", email, lang)
    except Exception as exc:
        logger.warning("Email confirmation adhésion %s : %s", email, exc)


_DECISION = {
    "fr": {
        "subject_ok": "Votre adhésion est approuvée — Bienvenue chez KDMARCHÉ × O'SCOP !",
        "subject_ko": "Votre demande d'adhésion — décision de la coopérative",
        "title_ok": "Adhésion approuvée 🎉",
        "title_ko": "Demande d'adhésion refusée",
        "hello": "Bonjour",
        "body_ok": "Excellente nouvelle : la demande d'adhésion de <strong>{org}</strong> a été <strong>approuvée</strong>. Vous avez désormais accès au catalogue B2B et pouvez passer commande. 100 crédits de bienvenue ont été ajoutés à votre wallet.",
        "body_ko": "Après examen, la demande d'adhésion de <strong>{org}</strong> n'a pas pu être acceptée.",
        "reason": "Motif",
        "comment": "Commentaire de l'équipe",
        "retry": "Vous pouvez corriger votre dossier et soumettre une nouvelle demande à tout moment.",
        "footer": "La coopérative KDMARCHÉ × O'SCOP",
    },
    "en": {
        "subject_ok": "Your membership is approved — Welcome to KDMARCHÉ × O'SCOP!",
        "subject_ko": "Your membership application — cooperative decision",
        "title_ok": "Membership approved 🎉",
        "title_ko": "Membership application rejected",
        "hello": "Hello",
        "body_ok": "Great news: the membership application for <strong>{org}</strong> has been <strong>approved</strong>. You now have access to the B2B catalog and can place orders. 100 welcome credits have been added to your wallet.",
        "body_ko": "After review, the membership application for <strong>{org}</strong> could not be accepted.",
        "reason": "Reason",
        "comment": "Team comment",
        "retry": "You can fix your file and submit a new application at any time.",
        "footer": "The KDMARCHÉ × O'SCOP cooperative",
    },
    "es": {
        "subject_ok": "Su adhesión ha sido aprobada — ¡Bienvenido a KDMARCHÉ × O'SCOP!",
        "subject_ko": "Su solicitud de adhesión — decisión de la cooperativa",
        "title_ok": "Adhesión aprobada 🎉",
        "title_ko": "Solicitud de adhesión rechazada",
        "hello": "Hola",
        "body_ok": "Buenas noticias: la solicitud de adhesión de <strong>{org}</strong> ha sido <strong>aprobada</strong>. Ya tiene acceso al catálogo B2B y puede realizar pedidos. Se han añadido 100 créditos de bienvenida a su wallet.",
        "body_ko": "Tras el examen, la solicitud de adhesión de <strong>{org}</strong> no pudo ser aceptada.",
        "reason": "Motivo",
        "comment": "Comentario del equipo",
        "retry": "Puede corregir su expediente y presentar una nueva solicitud en cualquier momento.",
        "footer": "La cooperativa KDMARCHÉ × O'SCOP",
    },
    "gcf": {
        "subject_ok": "Adézyon a'w apwouvé — Byenvini adan KDMARCHÉ × O'SCOP !",
        "subject_ko": "Dosyé adézyon a'w — désizyon koopérativ-la",
        "title_ok": "Adézyon apwouvé 🎉",
        "title_ko": "Dosyé adézyon pa asepté",
        "hello": "Bonjou",
        "body_ok": "Bon nouvèl : dosyé adézyon a <strong>{org}</strong> <strong>apwouvé</strong>. Ou ni aksè a katalòg B2B-la é ou pé komandé. Nou mèt 100 krédi byenvini adan wallet a'w.",
        "body_ko": "Apré nou gadé dosyé-la, adézyon a <strong>{org}</strong> pa té pé asepté.",
        "reason": "Rézon",
        "comment": "Komantè a ekip-la",
        "retry": "Ou pé korijé dosyé a'w é voyé on nouvo demann kan ou vlé.",
        "footer": "Koopérativ KDMARCHÉ × O'SCOP",
    },
}

_REASON_LABELS = {
    "INCOMPLETE_DOCS": "Documents incomplets ou illisibles",
    "INVALID_REGISTRATION": "Numéro d'immatriculation invalide",
    "INELIGIBLE_ACTIVITY": "Activité non éligible",
    "DUPLICATE": "Demande en doublon",
    "FRAUD_SUSPICION": "Suspicion de fraude",
    "OTHER": "Autre raison",
}


async def send_adhesion_decision_email(org: dict, approved: bool, reason_code=None, comment=None, lang: str = "fr"):
    """Email envoyé au membre à l'approbation ou au rejet du dossier."""
    email = (org or {}).get("contact_email")
    if not email:
        logger.info("Décision adhésion sans contact_email — email ignoré")
        return
    t = _DECISION.get(lang if lang in _DECISION else "fr", _DECISION["fr"])
    name = org.get("contact_name") or org.get("legal_name") or ""
    body = (t["body_ok"] if approved else t["body_ko"]).format(org=org.get("legal_name") or "")
    extra = ""
    if not approved:
        if reason_code:
            extra += f"<p><strong>{t['reason']} :</strong> {_REASON_LABELS.get(reason_code, reason_code)}</p>"
        if comment:
            extra += f"<p><strong>{t['comment']} :</strong> {comment}</p>"
        extra += f"<p>{t['retry']}</p>"
    color = "#1E7F4E" if approved else "#B4232C"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:{color};">{t['title_ok'] if approved else t['title_ko']}</h2>
      <p>{t['hello']} {name},</p>
      <p>{body}</p>
      {extra}
      <p style="color:#777;margin-top:24px;">{t['footer']}</p>
    </div>
    """
    try:
        from brevo_service import send_email
        await send_email(
            to_email=email,
            to_name=name or None,
            subject=t["subject_ok"] if approved else t["subject_ko"],
            html_content=html,
            tags=["adhesion-decision"],
        )
        logger.info("Email décision adhésion (%s) envoyé à %s (%s)", "APPROVED" if approved else "REJECTED", email, lang)
    except Exception as exc:
        logger.warning("Email décision adhésion %s : %s", email, exc)


_REMINDER = {
    "fr": {
        "subject": "Votre dossier d'adhésion attend vos documents — KDMARCHÉ × O'SCOP",
        "title": "Votre dossier est presque prêt !",
        "hello": "Bonjour",
        "body": "Le dossier d'adhésion de <strong>{org}</strong> est en attente depuis plus de 48 h : il ne manque plus que vos documents (Kbis, pièce d'identité).",
        "cta": "Reprenez votre dossier à l'adresse suivante et déposez vos pièces en quelques clics :",
        "footer": "La coopérative KDMARCHÉ × O'SCOP",
    },
    "en": {
        "subject": "Your membership file is waiting for your documents — KDMARCHÉ × O'SCOP",
        "title": "Your file is almost ready!",
        "hello": "Hello",
        "body": "The membership application for <strong>{org}</strong> has been pending for over 48 hours: only your documents are missing (registration doc, ID).",
        "cta": "Resume your application at the following address and upload your documents in a few clicks:",
        "footer": "The KDMARCHÉ × O'SCOP cooperative",
    },
    "es": {
        "subject": "Su expediente de adhesión espera sus documentos — KDMARCHÉ × O'SCOP",
        "title": "¡Su expediente está casi listo!",
        "hello": "Hola",
        "body": "La solicitud de adhesión de <strong>{org}</strong> está pendiente desde hace más de 48 h: solo faltan sus documentos (registro, identidad).",
        "cta": "Reanude su solicitud en la siguiente dirección y suba sus documentos en unos clics:",
        "footer": "La cooperativa KDMARCHÉ × O'SCOP",
    },
    "gcf": {
        "subject": "Dosyé adézyon a'w ka atann dokiman a'w — KDMARCHÉ × O'SCOP",
        "title": "Dosyé a'w prèské paré !",
        "hello": "Bonjou",
        "body": "Dosyé adézyon a <strong>{org}</strong> ka atann dépi plis ki 48 è : sé dokiman a'w ki ka manké (Kbis, pyès idantité).",
        "cta": "Rouvè dosyé a'w asi adrès-lasa é mèt dokiman a'w an dé klik :",
        "footer": "Koopérativ KDMARCHÉ × O'SCOP",
    },
}


async def run_adhesion_reminders(db, base_url: str = None) -> int:
    """Relance les dossiers DRAFT bloqués depuis 48 h+ (idempotent via reminder_sent_at)."""
    from datetime import datetime, timedelta
    import os
    base = base_url or os.environ.get("PUBLIC_BASE_URL") or "https://kdmarche-oscop.fr"
    cutoff = datetime.utcnow() - timedelta(hours=48)
    apps = await db.b2b_applications.find({
        "status": "DRAFT",
        "created_at": {"$lt": cutoff},
        "$or": [{"reminder_sent_at": {"$exists": False}}, {"reminder_sent_at": None}],
    }).to_list(200)
    sent = 0
    for app in apps:
        org = await db.orgs.find_one({"id": app["org_id"]}) or {}
        user = None
        if app.get("submitted_by_user_id"):
            user = await db.users.find_one({"id": app["submitted_by_user_id"]},
                                           {"_id": 0, "email": 1, "contact_name": 1, "preferred_language": 1})
        email = org.get("contact_email") or (user or {}).get("email")
        if not email:
            continue
        lang = (user or {}).get("preferred_language") or "fr"
        t = _REMINDER.get(lang if lang in _REMINDER else "fr", _REMINDER["fr"])
        name = org.get("contact_name") or (user or {}).get("contact_name") or ""
        link = f"{base}/adhesion"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#451F6B;">{t['title']}</h2>
          <p>{t['hello']} {name},</p>
          <p>{t['body'].format(org=org.get('legal_name') or '')}</p>
          <p>{t['cta']}</p>
          <p><a href="{link}" style="display:inline-block;background:#D9B35A;color:#2A1045;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">{link}</a></p>
          <p style="color:#777;margin-top:24px;">{t['footer']}</p>
        </div>
        """
        try:
            from brevo_service import send_email
            await send_email(to_email=email, to_name=name or None, subject=t["subject"],
                             html_content=html, tags=["adhesion-reminder"])
            await db.b2b_applications.update_one(
                {"id": app["id"]}, {"$set": {"reminder_sent_at": datetime.utcnow()}})
            sent += 1
            logger.info("Relance dossier incomplet envoyée à %s (app %s, %s)", email, app["id"], lang)
        except Exception as exc:
            logger.warning("Relance dossier %s : %s", app["id"], exc)
    return sent
