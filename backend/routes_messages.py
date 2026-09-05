"""Messagerie interne — tous les membres peuvent s'écrire entre eux (et avec l'admin)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id

logger = logging.getLogger(__name__)

messages_router = APIRouter(prefix="/api/messages", tags=["messages"])

db = None


def set_messages_database(database):
    global db
    db = database


class MessageBody(BaseModel):
    to_user_id: str
    subject: str
    body: str
    reply_to: Optional[str] = None


async def _user_info(uid: str) -> dict:
    u = await db.users.find_one({"id": uid}, {"_id": 0, "id": 1, "email": 1, "name": 1, "full_name": 1, "company": 1, "role": 1})
    if not u:
        u = await db.vendors.find_one({"id": uid}, {"_id": 0, "id": 1, "email": 1, "company_name": 1, "contact_name": 1})
        if u:
            u = {"id": u["id"], "email": u.get("email"), "name": u.get("contact_name"), "company": u.get("company_name"), "role": "vendor"}
    return u or {"id": uid, "name": "Utilisateur", "email": ""}


@messages_router.get("/directory")
async def directory(user_id: str = Depends(get_current_user_id)):
    """Annuaire des destinataires possibles."""
    users = await db.users.find(
        {"id": {"$ne": user_id}},
        {"_id": 0, "id": 1, "email": 1, "name": 1, "full_name": 1, "company": 1, "role": 1}
    ).limit(300).to_list(300)
    out = [{"id": u["id"], "label": f"{u.get('full_name') or u.get('name') or u.get('email')}"
            f"{(' — ' + u['company']) if u.get('company') else ''} ({u.get('role', 'membre')})"} for u in users]
    return {"users": sorted(out, key=lambda x: x["label"].lower())}


@messages_router.post("")
async def send_message(body: MessageBody, user_id: str = Depends(get_current_user_id)):
    if not body.subject.strip() or not body.body.strip():
        raise HTTPException(status_code=400, detail="Objet et message requis")
    sender = await _user_info(user_id)
    recipient = await _user_info(body.to_user_id)
    doc = {
        "id": str(uuid.uuid4()), "from_user_id": user_id, "to_user_id": body.to_user_id,
        "from_label": sender.get("full_name") or sender.get("name") or sender.get("email"),
        "to_label": recipient.get("full_name") or recipient.get("name") or recipient.get("email"),
        "subject": body.subject.strip()[:200], "body": body.body.strip()[:5000],
        "reply_to": body.reply_to, "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.internal_messages.insert_one({**doc})
    try:
        from core_deps import create_notification
        await create_notification("internal_message", "Nouveau message interne",
                                  f"{doc['from_label']} : {doc['subject']}", {"message_id": doc["id"]})
    except Exception:
        pass
    return doc


@messages_router.get("/inbox")
async def inbox(user_id: str = Depends(get_current_user_id)):
    items = await db.internal_messages.find({"to_user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@messages_router.get("/sent")
async def sent(user_id: str = Depends(get_current_user_id)):
    items = await db.internal_messages.find({"from_user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@messages_router.get("/unread-count")
async def unread_count(user_id: str = Depends(get_current_user_id)):
    n = await db.internal_messages.count_documents({"to_user_id": user_id, "read": False})
    return {"unread": n}


@messages_router.post("/{mid}/read")
async def mark_read(mid: str, user_id: str = Depends(get_current_user_id)):
    await db.internal_messages.update_one({"id": mid, "to_user_id": user_id}, {"$set": {"read": True}})
    return {"ok": True}


class ContextualBody(BaseModel):
    to_email: str
    subject: str
    body: str
    context_type: str = "operation"
    context_ref: str = ""


def _fr_date(dt: datetime) -> str:
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{days[dt.weekday()]} {dt.day} {months[dt.month - 1]} {dt.year} à {dt.strftime('%H:%M')}"


async def _send_contextual_email(doc: dict, sender: dict):
    from brevo_service import send_email, _wrap_html
    now = datetime.now(timezone.utc)
    label = "Opération" if doc["context_type"] == "operation" else "Commande"
    html = _wrap_html(doc["subject"], (
        f"<p style='font-size:12px;color:#B8A98F;'>{label} : <b>{doc['context_ref']}</b> — "
        f"Envoyé le {_fr_date(now)}</p>"
        f"<p style='font-size:14px;white-space:pre-line;'>{doc['body']}</p>"
        f"<p style='font-size:12px;color:#B8A98F;'>Expéditeur : {sender.get('name') or ''} "
        f"({sender.get('email') or ''}) — via la messagerie contextuelle de la centrale O'SCOP.</p>"))
    await send_email(doc["to_email"], doc["to_email"], doc["subject"], html, tags=["messagerie-contextuelle"])
    return now


@messages_router.post("/contextual")
async def send_contextual(payload: ContextualBody, user_id: str = Depends(get_current_user_id)):
    sender = await _user_info(user_id)
    doc = {
        "id": str(uuid.uuid4()), "user_id": user_id,
        "to_email": payload.to_email.strip().lower(), "subject": payload.subject.strip(),
        "body": payload.body.strip(), "context_type": payload.context_type,
        "context_ref": payload.context_ref, "resend_count": 0,
    }
    if not doc["to_email"] or not doc["subject"] or not doc["body"]:
        raise HTTPException(status_code=400, detail="Destinataire, objet et message requis")
    sent_at = await _send_contextual_email(doc, sender)
    doc["sent_at"] = sent_at.isoformat()
    doc["last_sent_at"] = doc["sent_at"]
    await db.contextual_messages.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"success": True, "message": doc}


@messages_router.get("/contextual")
async def list_contextual(context_ref: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    q = {"user_id": user_id}
    if context_ref:
        q["context_ref"] = context_ref
    items = await db.contextual_messages.find(q, {"_id": 0}).sort("sent_at", -1).to_list(50)
    return {"messages": items}


@messages_router.post("/contextual/{msg_id}/resend")
async def resend_contextual(msg_id: str, user_id: str = Depends(get_current_user_id)):
    doc = await db.contextual_messages.find_one({"id": msg_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Message introuvable")
    sender = await _user_info(user_id)
    sent_at = await _send_contextual_email(doc, sender)
    await db.contextual_messages.update_one(
        {"id": msg_id},
        {"$set": {"last_sent_at": sent_at.isoformat()}, "$inc": {"resend_count": 1}})
    return {"success": True, "last_sent_at": sent_at.isoformat()}
