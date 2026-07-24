"""Email de réinitialisation de mot de passe — multilingue (FR/EN/ES/GCF) selon la langue du membre."""
import logging
import os

logger = logging.getLogger(__name__)

RESET_I18N = {
    "fr": {
        "subject": "Réinitialisation de votre mot de passe — KDMARCHÉ × O'SCOP",
        "title": "Réinitialisation de votre mot de passe",
        "hello": "Bonjour {name},",
        "intro": "Vous avez demandé la réinitialisation de votre mot de passe sur la Communityplace KDMARCHÉ × O'SCOP.",
        "cta_intro": "Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe :",
        "btn": "Réinitialiser mon mot de passe",
        "warning": "⚠️ Ce lien expire dans 1 heure. Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.",
    },
    "en": {
        "subject": "Reset your password — KDMARCHÉ × O'SCOP",
        "title": "Reset your password",
        "hello": "Hello {name},",
        "intro": "You requested a password reset on the KDMARCHÉ × O'SCOP Communityplace.",
        "cta_intro": "Click the button below to create a new password:",
        "btn": "Reset my password",
        "warning": "⚠️ This link expires in 1 hour. If you did not request this reset, please ignore this email.",
    },
    "es": {
        "subject": "Restablecimiento de su contraseña — KDMARCHÉ × O'SCOP",
        "title": "Restablecimiento de su contraseña",
        "hello": "Hola {name}:",
        "intro": "Ha solicitado el restablecimiento de su contraseña en la Communityplace KDMARCHÉ × O'SCOP.",
        "cta_intro": "Haga clic en el botón de abajo para crear una nueva contraseña:",
        "btn": "Restablecer mi contraseña",
        "warning": "⚠️ Este enlace caduca en 1 hora. Si no solicitó este restablecimiento, ignore este correo.",
    },
    "gcf": {
        "subject": "Rétabli modpas a'w — KDMARCHÉ × O'SCOP",
        "title": "Rétabli modpas a'w",
        "hello": "Bonjou {name},",
        "intro": "Ou mandé pou rétabli modpas a'w asi Communityplace KDMARCHÉ × O'SCOP.",
        "cta_intro": "Kliké asi bouton-lasa pou kréyé on nouvo modpas :",
        "btn": "Rétabli modpas an mwen",
        "warning": "⚠️ Lyen-lasa ka bout adan 1 nèdtan. Si sé pa vou ki mandé sa, pa okipé'w di mèl-lasa.",
    },
}


async def send_reset_email(db, user: dict, token: str):
    """Envoie l'email de réinitialisation via Brevo, dans la langue préférée du membre."""
    from brevo_service import send_email
    lang = user.get("preferred_language")
    t = RESET_I18N.get(lang if lang in RESET_I18N else "fr")
    frontend = os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL", "")
    reset_link = f"{frontend}/reinitialiser-mot-de-passe?token={token}"
    name = user.get("contact_name") or user.get("name") or ""
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#2A1045'>"
        f"<h2 style='color:#5B2E8C'>{t['title']}</h2>"
        f"<p>{t['hello'].format(name=name)}</p>"
        f"<p>{t['intro']}</p>"
        f"<p>{t['cta_intro']}</p>"
        f"<p style='margin:24px 0;text-align:center'><a href='{reset_link}' "
        "style='background:#D4AF37;color:#1F0A33;padding:14px 28px;border-radius:12px;"
        f"text-decoration:none;font-weight:bold;'>{t['btn']}</a></p>"
        "<p style='background:rgba(255,107,107,0.08);border:1px solid rgba(255,107,107,0.25);"
        f"padding:12px;border-radius:10px;font-size:13px;color:#7a2e2e'>{t['warning']}</p>"
        "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP</b> — Communityplace B2B ESS</p></div>")
    await send_email(to_email=user["email"], to_name=name, subject=t["subject"],
                     html_content=html, tags=["password-reset"])
