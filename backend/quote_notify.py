"""Notification email Brevo vers l'équipe commerciale à chaque demande de devis."""
import logging
import os

logger = logging.getLogger(__name__)

QUOTE_NOTIFY_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


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
