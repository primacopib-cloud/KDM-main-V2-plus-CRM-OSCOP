"""Formulaire de contact support — envoi via Brevo + ticket en base + gestion admin."""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

import brevo_service
from brevo_service import _wrap_html
from auth import get_current_user_id
from admin_guard import require_admin

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


@support_router.get("/admin/stats")
async def support_stats(user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    tickets = await db.support_tickets.find(
        {}, {"_id": 0, "category": 1, "status": 1, "created_at": 1, "replies": 1}
    ).to_list(2000)
    by_category, delays = {}, []
    by_status = {"OPEN": 0, "ANSWERED": 0, "CLOSED": 0}
    for t in tickets:
        cat = t.get("category") or "GENERAL"
        by_category[cat] = by_category.get(cat, 0) + 1
        st = t.get("status") or "OPEN"
        by_status[st] = by_status.get(st, 0) + 1
        admin_replies = [r for r in (t.get("replies") or []) if not r.get("from_client")]
        if admin_replies and t.get("created_at"):
            delays.append((admin_replies[0]["at"] - t["created_at"]).total_seconds())
    avg_hours = round(sum(delays) / len(delays) / 3600, 1) if delays else None
    return {
        "total": len(tickets),
        "avg_first_response_hours": avg_hours,
        "by_category": by_category,
        "by_status": by_status,
    }


@support_router.get("/admin/open-count")
async def open_tickets_count(user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    return {"open": await db.support_tickets.count_documents({"status": "OPEN"})}


@support_router.get("/my-tickets")
async def my_tickets(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    tickets = await db.support_tickets.find(
        {"email": user["email"].lower()}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"tickets": tickets}


@support_router.get("/my-tickets/unread-count")
async def my_unread_count(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    if not user or not user.get("email"):
        return {"unread": 0}
    unread = await db.support_tickets.count_documents(
        {"email": user["email"].lower(), "user_unread": True}
    )
    return {"unread": unread}


@support_router.post("/my-tickets/mark-read")
async def my_tickets_mark_read(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    await db.support_tickets.update_many(
        {"email": user["email"].lower(), "user_unread": True},
        {"$set": {"user_unread": False}},
    )
    return {"ok": True}


class TicketReopen(BaseModel):
    message: Optional[str] = Field(None, max_length=5000)


@support_router.post("/my-tickets/{ticket_id}/reopen")
async def reopen_ticket(
    ticket_id: str,
    payload: TicketReopen,
    user_id: str = Depends(get_current_user_id),
):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    ticket = await db.support_tickets.find_one(
        {"id": ticket_id, "email": user["email"].lower()}, {"_id": 0}
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    if ticket["status"] != "CLOSED":
        raise HTTPException(status_code=400, detail="Seul un ticket fermé peut être relancé")

    update = {"$set": {"status": "OPEN", "updated_at": datetime.utcnow()}}
    if payload.message and payload.message.strip():
        update["$push"] = {"replies": {
            "message": payload.message.strip(),
            "from_client": True,
            "at": datetime.utcnow(),
        }}
    await db.support_tickets.update_one({"id": ticket_id}, update)

    support_email = os.environ.get("SUPPORT_CONTACT_EMAIL", "contact@centrale-ess.fr")
    note = (payload.message or "").strip().replace("\n", "<br/>") or "<em>Sans message complémentaire.</em>"
    body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Ticket relancé — {ticket['ticket_number']}</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        {ticket['name']} &lt;{ticket['email']}&gt; a rouvert le ticket : <em>{ticket['subject']}</em>
      </p>
      <div style=\"background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;color:rgba(255,255,255,0.85);font-size:14px;\">{note}</div>
    """
    try:
        await brevo_service.send_email(
            to_email=support_email, to_name="Support Communityplace",
            subject=f"[Relance {ticket['ticket_number']}] {ticket['subject']}",
            html_content=_wrap_html("Ticket relancé", body),
            tags=["support-reopen"],
        )
    except Exception as e:
        logger.error("Brevo reopen email failed: %s", e)

    return {"ok": True, "status": "OPEN"}


# ============== ADMIN — GESTION DES TICKETS ==============

class TicketReply(BaseModel):
    message: str = Field(..., min_length=2, max_length=5000)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(OPEN|ANSWERED|CLOSED)$")


@support_router.get("/admin/tickets")
async def list_tickets(
    status_filter: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    await require_admin(user_id)
    query = {}
    if status_filter in {"OPEN", "ANSWERED", "CLOSED"}:
        query["status"] = status_filter
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    counts = {s: await db.support_tickets.count_documents({"status": s}) for s in ("OPEN", "ANSWERED", "CLOSED")}
    return {"tickets": tickets, "counts": counts}


@support_router.post("/admin/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: str,
    reply: TicketReply,
    user_id: str = Depends(get_current_user_id),
):
    admin = await require_admin(user_id)
    ticket = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket introuvable")

    reply_entry = {
        "message": reply.message.strip(),
        "admin_name": admin.get("contact_name") or admin.get("email") or "Support",
        "at": datetime.utcnow(),
    }
    await db.support_tickets.update_one(
        {"id": ticket_id},
        {"$push": {"replies": reply_entry},
         "$set": {"status": "ANSWERED", "user_unread": True, "updated_at": datetime.utcnow()}},
    )

    reply_html = reply.message.strip().replace("\n", "<br/>")
    body = f"""
      <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Réponse à votre demande {ticket['ticket_number']}</h2>
      <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
        Bonjour {ticket['name']},<br/><br/>
        Concernant votre demande : <em>{ticket['subject']}</em>
      </p>
      <div style=\"background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;color:rgba(255,255,255,0.85);font-size:14px;\">{reply_html}</div>
      <p style=\"color:rgba(255,255,255,0.55);font-size:12px;margin-top:16px;\">— L'équipe support Communityplace</p>
    """
    try:
        await brevo_service.send_email(
            to_email=ticket["email"], to_name=ticket["name"],
            subject=f"Re: [{ticket['ticket_number']}] {ticket['subject']}",
            html_content=_wrap_html("Réponse du support", body),
            tags=["support-reply"],
        )
    except Exception as e:
        logger.error("Brevo reply email failed: %s", e)

    return {"ok": True, "status": "ANSWERED"}


@support_router.patch("/admin/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    update: TicketStatusUpdate,
    user_id: str = Depends(get_current_user_id),
):
    await require_admin(user_id)
    res = await db.support_tickets.update_one(
        {"id": ticket_id},
        {"$set": {"status": update.status, "updated_at": datetime.utcnow()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return {"ok": True, "status": update.status}
