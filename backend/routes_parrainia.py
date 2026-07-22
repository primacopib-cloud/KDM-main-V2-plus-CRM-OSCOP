"""PARRAIN'IA — agent IA qui lance, anime et suit le(s) programme(s) de parrainage."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin
from ai_usage import log_ai_usage

logger = logging.getLogger(__name__)
parrainia_router = APIRouter(prefix="/api/admin/parrainia", tags=["parrainia"])
db = None

KINDS = {
    "kickoff": "coup d'envoi du défi parrainage du mois (annonce, récompenses, motivation à partager son code)",
    "boost": "relance de mi-mois pour animer le classement (rappeler le rang, ce qu'il manque pour le podium, urgence douce)",
}


def set_parrainia_database(database):
    global db
    db = database


async def _sponsors(database, limit: int = 100) -> list:
    ids = await database.referral_links.distinct("sponsor_id")
    if not ids:
        return []
    return await database.users.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "email": 1, "first_name": 1}).to_list(limit)


async def _generate_template(kind: str, month: str, tiers: list) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"parrainia-{uuid.uuid4()}",
        system_message=("Tu es PARRAIN'IA, l'animateur du programme de parrainage de la Communityplace "
                        "coopérative KDMARCHÉ × O'SCOP (Outre-mer). Ton chaleureux, motivant, esprit coopératif. "
                        "Réponds UNIQUEMENT en JSON valide, sans markdown."),
    ).with_model("openai", "gpt-5.4")
    rewards = f"🥇 +{tiers[0]}" + (f" · 🥈 +{tiers[1]}" if tiers[1] else "") + (f" · 🥉 +{tiers[2]}" if tiers[2] else "") + " CREDI'SCOP"
    prompt = (
        f"Rédige l'email de {KINDS[kind]} pour le défi parrainage du mois {month}. "
        f"Récompenses du podium : {rewards}. "
        "Utilise LITTÉRALEMENT ces variables dans le texte (elles seront remplacées pour chaque membre) : "
        "{prenom} (prénom), {classement} (ex: '#2' ou 'non classé'), {filleuls} (nombre de filleuls ce mois-ci), "
        "{recompense} (récompense du podium), {lien} (lien vers l'espace membre). "
        'JSON attendu : {"subject" (objet accrocheur avec emoji), "body" (HTML simple <p>/<b>, 100-150 mots, '
        "un bouton/lien d'action vers {lien})}."
    )
    data = str(await chat.send_message(UserMessage(text=prompt))).strip()
    if data.startswith("```"):
        data = data.split("```")[1].lstrip("json").strip()
    return json.loads(data)


async def run_parrainia_campaign(database, kind: str, triggered_by: str) -> dict:
    from referral_challenge import _get_settings, _leaderboard
    settings = await _get_settings(database)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    launched = False
    if kind == "kickoff" and not settings.get("enabled"):
        await database.referral_challenge_settings.update_one(
            {"id": "default"}, {"$set": {"enabled": True}}, upsert=True)
        settings["enabled"] = True
        launched = True
    tiers = [settings.get("reward_credits", 50), settings.get("reward_2nd", 0), settings.get("reward_3rd", 0)]
    rewards_str = f"+{tiers[0]}" + (f" / +{tiers[1]}" if tiers[1] else "") + (f" / +{tiers[2]}" if tiers[2] else "") + " CREDI'SCOP"
    board = await _leaderboard(database, month, limit=100)
    ranks = {r["sponsor_id"]: (i + 1, r["referred"]) for i, r in enumerate(board)}
    sponsors = await _sponsors(database)
    if not sponsors:
        return {"sent": 0, "message": "Aucun parrain à animer pour le moment", "launched": launched}
    template = await _generate_template(kind, month, tiers)
    await log_ai_usage(database, "parrainia_campaign", f"{kind} {month}")
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    from brevo_service import send_email
    sent = 0
    for u in sponsors:
        if not u.get("email"):
            continue
        rank, count = ranks.get(u["id"], (None, 0))
        repl = {"{prenom}": u.get("first_name") or "cher membre",
                "{classement}": f"#{rank}" if rank else "non classé",
                "{filleuls}": str(count), "{recompense}": rewards_str,
                "{lien}": f"{base}/vendor?tab=cpc"}
        subject, body = template.get("subject", ""), template.get("body", "")
        for k, v in repl.items():
            subject, body = subject.replace(k, v), body.replace(k, v)
        try:
            await send_email(to_email=u["email"], to_name=u.get("first_name"),
                             subject=subject, html_content=body, tags=[f"parrainia-{kind}"])
            sent += 1
        except Exception as exc:
            logger.warning("PARRAIN'IA email %s échoué : %s", u["email"], exc)
    entry = {"id": str(uuid.uuid4()), "kind": kind, "month": month, "sent": sent,
             "subject": template.get("subject", ""), "launched_challenge": launched,
             "triggered_by": triggered_by, "at": datetime.now(timezone.utc).isoformat()}
    await database.parrainia_log.insert_one({**entry})
    from consultation_audit import audit
    await audit("PARRAINIA_CAMPAIGN", triggered_by, None,
                {"kind": kind, "month": month, "sent": sent, "launched": launched})
    logger.info("PARRAIN'IA %s %s : %s email(s) envoyés", kind, month, sent)
    return entry


@parrainia_router.post("/animate")
async def animate_now(body: dict, admin: dict = Depends(require_admin)):
    kind = (body or {}).get("kind") or "kickoff"
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail="Type de campagne invalide (kickoff ou boost)")
    try:
        return await run_parrainia_campaign(db, kind, admin.get("email"))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PARRAIN'IA animate échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Campagne PARRAIN'IA échouée — réessayez")


@parrainia_router.get("/log")
async def parrainia_log(admin: dict = Depends(require_admin)):
    items = await db.parrainia_log.find({}, {"_id": 0}).sort("at", -1).to_list(20)
    return {"items": items}


async def process_parrainia(database) -> None:
    """Scheduler : coup d'envoi automatique en début de mois, relance de mi-mois (une fois chacun)."""
    from ai_agents_settings import get_agents_settings
    settings = await get_agents_settings(database)
    if not settings.get("parrainia_enabled"):
        return
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    kind = None
    if now.day <= 3:
        kind = "kickoff"
    elif now.day >= 15:
        kind = "boost"
    if not kind:
        return
    if await database.parrainia_log.find_one({"kind": kind, "month": month}):
        return
    await run_parrainia_campaign(database, kind, "parrainia-auto")
