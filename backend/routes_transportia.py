"""TRANSPORT'IA — agent IA de recrutement des transporteurs : prospection, invitations, relances, assistance LOGICOOP."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin
from ai_usage import log_ai_usage

logger = logging.getLogger(__name__)
transportia_router = APIRouter(prefix="/api/admin/transportia", tags=["transportia"])
db = None

STATUSES = ["NEW", "INVITED", "FOLLOWED_UP", "REGISTERED", "DECLINED"]

LOGICOOP_CONTEXT = (
    "Tu es TRANSPORT'IA, l'agent de recrutement des opérateurs logistiques de LOGICOOP, le module "
    "logistique de la Communityplace coopérative KDMARCHÉ × O'SCOP (Outre-mer : Guadeloupe, Martinique, "
    "Guyane, La Réunion, Mayotte). Arguments clés pour les transporteurs : inscription 100% GRATUITE en tant "
    "que membre transporteur, accès à un flux régulier de missions de livraison B2B (EXW / CIF, inter-îles et "
    "dernier kilomètre), paiement rapide et tracé, outils fournis (espace livreur mobile avec tournée optimisée "
    "sur carte, signatures électroniques, reçus automatiques), gouvernance coopérative SCIC où chaque membre compte."
)


def set_transportia_database(database):
    global db
    db = database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_prospect(pid: str) -> dict:
    p = await db.transport_prospects.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Prospect introuvable")
    return p


@transportia_router.get("/prospects")
async def list_prospects(admin: dict = Depends(require_admin)):
    items = await db.transport_prospects.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    emails = [p["email"] for p in items if p.get("email") and p.get("status") not in ("REGISTERED", "DECLINED")]
    if emails:
        registered = {u["email"] async for u in db.users.find({"email": {"$in": emails}}, {"email": 1})}
        for p in items:
            if p.get("email") in registered and p.get("status") != "REGISTERED":
                p["status"] = "REGISTERED"
                await db.transport_prospects.update_one(
                    {"id": p["id"]},
                    {"$set": {"status": "REGISTERED", "registered_at": _now()},
                     "$push": {"history": {"at": _now(), "action": "REGISTERED",
                                           "detail": "Inscription détectée automatiquement"}}})
    counts = {s: 0 for s in STATUSES}
    for p in items:
        counts[p.get("status", "NEW")] = counts.get(p.get("status", "NEW"), 0) + 1
    return {"items": items, "counts": counts}


@transportia_router.post("/prospects")
async def create_prospect(body: dict, admin: dict = Depends(require_admin)):
    email = (body.get("email") or "").strip().lower()
    company = (body.get("company") or "").strip()
    if not company or not email:
        raise HTTPException(status_code=400, detail="Société et email requis")
    if await db.transport_prospects.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un prospect avec cet email existe déjà")
    doc = {
        "id": str(uuid.uuid4()), "company": company[:120], "contact_name": (body.get("contact_name") or "").strip()[:80],
        "email": email, "phone": (body.get("phone") or "").strip()[:30],
        "territory": (body.get("territory") or "").strip()[:30], "fleet_type": (body.get("fleet_type") or "").strip()[:60],
        "notes": (body.get("notes") or "").strip()[:500], "status": "NEW",
        "created_at": _now(), "history": [{"at": _now(), "action": "CREATED", "detail": f"Ajouté par {admin.get('email')}"}],
    }
    await db.transport_prospects.insert_one({**doc})
    return doc


@transportia_router.put("/prospects/{pid}")
async def update_prospect(pid: str, body: dict, admin: dict = Depends(require_admin)):
    await _get_prospect(pid)
    updates = {k: v for k, v in body.items() if k in ("status", "notes", "contact_name", "phone", "territory", "fleet_type")}
    if updates.get("status") and updates["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    if updates:
        await db.transport_prospects.update_one(
            {"id": pid}, {"$set": updates,
                          "$push": {"history": {"at": _now(), "action": "UPDATED", "detail": ", ".join(updates.keys())}}})
    return await _get_prospect(pid)


@transportia_router.delete("/prospects/{pid}")
async def delete_prospect(pid: str, admin: dict = Depends(require_admin)):
    res = await db.transport_prospects.delete_one({"id": pid})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Prospect introuvable")
    return {"ok": True}


async def _llm_json(system: str, prompt: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"transportia-{uuid.uuid4()}",
                   system_message=system).with_model("openai", "gpt-5.4")
    raw = str(await chat.send_message(UserMessage(text=prompt))).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def _prospect_brief(p: dict) -> str:
    return (f"Prospect : société {p['company']}, contact {p.get('contact_name') or 'inconnu'}, "
            f"territoire {p.get('territory') or 'Outre-mer'}, flotte : {p.get('fleet_type') or 'non précisée'}. "
            f"Notes internes : {p.get('notes') or 'aucune'}.")


@transportia_router.post("/prospects/{pid}/generate-invite")
async def generate_invite(pid: str, admin: dict = Depends(require_admin)):
    p = await _get_prospect(pid)
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    try:
        data = await _llm_json(
            f"{LOGICOOP_CONTEXT}\nRéponds UNIQUEMENT en JSON valide, sans markdown.",
            f"{_prospect_brief(p)}\n"
            "Rédige un email d'invitation personnalisé pour convaincre ce transporteur de s'inscrire GRATUITEMENT "
            "comme membre transporteur LOGICOOP. JSON attendu : {\"subject\" (objet accrocheur), \"body\" (HTML simple "
            "<p>/<b> uniquement, 130-180 mots, personnalisé avec le nom du contact et la société, un seul appel à "
            f"l'action vers le lien {base}/adhesion, signature 'L'équipe LOGICOOP — KDMARCHÉ × O'SCOP')}}.")
    except Exception as exc:
        logger.error("TRANSPORT'IA invitation échouée : %s", exc)
        raise HTTPException(status_code=502, detail="Génération IA échouée — réessayez")
    await log_ai_usage(db, "transportia_invite", p["company"])
    return {"subject": data.get("subject", ""), "body": data.get("body", "")}


@transportia_router.post("/prospects/{pid}/generate-followup")
async def generate_followup(pid: str, admin: dict = Depends(require_admin)):
    p = await _get_prospect(pid)
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    invited_at = p.get("invited_at", "récemment")
    try:
        data = await _llm_json(
            f"{LOGICOOP_CONTEXT}\nRéponds UNIQUEMENT en JSON valide, sans markdown.",
            f"{_prospect_brief(p)}\nCe transporteur a été invité le {invited_at} et n'a pas encore répondu. "
            "Rédige une RELANCE courte (80-120 mots) avec un angle différent (missions concrètes, gratuité, outils "
            "livreur fournis). JSON attendu : {\"subject\", \"body\" (HTML simple <p>/<b>, appel à l'action vers "
            f"{base}/adhesion)}}.")
    except Exception as exc:
        logger.error("TRANSPORT'IA relance échouée : %s", exc)
        raise HTTPException(status_code=502, detail="Génération IA échouée — réessayez")
    await log_ai_usage(db, "transportia_invite", f"relance {p['company']}")
    return {"subject": data.get("subject", ""), "body": data.get("body", "")}


@transportia_router.post("/prospects/{pid}/send")
async def send_prospect_email(pid: str, body: dict, admin: dict = Depends(require_admin)):
    p = await _get_prospect(pid)
    subject = (body.get("subject") or "").strip()
    html = (body.get("body") or "").strip()
    if not subject or not html:
        raise HTTPException(status_code=400, detail="Objet et corps requis")
    kind = body.get("kind") or ("followup" if p.get("status") in ("INVITED", "FOLLOWED_UP") else "invite")
    from brevo_service import send_email
    try:
        await send_email(to_email=p["email"], to_name=p.get("contact_name") or p["company"],
                         subject=subject, html_content=html, tags=[f"transportia-{kind}"])
    except Exception as exc:
        logger.error("Envoi TRANSPORT'IA échoué %s : %s", p["email"], exc)
        raise HTTPException(status_code=502, detail="Envoi email échoué")
    new_status = "FOLLOWED_UP" if kind == "followup" else "INVITED"
    sets = {"status": new_status, "last_action_at": _now()}
    if kind == "invite":
        sets["invited_at"] = _now()
    await db.transport_prospects.update_one(
        {"id": pid}, {"$set": sets,
                      "$push": {"history": {"at": _now(), "action": new_status, "detail": subject[:120]}}})
    from consultation_audit import audit
    await audit("TRANSPORTIA_EMAIL_SENT", admin.get("email"), None,
                {"prospect": p["company"], "email": p["email"], "kind": kind})
    return {"ok": True, "status": new_status}


@transportia_router.post("/assist")
async def transportia_assist(body: dict, admin: dict = Depends(require_admin)):
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question requise")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"transportia-assist-{uuid.uuid4()}",
                   system_message=(f"{LOGICOOP_CONTEXT}\nTu assistes l'équipe KDMARCHÉ pour répondre aux questions et "
                                   "objections des transporteurs prospectés. Réponses concrètes, en français, "
                                   "120 mots max, prêtes à copier-coller.")).with_model("openai", "gpt-5.4")
    try:
        answer = str(await chat.send_message(UserMessage(text=question))).strip()
    except Exception as exc:
        logger.error("TRANSPORT'IA assist échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Assistant IA indisponible — réessayez")
    await log_ai_usage(db, "transportia_assist", question[:80])
    return {"answer": answer}
