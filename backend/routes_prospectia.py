"""PROSPECT'IA — routes admin : génération, storyboard, campagnes d'envoi autonome (Brevo) et tracking."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

prospectia_router = APIRouter(prefix="/api/admin/prospectia", tags=["prospectia"])
prospectia_public_router = APIRouter(prefix="/api/prospectia", tags=["prospectia-public"])

db = None
BATCH_PER_CYCLE = 20


def set_prospectia_database(database):
    global db
    db = database


class GenerateBody(BaseModel):
    target: str = "vendor"
    territory: Optional[str] = ""
    sector: Optional[str] = ""
    lang: str = "fr"
    tone: Optional[str] = ""
    content_type: str = "email"


class StoryboardBody(BaseModel):
    script: str
    hint: Optional[str] = ""


class CampaignBody(BaseModel):
    name: str
    subject: str
    body: str
    prospects_csv: str
    library_id: Optional[str] = None


async def _require_enabled():
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(db)
    if not s.get("prospectia_enabled"):
        raise HTTPException(status_code=403, detail="PROSPECT'IA est désactivé — activez-le d'abord")


@prospectia_router.post("/generate")
async def generate(body: GenerateBody, admin: dict = Depends(require_admin)):
    await _require_enabled()
    from prospectia_service import generate_script
    content = await generate_script(body.target, body.territory, body.sector, body.lang, body.tone, body.content_type)
    from consultation_audit import audit
    await audit("PROSPECTIA_GENERATED", admin.get("email"), None, {"target": body.target, "type": body.content_type, "lang": body.lang})
    return {"content": content}


@prospectia_router.post("/storyboard")
async def storyboard(body: StoryboardBody, admin: dict = Depends(require_admin)):
    await _require_enabled()
    from prospectia_service import generate_storyboard_images
    urls = await generate_storyboard_images(body.script, body.hint or "")
    if not urls:
        raise HTTPException(status_code=502, detail="Génération d'images indisponible, réessayez")
    return {"images": urls}


def _parse_prospects(csv_text: str) -> list:
    prospects = []
    for line in csv_text.strip().splitlines():
        parts = [p.strip() for p in line.replace(";", ",").split(",")]
        if not parts or "@" not in parts[0]:
            continue
        prospects.append({
            "id": uuid.uuid4().hex[:10], "email": parts[0].lower(),
            "company": parts[1] if len(parts) > 1 else "",
            "first_name": parts[2] if len(parts) > 2 else "",
            "status": "pending", "clicked": False,
        })
    return prospects[:500]


@prospectia_router.post("/campaigns")
async def create_campaign(body: CampaignBody, admin: dict = Depends(require_admin)):
    await _require_enabled()
    prospects = _parse_prospects(body.prospects_csv)
    if not prospects:
        raise HTTPException(status_code=400, detail="Aucun prospect valide (format : email, entreprise, prénom — un par ligne)")
    for i, p in enumerate(prospects):
        p["variant"] = "A" if i % 2 == 0 else "B"
        p["followups"] = 0
        p["converted"] = False
    from prospectia_service import generate_campaign_extras
    extras = await generate_campaign_extras(body.subject.strip(), body.body)
    doc = {
        "id": str(uuid.uuid4()), "name": body.name.strip() or "Campagne", "subject": body.subject.strip(),
        "subject_b": extras["subject_b"], "followup_1": extras["followup_1"], "followup_2": extras["followup_2"],
        "body": body.body, "prospects": prospects, "status": "running",
        "sent_count": 0, "click_count": 0, "clicks_a": 0, "clicks_b": 0,
        "followups_count": 0, "conversions_count": 0, "library_id": body.library_id,
        "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.prospectia_campaigns.insert_one({**doc})
    from consultation_audit import audit
    await audit("PROSPECTIA_CAMPAIGN_CREATED", admin.get("email"), None, {"name": doc["name"], "prospects": len(prospects), "ab_test": True})
    await process_prospectia_campaigns(db)
    fresh = await db.prospectia_campaigns.find_one({"id": doc["id"]}, {"_id": 0, "prospects": 0})
    return fresh


@prospectia_router.get("/campaigns")
async def list_campaigns(admin: dict = Depends(require_admin)):
    items = await db.prospectia_campaigns.find({}, {"_id": 0, "body": 0}).sort("created_at", -1).to_list(50)
    for c in items:
        c["prospects_total"] = len(c.pop("prospects", []))
    return {"items": items}


@prospectia_router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, admin: dict = Depends(require_admin)):
    c = await db.prospectia_campaigns.find_one({"id": campaign_id})
    if not c:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    new_status = "paused" if c["status"] == "running" else "running"
    await db.prospectia_campaigns.update_one({"id": campaign_id}, {"$set": {"status": new_status}})
    return {"ok": True, "status": new_status}


@prospectia_public_router.get("/c/{campaign_id}/{prospect_id}")
async def track_click(campaign_id: str, prospect_id: str):
    c = await db.prospectia_campaigns.find_one({"id": campaign_id}, {"_id": 0, "prospects": 1})
    if c:
        p = next((x for x in c["prospects"] if x["id"] == prospect_id), None)
        if p and not p.get("clicked"):
            inc = {"click_count": 1, f"clicks_{(p.get('variant') or 'a').lower()}": 1}
            await db.prospectia_campaigns.update_one(
                {"id": campaign_id, "prospects.id": prospect_id},
                {"$set": {"prospects.$.clicked": True}, "$inc": inc})
    base = os.environ.get("FRONTEND_URL", "").rstrip("/") or "/"
    return RedirectResponse(url=f"{base}/adhesion" if base != "/" else "/")


def _render(body: str, p: dict, link: str) -> str:
    text = body.replace("{prenom}", p.get("first_name") or "").replace("{entreprise}", p.get("company") or "votre entreprise").replace("{lien}", link)
    return "<div style='font-family:Arial,sans-serif;max-width:560px;white-space:pre-line'>" + text + \
           f"<p style='margin-top:16px'><a href='{link}' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Découvrir la Communityplace</a></p>" + \
           "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — Communityplace B2B ESS des Outre-mer</p></div>"


async def _check_conversions(database, c: dict) -> None:
    emails = [p["email"] for p in c.get("prospects", []) if p.get("status") == "sent" and not p.get("converted")]
    if not emails:
        return
    converted = set()
    for coll in ("users", "partner_applications", "quote_requests"):
        for e in await database[coll].distinct("email", {"email": {"$in": emails}}):
            converted.add(e.lower())
    for email in converted:
        await database.prospectia_campaigns.update_one(
            {"id": c["id"], "prospects.email": email, "prospects.converted": False},
            {"$set": {"prospects.$.converted": True}, "$inc": {"conversions_count": 1}})
    if converted:
        logger.info("PROSPECT'IA : %s conversion(s) détectée(s) sur %s", len(converted), c["name"])


async def _send_followups(database, c: dict, base: str) -> None:
    from brevo_service import send_email
    now = datetime.now(timezone.utc)
    sent_fu = 0
    for p in c.get("prospects", []):
        if p.get("status") != "sent" or p.get("clicked") or p.get("converted") or not p.get("sent_at"):
            continue
        try:
            age_days = (now - datetime.fromisoformat(p["sent_at"])).days
        except Exception:
            continue
        fu = p.get("followups", 0)
        body, subj = None, None
        if fu == 0 and age_days >= 3 and c.get("followup_1"):
            body, subj = c["followup_1"], f"Re : {c['subject']}"
        elif fu == 1 and age_days >= 7 and c.get("followup_2"):
            body, subj = c["followup_2"], f"Dernière invitation — {c['subject']}"
        if not body:
            continue
        link = f"{base}/api/prospectia/c/{c['id']}/{p['id']}"
        try:
            await send_email(to_email=p["email"], to_name=p.get("first_name") or None,
                             subject=subj, html_content=_render(body, p, link), tags=["prospectia-followup"])
            sent_fu += 1
            await database.prospectia_campaigns.update_one(
                {"id": c["id"], "prospects.id": p["id"]},
                {"$set": {"prospects.$.followups": fu + 1}, "$inc": {"followups_count": 1}})
        except Exception as exc:
            logger.warning("PROSPECT'IA relance échouée %s : %s", p["email"], exc)
        if sent_fu >= BATCH_PER_CYCLE:
            break
    if sent_fu:
        logger.info("PROSPECT'IA : %s relance(s) J+3/J+7 envoyées (%s)", sent_fu, c["name"])


async def process_prospectia_campaigns(database) -> None:
    """Scheduler : envois initiaux (A/B), relances J+3/J+7 des non-cliqueurs, détection des conversions."""
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(database)
    if not s.get("prospectia_enabled"):
        return
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    campaigns = await database.prospectia_campaigns.find({"status": "running"}).to_list(20)
    for c in campaigns:
        pending = [p for p in c.get("prospects", []) if p.get("status") == "pending"][:BATCH_PER_CYCLE]
        from brevo_service import send_email
        sent = 0
        for p in pending:
            link = f"{base}/api/prospectia/c/{c['id']}/{p['id']}"
            subject = c.get("subject_b") if p.get("variant") == "B" and c.get("subject_b") else c["subject"]
            status = "sent"
            try:
                await send_email(to_email=p["email"], to_name=p.get("first_name") or None,
                                 subject=subject, html_content=_render(c["body"], p, link), tags=["prospectia"])
                sent += 1
            except Exception as exc:
                status = "failed"
                logger.warning("PROSPECT'IA envoi échoué %s : %s", p["email"], exc)
            await database.prospectia_campaigns.update_one(
                {"id": c["id"], "prospects.id": p["id"]},
                {"$set": {"prospects.$.status": status, "prospects.$.sent_at": datetime.now(timezone.utc).isoformat()}})
        if sent:
            await database.prospectia_campaigns.update_one({"id": c["id"]}, {"$inc": {"sent_count": sent}})
            logger.info("PROSPECT'IA : %s email(s) envoyés pour la campagne %s", sent, c["name"])
        fresh = await database.prospectia_campaigns.find_one({"id": c["id"]})
        await _check_conversions(database, fresh)
        fresh = await database.prospectia_campaigns.find_one({"id": c["id"]})
        await _send_followups(database, fresh, base)
        fresh = await database.prospectia_campaigns.find_one({"id": c["id"]})
        active = any(p.get("status") == "pending" or
                     (p.get("status") == "sent" and not p.get("clicked") and not p.get("converted") and p.get("followups", 0) < 2)
                     for p in fresh.get("prospects", []))
        if not active:
            await database.prospectia_campaigns.update_one({"id": c["id"]}, {"$set": {"status": "done"}})
