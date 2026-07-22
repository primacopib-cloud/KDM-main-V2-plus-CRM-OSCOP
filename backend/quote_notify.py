"""Notification email Brevo vers l'équipe commerciale à chaque demande de devis."""
import logging
import os

logger = logging.getLogger(__name__)

QUOTE_NOTIFY_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")

STALE_HOURS = 48
FOLLOWUP_DAYS = 3

FOLLOWUP_T = {
    "fr": ("Votre demande de devis est entre de bonnes mains",
           "<p>Bonjour {name},</p><p>Votre demande de devis pour <b>{company}</b> est en cours de traitement par notre équipe commerciale. "
           "Un conseiller KDMARCHÉ × O'SCOP vous recontacte très vite.</p>"
           "<p>Besoin d'ajouter une précision ? Répondez simplement à cet email.</p>"
           "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — Communityplace coopérative</p>"),
    "en": ("Your quote request is in good hands",
           "<p>Hello {name},</p><p>Your quote request for <b>{company}</b> is being processed by our sales team. "
           "A KDMARCHÉ × O'SCOP advisor will get back to you shortly.</p>"
           "<p>Need to add anything? Simply reply to this email.</p>"
           "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p>"),
    "es": ("Su solicitud de presupuesto está en buenas manos",
           "<p>Hola {name},</p><p>Su solicitud de presupuesto para <b>{company}</b> está siendo procesada por nuestro equipo comercial. "
           "Un asesor de KDMARCHÉ × O'SCOP le contactará muy pronto.</p>"
           "<p>¿Necesita añadir algo? Responda simplemente a este correo.</p>"
           "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p>"),
}


async def send_quote_followups(db) -> None:
    """Relance automatique client : demandes restées « Nouveau » depuis plus de 3 jours."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=FOLLOWUP_DAYS)
    oldest = now - timedelta(days=30)
    stale = await db.quote_requests.find(
        {"status": "pending", "created_at": {"$lt": cutoff, "$gt": oldest},
         "followup_sent_at": {"$exists": False}},
        {"_id": 0}).sort("created_at", 1).to_list(30)
    if not stale:
        return
    from brevo_service import send_email
    for q in stale:
        if not q.get("email"):
            continue
        lang = q.get("lang") if q.get("lang") in FOLLOWUP_T else "fr"
        subject, body = FOLLOWUP_T[lang]
        name = q.get("first_name") or q.get("company") or ""
        try:
            await send_email(to_email=q["email"], to_name=name,
                             subject=subject,
                             html_content=body.replace("{name}", name).replace("{company}", q.get("company", "")),
                             tags=["quote-followup"])
            await db.quote_requests.update_one(
                {"id": q["id"]},
                {"$set": {"followup_sent_at": datetime.now(timezone.utc).isoformat()}})
            logger.info("Relance devis J+%s envoyée à %s (%s)", FOLLOWUP_DAYS, q["email"], lang)
        except Exception as exc:
            logger.warning("Relance devis %s échouée : %s", q.get("email"), exc)


async def send_stale_quote_reminders(db) -> None:
    """Digest quotidien : demandes de devis en attente depuis plus de 48h."""
    from datetime import date, datetime, timedelta, timezone
    today = date.today().isoformat()
    if await db.system_flags.find_one({"key": "quote_stale_reminder", "date": today}):
        return
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=STALE_HOURS)
    stale = await db.quote_requests.find(
        {"status": "pending", "created_at": {"$lt": cutoff}}, {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    if not stale:
        await db.system_flags.insert_one({"key": "quote_stale_reminder", "date": today, "count": 0})
        return
    try:
        from brevo_service import send_email
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows = ""
        for q in stale:
            created = q.get("created_at")
            days = max((now - created).days, 0) if created else "?"
            contact = f"{q.get('first_name') or ''} {q.get('last_name') or ''}".strip() or q.get("contact_name", "")
            phone = f" · {(q.get('phone_country') or '')} {q.get('phone')}" if q.get("phone") else ""
            rows += (f"<tr><td style='padding:6px 10px;font-size:13px'><strong>{q.get('company')}</strong>"
                     f"{' · ' + q.get('legal_status') if q.get('legal_status') else ''}</td>"
                     f"<td style='padding:6px 10px;font-size:13px'>{contact}<br/>{q.get('email')}{phone}</td>"
                     f"<td style='padding:6px 10px;font-size:13px;color:#C0392B'><strong>{days} j</strong></td></tr>")
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:640px'>
          <h2 style='color:#5B2E8C'>{len(stale)} demande(s) de devis en attente depuis plus de {STALE_HOURS}h</h2>
          <table style='border-collapse:collapse;background:#f8f6fb;border-radius:8px;width:100%'>
            <tr style='color:#666;font-size:12px'><th style='padding:6px 10px;text-align:left'>Entreprise</th>
            <th style='padding:6px 10px;text-align:left'>Contact</th><th style='padding:6px 10px;text-align:left'>Attente</th></tr>
            {rows}
          </table>
          <p style='color:#999;font-size:11px;margin-top:16px'>À traiter dans le Super Admin (onglet Demandes) — marquez-les « Traitée » pour arrêter les relances.</p>
        </div>"""
        await send_email(
            to_email=QUOTE_NOTIFY_EMAIL, to_name="Équipe commerciale O'SCOP",
            subject=f"Relance : {len(stale)} devis non traité(s) depuis +{STALE_HOURS}h — KDMARCHÉ × O'SCOP",
            html_content=html, tags=["quote-stale-reminder"],
        )
        logger.info("Relance devis oubliés envoyée : %s demande(s) en attente", len(stale))
    except Exception as exc:
        logger.error("Relance devis oubliés échouée : %s", exc)
        return
    await db.system_flags.insert_one({"key": "quote_stale_reminder", "date": today, "count": len(stale)})


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
