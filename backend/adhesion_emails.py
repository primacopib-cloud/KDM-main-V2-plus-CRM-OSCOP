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
