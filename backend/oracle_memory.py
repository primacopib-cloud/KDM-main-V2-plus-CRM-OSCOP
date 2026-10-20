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
SHARED_SCOPE = "admin_team"
ADMIN_ROLES = ["oscop_super_admin", "kdm_b2b_admin", "admin", "SUPER_ADMIN", "ADMIN"]
KIND_LABELS = {"fact": "Fait", "preference": "Préférence", "rule": "Consigne", "correction": "Correction"}


def _is_admin(user: dict) -> bool:
    role = user.get("role") or user.get("user_role") or user.get("role_v2")
    return user.get("is_admin", False) or role in ADMIN_ROLES


EXTRACT_SYSTEM = (
    "Tu gères la mémoire longue durée de l'assistant Oracle (plateforme coopérative KDMARCHÉ × O'SCOP). "
    "À partir d'un échange, tu extrais UNIQUEMENT les informations durables et réutilisables dans les "
    "discussions futures : préférences exprimées par l'utilisateur, consignes permanentes qu'il donne, "
    "faits stables sur son activité, son organisation ou ses habitudes. "
    "JAMAIS d'informations transitoires (soldes, dates du jour, états momentanés), JAMAIS de mots de passe ou "
    "secrets, JAMAIS de reformulation de la question. "
    "Réponds EXCLUSIVEMENT avec un JSON valide : {\"memories\":[{\"kind\":\"fact|preference|rule\","
    "\"text\":\"phrase courte à la 3e personne\",\"shared\":false}]} (0 à 3 éléments, souvent 0). "
    "\"shared\": true UNIQUEMENT si l'utilisateur est un administrateur ET que la consigne est une règle "
    "collective valable pour toute l'équipe d'administration (règle de campagne, politique de crédits, "
    "procédure de validation) ; false pour tout ce qui est personnel. "
    "Si rien ne mérite d'être retenu : {\"memories\":[]}."
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())[:300]


async def add_memory(db, user_id: str, kind: str, text: str, source: str = "",
                     shared: bool = False, by: str = "") -> bool:
    text = (text or "").strip()[:400]
    if len(text) < 8 or kind not in KIND_LABELS:
        return False
    key = _norm(text)
    flt = {"scope": SHARED_SCOPE, "key": key} if shared else {"user_id": user_id, "key": key, "scope": {"$ne": SHARED_SCOPE}}
    if await db.oracle_memory.find_one(flt):
        return False
    await db.oracle_memory.insert_one({
        "id": str(uuid.uuid4()), "user_id": None if shared else user_id,
        "scope": SHARED_SCOPE if shared else "personal", "kind": kind, "key": key,
        "text": text, "source": source, "created_by": by,
        "created_at": datetime.now(timezone.utc).isoformat()})
    cap_flt = {"scope": SHARED_SCOPE} if shared else {"user_id": user_id, "scope": {"$ne": SHARED_SCOPE}}
    if await db.oracle_memory.count_documents(cap_flt) > MAX_MEMORIES:
        old = await db.oracle_memory.find(cap_flt, {"_id": 0, "id": 1}).sort(
            "created_at", 1).limit(5).to_list(5)
        await db.oracle_memory.delete_many({"id": {"$in": [o["id"] for o in old]}})
    return True


async def memories_text(db, user_id: str, limit: int = 12, include_shared: bool = False) -> str:
    docs = await db.oracle_memory.find(
        {"user_id": user_id, "scope": {"$ne": SHARED_SCOPE}}, {"_id": 0, "kind": 1, "text": 1}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    blocks = []
    if docs:
        lines = [f"- [{KIND_LABELS.get(d['kind'], d['kind'])}] {d['text']}" for d in reversed(docs)]
        blocks.append("Mémoire longue durée d'Oracle (apprise au fil des discussions avec cet utilisateur — "
                      "respecte ces faits, préférences et consignes dans ta réponse) :\n" + "\n".join(lines))
    if include_shared:
        shared = await db.oracle_memory.find(
            {"scope": SHARED_SCOPE}, {"_id": 0, "kind": 1, "text": 1}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        if shared:
            lines = [f"- [{KIND_LABELS.get(d['kind'], d['kind'])}] {d['text']}" for d in reversed(shared)]
            blocks.append("Consignes collectives de l'équipe d'administration (partagées entre tous les admins — "
                          "applique-les systématiquement) :\n" + "\n".join(lines))
    return "\n".join(blocks)


def should_learn(message: str) -> bool:
    m = (message or "").strip()
    return len(m) >= 25 and not re.match(r"^(ex[ée]cute|oui|non|annule|ok|merci|stop)\b", m, re.I)


def _extract_sync(question: str, answer: str, is_admin: bool = False) -> list:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    prompt = (f"Utilisateur administrateur : {'oui' if is_admin else 'non'}.\n"
              f"Message de l'utilisateur :\n{question[:800]}\n\nRéponse d'Oracle :\n{answer[:800]}\n\n"
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


async def learn_from_exchange(user_id: str, question: str, answer: str,
                              is_admin: bool = False, by: str = ""):
    """Fire-and-forget : extrait les éléments durables de l'échange et les mémorise."""
    try:
        from fastapi.concurrency import run_in_threadpool
        items = await run_in_threadpool(_extract_sync, question, answer, is_admin)
        db = get_database()
        for it in items[:3]:
            shared = bool(is_admin and it.get("shared"))
            await add_memory(db, user_id, str(it.get("kind") or "fact"), str(it.get("text") or ""),
                             source="echange", shared=shared, by=by)
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
        {"user_id": current_user["id"], "scope": {"$ne": SHARED_SCOPE}},
        {"_id": 0, "id": 1, "kind": 1, "text": 1, "created_at": 1}
    ).sort("created_at", -1).limit(MAX_MEMORIES).to_list(MAX_MEMORIES)
    shared = []
    if _is_admin(current_user):
        shared = await db.oracle_memory.find(
            {"scope": SHARED_SCOPE},
            {"_id": 0, "id": 1, "kind": 1, "text": 1, "created_by": 1, "created_at": 1}
        ).sort("created_at", -1).limit(MAX_MEMORIES).to_list(MAX_MEMORIES)
    return {"memories": items, "shared": shared, "is_admin": _is_admin(current_user)}


@oracle_memory_router.get("/export.pdf")
async def export_memories_pdf(current_user: dict = Depends(get_current_user)):
    """Export PDF de la mémoire d'Oracle (traçabilité RGPD avant oubli total)."""
    db = get_database()
    items = await db.oracle_memory.find(
        {"user_id": current_user["id"], "scope": {"$ne": SHARED_SCOPE}},
        {"_id": 0, "kind": 1, "text": 1, "source": 1, "created_at": 1}
    ).sort("created_at", 1).limit(MAX_MEMORIES).to_list(MAX_MEMORIES)
    pdf = _build_memory_pdf(current_user, items)
    from fastapi.responses import Response
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="memoire-oracle.pdf"'})


def _build_memory_pdf(user: dict, items: list) -> bytes:
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    gold, dark, grey = colors.HexColor("#B8860B"), colors.HexColor("#1F2A3A"), colors.HexColor("#555555")
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Mémoire Oracle — export RGPD")
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, textColor=gold, spaceAfter=2 * mm)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=grey, spaceAfter=6 * mm)
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=9, textColor=dark, leading=12)
    foot = ParagraphStyle("foot", fontName="Helvetica-Oblique", fontSize=8, textColor=grey, spaceBefore=6 * mm)
    name = user.get("contact_name") or user.get("name") or ""
    story = [
        Paragraph("O'SCOP × ORACLE — MÉMOIRE DE L'ASSISTANT", h1),
        Paragraph(
            f"Export personnel RGPD (art. 20 — portabilité) de {name} &lt;{user.get('email', '')}&gt; "
            f"— généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')} — "
            f"{len(items)} souvenir(s)", sub)]
    if not items:
        story.append(Paragraph("Aucun souvenir enregistré : la mémoire d'Oracle est vide pour ce compte.", cell))
    else:
        rows = [[Paragraph("<b>Type</b>", cell), Paragraph("<b>Souvenir</b>", cell),
                 Paragraph("<b>Origine</b>", cell), Paragraph("<b>Date</b>", cell)]]
        for m in items:
            rows.append([
                Paragraph(KIND_LABELS.get(m["kind"], m["kind"]), cell),
                Paragraph(m["text"].replace("&", "&amp;").replace("<", "&lt;"), cell),
                Paragraph(m.get("source") or "—", cell),
                Paragraph((m.get("created_at") or "")[:16].replace("T", " "), cell)])
        t = Table(rows, colWidths=[24 * mm, 104 * mm, 22 * mm, 28 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3E9D2")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8CFBF")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBF6EE")]),
        ]))
        story.append(t)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Ces souvenirs sont des informations durables qu'Oracle a retenues de vos discussions pour personnaliser "
        "ses réponses. Vous pouvez en supprimer chacun individuellement depuis le menu mémoire (icône cerveau) ou "
        "tout effacer d'un coup via « Tout oublier ». Document généré automatiquement — Communityplace, "
        "KDMARCHÉ × O'SCOP.", foot))
    doc.build(story)
    return buf.getvalue()


@oracle_memory_router.delete("/all")
async def forget_all(current_user: dict = Depends(get_current_user)):
    """Oubli total RGPD : purge toute la mémoire personnelle d'Oracle pour cet utilisateur."""
    db = get_database()
    res = await db.oracle_memory.delete_many({"user_id": current_user["id"], "scope": {"$ne": SHARED_SCOPE}})
    return {"ok": True, "deleted": res.deleted_count}


@oracle_memory_router.post("/{memory_id}/share")
async def share_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Promeut un souvenir personnel en consigne collective de l'équipe admin."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    db = get_database()
    res = await db.oracle_memory.update_one(
        {"id": memory_id, "user_id": current_user["id"], "scope": {"$ne": SHARED_SCOPE}},
        {"$set": {"scope": SHARED_SCOPE, "user_id": None,
                  "created_by": current_user.get("email") or ""}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")
    return {"ok": True}


@oracle_memory_router.delete("/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    flt = {"id": memory_id, "$or": [{"user_id": current_user["id"]}]}
    if _is_admin(current_user):
        flt["$or"].append({"scope": SHARED_SCOPE})
    res = await db.oracle_memory.delete_one(flt)
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")
    return {"ok": True}
