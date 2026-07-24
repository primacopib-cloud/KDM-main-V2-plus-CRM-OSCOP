"""Accusé de réception des candidatures partenaire — multilingue (FR/EN/ES/GCF)."""
import logging

logger = logging.getLogger(__name__)

ACK_I18N = {
    "fr": {
        "subject": "Candidature reçue — {type} | KDMARCHÉ × O'SCOP",
        "title": "Merci pour votre candidature !",
        "hello": "Bonjour {name},",
        "intro": "Nous avons bien reçu votre demande « <strong>{type}</strong> »{for_company}. Notre équipe l'étudie et reviendra vers vous rapidement.",
        "for_company": " pour {company}",
        "recap_title": "Récapitulatif de votre candidature :",
        "labels": {"type": "Type de partenariat", "name": "Nom", "company": "Raison sociale",
                   "legal": "Statut juridique", "email": "Email", "phone": "Téléphone",
                   "project": "Votre projet", "ref": "Référence"},
        "footer": "Conservez la référence <strong>{ref}</strong> pour tout échange avec notre équipe partenariats — réponse sous 48 h ouvrées.",
        "signature": "La coopérative KDMARCHÉ × O'SCOP",
    },
    "en": {
        "subject": "Application received — {type} | KDMARCHÉ × O'SCOP",
        "title": "Thank you for your application!",
        "hello": "Hello {name},",
        "intro": "We have received your \u201c<strong>{type}</strong>\u201d application{for_company}. Our team is reviewing it and will get back to you shortly.",
        "for_company": " for {company}",
        "recap_title": "Summary of your application:",
        "labels": {"type": "Partnership type", "name": "Name", "company": "Company name",
                   "legal": "Legal status", "email": "Email", "phone": "Phone",
                   "project": "Your project", "ref": "Reference"},
        "footer": "Keep the reference <strong>{ref}</strong> for any exchange with our partnerships team — reply within 48 business hours.",
        "signature": "The KDMARCHÉ × O'SCOP cooperative",
    },
    "es": {
        "subject": "Candidatura recibida — {type} | KDMARCHÉ × O'SCOP",
        "title": "¡Gracias por su candidatura!",
        "hello": "Hola {name}:",
        "intro": "Hemos recibido su solicitud « <strong>{type}</strong> »{for_company}. Nuestro equipo la está estudiando y le responderá en breve.",
        "for_company": " para {company}",
        "recap_title": "Resumen de su candidatura:",
        "labels": {"type": "Tipo de asociación", "name": "Nombre", "company": "Razón social",
                   "legal": "Forma jurídica", "email": "Correo", "phone": "Teléfono",
                   "project": "Su proyecto", "ref": "Referencia"},
        "footer": "Conserve la referencia <strong>{ref}</strong> para cualquier intercambio con nuestro equipo — respuesta en 48 horas laborables.",
        "signature": "La cooperativa KDMARCHÉ × O'SCOP",
    },
    "gcf": {
        "subject": "Nou byen risivwè kandidati a'w — {type} | KDMARCHÉ × O'SCOP",
        "title": "Mèsi pou kandidati a'w !",
        "hello": "Bonjou {name},",
        "intro": "Nou byen risivwè demann a'w « <strong>{type}</strong> »{for_company}. Ékip an nou ka gadé'y é ké viré vin' vè'w byen vit.",
        "for_company": " pou {company}",
        "recap_title": "Rézimé a kandidati a'w :",
        "labels": {"type": "Kalité patenarya", "name": "Non", "company": "Rézon sosyal",
                   "legal": "Stati jiridik", "email": "Imel", "phone": "Téléfòn",
                   "project": "Pwojé a'w", "ref": "Référans"},
        "footer": "Sonjé référans <strong>{ref}</strong> pou tout échanj èvè ékip patenarya an nou — répons avan 48 tè ouvrab.",
        "signature": "Koopérativ KDMARCHÉ × O'SCOP",
    },
}


DECISION_I18N = {
    "fr": {
        "hello": "Bonjour {name},", "ref": "Référence : {ref} — KDMARCHÉ × O'SCOP.",
        "accepted": {"subject": "🎉 Candidature acceptée — {type}", "title": "Bienvenue dans la coopérative !",
                     "body": "Bonne nouvelle : votre candidature « <strong>{type}</strong> » a été "
                             "<strong style='color:#1E8449;'>acceptée</strong>. Notre équipe vous contactera très vite "
                             "pour finaliser votre intégration et vos accès."},
        "rejected": {"subject": "Votre candidature {type} — réponse", "title": "Réponse à votre candidature",
                     "body": "Après étude, nous ne pouvons pas donner suite à votre candidature "
                             "« <strong>{type}</strong> » pour le moment. Vous pourrez candidater à nouveau "
                             "ultérieurement — merci de l'intérêt porté à la coopérative."},
    },
    "en": {
        "hello": "Hello {name},", "ref": "Reference: {ref} — KDMARCHÉ × O'SCOP.",
        "accepted": {"subject": "🎉 Application accepted — {type}", "title": "Welcome to the cooperative!",
                     "body": "Great news: your \u201c<strong>{type}</strong>\u201d application has been "
                             "<strong style='color:#1E8449;'>accepted</strong>. Our team will contact you very soon "
                             "to finalise your onboarding and access."},
        "rejected": {"subject": "Your {type} application — answer", "title": "Answer to your application",
                     "body": "After review, we cannot move forward with your \u201c<strong>{type}</strong>\u201d "
                             "application at this time. You may apply again later — thank you for your interest "
                             "in the cooperative."},
    },
    "es": {
        "hello": "Hola {name}:", "ref": "Referencia: {ref} — KDMARCHÉ × O'SCOP.",
        "accepted": {"subject": "🎉 Candidatura aceptada — {type}", "title": "¡Bienvenido a la cooperativa!",
                     "body": "Buenas noticias: su candidatura « <strong>{type}</strong> » ha sido "
                             "<strong style='color:#1E8449;'>aceptada</strong>. Nuestro equipo le contactará muy pronto "
                             "para finalizar su integración y sus accesos."},
        "rejected": {"subject": "Su candidatura {type} — respuesta", "title": "Respuesta a su candidatura",
                     "body": "Tras el estudio, no podemos dar curso a su candidatura « <strong>{type}</strong> » "
                             "por el momento. Podrá presentarse de nuevo más adelante — gracias por su interés "
                             "en la cooperativa."},
    },
    "gcf": {
        "hello": "Bonjou {name},", "ref": "Référans : {ref} — KDMARCHÉ × O'SCOP.",
        "accepted": {"subject": "🎉 Kandidati a'w aksèpté — {type}", "title": "Byenvini adan koopérativ-la !",
                     "body": "Bon nouvèl : kandidati a'w « <strong>{type}</strong> » "
                             "<strong style='color:#1E8449;'>aksèpté</strong>. Ékip an nou ké kontakté'w byen vit "
                             "pou fini entégrasyon a'w é ba'w aksè a'w."},
        "rejected": {"subject": "Répons asi kandidati a'w {type}", "title": "Répons asi kandidati a'w",
                     "body": "Apré nou gadé'y byen, nou pa pé bay swit a kandidati a'w « <strong>{type}</strong> » "
                             "pou lè moman. Ou ké pé pozé kandidati a'w ankò pli ta — mèsi pou lentéré "
                             "ou ka pòté ba koopérativ-la."},
    },
}


async def send_partner_decision(doc: dict, accepted: bool):
    """Email de décision (acceptée/refusée) au candidat, dans sa langue."""
    from brevo_service import send_email
    lang = doc.get("lang")
    t = DECISION_I18N.get(lang if lang in DECISION_I18N else "fr")
    d = t["accepted" if accepted else "rejected"]
    type_label = doc.get("type_label") or doc.get("type")
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#2A1045'>"
        f"<h2 style='color:#451F6B'>{d['title']}</h2>"
        f"<p>{t['hello'].format(name=doc['name'])}</p>"
        f"<p>{d['body'].format(type=type_label)}</p>"
        f"<p style='color:#777;font-size:12px'>{t['ref'].format(ref=doc['id'][:8].upper())}</p></div>")
    await send_email(to_email=doc["email"], to_name=doc["name"],
                     subject=d["subject"].format(type=type_label),
                     html_content=html, tags=["partner-application-decision"])


def _row(label: str, value: str) -> str:
    return (f"<tr><td style='padding:7px 12px;border-bottom:1px solid #eee;color:#777;width:160px'>{label}</td>"
            f"<td style='padding:7px 12px;border-bottom:1px solid #eee;font-weight:bold'>{value}</td></tr>")


async def send_partner_ack(doc: dict):
    """Envoie l'accusé de réception au candidat dans sa langue, avec récapitulatif complet."""
    from brevo_service import send_email
    lang = doc.get("lang")
    t = ACK_I18N.get(lang if lang in ACK_I18N else "fr")
    lb = t["labels"]
    ref = doc["id"][:8].upper()
    recap = (
        "<table style='width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;"
        "border:1px solid #eee;border-radius:10px'>"
        + _row(lb["type"], doc.get("type_label") or doc.get("type"))
        + _row(lb["name"], doc["name"])
        + _row(lb["company"], doc.get("company") or "—")
        + _row(lb["legal"], doc.get("legal_status") or "—")
        + _row(lb["email"], doc["email"])
        + _row(lb["phone"], doc.get("phone") or "—")
        + _row(lb["project"], doc.get("message") or "—")
        + _row(lb["ref"], ref)
        + "</table>")
    for_company = t["for_company"].format(company=doc["company"]) if doc.get("company") else ""
    html = (
        f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#2A1045'>"
        f"<h2 style='color:#451F6B'>{t['title']}</h2>"
        f"<p>{t['hello'].format(name=doc['name'])}</p>"
        f"<p>{t['intro'].format(type=doc.get('type_label') or doc.get('type'), for_company=for_company)}</p>"
        f"<p style='margin-bottom:4px'><strong>{t['recap_title']}</strong></p>"
        f"{recap}"
        f"<p style='color:#777;font-size:12px'>{t['footer'].format(ref=ref)}</p>"
        f"<p style='color:#D4AF37'><strong>{t['signature']}</strong></p></div>")
    await send_email(to_email=doc["email"], to_name=doc["name"],
                     subject=t["subject"].format(type=doc.get("type_label") or doc.get("type")),
                     html_content=html, tags=["partner-application-ack"])
