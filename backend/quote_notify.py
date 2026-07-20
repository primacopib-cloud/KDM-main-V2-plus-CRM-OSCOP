"""Notification email Brevo vers l'équipe commerciale à chaque demande de devis."""
import logging
import os

logger = logging.getLogger(__name__)

QUOTE_NOTIFY_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


ACK_T = {
    "fr": {"subject": "Votre demande de devis a bien été reçue — KDMARCHÉ × O'SCOP",
           "title": "Merci pour votre demande !",
           "body": "Nous avons bien reçu votre demande de devis pour <strong>{company}</strong>. Notre équipe commerciale vous recontacte sous 48h ouvrées.",
           "footer": "Communityplace B2B ESS — KDMARCHÉ × O'SCOP"},
    "en": {"subject": "Your quote request has been received — KDMARCHÉ × O'SCOP",
           "title": "Thank you for your request!",
           "body": "We have received your quote request for <strong>{company}</strong>. Our sales team will get back to you within 48 business hours.",
           "footer": "B2B SSE Communityplace — KDMARCHÉ × O'SCOP"},
    "es": {"subject": "Su solicitud de presupuesto ha sido recibida — KDMARCHÉ × O'SCOP",
           "title": "¡Gracias por su solicitud!",
           "body": "Hemos recibido su solicitud de presupuesto para <strong>{company}</strong>. Nuestro equipo comercial le responderá en 48 horas laborables.",
           "footer": "Communityplace B2B ESS — KDMARCHÉ × O'SCOP"},
}


async def send_quote_ack_email(q: dict) -> None:
    """Accusé de réception envoyé au prospect dans sa langue."""
    try:
        from brevo_service import send_email
        t = ACK_T.get((q.get("lang") or "fr").lower(), ACK_T["fr"])
        name = f"{q.get('first_name') or ''} {q.get('last_name') or ''}".strip() or q.get("contact_name") or ""
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:560px'>
          <h2 style='color:#5B2E8C'>{t['title']}</h2>
          <p style='font-size:14px;color:#333'>{name},</p>
          <p style='font-size:14px;color:#333'>{t['body'].format(company=q.get('company'))}</p>
          <p style='color:#999;font-size:11px;margin-top:20px'>{t['footer']}</p>
        </div>"""
        await send_email(
            to_email=q.get("email"), to_name=name or None,
            subject=t["subject"], html_content=html, tags=["quote-ack"],
        )
        logger.info("Accusé de réception devis (%s) envoyé à %s", q.get("lang"), q.get("email"))
    except Exception as exc:
        logger.error("Envoi accusé réception devis échoué : %s", exc)


async def send_quote_notification_email(q: dict) -> None:
    try:
        from brevo_service import send_email
        rows = [
            ("Raison sociale", q.get("company")),
            ("Statut juridique", q.get("legal_status") or "—"),
            ("Contact", f"{q.get('first_name') or ''} {q.get('last_name') or ''}".strip() or q.get("contact_name")),
            ("Email", q.get("email")),
            ("Téléphone", f"{q.get('phone_country') or ''} {q.get('phone')}".strip()),
            ("Langue", (q.get("lang") or "fr").upper()),
            ("Message", q.get("message") or "—"),
        ]
        rows_html = "".join(
            f"<tr><td style='padding:6px 12px;color:#666;font-size:13px'>{k}</td>"
            f"<td style='padding:6px 12px;font-size:13px'><strong>{v}</strong></td></tr>"
            for k, v in rows
        )
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:600px'>
          <h2 style='color:#5B2E8C'>Nouvelle demande de devis — Communityplace</h2>
          <table style='border-collapse:collapse;background:#f8f6fb;border-radius:8px;width:100%'>{rows_html}</table>
          <p style='color:#999;font-size:11px;margin-top:16px'>Demande n° {q.get('id')} — à traiter dans le Super Admin (onglet Demandes).</p>
        </div>"""
        await send_email(
            to_email=QUOTE_NOTIFY_EMAIL,
            to_name="Équipe commerciale O'SCOP",
            subject=f"Devis — {q.get('company')} ({q.get('email')})",
            html_content=html,
            tags=["quote-request"],
        )
        logger.info("Notification devis envoyée à %s pour %s", QUOTE_NOTIFY_EMAIL, q.get("email"))
    except Exception as exc:
        logger.error("Envoi notification devis échoué : %s", exc)
