"""Oracle Admin Exécutif — exécute les tâches d'administration en langage naturel (dictée vocale côté UI).
Flux : /command (compréhension + proposition) → confirmation admin → /execute (whitelist + journal d'audit)."""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from db import get_database
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
oracle_admin_router = APIRouter(prefix="/api/oracle-admin", tags=["oracle-admin"])

VALID_ROLES = ["COOPER", "DETAILLANT", "GERANT_LOLO_POINT", "OPERATEUR_POS",
               "TITULAIRE_PASS", "buyer", "vendor"]

ACTIONS_CATALOG = {
    "approve_pops_offer": {"label": "Valider une offre POP'S", "params": ["offer_id"], "destructive": False},
    "reject_pops_offer": {"label": "Rejeter une offre POP'S (crédits remboursés)", "params": ["offer_id", "note"], "destructive": True},
    "adjust_coopact_credits": {"label": "Ajuster les crédits COOP'ACT d'un membre", "params": ["user_query", "delta", "reason"], "destructive": True},
    "settle_incident": {"label": "Régler un avoir gagnant (incident retrait)", "params": ["auction_id"], "destructive": False},
    "resolve_abandoned_lot": {"label": "Trancher un lot abandonné", "params": ["auction_id", "resolution", "note"], "destructive": True},
    "suspend_user": {"label": "Suspendre un membre", "params": ["user_query"], "destructive": True},
    "activate_user": {"label": "Réactiver un membre", "params": ["user_query"], "destructive": False},
    "change_user_role": {"label": "Changer le rôle d'un membre", "params": ["user_query", "role"], "destructive": True},
    "resend_welcome_email": {"label": "Renvoyer l'email de bienvenue", "params": ["user_query"], "destructive": False},
    "approve_product": {"label": "Approuver un produit vendeur", "params": ["product_id"], "destructive": False},
    "reject_product": {"label": "Rejeter un produit vendeur", "params": ["product_id", "note"], "destructive": True},
    "hide_product": {"label": "Masquer un produit du catalogue", "params": ["product_id"], "destructive": True},
    "whatsapp_campaign": {"label": "Envoyer une campagne WhatsApp", "params": ["audience", "message"], "destructive": True},
}

SYSTEM_PROMPT = (
    "Tu es Oracle Admin, le copilote exécutif du Super Admin de Communityplace (KDMARCHÉ × O'SCOP), plateforme "
    "coopérative ESS des Outre-mer. L'admin te donne des commandes en langage naturel (souvent dictées à la voix) ; "
    "tu les transformes en actions d'administration précises, ou tu réponds à ses questions, ou tu mènes des "
    "recherches externes avec des analyses professionnelles.\n"
    "Tu réponds EXCLUSIVEMENT avec un objet JSON valide, sans balises Markdown, sans texte autour. Formats :\n"
    "1) Question/conversation → {\"mode\":\"answer\",\"text\":\"réponse claire 2-6 phrases\","
    "\"suggestions\":[\"q1\",\"q2\",\"q3\"]}\n"
    "2) Commande d'administration → {\"mode\":\"propose\",\"action\":\"<id>\",\"params\":{...},"
    "\"summary\":\"phrase décrivant précisément ce qui sera exécuté\"}\n"
    "3) Recherche externe / veille / analyse marché → {\"mode\":\"research\",\"query\":\"requête de recherche "
    "optimisée en anglais ou français\"}\n"
    "Actions disponibles (id → paramètres requis) :\n"
    + "\n".join(f"- {aid} ({meta['label']}) : {', '.join(meta['params'])}" for aid, meta in ACTIONS_CATALOG.items())
    + "\nRègles params : offer_id / auction_id / product_id doivent venir des listes du contexte (jamais inventés) ; "
    "user_query = email exact si connu, sinon nom/société tels que dictés ; delta = entier relatif (ex. +100, -50) ; "
    "resolution = RELIST ou DON ; role parmi " + ", ".join(VALID_ROLES) + " ; "
    "audience = pops (tous les détaillants POP'S) ou phones:+590...,+596... (liste E.164).\n"
    "Si la commande est ambiguë ou l'entité introuvable dans le contexte, réponds en mode answer en demandant la "
    "précision manquante (propose les candidats du contexte). Ne propose JAMAIS une action hors catalogue. "
    "Réponds dans la langue de l'admin (français par défaut), ton professionnel."
)


async def _context_pack(db) -> str:
    lines = []
    try:
        offers = await db.detaillant_offers.find(
            {"status": "PENDING"}, {"_id": 0, "id": 1, "company_name": 1, "product_name": 1,
                                    "final_price": 1, "created_at": 1}).sort("created_at", -1).limit(10).to_list(10)
        if offers:
            lines.append("Offres POP'S en attente de validation :")
            lines += [f"  offer_id={o['id']} | {o.get('company_name')} | {o.get('product_name')} | "
                      f"{o.get('final_price')} € | déposée {(o.get('created_at') or '')[:10]}" for o in offers]
        incidents = await db.auctions.find(
            {"pickup_incident.settled": False},
            {"_id": 0, "id": 1, "reference": 1, "title": 1, "winner.name": 1,
             "pickup_incident.credit_eur": 1}).limit(10).to_list(10)
        if incidents:
            lines.append("Avoirs gagnants à régler (incidents retrait) :")
            lines += [f"  auction_id={a['id']} | {a.get('reference')} | {a.get('title')} | gagnant "
                      f"{(a.get('winner') or {}).get('name')} | avoir {(a.get('pickup_incident') or {}).get('credit_eur')} €"
                      for a in incidents]
        abandoned = await db.auctions.find(
            {"abandoned_action": "PENDING"},
            {"_id": 0, "id": 1, "reference": 1, "title": 1}).limit(10).to_list(10)
        if abandoned:
            lines.append("Lots abandonnés à trancher (RELIST ou DON) :")
            lines += [f"  auction_id={a['id']} | {a.get('reference')} | {a.get('title')}" for a in abandoned]
        products = await db.products.find(
            {"status": "pending_approval"}, {"_id": 0, "id": 1, "name": 1, "vendor_name": 1}).limit(10).to_list(10)
        if products:
            lines.append("Produits vendeurs en attente d'approbation :")
            lines += [f"  product_id={p['id']} | {p.get('name')} | vendeur {p.get('vendor_name')}" for p in products]
    except Exception as exc:
        logger.debug("Oracle admin context: %s", exc)
    from whatsapp_service import is_whatsapp_configured
    lines.append(f"WhatsApp société : {'configuré' if is_whatsapp_configured() else 'NON configuré (clés Twilio manquantes)'}.")
    exa = bool(os.environ.get("EXA_API_KEY"))
    lines.append(f"Recherche web temps réel : {'active (Exa)' if exa else 'clé EXA_API_KEY absente — analyses sur base de connaissances'}.")
    return "\n".join(lines)[:3500]


async def _find_users(db, q: str) -> list:
    q = (q or "").strip()
    if not q:
        return []
    rx = {"$regex": re.escape(q), "$options": "i"}
    return await db.users.find(
        {"$or": [{"email": rx}, {"name": rx}, {"contact_name": rx}, {"company_name": rx}]},
        {"_id": 0, "id": 1, "email": 1, "name": 1, "contact_name": 1, "role": 1, "suspended": 1}
    ).limit(5).to_list(5)


async def _llm_json(session_id: str, prompt: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"), session_id=session_id,
                   system_message=SYSTEM_PROMPT).with_model("openai", "gpt-5.4")
    raw = await chat.send_message(UserMessage(text=prompt)) or ""
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return {"mode": "answer", "text": raw[:800], "suggestions": []}


async def _research(query: str, lang: str) -> str:
    sources = []
    if os.environ.get("EXA_API_KEY"):
        try:
            from exa_py import Exa
            exa = Exa(os.environ["EXA_API_KEY"])
            resp = await run_in_threadpool(
                lambda: exa.search(query, type="auto", num_results=5, contents={"highlights": True}))
            sources = [{"title": getattr(r, "title", None) or r.url, "url": r.url,
                        "highlights": getattr(r, "highlights", None) or []} for r in resp.results]
        except Exception as exc:
            logger.warning("Recherche Exa échouée : %s", exc)
    from ai_guide_i18n import LANG_NAMES
    if sources:
        evidence = "\n\n".join(f"[{i + 1}] {s['title']}\n{s['url']}\n" + "\n".join(s["highlights"][:3])
                               for i, s in enumerate(sources))
        prompt = (f"Analyse professionnelle pour la direction de la coopérative KDMARCHÉ × O'SCOP (Outre-mer, ESS). "
                  f"Question : {query}\nSources web :\n{evidence}\n"
                  f"Rédige une analyse structurée, factuelle et actionnable (5-10 phrases), cite les sources [1], [2]… "
                  f"Réponds en {LANG_NAMES.get(lang, 'français')}. Texte brut, pas de Markdown.")
    else:
        prompt = (f"Analyse professionnelle pour la direction de la coopérative KDMARCHÉ × O'SCOP (Outre-mer, ESS). "
                  f"Question : {query}\nAucune source web en direct disponible : fonde-toi sur tes connaissances, "
                  f"précise les limites temporelles de l'analyse. 5-10 phrases structurées et actionnables, "
                  f"en {LANG_NAMES.get(lang, 'français')}. Texte brut, pas de Markdown.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"),
                   session_id=f"research_{uuid.uuid4().hex[:10]}",
                   system_message="Tu es un analyste senior, rigoureux et professionnel.").with_model("openai", "gpt-5.4")
    analysis = await chat.send_message(UserMessage(text=prompt)) or ""
    if sources:
        analysis += "\n\nSources :\n" + "\n".join(f"[{i + 1}] {s['title']} — {s['url']}" for i, s in enumerate(sources))
    else:
        analysis += "\n\n(Analyse sur base de connaissances — ajoutez la clé EXA_API_KEY pour la recherche web en temps réel.)"
    return analysis


class CommandBody(BaseModel):
    message: str
    session_id: Optional[str] = None
    lang: str = "fr"


class ExecuteBody(BaseModel):
    proposal_id: str


async def _store_exchange(db, session_id: str, user_id: str, question: str, answer: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.ai_guide_messages.insert_many([
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id,
         "role": "user", "content": question, "space": "admin", "created_at": now_iso},
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id,
         "role": "assistant", "content": answer, "space": "admin",
         "created_at": datetime.now(timezone.utc).isoformat()}])
    await db.ai_guide_sessions.update_one(
        {"id": session_id},
        {"$set": {"user_id": user_id, "space": "admin",
                  "last_message_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"created_at": now_iso, "title": question[:70]},
         "$inc": {"messages": 2}}, upsert=True)


@oracle_admin_router.post("/command")
async def oracle_admin_command(body: CommandBody, admin: dict = Depends(require_admin)):
    db = get_database()
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Commande vide")
    session_id = body.session_id or f"oadmin_{uuid.uuid4().hex[:16]}"
    history = await db.ai_guide_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1}
    ).sort("created_at", -1).limit(8).to_list(8)
    history_txt = "\n".join(
        f"{'Admin' if m['role'] == 'user' else 'Oracle'}: {m['content'][:400]}" for m in reversed(history))
    context = await _context_pack(db)
    from ai_guide_i18n import LANG_NAMES, norm_lang
    lang = norm_lang(body.lang)
    prompt = (f"Contexte plateforme en direct :\n{context}\n"
              f"Langue de l'admin : {LANG_NAMES[lang]}.\n"
              + (f"Historique :\n{history_txt}\n" if history_txt else "")
              + f"Commande de l'admin : {message}")
    try:
        parsed = await _llm_json(session_id, prompt)
    except Exception as exc:
        logger.exception("Oracle admin LLM erreur : %s", exc)
        raise HTTPException(status_code=502, detail="Oracle Admin momentanément indisponible — réessayez.")

    mode = parsed.get("mode")
    if mode == "research":
        answer = await _research(parsed.get("query") or message, lang)
        await _store_exchange(db, session_id, admin["id"], message, answer)
        return {"answer": answer, "suggestions": [], "proposal": None, "session_id": session_id}

    if mode == "propose":
        action = parsed.get("action")
        params = parsed.get("params") or {}
        meta = ACTIONS_CATALOG.get(action)
        if not meta:
            answer = "Cette action n'est pas dans mon catalogue d'administration — reformulez votre commande."
            await _store_exchange(db, session_id, admin["id"], message, answer)
            return {"answer": answer, "suggestions": [], "proposal": None, "session_id": session_id}
        resolved_user = None
        if "user_query" in meta["params"]:
            matches = await _find_users(db, str(params.get("user_query") or ""))
            if not matches:
                answer = f"Aucun membre ne correspond à « {params.get('user_query')} ». Précisez l'email exact."
                await _store_exchange(db, session_id, admin["id"], message, answer)
                return {"answer": answer, "suggestions": [], "proposal": None, "session_id": session_id}
            if len(matches) > 1:
                cands = "\n".join(f"• {u.get('contact_name') or u.get('name') or '—'} — {u['email']} ({u.get('role')})"
                                  for u in matches)
                answer = f"Plusieurs membres correspondent :\n{cands}\nReformulez avec l'email exact."
                await _store_exchange(db, session_id, admin["id"], message, answer)
                return {"answer": answer, "suggestions": [], "proposal": None, "session_id": session_id}
            resolved_user = matches[0]
            params["user_id"] = resolved_user["id"]
            params["user_email"] = resolved_user["email"]
        if action == "change_user_role" and params.get("role") not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Rôle invalide — rôles possibles : {', '.join(VALID_ROLES)}")
        summary = parsed.get("summary") or meta["label"]
        if resolved_user:
            summary += f" — membre : {resolved_user.get('contact_name') or resolved_user.get('name') or ''} <{resolved_user['email']}>"
        proposal = {"id": str(uuid.uuid4()), "admin_id": admin["id"], "action": action,
                    "label": meta["label"], "params": params, "summary": summary,
                    "destructive": meta["destructive"], "status": "PROPOSED",
                    "session_id": session_id,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()}
        await db.oracle_admin_proposals.insert_one({**proposal})
        answer = f"Action prête : {summary}\nConfirmez avec « Exécuter » ou annulez."
        await _store_exchange(db, session_id, admin["id"], message, answer)
        proposal.pop("admin_id")
        return {"answer": answer, "suggestions": [], "proposal": proposal, "session_id": session_id}

    answer = parsed.get("text") or "Je n'ai pas compris — reformulez votre commande."
    await _store_exchange(db, session_id, admin["id"], message, answer)
    return {"answer": answer, "suggestions": (parsed.get("suggestions") or [])[:3],
            "proposal": None, "session_id": session_id}


async def _execute_action(db, action: str, params: dict, admin: dict) -> str:
    if action in ("approve_pops_offer", "reject_pops_offer"):
        from routes_detaillant import admin_review_offer, ReviewBody
        act = "APPROVE" if action == "approve_pops_offer" else "REJECT"
        await admin_review_offer(params["offer_id"], ReviewBody(action=act, note=params.get("note")), admin)
        if act == "APPROVE":
            return f"Offre POP'S {params['offer_id'][:8]}… validée et programmée en salle COOP'ACT."
        return f"Offre POP'S {params['offer_id'][:8]}… rejetée (crédits remboursés au POP'S)."
    if action == "adjust_coopact_credits":
        delta = int(params["delta"])
        now = datetime.now(timezone.utc).isoformat()
        await db.auction_accounts.update_one(
            {"user_id": params["user_id"]},
            {"$inc": {"credits": delta}, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True)
        await db.auction_credit_ledger.insert_one({
            "id": str(uuid.uuid4()), "user_id": params["user_id"], "type": "ADMIN_ADJUST",
            "amount": delta, "label": f"Ajustement Oracle Admin — {params.get('reason') or 'sans motif'}",
            "by": admin.get("email"), "created_at": now})
        acc = await db.auction_accounts.find_one({"user_id": params["user_id"]}, {"_id": 0, "credits": 1})
        return f"Crédits COOP'ACT de {params['user_email']} ajustés de {delta:+d} — nouveau solde : {(acc or {}).get('credits', 0)}."
    if action == "settle_incident":
        from routes_auctions_admin import settle_pickup_incident
        r = await settle_pickup_incident(params["auction_id"], admin)
        return f"Avoir réglé — {r.get('credits_granted', 0)} crédits COOP'ACT crédités au gagnant (email envoyé)."
    if action == "resolve_abandoned_lot":
        from routes_auctions_admin import resolve_abandoned_lot, AbandonedResolveBody
        r = await resolve_abandoned_lot(
            params["auction_id"], AbandonedResolveBody(action=params.get("resolution", "").upper(),
                                                       note=params.get("note")), admin)
        return (f"Lot remis en salle — nouvelle référence {r['new_reference']}." if r.get("new_reference")
                else f"Lot tranché en don solidaire : {r.get('don')}.")
    if action in ("suspend_user", "activate_user"):
        suspended = action == "suspend_user"
        await db.users.update_one({"id": params["user_id"]},
                                  {"$set": {"suspended": suspended,
                                            "updated_at": datetime.now(timezone.utc).isoformat()}})
        return f"Membre {params['user_email']} {'suspendu' if suspended else 'réactivé'}."
    if action == "change_user_role":
        await db.users.update_one({"id": params["user_id"]},
                                  {"$set": {"role": params["role"],
                                            "updated_at": datetime.now(timezone.utc).isoformat()}})
        return f"Rôle de {params['user_email']} changé en {params['role']}."
    if action == "resend_welcome_email":
        from brevo_service import send_email, is_brevo_configured
        if not is_brevo_configured():
            raise HTTPException(status_code=503, detail="Service email non configuré")
        u = await db.users.find_one({"id": params["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "name": 1})
        name = u.get("contact_name") or u.get("name") or ""
        await send_email(
            to_email=u["email"], to_name=name or u["email"],
            subject="Bienvenue sur KDMARCHÉ × O'SCOP",
            html_content=(f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#5B2E8C'>Bienvenue{' ' + name if name else ''} !</h2>"
                          "<p>Votre espace Communityplace KDMARCHÉ × O'SCOP vous attend : connectez-vous pour "
                          "découvrir le catalogue, la salle COOP'ACT et votre PASS Vie Chère.</p>"
                          "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP</b></p></div>"),
            tags=["welcome-resend"])
        return f"Email de bienvenue renvoyé à {u['email']}."
    if action == "approve_product":
        from routes_superadmin import approve_product
        await approve_product(params["product_id"])
        return f"Produit {params['product_id'][:8]}… approuvé et publié au catalogue."
    if action == "reject_product":
        from routes_superadmin import reject_product
        await reject_product(params["product_id"], params.get("note") or "")
        return f"Produit {params['product_id'][:8]}… rejeté."
    if action == "hide_product":
        r = await db.products.update_one(
            {"id": params["product_id"]},
            {"$set": {"status": "hidden", "hidden_at": datetime.now(timezone.utc).isoformat(),
                      "hidden_by": admin.get("email")}})
        if not r.matched_count:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        return f"Produit {params['product_id'][:8]}… masqué du catalogue."
    if action == "whatsapp_campaign":
        from whatsapp_service import is_whatsapp_configured, send_whatsapp
        if not is_whatsapp_configured():
            raise HTTPException(status_code=503, detail=(
                "WhatsApp non configuré — fournissez TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN et "
                "TWILIO_WHATSAPP_FROM pour connecter le WhatsApp de la société."))
        audience = str(params.get("audience") or "")
        phones = []
        if audience.startswith("phones:"):
            phones = [p.strip() for p in audience[7:].split(",") if re.fullmatch(r"\+[1-9]\d{7,14}", p.strip())]
        elif audience == "pops":
            async for p in db.detaillant_profiles.find({"phone": {"$nin": ["", None]}}, {"_id": 0, "phone": 1}):
                ph = re.sub(r"[\s.-]", "", p["phone"])
                if re.fullmatch(r"\+[1-9]\d{7,14}", ph):
                    phones.append(ph)
        if not phones:
            raise HTTPException(status_code=400, detail="Aucun numéro E.164 valide dans l'audience.")
        phones = list(dict.fromkeys(phones))[:50]
        sent, failed = 0, 0
        for ph in phones:
            try:
                await run_in_threadpool(send_whatsapp, ph, params["message"])
                sent += 1
            except Exception as exc:
                failed += 1
                logger.warning("WhatsApp échec %s : %s", ph[-4:], exc)
        return f"Campagne WhatsApp envoyée : {sent} message(s) sur {len(phones)} ({failed} échec(s))."
    raise HTTPException(status_code=400, detail="Action inconnue")


@oracle_admin_router.post("/execute")
async def oracle_admin_execute(body: ExecuteBody, admin: dict = Depends(require_admin)):
    db = get_database()
    prop = await db.oracle_admin_proposals.find_one({"id": body.proposal_id}, {"_id": 0})
    if not prop or prop.get("admin_id") != admin["id"]:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    if prop.get("status") != "PROPOSED":
        raise HTTPException(status_code=409, detail="Proposition déjà traitée")
    if datetime.fromisoformat(prop["expires_at"]) < datetime.now(timezone.utc):
        await db.oracle_admin_proposals.update_one({"id": prop["id"]}, {"$set": {"status": "EXPIRED"}})
        raise HTTPException(status_code=410, detail="Proposition expirée (15 min) — redonnez la commande.")
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        message = await _execute_action(db, prop["action"], prop["params"], admin)
        status, detail = "EXECUTED", message
    except HTTPException as exc:
        status, detail = "FAILED", exc.detail
    except Exception as exc:
        logger.exception("Oracle admin exécution : %s", exc)
        status, detail = "FAILED", "Erreur interne pendant l'exécution"
    await db.oracle_admin_proposals.update_one({"id": prop["id"]}, {"$set": {"status": status}})
    await db.oracle_admin_audit.insert_one({
        "id": str(uuid.uuid4()), "admin_id": admin["id"], "admin_email": admin.get("email"),
        "action": prop["action"], "label": prop["label"], "params": prop["params"],
        "summary": prop["summary"], "status": status, "result": detail, "created_at": now_iso})
    if status == "FAILED":
        raise HTTPException(status_code=422, detail=detail)
    await db.ai_guide_messages.insert_one({
        "id": str(uuid.uuid4()), "session_id": prop.get("session_id"), "user_id": admin["id"],
        "role": "assistant", "content": f"✅ {message}", "space": "admin", "created_at": now_iso})
    return {"ok": True, "message": message}


@oracle_admin_router.post("/cancel")
async def oracle_admin_cancel(body: ExecuteBody, admin: dict = Depends(require_admin)):
    db = get_database()
    await db.oracle_admin_proposals.update_one(
        {"id": body.proposal_id, "admin_id": admin["id"], "status": "PROPOSED"},
        {"$set": {"status": "CANCELLED"}})
    return {"ok": True}


@oracle_admin_router.get("/audit")
async def oracle_admin_audit(admin: dict = Depends(require_admin)):
    db = get_database()
    items = await db.oracle_admin_audit.find(
        {}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"audit": items}
