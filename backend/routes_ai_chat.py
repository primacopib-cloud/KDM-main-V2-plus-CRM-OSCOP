"""Chat IA payant — crédits CREDI'SCOP, tarification par longueur de question (Super Admin)."""
import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user_id
from lolodrive_helpers import get_current_user, require_admin, get_or_create_wallet

load_dotenv()
logger = logging.getLogger(__name__)

ai_chat_router = APIRouter(prefix="/api/ai-chat", tags=["ai-chat"])

db = None


def set_ai_chat_database(database):
    global db
    db = database


DEFAULT_SETTINGS = {
    "id": "default",
    "enabled": True,
    "provider": "openai",
    "model": "gpt-5.4",
    "assistant_name": "COOP'IA",
    "system_prompt": (
        "Tu es COOP'IA, l'assistant intelligent de Communityplace (KDMARCHÉ × O'SCOP), "
        "plateforme coopérative B2B2C de l'Économie Sociale et Solidaire dans les Outre-mer "
        "(Guadeloupe, Martinique, Guyane, La Réunion, Mayotte). Tu aides les membres "
        "(acheteurs professionnels, vendeurs, coopérateurs) sur l'achat mutualisé, la logistique, "
        "les adhésions, la conformité ESS et l'usage de la plateforme. Réponds en multilingue, "
        "de façon claire, concise et professionnelle."
    ),
    "block_size_chars": 50,
    "credits_per_block": 4,
    "min_cost_uc": 1,
    "max_question_chars": 1000,
}


async def get_settings() -> dict:
    doc = await db.ai_chat_settings.find_one({"id": "default"}, {"_id": 0})
    if not doc:
        await db.ai_chat_settings.insert_one({**DEFAULT_SETTINGS, "updated_at": datetime.now(timezone.utc).isoformat()})
        return dict(DEFAULT_SETTINGS)
    return {**DEFAULT_SETTINGS, **doc}


def compute_cost(question: str, s: dict) -> int:
    block = max(1, int(s.get("block_size_chars") or 50))
    per_block = max(0, int(s.get("credits_per_block") or 0))
    cost = math.ceil(max(1, len(question.strip())) / block) * per_block
    return max(int(s.get("min_cost_uc") or 0), cost)


class QuoteBody(BaseModel):
    question: str


class AskBody(BaseModel):
    question: str
    session_id: Optional[str] = None


class SettingsBody(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    assistant_name: Optional[str] = None
    system_prompt: Optional[str] = None
    block_size_chars: Optional[int] = None
    credits_per_block: Optional[int] = None
    min_cost_uc: Optional[int] = None
    max_question_chars: Optional[int] = None


@ai_chat_router.get("/settings")
async def public_settings(user_id: str = Depends(get_current_user_id)):
    """Paramètres publics (tarification affichée aux membres)."""
    s = await get_settings()
    wallet = await get_or_create_wallet(user_id)
    return {
        "enabled": s["enabled"],
        "assistant_name": s["assistant_name"],
        "block_size_chars": s["block_size_chars"],
        "credits_per_block": s["credits_per_block"],
        "min_cost_uc": s["min_cost_uc"],
        "max_question_chars": s["max_question_chars"],
        "balance_uc": wallet.get("balance_uc", 0),
    }


@ai_chat_router.post("/quote")
async def quote_question(body: QuoteBody, user_id: str = Depends(get_current_user_id)):
    s = await get_settings()
    wallet = await get_or_create_wallet(user_id)
    cost = compute_cost(body.question, s)
    balance = wallet.get("balance_uc", 0)
    return {"cost_uc": cost, "balance_uc": balance, "can_afford": balance >= cost,
            "chars": len(body.question.strip())}


async def _debit(user_id: str, amount: int, reason: str) -> dict:
    wallet = await get_or_create_wallet(user_id)
    now = datetime.utcnow()
    await db.lolodrive_wallets.update_one(
        {"id": wallet["id"]}, {"$inc": {"balance_uc": -amount}, "$set": {"updated_at": now}})
    await db.lolodrive_wallet_ledger.insert_one({
        "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "DEBIT",
        "amount_uc": amount, "reason": reason, "created_at": now,
    })
    return wallet


async def _refund(wallet: dict, amount: int, reason: str):
    now = datetime.utcnow()
    await db.lolodrive_wallets.update_one(
        {"id": wallet["id"]}, {"$inc": {"balance_uc": amount}, "$set": {"updated_at": now}})
    await db.lolodrive_wallet_ledger.insert_one({
        "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
        "amount_uc": amount, "reason": reason, "created_at": now,
    })


async def _session_history(session_id: str, limit: int = 10) -> str:
    msgs = await db.ai_chat_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    if not msgs:
        return ""
    lines = [f"{'Utilisateur' if m['role'] == 'user' else 'Assistant'}: {m['content'][:600]}" for m in reversed(msgs)]
    return "\n".join(lines)


@ai_chat_router.post("/ask")
async def ask_question(body: AskBody, user_id: str = Depends(get_current_user_id)):
    s = await get_settings()
    if not s["enabled"]:
        raise HTTPException(status_code=503, detail="L'assistant IA est momentanément désactivé.")
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide.")
    if len(question) > int(s["max_question_chars"]):
        raise HTTPException(status_code=400, detail=f"Question trop longue (max {s['max_question_chars']} caractères).")

    cost = compute_cost(question, s)
    wallet = await get_or_create_wallet(user_id)
    balance = wallet.get("balance_uc", 0)
    if balance < cost:
        raise HTTPException(status_code=402, detail=f"Crédits insuffisants : cette question coûte {cost} UC, votre solde est de {balance} UC.")

    session_id = body.session_id or str(uuid.uuid4())
    history = await _session_history(session_id)
    wallet = await _debit(user_id, cost, "AI_CHAT")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.ai_chat_messages.insert_one({
        "id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id,
        "role": "user", "content": question, "cost_uc": cost, "created_at": now_iso,
    })
    await db.ai_chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"user_id": user_id, "last_message_at": now_iso},
         "$setOnInsert": {"created_at": now_iso, "title": question[:60]},
         "$inc": {"questions": 1, "credits_spent": cost}},
        upsert=True,
    )

    prompt = question if not history else f"Historique de la conversation :\n{history}\n\nNouvelle question : {question}"

    async def event_stream():
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        try:
            chat = LlmChat(
                api_key=os.environ.get("EMERGENT_LLM_KEY"),
                session_id=session_id,
                system_message=s["system_prompt"],
            ).with_model(s["provider"], s["model"])
            answer = await chat.send_message(UserMessage(text=prompt))
            answer = answer or ""
            for i in range(0, len(answer), 80):
                yield f"data: {json.dumps({'type': 'delta', 'content': answer[i:i + 80]})}\n\n"
            await db.ai_chat_messages.insert_one({
                "id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id,
                "role": "assistant", "content": answer, "cost_uc": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'cost_uc': cost, 'balance_uc': (fresh or {}).get('balance_uc', 0)})}\n\n"
        except Exception as exc:
            logger.exception("AI chat error (session %s): %s", session_id, exc)
            await _refund(wallet, cost, "AI_CHAT_REFUND")
            fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Réponse indisponible — vos crédits ont été remboursés.', 'balance_uc': (fresh or {}).get('balance_uc', 0)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@ai_chat_router.get("/sessions")
async def my_sessions(user_id: str = Depends(get_current_user_id)):
    sessions = await db.ai_chat_sessions.find(
        {"user_id": user_id}, {"_id": 0}).sort("last_message_at", -1).limit(20).to_list(20)
    return {"sessions": sessions}


@ai_chat_router.get("/messages/{session_id}")
async def session_messages(session_id: str, user_id: str = Depends(get_current_user_id)):
    session = await db.ai_chat_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    msgs = await db.ai_chat_messages.find(
        {"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return {"messages": msgs, "session": session}


# ===================== ADMIN (Super Admin & Admin) =====================

@ai_chat_router.get("/admin/settings")
async def admin_get_settings(admin: dict = Depends(require_admin)):
    return await get_settings()


@ai_chat_router.put("/admin/settings")
async def admin_update_settings(body: SettingsBody, admin: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "block_size_chars" in updates and updates["block_size_chars"] < 1:
        raise HTTPException(status_code=400, detail="La taille de bloc doit être ≥ 1 caractère")
    if "credits_per_block" in updates and updates["credits_per_block"] < 0:
        raise HTTPException(status_code=400, detail="Le coût par bloc doit être ≥ 0")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = admin.get("email")
    await db.ai_chat_settings.update_one({"id": "default"}, {"$set": updates}, upsert=True)
    logger.info("AI chat settings mis à jour par %s : %s", admin.get("email"), updates)
    return await get_settings()


@ai_chat_router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    total_questions = await db.ai_chat_messages.count_documents({"role": "user"})
    pipeline = [{"$match": {"role": "user"}}, {"$group": {"_id": None, "credits": {"$sum": "$cost_uc"}}}]
    agg = await db.ai_chat_messages.aggregate(pipeline).to_list(1)
    total_credits = (agg[0]["credits"] if agg else 0) or 0
    users = await db.ai_chat_messages.distinct("user_id", {"role": "user"})
    recent = await db.ai_chat_messages.find(
        {"role": "user"}, {"_id": 0, "content": 1, "cost_uc": 1, "created_at": 1, "user_id": 1}
    ).sort("created_at", -1).limit(20).to_list(20)
    emails = {u["id"]: u.get("email") for u in await db.users.find(
        {"id": {"$in": [r["user_id"] for r in recent]}}, {"_id": 0, "id": 1, "email": 1}).to_list(50)}
    for r in recent:
        r["user_email"] = emails.get(r.pop("user_id"), "?")
    return {"total_questions": total_questions, "total_credits_uc": total_credits,
            "unique_users": len(users), "recent": recent}
