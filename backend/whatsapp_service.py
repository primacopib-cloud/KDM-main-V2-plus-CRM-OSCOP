"""Envoi WhatsApp (Twilio) — campagnes Oracle Admin. Actif dès que les clés TWILIO_* sont fournies."""
import json
import logging
import os

logger = logging.getLogger(__name__)


def is_whatsapp_configured() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN")
                and os.environ.get("TWILIO_WHATSAPP_FROM"))


def send_whatsapp(phone: str, body: str) -> dict:
    """Envoie un message WhatsApp (fenêtre 24 h ou sandbox). phone au format E.164 (+590...)."""
    from twilio.rest import Client
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    kwargs = {"from_": os.environ["TWILIO_WHATSAPP_FROM"], "to": f"whatsapp:{phone}"}
    content_sid = os.environ.get("TWILIO_CONTENT_SID")
    if content_sid:
        kwargs["content_sid"] = content_sid
        kwargs["content_variables"] = json.dumps({"1": body[:600]})
    else:
        kwargs["body"] = body[:1500]
    msg = client.messages.create(**kwargs)
    return {"sid": msg.sid, "status": msg.status}
