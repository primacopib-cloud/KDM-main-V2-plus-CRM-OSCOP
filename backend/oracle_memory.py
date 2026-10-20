"""Mémoire auto-apprenante d'Oracle : faits/préférences retenus entre sessions + apprentissage des corrections."""
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core_deps import get_current_user
from db import get_database

logger = logging.getLogger(__name__)
oracle_memory_router = APIRouter(prefix="/api/oracle-memory", tags=["oracle-memory"])

MAX_MEMORIES = 60
KIND_LABELS = {"fact": "Fait", "preference": "Préférence", "rule": "Consigne", "correction": "Correction"}

EXTRACT_SYSTEM = (
    "Tu gères la mémoire longue durée de l'assistant Oracle (plateforme coopérative KDMARCHÉ × O'SCOP). "
    "À partir d'un échange, tu extrais UNIQUEMENT les informations durables et réutilisables dans les "
    "discussions futures : préférences exprimées par l'utilisateur, consignes permanentes qu'il donne, "
    "faits stables sur son activité, son organisation ou ses habitudes. "
    "JAMAIS d'informations transitoires (soldes, dates du jour, états momentanés), JAMAIS de mots de passe ou "
    "secrets, JAMAIS de reformulation de la question. "
    "Réponds EXCLUSIVEMENT avec un JSON valide : {\"memories\":[{\"kind\":\"fact|preference|rule\","
    "\"text\":\"phrase courte à la 3e personne\"}]} (0 à 3 éléments, souvent 0). "
    "Si rien ne mérite d'être retenu : {\"memories\":[]}."
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())[:300]


async def add_memory(db, user_id: str, kind: str, text: str, source: str = "") -> bool:
    text = (text or "").strip()[:400]
    if len(text) < 8 or kind not in KIND_LABELS:
        return False
    key = _norm(text)
    if await db.oracle_memory.find_one({"user_id": user_id, "key": key}):
        return False
    await db.oracle_memory.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "kind": kind, "key": key,
        "text": text, "source": source, "created_at": datetime.now(timezone.utc).isoformat()})
    if await db.oracle_memory.count_documents({"user_id": user_id}) > MAX_MEMORIES:
        old = await db.oracle_memory.find({"user_id": user_id}, {"_id": 0, "id": 1}).sort(
            "created_at", 1).limit(5).to_list(5)
        await db.oracle_memory.delete_many({"id": {"$in": [o["id"] for o in old]}})
    return True


async def memories_text(db, user_id: str, limit: int = 12) -> str:
    docs = await db.oracle_memory.find(
        {"user_id": user_id}, {"_id": 0, "kind": 1, "text": 1}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    if not docs:
        return ""
    lines = [f"- [{KIND_LABELS.get(d['kind'], d['kind'])}] {d['text']}" for d in reversed(docs)]
    return ("Mémoire longue durée d'Oracle (apprise au fil des discussions avec cet utilisateur — "
            "respecte ces faits, préférences et consignes dans ta réponse) :\n" + "\n".join(lines))


def should_learn(message: str) -> bool:
    m = (message or "").strip()
    return len(m) >= 25 and not re.match(r"^(ex[ée]cute|oui|non|annule|ok|merci|stop)\b", m, re.I)


def _extract_sync(question: str, answer: str) -> list:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    prompt = (f"Message de l'utilisateur :\n{question[:800]}\n\nRéponse d'Oracle :\n{answer[:800]}\n\n"
              "Extrais les éléments durables à mémoriser (JSON uniquement).")

    async def _go():
        chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"),
                       session_id=f"mem_{uuid.uuid4().hex[:10]}",
                       system_message=EXTRACT_SYSTEM).with_model("openai", "gpt-5.4")
        return await chat.send_message(UserMessage(text=prompt)) or ""
    raw = asyncio.run(_go())
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    return [it for it in (data.get("memories") or []) if isinstance(it, dict)]


async def learn_from_exchange(user_id: str, question: str, answer: str):
    """Fire-and-forget : extrait les éléments durables de l'échange et les mémorise."""
    try:
        from fastapi.concurrency import run_in_threadpool
        items = await run_in_threadpool(_extract_sync, question, answer)
        db = get_database()
        for it in items[:3]:
            await add_memory(db, user_id, str(it.get("kind") or "fact"), str(it.get("text") or ""), source="echange")
    except Exception as exc:
        logger.debug("Oracle memory learn: %s", exc)


async def learn_correction(db, user_id: str, old: str, new: str):
    """Quand l'utilisateur corrige un prompt déjà envoyé, Oracle en tire une règle."""
    old, new = (old or "").strip()[:200], (new or "").strip()[:200]
    if not old or not new or _norm(old) == _norm(new):
        return
    await add_memory(db, user_id, "correction",
                     f"L'utilisateur a corrigé sa demande « {old} » en « {new} » — "
                     "privilégier la seconde formulation et l'intention qu'elle exprime.", source="edition")


@oracle_memory_router.get("")
async def list_memories(current_user: dict = Depends(get_current_user)):
    db = get_database()
    items = await db.oracle_memory.find(
        {"user_id": current_user["id"]}, {"_id": 0, "id": 1, "kind": 1, "text": 1, "created_at": 1}
    ).sort("created_at", -1).limit(MAX_MEMORIES).to_list(MAX_MEMORIES)
    return {"memories": items}


@oracle_memory_router.delete("/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    res = await db.oracle_memory.delete_one({"id": memory_id, "user_id": current_user["id"]})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")
    return {"ok": True}
