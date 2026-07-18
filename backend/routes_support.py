"""Formulaire de contact support — envoi via Brevo + ticket en base."""
import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import brevo_service
from brevo_service import _wrap_html

logger = logging.getLogger(__name__)

support_router = APIRouter(prefix="/api/support")

db = None


def set_support_database(database):
    global db
    db = database


CATEGORY_LABELS = {
    "GENERAL": "Question générale",
    "COMPTE": "Compte & connexion",
    "COMMANDE": "Commandes & livraison",
    "PAIEMENT": "Paiement & facturation",
    "CREDISCOP": "CREDI'SCOP & crédits",
    "TECHNIQUE": "Problème technique",
}


class ContactForm(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=200)
    subject: str = Field(..., min_length=3, max_length=200)
    category: str = "GENERAL"
    message: str = Field(..., min_length=10, max_length=5000)


@support_router.post("/contact")
async def submit_contact(form: ContactForm):
    if "@" not in form.email or "." not in form.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Adresse email invalide")

    category = form.category if form.category in CATEGORY_LABELS else "GENERAL"
    ticket_id = f"SUP-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    ticket = {
        "id": str(uuid.uuid4()),
        "ticket_number": ticket_id,
        "name": form.name.strip(),
        "email": form.email.strip().lower(),
        "subject": form.subject.strip(),
        "category": category,
        "message": form.message.strip(),
        "status": "OPEN",
        "created_at": datetime.utcnow(),
    }
    await db.support_tickets.insert_one(ticket)

    support_email = os.environ.get("SUPPORT_CONTACT_EMAIL", "contact@centrale-ess.fr")
    cat_label = CATEGORY_LABELS[category]
    msg_html = form.message.strip().replace("\n", "<br/>")

    admin_body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Nouveau message support — {ticket_id}</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        <strong>De :</strong> {form.name} &lt;{form.email}&gt;<br/>
        <strong>Catégorie :</strong> {cat_label}<br/>
        <strong>Sujet :</strong> {form.subject}
      </p>
      <div style=\"background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;color:rgba(255,255,255,0.85);font-size:14px;\">{msg_html}</div>
    """
    user_body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Votre demande a bien été reçue ✅</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        Bonjour {form.name},<br/><br/>
        Nous avons bien reçu votre message (référence <strong>{ticket_id}</strong>) concernant :
        <em>{form.subject}</em>.<br/><br/>
        Notre équipe support vous répondra dans les plus brefs délais à l'adresse {form.email}.
      </p>
    """

    try:
        await brevo_service.send_email(
            to_email=support_email, to_name="Support Communityplace",
            subject=f"[Support {ticket_id}] {form.subject}",
            html_content=_wrap_html("Nouveau message support", admin_body),
            tags=["support-contact"],
        )
        await brevo_service.send_email(
            to_email=ticket["email"], to_name=form.name,
            subject=f"Votre demande {ticket_id} — Support Communityplace",
            html_content=_wrap_html("Demande reçue", user_body),
            tags=["support-confirmation"],
        )
    except Exception as e:
        logger.error("Brevo support email failed: %s", e)

    return {"ok": True, "ticket_number": ticket_id}
