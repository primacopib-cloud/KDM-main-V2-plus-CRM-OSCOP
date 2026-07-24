"""GUID'IA — assistant conversationnel gratuit qui guide chaque utilisateur dans son espace."""
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core_deps import get_current_user
from db import get_database

logger = logging.getLogger(__name__)
ai_guide_router = APIRouter(prefix="/api/ai-guide", tags=["ai-guide"])

SPACE_LABELS = {
    "buyer": "Espace Acheteur Pro (catalogue B2B, commandes, factures, consultations, transport LOGI'SCOP)",
    "vendor": "Espace Vendeur Pro (produits, commandes reçues, attestations RCR, crédits)",
    "admin": "Espace Super Admin (pilotage complet : membres, comptabilité, trésorerie, LOGICOOP, litiges, GEDESS)",
    "operator": "Espace Opérateur LOGICOOP (missions de transport, ePOD, médias cargaison, rémunération)",
    "pos": "Espace Opérateur POS (encaissement et retraits LOLODRIVE)",
    "lolo_point": "Espace Gérant Lolo Point (réassorts B2B, réception clients, statistiques)",
    "member": "Espace Membre (PASS Vie Chère, catalogue LOLODRIVE, commandes, wallet UC)",
    "general": "Plateforme Communityplace KDMARCHÉ × O'SCOP",
}

BASE_SUGGESTIONS = {
    "buyer": ["Comment émettre un Ordre de Transport LOGI'SCOP ?",
              "Comment payer une facture transport en ligne ?",
              "À quoi servent les avoirs de service (article 22) ?",
              "Comment lancer une consultation compétitive ?"],
    "vendor": ["Comment ajouter un produit au catalogue ?",
               "Comment fonctionne la retenue RCR sur mes règlements ?",
               "Où suivre mes commandes reçues ?",
               "Comment renouveler mon attestation nominative ?"],
    "admin": ["Résume-moi la santé financière de la plateforme",
              "Comment fonctionne la trésorerie consolidée 30/60/90 j ?",
              "Que faire face à une facture transport impayée à 45 jours ?",
              "Comment lever une suspension d'OT avec un échéancier ?"],
    "operator": ["Comment clôturer une mission avec ePOD ?",
                 "Comment ajouter des photos de la cargaison ?",
                 "Où voir ma rémunération sur les OT livrés ?"],
    "pos": ["Comment encaisser un retrait de commande ?", "Comment scanner un QR-code client ?"],
    "lolo_point": ["Comment passer une commande de réassort B2B ?", "Où voir mes statistiques de point ?"],
    "member": ["Comment fonctionne le PASS Vie Chère ?", "Comment recharger mes UC ?",
               "Comment retirer ma commande en Lolo Point ?"],
    "general": ["Que puis-je faire sur Communityplace ?", "Comment adhérer à la coopérative ?"],
}

ACTIONS = {
    "buyer_orders": ("Voir mes commandes", "/espace-acheteur?tab=orders"),
    "buyer_invoices": ("Voir mes factures", "/espace-acheteur?tab=invoices"),
    "buyer_transport": ("Ouvrir Transport LOGI'SCOP", "/espace-acheteur?tab=transport"),
    "buyer_consultations": ("Mes consultations compétitives", "/espace-acheteur?tab=consultations"),
    "buyer_catalog": ("Parcourir le catalogue B2B", "/espace-acheteur?tab=dashboard"),
    "buyer_tools": ("Outils d'achat", "/espace-acheteur?tab=tools"),
    "buyer_credits": ("Mon CREDI'SCOP", "/espace-acheteur?tab=crediscop"),
    "vendor_products": ("Gérer mes produits", "/espace-vendeur"),
    "admin_accounting": ("Ouvrir la Comptabilité", "/superadmin?tab=accounting"),
    "admin_logicoop": ("Ouvrir LOGICOOP", "/superadmin?tab=logicoop"),
    "admin_users": ("Gérer les membres", "/superadmin?tab=users"),
    "admin_support": ("Voir le Support", "/superadmin?tab=support"),
    "admin_registres": ("Ouvrir les Registres", "/superadmin?tab=registry"),
    "admin_stats": ("Voir les Statistiques", "/superadmin?tab=stats"),
    "member_pass": ("Mon PASS Vie Chère", "/pass"),
    "member_catalog": ("Catalogue LOLODRIVE", "/catalogue-lolodrive"),
    "operator_missions": ("Mes missions transport", "/logicoop"),
}
SPACE_ACTIONS = {
    "buyer": ["buyer_orders", "buyer_invoices", "buyer_transport", "buyer_consultations",
              "buyer_catalog", "buyer_tools", "buyer_credits"],
    "vendor": ["vendor_products"],
    "admin": ["admin_accounting", "admin_logicoop", "admin_users", "admin_support",
              "admin_registres", "admin_stats"],
    "operator": ["operator_missions"],
    "member": ["member_pass", "member_catalog"],
    "pos": [], "lolo_point": [], "general": ["member_pass", "member_catalog"],
}

SYSTEM_PROMPT = (
    "Tu es GUID'IA, le copilote conversationnel haut de gamme de Communityplace (KDMARCHÉ × O'SCOP), "
    "plateforme coopérative B2B2C de l'Économie Sociale et Solidaire des Outre-mer (Guadeloupe, Martinique, "
    "Guyane, La Réunion, Mayotte). Tu guides l'utilisateur pas à pas dans son espace, de façon proactive, "
    "chaleureuse et ultra professionnelle.\n"
    "Contexte plateforme : achats mutualisés B2B, catalogue vendeurs, consultations compétitives / enchères "
    "inversées, transport routier LOGI'SCOP Mode D (conventions cadres, Ordres de Transport, ePOD, factures à "
    "30 j, avoirs de service article 22, litiges température article 12), garanties RCR (retenue de "
    "cautionnement réciproque, FOGEDOM-SCIC), PASS Vie Chère et LOLODRIVE (wallet UC, Lolo Points), "
    "adhésions vendeur/acheteur, archivage GEDESS, paiements Stripe.\n"
    "Règles : réponds dans la langue de l'utilisateur (français par défaut), en 2 à 6 phrases claires, "
    "orientées action (indique les onglets/boutons à utiliser). N'utilise JAMAIS de Markdown ni "
    "d'astérisques : texte brut uniquement, avec les noms d'onglets entre guillemets « ». "
    "Ne révèle jamais de données d'autres membres. "
    "Si une question sort de la plateforme, ramène poliment vers son usage.\n"
    "IMPORTANT : termine CHAQUE réponse par une ligne exactement au format "
    "« SUGGESTIONS: question 1 | question 2 | question 3 » proposant 3 questions de suivi courtes et "
    "pertinentes pour cet utilisateur. Si une action de navigation aide directement l'utilisateur, ajoute "
    "juste avant la ligne SUGGESTIONS une ligne « ACTIONS: id1 | id2 » (2 maximum) en choisissant les id "
    "STRICTEMENT dans la liste d'actions disponibles fournie dans le contexte."
)


def _space_of(user: dict, requested: str) -> str:
    if requested in SPACE_LABELS:
        return requested
    if user.get("is_admin"):
        return "admin"
    return "general"


async def _facts(db, user: dict, space: str, lang: str = "fr") -> str:
    from ai_guide_i18n import FACT_TEMPLATES
    try:
        if space == "buyer":
            org_id = await _org_of(db, user)
            if org_id:
                unpaid = await db.logiscop_transport_invoices.count_documents(
                    {"org_id": org_id, "status": {"$ne": "PAID"}})
                ots = await db.logiscop_transport_orders.count_documents({"org_id": org_id})
                return FACT_TEMPLATES["buyer"][lang].format(unpaid=unpaid, ots=ots)
        elif space == "admin":
            pending = await db.logiscop_transport_orders.count_documents({"status": "PROPOSE"})
            disputes = await db.logiscop_disputes.count_documents({"status": {"$ne": "RESOLVED"}})
            return FACT_TEMPLATES["admin"][lang].format(pending=pending, disputes=disputes)
        elif space == "vendor":
            vid = user.get("vendor_id")
            if vid:
                pending = await db.products.count_documents({"vendor_id": vid, "status": "pending"})
                return FACT_TEMPLATES["vendor"][lang].format(pending=pending)
    except Exception as exc:
        logger.debug("GUID'IA facts: %s", exc)
    return ""


async def _org_of(db, user: dict):
    m = await db.org_memberships.find_one({"user_id": user["id"]}, {"_id": 0, "org_id": 1})
    return user.get("organization_id") or (m or {}).get("org_id")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:.2f} €"


async def _data_pack(db, user: dict, space: str) -> str:
    """Chiffres précis du membre injectés dans le prompt (impayés, échéances, soldes)."""
    lines = []
    try:
        if space == "buyer":
            org_id = await _org_of(db, user)
            if org_id:
                total, overdue = 0, 0
                from datetime import timedelta
                now = datetime.now(timezone.utc)
                async for inv in db.logiscop_transport_invoices.find(
                        {"org_id": org_id, "status": {"$ne": "PAID"}}, {"_id": 0}).limit(10):
                    credit = await db.logiscop_transport_credits.find_one(
                        {"invoice_id": inv["id"]}, {"_id": 0, "total_ttc_cents": 1})
                    net = max(0, (inv.get("total_ttc_cents") or 0) - ((credit or {}).get("total_ttc_cents") or 0))
                    total += net
                    due = datetime.fromisoformat(inv["issued_at"]) + timedelta(days=30)
                    late = due < now
                    if late:
                        overdue += net
                    lines.append(f"Facture {inv['ref']} : {_eur(net)} net à régler, échéance {due.date()}"
                                 + (" (ÉCHUE)" if late else ""))
                    plan = (inv.get("payment_plan") or {}).get("installments") or []
                    nxt = next((i for i in plan if i.get("status") != "PAID"), None)
                    if nxt:
                        lines.append(f"  Prochaine échéance de l'échéancier {inv['ref']} : "
                                     f"{_eur(nxt['amount_cents'])} le {nxt['due_date']}")
                lines.insert(0, f"Total restant à régler (transport) : {_eur(total)} dont {_eur(overdue)} échus.")
                credits = await db.logiscop_transport_credits.count_documents({"org_id": org_id, "invoice_id": None})
        elif space == "admin":
            from routes_treasury_consolidated import compute_consolidated_treasury
            t = await compute_consolidated_treasury(db)
            lines.append(
                f"Trésorerie : RCR détenue {_eur(t['rcr']['held_cents'])} ; encours transport "
                f"{_eur(t['transport']['outstanding_cents'])} ({t['transport']['unpaid_count']} factures, "
                f"dont échu {_eur(t['transport']['overdue_cents'])}) ; adhésions/mois "
                f"{_eur(t['memberships']['mrr_cents'])} ({t['memberships']['active_count']} actifs) ; "
                f"net projeté 90 j {_eur(t['projected_net_90d_cents'])}.")
        elif space in ("member", "general"):
            w = await db.lolodrive_wallets.find_one({"user_id": user["id"]}, {"_id": 0, "balance_uc": 1})
            if w:
                lines.append(f"Solde wallet : {w.get('balance_uc', 0)} UC.")
    except Exception as exc:
        logger.debug("GUID'IA data pack: %s", exc)
    return "\n".join(lines)[:900]


@ai_guide_router.get("/welcome")
async def guide_welcome(space: str = "general", lang: str = "fr",
                        current_user: dict = Depends(get_current_user)):
    """Accueil personnalisé instantané multilingue + suggestions contextuelles (sans appel LLM)."""
    from ai_guide_i18n import GREETINGS, SUGGESTIONS_I18N, norm_lang
    db = get_database()
    space = _space_of(current_user, space)
    lang = norm_lang(lang)
    first = (current_user.get("contact_name") or current_user.get("name") or "").split(" ")[0]
    facts = await _facts(db, current_user, space, lang)
    g = GREETINGS[lang]
    greeting = g["hello"].format(name=f" {first}" if first else "")
    if facts:
        greeting += g["note"].format(facts=facts)
    greeting += g["ask"]
    suggestions = (SUGGESTIONS_I18N.get(lang, {}).get(space)
                   or BASE_SUGGESTIONS.get(space, BASE_SUGGESTIONS["general"]))
    return {"assistant_name": "GUID'IA", "greeting": greeting, "space": space, "lang": lang,
            "suggestions": suggestions}


class GuideChatBody(BaseModel):
    message: str
    session_id: Optional[str] = None
    space: str = "general"
    lang: str = "fr"


@ai_guide_router.post("/chat")
async def guide_chat(body: GuideChatBody, current_user: dict = Depends(get_current_user)):
    db = get_database()
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide")
    if len(message) > 800:
        raise HTTPException(status_code=400, detail="Message trop long (800 caractères max)")
    space = _space_of(current_user, body.space)
    session_id = body.session_id or f"guide_{uuid.uuid4().hex[:16]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    history = await db.ai_guide_messages.find(
        {"session_id": session_id, "user_id": current_user["id"]},
        {"_id": 0, "role": 1, "content": 1}).sort("created_at", -1).limit(12).to_list(12)
    history_txt = "\n".join(
        f"{'Utilisateur' if m['role'] == 'user' else 'GUID’IA'}: {m['content'][:500]}" for m in reversed(history))

    facts = await _facts(db, current_user, space)
    data_pack = await _data_pack(db, current_user, space)
    from ai_guide_i18n import LANG_NAMES, norm_lang
    lang = norm_lang(body.lang)
    action_ids = SPACE_ACTIONS.get(space, [])
    actions_txt = " ; ".join(f"{a}: {ACTIONS[a][0]}" for a in action_ids)
    context = (
        f"Profil : {current_user.get('contact_name') or current_user.get('email')} — rôle {current_user.get('role')} "
        f"— espace actuel : {SPACE_LABELS[space]}. Langue préférée : {LANG_NAMES[lang]} — réponds dans cette langue."
        + (f" Données en direct : {facts}." if facts else "")
        + (f" Actions disponibles : {actions_txt}." if actions_txt else "")
        + (f"\nDonnées chiffrées exactes du membre (utilise-les pour répondre avec des montants précis) :\n{data_pack}"
           if data_pack else ""))
    prompt = f"{context}\n"
    if history_txt:
        prompt += f"Historique :\n{history_txt}\n"
    prompt += f"Message de l'utilisateur : {message}"

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"), session_id=session_id,
                       system_message=SYSTEM_PROMPT).with_model("openai", "gpt-5.4")
        raw = await chat.send_message(UserMessage(text=prompt)) or ""
    except Exception as exc:
        logger.exception("GUID'IA erreur (session %s): %s", session_id, exc)
        raise HTTPException(status_code=502, detail="GUID'IA est momentanément indisponible — réessayez dans un instant.")

    suggestions = []
    answer = raw
    match = re.search(r"SUGGESTIONS\s*:\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if match:
        suggestions = [s.strip(" -•\n") for s in match.group(1).split("|") if s.strip()][:3]
        answer = raw[:match.start()].strip()
    actions = []
    amatch = re.search(r"ACTIONS\s*:\s*(.+?)$", answer, re.IGNORECASE | re.MULTILINE)
    if amatch:
        allowed = SPACE_ACTIONS.get(space, [])
        for aid in [a.strip(" -•«»\n") for a in amatch.group(1).split("|")]:
            if aid in ACTIONS and aid in allowed:
                actions.append({"id": aid, "label": ACTIONS[aid][0], "path": ACTIONS[aid][1]})
        actions = actions[:2]
        answer = (answer[:amatch.start()] + answer[amatch.end():]).strip()

    await db.ai_guide_messages.insert_many([
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": current_user["id"],
         "role": "user", "content": message, "space": space, "created_at": now_iso},
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": current_user["id"],
         "role": "assistant", "content": answer, "space": space,
         "created_at": datetime.now(timezone.utc).isoformat()}])
    await db.ai_guide_sessions.update_one(
        {"id": session_id},
        {"$set": {"user_id": current_user["id"], "space": space,
                  "last_message_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"created_at": now_iso, "title": message[:70]},
         "$inc": {"messages": 2}},
        upsert=True)
    return {"answer": answer, "suggestions": suggestions, "actions": actions, "session_id": session_id}


class FormHelpBody(BaseModel):
    form_hint: str
    page: str = ""
    space: str = "general"
    lang: str = "fr"


@ai_guide_router.post("/form-help")
async def guide_form_help(body: FormHelpBody, current_user: dict = Depends(get_current_user)):
    """Conseil ciblé quand l'utilisateur semble bloqué sur un formulaire."""
    db = get_database()
    space = _space_of(current_user, body.space)
    from ai_guide_i18n import LANG_NAMES, norm_lang
    lang = norm_lang(body.lang)
    prompt = (
        f"L'utilisateur ({current_user.get('role')}) semble bloqué depuis un moment sur un formulaire de la page "
        f"« {body.page[:120]} » de l'espace {SPACE_LABELS[space]}. Champ / formulaire concerné : "
        f"« {body.form_hint[:200]} ». Donne-lui spontanément un conseil ciblé, bienveillant et concret "
        f"(2-3 phrases max) pour l'aider à compléter ce formulaire, en {LANG_NAMES[lang]}.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"),
                       session_id=f"formhelp_{uuid.uuid4().hex[:10]}",
                       system_message=SYSTEM_PROMPT).with_model("openai", "gpt-5.4")
        raw = await chat.send_message(UserMessage(text=prompt)) or ""
    except Exception as exc:
        logger.warning("GUID'IA form-help erreur : %s", exc)
        raise HTTPException(status_code=502, detail="Aide momentanément indisponible")
    suggestions = []
    match = re.search(r"SUGGESTIONS\s*:\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if match:
        suggestions = [s.strip(" -•\n") for s in match.group(1).split("|") if s.strip()][:3]
        raw = raw[:match.start()].strip()
    raw = re.sub(r"^ACTIONS\s*:.*$", "", raw, flags=re.IGNORECASE | re.MULTILINE).strip()
    return {"tip": raw, "suggestions": suggestions}


FRICTION_THRESHOLD = int(os.environ.get("GUIDIA_FRICTION_THRESHOLD", "5"))


async def check_guidia_friction(db) -> int:
    """Alerte admins quand une même question revient souvent sur 7 jours (idempotent question+semaine)."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    week = datetime.now(timezone.utc).strftime("%G-W%V")
    alerts = 0
    async for g in db.ai_guide_messages.aggregate([
            {"$match": {"role": "user", "created_at": {"$gte": since}}},
            {"$group": {"_id": {"$toLower": {"$trim": {"input": "$content"}}}, "n": {"$sum": 1}}},
            {"$match": {"n": {"$gte": FRICTION_THRESHOLD}}}, {"$sort": {"n": -1}}, {"$limit": 5}]):
        question, count = g["_id"][:150], g["n"]
        if await db.system_flags.find_one({"key": "guidia_friction", "week": week, "question": question}):
            continue
        try:
            from core_deps import create_notification
            await create_notification(
                "guidia_friction", "Point de friction détecté par GUID'IA",
                f"La question « {question} » a été posée {count} fois ces 7 derniers jours — "
                "la page concernée mérite peut-être d'être clarifiée.",
                target_roles=["oscop_super_admin", "kdm_b2b_admin"],
                data={"question": question, "count": count})
        except Exception as exc:
            logger.warning("Notification friction échouée : %s", exc)
        try:
            from brevo_service import send_email, is_brevo_configured
            admin_email = os.environ.get("ADMIN_ALERT_EMAIL") or os.environ.get(
                "QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
            if is_brevo_configured():
                await send_email(
                    to_email=admin_email, to_name="Administration KDMARCHÉ × O'SCOP",
                    subject=f"[GUID'IA] Point de friction : une question revient {count} fois",
                    html_content=(
                        "<div style='font-family:Arial;color:#2A1045'><h2 style='color:#5B2E8C'>Point de friction détecté</h2>"
                        f"<p>La question <b>« {question} »</b> a été posée <b>{count} fois</b> ces 7 derniers jours "
                        "via GUID'IA.</p><p>C'est le signe qu'une page, un onglet ou un parcours mérite d'être "
                        "clarifié. Consultez le panneau « GUID'IA — questions des membres » (onglet Chat IA du "
                        "Super Admin) pour le détail.</p>"
                        "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP</b></p></div>"),
                    tags=["guidia-friction"])
        except Exception as exc:
            logger.warning("Email friction échoué : %s", exc)
        await db.system_flags.insert_one({"key": "guidia_friction", "week": week, "question": question,
                                          "count": count,
                                          "sent_at": datetime.now(timezone.utc).isoformat()})
        alerts += 1
        logger.info("Alerte friction GUID'IA : « %s » ×%d", question, count)
    return alerts


class TtsBody(BaseModel):
    text: str


@ai_guide_router.post("/tts")
async def guide_tts(body: TtsBody, current_user: dict = Depends(get_current_user)):
    """Lecture audio premium des réponses GUID'IA (OpenAI TTS voix naturelle)."""
    text = body.text.strip()[:900]
    if not text:
        raise HTTPException(status_code=400, detail="Texte vide")
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    from fastapi.responses import Response
    try:
        tts = OpenAITextToSpeech(api_key=os.environ.get("EMERGENT_LLM_KEY"))
        audio = await tts.generate_speech(text=text, model="tts-1-hd", voice="coral")
    except Exception as exc:
        logger.warning("GUID'IA TTS erreur : %s", exc)
        raise HTTPException(status_code=502, detail="Synthèse vocale momentanément indisponible")
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Cache-Control": "no-store"})


@ai_guide_router.get("/sessions")
async def guide_sessions(current_user: dict = Depends(get_current_user)):
    """Conversations passées de l'utilisateur avec GUID'IA."""
    db = get_database()
    sessions = await db.ai_guide_sessions.find(
        {"user_id": current_user["id"]}, {"_id": 0}).sort("last_message_at", -1).limit(15).to_list(15)
    return {"sessions": sessions}


@ai_guide_router.get("/sessions/{session_id}/messages")
async def guide_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    session = await db.ai_guide_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    msgs = await db.ai_guide_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1, "created_at": 1}
    ).sort("created_at", 1).to_list(100)
    return {"session": session, "messages": msgs}


@ai_guide_router.get("/admin/stats")
async def guide_admin_stats(current_user: dict = Depends(get_current_user)):
    """Questions les plus posées à GUID'IA — détection des points de friction."""
    from core_deps import check_admin
    await check_admin(current_user)
    db = get_database()
    total = await db.ai_guide_messages.count_documents({"role": "user"})
    users = await db.ai_guide_messages.distinct("user_id", {"role": "user"})
    by_space = {}
    async for g in db.ai_guide_messages.aggregate(
            [{"$match": {"role": "user"}}, {"$group": {"_id": "$space", "n": {"$sum": 1}}}]):
        by_space[g["_id"] or "general"] = g["n"]
    top = []
    async for g in db.ai_guide_messages.aggregate([
            {"$match": {"role": "user"}},
            {"$group": {"_id": {"$toLower": {"$trim": {"input": "$content"}}},
                        "n": {"$sum": 1}, "last": {"$max": "$created_at"}}},
            {"$sort": {"n": -1, "last": -1}}, {"$limit": 10}]):
        top.append({"question": g["_id"][:120], "count": g["n"], "last_asked": g["last"]})
    recent = await db.ai_guide_messages.find(
        {"role": "user"}, {"_id": 0, "content": 1, "space": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    return {"total_questions": total, "unique_users": len(users),
            "by_space": by_space, "top_questions": top, "recent": recent}
