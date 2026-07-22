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
    program = await database.parrainia_programs.find_one({"month": month}, {"_id": 0})
    launched = False
    if kind == "kickoff":
        updates = {}
        if not settings.get("enabled"):
            updates["enabled"] = True
            launched = True
        if program:
            updates.update({"reward_credits": program.get("reward_credits", settings.get("reward_credits", 50)),
                            "reward_2nd": program.get("reward_2nd", 0), "reward_3rd": program.get("reward_3rd", 0)})
        if updates:
            await database.referral_challenge_settings.update_one({"id": "default"}, {"$set": updates}, upsert=True)
            settings.update(updates)
    tiers = [settings.get("reward_credits", 50), settings.get("reward_2nd", 0), settings.get("reward_3rd", 0)]
    rewards_str = f"+{tiers[0]}" + (f" / +{tiers[1]}" if tiers[1] else "") + (f" / +{tiers[2]}" if tiers[2] else "") + " CREDI'SCOP"
    board = await _leaderboard(database, month, limit=100)
    ranks = {r["sponsor_id"]: (i + 1, r["referred"]) for i, r in enumerate(board)}
    sponsors = await _sponsors(database)
    if not sponsors:
        return {"sent": 0, "message": "Aucun parrain à animer pour le moment", "launched": launched}
    if program and program.get(f"{kind}_subject") and program.get(f"{kind}_body"):
        template = {"subject": program[f"{kind}_subject"], "body": program[f"{kind}_body"]}
    else:
        template = await _generate_template(kind, month, tiers)
        await log_ai_usage(database, "parrainia_campaign", f"{kind} {month}")
    if program and kind == "kickoff":
        await database.parrainia_programs.update_one({"id": program["id"]}, {"$set": {"status": "ACTIVE"}})
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
    """Scheduler : coup d'envoi automatique en début de mois, relance de mi-mois, bilan mensuel (une fois chacun)."""
    from ai_agents_settings import get_agents_settings
    settings = await get_agents_settings(database)
    if not settings.get("parrainia_enabled"):
        return
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    if now.day <= 3:
        prev = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
        if not await database.parrainia_log.find_one({"kind": "report", "month": prev}):
            try:
                await send_parrainia_monthly_report(database, prev, "parrainia-auto")
            except Exception as exc:
                logger.warning("Bilan PARRAIN'IA auto échoué : %s", exc)
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


async def _month_stats(database, month: str) -> dict:
    links = await database.referral_links.find(
        {"created_at": {"$gte": f"{month}-01", "$lt": f"{month}-99"}}, {"_id": 0}).to_list(500)
    paid = [l for l in links if l.get("bonus_paid")]
    by_sponsor = {}
    for l in links:
        by_sponsor[l["sponsor_id"]] = by_sponsor.get(l["sponsor_id"], 0) + 1
    challenge = await database.referral_challenges.find_one({"month": month}, {"_id": 0})
    return {"new_links": len(links), "sponsors": len(by_sponsor),
            "bonus_paid": len(paid), "credits": sum(l.get("bonus_amount", 0) for l in paid),
            "top": sorted(by_sponsor.values(), reverse=True)[:3],
            "challenge": challenge}


async def send_parrainia_monthly_report(database, month: str, triggered_by: str) -> dict:
    """Bilan IA mensuel du programme de parrainage envoyé à l'équipe admin."""
    stats = await _month_stats(database, month)
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"parrainia-report-{uuid.uuid4()}",
        system_message=("Tu es PARRAIN'IA, analyste du programme de parrainage KDMARCHÉ × O'SCOP. "
                        "Rédige en français, HTML simple <p>/<b>/<ul><li> uniquement, sans markdown.")
    ).with_model("openai", "gpt-5.4")
    prompt = (
        f"Rédige le bilan mensuel du programme de parrainage pour {month} destiné à l'équipe admin (150-220 mots) : "
        "analyse chiffrée, points forts/faibles, puis exactement 3 recommandations concrètes en liste pour le mois suivant.\n"
        f"Données : {json.dumps(stats, ensure_ascii=False, default=str)[:1500]}")
    analysis = str(await chat.send_message(UserMessage(text=prompt))).strip()
    await log_ai_usage(database, "parrainia_campaign", f"bilan {month}")
    admins = await database.users.find(
        {"$or": [{"is_admin": True}, {"role": {"$in": ["SUPER_ADMIN", "ADMIN", "admin"]}}]},
        {"_id": 0, "email": 1, "first_name": 1}).to_list(5)
    html = (f"<div style='font-family:Arial,sans-serif;max-width:620px'>"
            f"<h2 style='color:#451F6B'>📊 Bilan PARRAIN'IA — {month}</h2>"
            f"<p><b>{stats['new_links']}</b> nouveau(x) filleul(s) · <b>{stats['sponsors']}</b> parrain(s) actif(s) · "
            f"<b>{stats['bonus_paid']}</b> bonus versé(s) ({stats['credits']} CREDI'SCOP)</p>"
            f"{analysis}"
            "<p style='color:#999;font-size:10px;margin-top:18px'>Généré automatiquement par PARRAIN'IA — KDMARCHÉ × O'SCOP</p></div>")
    from brevo_service import send_email
    sent = 0
    for a in admins:
        if not a.get("email"):
            continue
        try:
            await send_email(to_email=a["email"], to_name=a.get("first_name"),
                             subject=f"📊 Bilan mensuel du parrainage — {month} (PARRAIN'IA)",
                             html_content=html, tags=["parrainia-report"])
            sent += 1
        except Exception as exc:
            logger.warning("Bilan PARRAIN'IA email %s échoué : %s", a["email"], exc)
    entry = {"id": str(uuid.uuid4()), "kind": "report", "month": month, "sent": sent,
             "subject": f"Bilan mensuel {month}", "triggered_by": triggered_by,
             "at": datetime.now(timezone.utc).isoformat()}
    await database.parrainia_log.insert_one({**entry, "analysis": analysis})
    logger.info("Bilan PARRAIN'IA %s envoyé à %s admin(s)", month, sent)
    return entry


@parrainia_router.post("/report")
async def report_now(admin: dict = Depends(require_admin)):
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    try:
        return await send_parrainia_monthly_report(db, month, admin.get("email"))
    except Exception as exc:
        logger.error("Bilan PARRAIN'IA manuel échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Génération du bilan échouée — réessayez")


@parrainia_router.post("/programs/generate")
async def generate_program(body: dict, admin: dict = Depends(require_admin)):
    """PARRAIN'IA crée un ou plusieurs programmes de parrainage (jusqu'à 3 mois), programmés pour diffusion."""
    now = datetime.now(timezone.utc)
    months_count = max(1, min(int((body or {}).get("months", 1)), 3))
    explicit_month = ((body or {}).get("month") or "").strip()
    months = []
    if explicit_month:
        months = [explicit_month]
    else:
        y, m = now.year, now.month
        while len(months) < months_count:
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            candidate = f"{y}-{m:02d}"
            if not await db.parrainia_programs.find_one({"month": candidate}):
                months.append(candidate)
            if m == now.month and y == now.year + 1:
                break
    created = []
    for month in months:
        if await db.parrainia_programs.find_one({"month": month}):
            if len(months) == 1:
                raise HTTPException(status_code=409, detail=f"Un programme est déjà planifié pour {month}")
            continue
        created.append(await _generate_one_program(month, admin.get("email"),
                                                   previous=[p["theme"] for p in created]))
    if not created:
        raise HTTPException(status_code=409, detail="Tous les mois visés ont déjà un programme planifié")
    return created[0] if len(created) == 1 and months_count == 1 else {"items": created, "created": len(created)}


async def _generate_one_program(month: str, admin_email: str, previous: list = None) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"parrainia-prog-{uuid.uuid4()}",
        system_message=("Tu es PARRAIN'IA, concepteur de programmes de parrainage pour la Communityplace "
                        "coopérative KDMARCHÉ × O'SCOP (Outre-mer). Réponds UNIQUEMENT en JSON valide, sans markdown."),
    ).with_model("openai", "gpt-5.4")
    avoid = f" Thèmes déjà utilisés à éviter : {', '.join(previous)}." if previous else ""
    prompt = (
        f"Conçois le programme de parrainage du mois {month} : un thème original et fédérateur (esprit coopératif, "
        f"culture Outre-mer, saisonnalité), des récompenses de podium équilibrées, et les 2 emails de la campagne.{avoid} "
        "Utilise LITTÉRALEMENT les variables {prenom} {classement} {filleuls} {recompense} {lien} dans les corps d'emails. "
        'JSON attendu : {"theme" (nom du programme, 4-8 mots), "pitch" (1 phrase), '
        '"reward_credits" (1er, entre 30 et 100), "reward_2nd" (entre 10 et 50), "reward_3rd" (entre 5 et 25), '
        '"kickoff_subject", "kickoff_body" (HTML simple <p>/<b>, 100-150 mots), '
        '"boost_subject", "boost_body" (HTML simple, 80-120 mots, relance mi-mois)}.')
    try:
        raw = str(await chat.send_message(UserMessage(text=prompt))).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
    except Exception as exc:
        logger.error("Programme PARRAIN'IA échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Création du programme échouée — réessayez")
    await log_ai_usage(db, "parrainia_campaign", f"programme {month}")
    doc = {"id": str(uuid.uuid4()), "month": month, "status": "SCHEDULED",
           "theme": data.get("theme", ""), "pitch": data.get("pitch", ""),
           "reward_credits": max(1, min(int(data.get("reward_credits", 50)), 1000)),
           "reward_2nd": max(0, min(int(data.get("reward_2nd", 20)), 1000)),
           "reward_3rd": max(0, min(int(data.get("reward_3rd", 10)), 1000)),
           "kickoff_subject": data.get("kickoff_subject", ""), "kickoff_body": data.get("kickoff_body", ""),
           "boost_subject": data.get("boost_subject", ""), "boost_body": data.get("boost_body", ""),
           "created_by": admin_email, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.parrainia_programs.insert_one({**doc})
    from consultation_audit import audit
    await audit("PARRAINIA_PROGRAM_CREATED", admin_email, None, {"month": month, "theme": doc["theme"]})
    return doc


@parrainia_router.get("/programs")
async def list_programs(admin: dict = Depends(require_admin)):
    items = await db.parrainia_programs.find({}, {"_id": 0}).sort("month", -1).to_list(12)
    return {"items": items}


@parrainia_router.put("/programs/{pid}")
async def update_program(pid: str, body: dict, admin: dict = Depends(require_admin)):
    """Relecture/modification d'un programme planifié avant diffusion."""
    prog = await db.parrainia_programs.find_one({"id": pid}, {"_id": 0})
    if not prog:
        raise HTTPException(status_code=404, detail="Programme introuvable")
    if prog.get("status") != "SCHEDULED":
        raise HTTPException(status_code=409, detail="Programme déjà lancé — non modifiable")
    updates = {}
    for k in ("theme", "pitch", "kickoff_subject", "kickoff_body", "boost_subject", "boost_body"):
        if isinstance(body.get(k), str):
            updates[k] = body[k].strip()
    for k, lo in (("reward_credits", 1), ("reward_2nd", 0), ("reward_3rd", 0)):
        if body.get(k) is not None:
            updates[k] = max(lo, min(int(body[k]), 1000))
    if not updates:
        raise HTTPException(status_code=400, detail="Rien à mettre à jour")
    updates["updated_by"] = admin.get("email")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.parrainia_programs.update_one({"id": pid}, {"$set": updates})
    return await db.parrainia_programs.find_one({"id": pid}, {"_id": 0})


@parrainia_router.delete("/programs/{pid}")
async def delete_program(pid: str, admin: dict = Depends(require_admin)):
    res = await db.parrainia_programs.delete_one({"id": pid, "status": "SCHEDULED"})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Programme introuvable ou déjà lancé")
    return {"ok": True}
