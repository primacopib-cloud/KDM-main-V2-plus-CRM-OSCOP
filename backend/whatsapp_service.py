"""Envoi WhatsApp via Brevo — campagnes Oracle Admin. Réutilise BREVO_API_KEY (déjà en place pour les emails)."""
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)
BREVO = "https://api.brevo.com/v3"


def _headers():
    return {"api-key": os.environ.get("BREVO_API_KEY", ""), "accept": "application/json",
            "content-type": "application/json"}


def is_whatsapp_configured() -> bool:
    return bool(os.environ.get("BREVO_API_KEY"))


async def whatsapp_status() -> dict:
    """Vérifie la connexion WhatsApp Business du compte Brevo."""
    if not is_whatsapp_configured():
        return {"configured": False, "reason": "BREVO_API_KEY absente."}
    sender = re.sub(r"\D", "", os.environ.get("BREVO_WHATSAPP_SENDER", ""))
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BREVO}/whatsappCampaigns/config", headers=_headers())
    except Exception as exc:
        return {"configured": False, "reason": f"Brevo injoignable ({exc})."}
    if r.status_code != 200:
        return {"configured": False, "reason": (
            "le compte WhatsApp Business n'est pas encore connecté à Brevo "
            "(Brevo → Paramètres → WhatsApp → Se connecter avec Facebook).")}
    if not sender:
        return {"configured": False, "reason": (
            "compte WhatsApp connecté à Brevo, mais le numéro émetteur manque — ajoutez "
            "BREVO_WHATSAPP_SENDER (numéro WhatsApp de la société, ex. 590690XXXXXX).")}
    return {"configured": True, "sender": sender, "config": r.json()}


async def send_whatsapp_batch(phones: list, text: str, sender: str) -> dict:
    """Envoie un message WhatsApp à un lot de numéros (E.164 sans « + » pour Brevo)."""
    numbers = [re.sub(r"\D", "", p) for p in phones]
    payload = {"contactNumbers": numbers, "senderNumber": sender}
    template_id = os.environ.get("BREVO_WHATSAPP_TEMPLATE_ID")
    if template_id:
        payload["templateId"] = int(template_id)
    else:
        payload["text"] = text[:4000]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{BREVO}/whatsapp/sendMessage", headers=_headers(), json=payload)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Brevo {r.status_code} : {r.text[:300]}")
    return r.json() if r.text else {}
