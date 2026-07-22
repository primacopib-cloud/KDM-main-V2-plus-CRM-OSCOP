"""PROSPECT'IA — Preuve sociale : témoignages membres (collecte IA, modération, traduction, affichage public)."""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
social_admin_router = APIRouter(prefix="/api/admin/social-proof", tags=["social-proof"])
social_public_router = APIRouter(prefix="/api/public/testimonials", tags=["social-proof-public"])
db = None


def set_social_proof_database(database):
    global db
    db = database


class TestimonialSubmit(BaseModel):
    name: str
    company: Optional[str] = ""
    role: Optional[str] = ""
    territory: Optional[str] = ""
    email: Optional[str] = ""
    rating: int = 5
    text: str


class ModerateBody(BaseModel):
    status: str  # approved | rejected


class InviteBody(BaseModel):
    limit: int = 20


@social_public_router.post("")
async def submit_testimonial(body: TestimonialSubmit, request: Request):
    if len(body.text.strip()) < 15:
        raise HTTPException(status_code=400, detail="Témoignage trop court (15 caractères minimum)")
    verified = False
    email = (body.email or "").strip().lower()[:120]
    try:
        from auth import extract_user_id_from_request
        uid = extract_user_id_from_request(request)
        if uid:
            u = await db.users.find_one({"id": uid}, {"email": 1})
            if u:
                verified = True
                email = email or u.get("email", "")
    except Exception:
        pass
    doc = {
        "id": str(uuid.uuid4()), "name": body.name.strip()[:80], "company": (body.company or "").strip()[:80],
        "role": (body.role or "").strip()[:80], "territory": (body.territory or "").strip()[:60],
        "email": email, "rating": max(1, min(5, body.rating)), "text": body.text.strip()[:900],
        "status": "pending", "source": "public", "verified_member": verified,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.testimonials.insert_one({**doc})
    return {"ok": True, "verified_member": verified, "message": "Merci ! Votre témoignage sera publié après modération."}


@social_public_router.get("")
async def public_testimonials(lang: str = "fr"):
    items = await db.testimonials.find(
        {"status": "approved"},
        {"_id": 0, "id": 1, "name": 1, "company": 1, "role": 1, "territory": 1, "rating": 1,
         "text": 1, "text_en": 1, "text_es": 1, "verified_member": 1},
    ).sort("created_at", -1).to_list(12)
    for t in items:
        if lang == "en" and t.get("text_en"):
            t["text"] = t["text_en"]
        elif lang == "es" and t.get("text_es"):
            t["text"] = t["text_es"]
        t.pop("text_en", None)
        t.pop("text_es", None)
    return {"items": items}


@social_admin_router.get("/testimonials")
async def list_all(admin: dict = Depends(require_admin)):
    items = await db.testimonials.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    invited = await db.testimonial_invites.count_documents({})
    return {"items": items, "invited_count": invited}


async def _translate_testimonial(tid: str) -> None:
    """Traduit le témoignage en EN et ES (stocké en text_en / text_es)."""
    t = await db.testimonials.find_one({"id": tid}, {"text": 1})
    if not t:
        return
    import json as _json
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"social-translate-{uuid.uuid4()}",
            system_message="Tu es traducteur professionnel. Réponds UNIQUEMENT en JSON valide.",
        ).with_model("openai", "gpt-5.4")
        raw = str(await chat.send_message(UserMessage(text=(
            f"Traduis ce témoignage client en anglais et en espagnol (naturel, première personne) :\n{t['text']}\n\n"
            'JSON brut avec les clés "en" et "es" uniquement, sans markdown.')))).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = _json.loads(raw)
        await db.testimonials.update_one(
            {"id": tid}, {"$set": {"text_en": (data.get("en") or "").strip()[:900],
                                   "text_es": (data.get("es") or "").strip()[:900]}})
        logger.info("Témoignage %s traduit EN/ES", tid)
    except Exception as exc:
        logger.error("Traduction témoignage %s échouée : %s", tid, exc)


@social_admin_router.patch("/testimonials/{tid}")
async def moderate(tid: str, body: ModerateBody, admin: dict = Depends(require_admin)):
    if body.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Statut invalide")
    res = await db.testimonials.update_one({"id": tid}, {"$set": {"status": body.status}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Témoignage introuvable")
    if body.status == "approved":
        asyncio.create_task(_translate_testimonial(tid))
    from consultation_audit import audit
    await audit("TESTIMONIAL_MODERATED", admin.get("email"), None, {"id": tid, "status": body.status})
    return {"ok": True}


async def _require_prospectia():
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(db)
    if not s.get("prospectia_enabled"):
        raise HTTPException(status_code=403, detail="PROSPECT'IA est désactivé — activez-le d'abord")


@social_admin_router.post("/testimonials/{tid}/polish")
async def polish(tid: str, admin: dict = Depends(require_admin)):
    await _require_prospectia()
    t = await db.testimonials.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Témoignage introuvable")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"social-polish-{uuid.uuid4()}",
        system_message="Tu es PROSPECT'IA. Tu reformules des témoignages clients pour un site web : corrige orthographe et syntaxe, garde la voix authentique et le fond exact, 40 à 70 mots, à la première personne, en français. Réponds uniquement avec le texte reformulé.",
    ).with_model("openai", "gpt-5.4")
    polished = str(await chat.send_message(UserMessage(text=t["text"]))).strip().strip('"')
    await db.testimonials.update_one(
        {"id": tid},
        {"$set": {"text": polished[:900], "text_original": t.get("text_original") or t["text"], "polished": True}})
    if t.get("status") == "approved":
        asyncio.create_task(_translate_testimonial(tid))
    from consultation_audit import audit
    await audit("TESTIMONIAL_POLISHED", admin.get("email"), None, {"id": tid})
    return {"ok": True, "text": polished}


async def _generate_invite_email() -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"social-invite-{uuid.uuid4()}",
        system_message="Tu es PROSPECT'IA, copywriter de la Communityplace KDMARCHÉ × O'SCOP (plateforme coopérative B2B des Outre-mer). Réponds uniquement avec le contenu demandé.",
    ).with_model("openai", "gpt-5.4")
    prompt = ("Rédige un email court (80-120 mots) invitant chaleureusement un membre de la plateforme à laisser un témoignage "
              "sur son expérience (2 minutes, aide la coopérative à grandir). Un seul appel à l'action vers {lien}. "
              "Pas d'objet, pas de placeholder autre que {lien}. Français, ton coopératif et reconnaissant.")
    return str(await chat.send_message(UserMessage(text=prompt))).strip()


def _invite_html(body_text: str, link: str) -> str:
    return ("<div style='font-family:Arial,sans-serif;max-width:560px;white-space:pre-line'>" + body_text.replace("{lien}", link) +
            f"<p style='margin-top:16px'><a href='{link}' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Laisser mon témoignage</a></p>"
            "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — Communityplace B2B ESS des Outre-mer</p></div>")


@social_admin_router.post("/invite")
async def invite_members(body: InviteBody, admin: dict = Depends(require_admin)):
    await _require_prospectia()
    already = {d["email"] async for d in db.testimonial_invites.find({}, {"email": 1})}
    already |= {t["email"] async for t in db.testimonials.find({"email": {"$ne": ""}}, {"email": 1})}
    users = await db.users.find(
        {"role": {"$in": ["vendor", "buyer"]}, "email": {"$nin": list(already)}},
        {"_id": 0, "email": 1, "first_name": 1, "name": 1},
    ).to_list(max(1, min(body.limit, 100)))
    if not users:
        return {"ok": True, "sent": 0, "message": "Aucun nouveau membre à inviter"}
    template = await _generate_invite_email()
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    html = _invite_html(template, f"{base}/temoignage")
    from brevo_service import send_email
    sent = 0
    for u in users:
        try:
            await send_email(to_email=u["email"], to_name=u.get("first_name") or u.get("name"),
                             subject="Votre avis compte pour la Communityplace 💜",
                             html_content=html, tags=["testimonial-invite"])
            sent += 1
            await db.testimonial_invites.insert_one({"email": u["email"], "sent_at": datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            logger.warning("Invitation témoignage échouée %s : %s", u["email"], exc)
    from consultation_audit import audit
    await audit("TESTIMONIAL_INVITES_SENT", admin.get("email"), None, {"sent": sent})
    return {"ok": True, "sent": sent, "template": template}


async def process_testimonial_reminders(database) -> None:
    """Relance J+7 des membres invités qui n'ont pas encore témoigné (une seule relance)."""
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(database)
    if not s.get("prospectia_enabled"):
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    invites = await database.testimonial_invites.find(
        {"sent_at": {"$lt": cutoff}, "reminder_sent": {"$ne": True}}).to_list(20)
    if not invites:
        return
    testified = {t["email"] async for t in database.testimonials.find({"email": {"$ne": ""}}, {"email": 1})}
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/temoignage"
    html = ("<div style='font-family:Arial,sans-serif;max-width:560px'>"
            "<p>Bonjour,</p><p>Il y a quelques jours, nous vous invitions à partager votre expérience sur la "
            "Communityplace KDMARCHÉ × O'SCOP. Votre avis compte énormément pour la coopérative et les futurs membres — "
            "2 minutes suffisent.</p>"
            f"<p><a href='{link}' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Laisser mon témoignage</a></p>"
            "<p style='color:#999;font-size:10px;margin-top:18px'>PROSPECT'IA — KDMARCHÉ × O'SCOP</p></div>")
    from brevo_service import send_email
    sent = 0
    for inv in invites:
        if inv["email"] in testified:
            await database.testimonial_invites.update_one({"_id": inv["_id"]}, {"$set": {"reminder_sent": True, "converted": True}})
            continue
        try:
            await send_email(to_email=inv["email"], to_name=None,
                             subject="Un petit rappel — votre témoignage compte 💜",
                             html_content=html, tags=["testimonial-reminder"])
            sent += 1
        except Exception as exc:
            logger.warning("Relance témoignage échouée %s : %s", inv["email"], exc)
        await database.testimonial_invites.update_one({"_id": inv["_id"]}, {"$set": {"reminder_sent": True}})
    if sent:
        logger.info("PROSPECT'IA : %s relance(s) témoignage J+7 envoyées", sent)
