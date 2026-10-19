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

async def _check_whatsapp_approvals(db):
    """Synchronise les statuts de templates et expédie les campagnes en attente dès approbation Meta."""
    import asyncio as _a  # noqa: F401
    from datetime import datetime, timedelta, timezone
    if not is_whatsapp_configured():
        return
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BREVO}/whatsappCampaigns/template-list?limit=50", headers=_headers())
    if r.status_code != 200:
        return
    templates = {t["id"]: t for t in (r.json().get("templates") or [])}
    async for doc in db.whatsapp_templates.find({"brevo_template_id": {"$exists": True}}):
        t = templates.get(doc["brevo_template_id"])
        if t and (t.get("status") or "").upper() != doc.get("brevo_status"):
            upd = {"brevo_status": (t.get("status") or "").upper()}
            if t.get("status") == "approved":
                upd["status"] = "APPROUVÉ"
            await db.whatsapp_templates.update_one({"id": doc["id"]}, {"$set": upd})
            logger.info("Template WhatsApp %s → %s", doc["id"], upd["brevo_status"])
    async for auto in db.whatsapp_autosend.find({"status": "WAITING"}):
        tpl_doc = await db.whatsapp_templates.find_one({"id": auto.get("template_key")})
        bid = (tpl_doc or {}).get("brevo_template_id")
        t = templates.get(bid)
        if not t or t.get("status") != "approved":
            continue
        sender = re.sub(r"\D", "", os.environ.get("BREVO_WHATSAPP_SENDER", ""))
        if not sender:
            continue
        sched = (datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        payload = {"name": auto.get("campaign_name", "Campagne Oracle"), "templateId": bid,
                   "senderNumber": sender, "scheduledAt": sched,
                   "recipients": {"listIds": auto.get("list_ids", [])}}
        async with httpx.AsyncClient(timeout=30) as c:
            rc = await c.post(f"{BREVO}/whatsappCampaigns", headers=_headers(), json=payload)
        if rc.status_code not in (200, 201):
            logger.warning("Auto-campagne WhatsApp refusée (%s) : %s", rc.status_code, rc.text[:200])
            continue
        cid = (rc.json() or {}).get("id")
        await db.whatsapp_autosend.update_one(
            {"id": auto["id"]},
            {"$set": {"status": "SENT", "campaign_id": cid,
                      "sent_at": datetime.now(timezone.utc).isoformat()}})
        logger.info("Auto-campagne WhatsApp « %s » expédiée (campagne Brevo %s)", auto.get("campaign_name"), cid)
        try:
            from brevo_service import send_email
            admins = await db.users.find(
                {"role": {"$in": ["SUPER_ADMIN", "oscop_super_admin", "ADMIN"]},
                 "email": {"$nin": ["", None]}}, {"_id": 0, "email": 1, "name": 1}).to_list(10)
            for a in admins:
                await send_email(
                    a["email"], a.get("name"),
                    "WhatsApp : modèle approuvé — campagne expédiée automatiquement",
                    ("<p>Le modèle WhatsApp « " + str((tpl_doc or {}).get("title", "")) + " » vient d'être "
                     "approuvé par Meta.</p><p>Oracle a expédié automatiquement la campagne « "
                     + str(auto.get("campaign_name")) + " » (envoi programmé sous 2 minutes). "
                     "Vérifiez la réception sur WhatsApp.</p>"),
                    tags=["whatsapp-auto"])
        except Exception:
            logger.warning("Notification admin auto-campagne échouée")


async def whatsapp_approval_loop(db):
    """Vérifie toutes les 10 min l'approbation Meta des templates et expédie les campagnes en attente."""
    import asyncio
    await asyncio.sleep(20)
    while True:
        try:
            await _check_whatsapp_approvals(db)
        except Exception:
            logger.exception("WhatsApp approval watcher crashed")
        await asyncio.sleep(600)
