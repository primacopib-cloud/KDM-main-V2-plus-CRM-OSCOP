"""Oracle Admin Exécutif — exécute les tâches d'administration en langage naturel (dictée vocale côté UI).
Flux : /command (compréhension + proposition) → confirmation admin → /execute (whitelist + journal d'audit)."""
import asyncio
import json

import httpx
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
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
    "whatsapp_template_campaign": {"label": "Envoyer une campagne WhatsApp avec un modèle prêt",
                                   "params": ["template_id", "audience", "variables"], "destructive": True},
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
    "3) Recherche externe / analyse marché → {\"mode\":\"research\",\"query\":\"requête de recherche optimisée\"}\n"
    "4) Veille réglementaire (lois, décrets, conformité, bouclier qualité-prix, octroi de mer, ESS, coopératives, "
    "Outre-mer) → {\"mode\":\"veille\",\"query\":\"sujet de veille précis\"}\n"
    "5) Stratégie commerciale (croissance, pricing, campagnes, partenariats, fidélisation) → "
    "{\"mode\":\"strategy\",\"query\":\"objectif stratégique reformulé\"}\n"
    "6) Rédaction ou assistance de contrat commercial (convention POP'S, partenariat fournisseur, prestation, "
    "distribution…) → {\"mode\":\"contract\",\"query\":\"objet du contrat + parties + points clés dictés par l'admin\"}\n"
    "Actions disponibles (id → paramètres requis) :\n"
    + "\n".join(f"- {aid} ({meta['label']}) : {', '.join(meta['params'])}" for aid, meta in ACTIONS_CATALOG.items())
    + "\nRègles params : offer_id / auction_id / product_id doivent venir des listes du contexte (jamais inventés) ; "
    "user_query = email exact si connu, sinon nom/société tels que dictés ; delta = entier relatif (ex. +100, -50) ; "
    "resolution = RELIST ou DON ; role parmi " + ", ".join(VALID_ROLES) + " ; "
    "audience = pops (tous les détaillants POP'S) ou phones:+590...,+596... (liste E.164) ; "
    "template_id parmi les modèles listés dans le contexte ; variables = objet {\"1\":\"valeur\", ...} "
    "remplaçant les {{1}} du modèle.\n"
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
    lines.append(f"WhatsApp société : {'via Brevo (clé présente — nécessite compte WhatsApp Business connecté à Brevo)' if is_whatsapp_configured() else 'NON configuré'}.")
    try:
        tpls = await db.whatsapp_templates.find({}, {"_id": 0, "id": 1, "title": 1, "body": 1}).to_list(10)
        if tpls:
            lines.append("Modèles WhatsApp prêts (utiliser whatsapp_template_campaign) :")
            lines += [f"  template_id={t['id']} | {t['title']} | « {t['body'][:70]}… »" for t in tpls]
    except Exception:
        pass
    exa = bool(os.environ.get("EXA_API_KEY"))
    lines.append(f"Recherche web temps réel : active ({'Exa' if exa else 'DuckDuckGo — EXA_API_KEY optionnelle pour du premium'}).")
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


def _llm_sync(system: str, session_id: str, prompt: str) -> str:
    """Appel LLM dans un thread dédié (litellm bloque l'event loop sinon)."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    async def _go():
        chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"), session_id=session_id,
                       system_message=system).with_model("openai", "gpt-5.4")
        return await chat.send_message(UserMessage(text=prompt)) or ""
    return asyncio.run(_go())


async def _llm_json(session_id: str, prompt: str) -> dict:
    raw = await run_in_threadpool(_llm_sync, SYSTEM_PROMPT, session_id, prompt)
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return {"mode": "answer", "text": raw[:800], "suggestions": []}


async def _web_search(query: str, max_results: int = 6) -> list:
    """Recherche web : Exa si clé présente, sinon DuckDuckGo (sans clé)."""
    if os.environ.get("EXA_API_KEY"):
        try:
            from exa_py import Exa
            exa = Exa(os.environ["EXA_API_KEY"])
            resp = await run_in_threadpool(
                lambda: exa.search(query, type="auto", num_results=max_results, contents={"highlights": True}))
            return [{"title": getattr(r, "title", None) or r.url, "url": r.url,
                     "snippet": " ".join((getattr(r, "highlights", None) or [])[:3])} for r in resp.results]
        except Exception as exc:
            logger.warning("Exa indisponible (%s) — bascule DuckDuckGo", exc)
    try:
        from ddgs import DDGS
        rows = await run_in_threadpool(
            lambda: list(DDGS().text(query, region="fr-fr", max_results=max_results)))
        return [{"title": r.get("title") or "", "url": r.get("href") or r.get("url") or "",
                 "snippet": r.get("body") or ""} for r in rows if r.get("href") or r.get("url")]
    except Exception as exc:
        logger.warning("Recherche web indisponible : %s", exc)
        return []


EXPERT_MODES = {
    "research": {
        "system": "Tu es un analyste senior, rigoureux et professionnel, au service de la direction d'une coopérative ESS des Outre-mer.",
        "searches": lambda q: [q],
        "instructions": ("Rédige une analyse structurée, factuelle et actionnable (8-14 phrases) : contexte, "
                         "chiffres clés, implications pour la coopérative, recommandations. Cite les sources [1], [2]…"),
    },
    "veille": {
        "system": ("Tu es un juriste-veilleur réglementaire senior spécialisé en droit commercial, ESS, coopératives "
                   "et Outre-mer français (bouclier qualité-prix, octroi de mer, loi Lurel, LME, Egalim)."),
        "searches": lambda q: [f"{q} réglementation 2026 Outre-mer", f"{q} site:legifrance.gouv.fr OR site:economie.gouv.fr"],
        "instructions": ("Produis une note de veille réglementaire structurée : 1) TEXTES ET ÉVOLUTIONS RÉCENTES "
                         "(avec dates et références), 2) IMPACT POUR LA COOPÉRATIVE ET LES POP'S, 3) ACTIONS DE MISE "
                         "EN CONFORMITÉ RECOMMANDÉES (priorisées). Cite les sources [1], [2]… Signale toute incertitude."),
    },
    "strategy": {
        "system": ("Tu es un directeur de la stratégie commerciale senior, expert de la grande distribution, du "
                   "e-commerce coopératif et des marchés ultramarins (vie chère, circuits courts, fidélisation)."),
        "searches": lambda q: [f"{q} tendances marché Outre-mer 2026"],
        "instructions": ("Produis une recommandation stratégique structurée : 1) CONSTATS (données internes de la "
                         "plateforme + marché), 2) OPPORTUNITÉS, 3) RECOMMANDATIONS PRIORISÉES (3-5, avec premiers "
                         "pas concrets), 4) KPIs DE SUIVI. Reste réaliste pour une coopérative ESS. Cite les sources si présentes."),
    },
    "contract": {
        "system": ("Tu es un juriste d'affaires senior, expert en rédaction de contrats commerciaux français "
                   "(conventions de partenariat, distribution, prestation, dépôt-vente, ESS/coopératives)."),
        "searches": lambda q: [],
        "instructions": ("Rédige un PROJET de contrat commercial complet et professionnel en articles numérotés "
                         "(Parties, Préambule, Objet, Durée, Obligations réciproques, Conditions financières, "
                         "Confidentialité, RGPD, Responsabilité, Résiliation, Droit applicable et juridiction, "
                         "Signatures) adapté au contexte dicté. Utilise [À COMPLÉTER] pour les informations "
                         "manquantes. Termine OBLIGATOIREMENT par : « Projet généré par Oracle — à faire relire et "
                         "valider par un conseil juridique avant signature. »"),
    },
    "contract_review": {
        "system": ("Tu es un juriste d'affaires senior spécialisé en revue de contrats commerciaux français, "
                   "au service d'une coopérative ESS des Outre-mer."),
        "searches": lambda q: [],
        "instructions": ("Analyse le contrat fourni et produis une revue structurée : 1) SYNTHÈSE (objet, parties, "
                         "durée, montants clés), 2) CLAUSES À RISQUE (chaque clause citée avec sa référence "
                         "d'article, le risque expliqué et sa gravité FAIBLE/MOYENNE/ÉLEVÉE), 3) DÉSÉQUILIBRES ET "
                         "CLAUSES MANQUANTES attendues dans ce type de contrat, 4) RECOMMANDATIONS DE NÉGOCIATION "
                         "priorisées. Termine OBLIGATOIREMENT par : « Analyse générée par Oracle — à faire valider "
                         "par un conseil juridique avant toute décision. »"),
    },
}


async def _expert(kind: str, query: str, lang: str, internal_context: str = "") -> str:
    cfg = EXPERT_MODES[kind]
    sources = []
    for sq in cfg["searches"](query):
        for s in await _web_search(sq, max_results=4):
            if s["url"] not in [x["url"] for x in sources]:
                sources.append(s)
        if len(sources) >= 6:
            break
    sources = sources[:6]
    from ai_guide_i18n import LANG_NAMES
    parts = [f"Demande de l'admin : {query}"]
    if internal_context:
        parts.append(f"Données internes de la plateforme :\n{internal_context}")
    if sources:
        parts.append("Sources web (recherche en direct) :\n" + "\n\n".join(
            f"[{i + 1}] {s['title']}\n{s['url']}\n{s['snippet'][:400]}" for i, s in enumerate(sources)))
    elif kind != "contract":
        parts.append("Aucune source web disponible à l'instant : fonde-toi sur tes connaissances et précise leurs limites temporelles.")
    parts.append(cfg["instructions"])
    parts.append(f"Réponds en {LANG_NAMES.get(lang, 'français')}. Texte brut structuré, pas de Markdown.")
    analysis = await run_in_threadpool(
        _llm_sync, cfg["system"], f"{kind}_{uuid.uuid4().hex[:10]}", "\n\n".join(parts))
    if sources:
        analysis += "\n\nSources :\n" + "\n".join(f"[{i + 1}] {s['title']} — {s['url']}" for i, s in enumerate(sources))
    return analysis


async def _business_snapshot(db) -> str:
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        users = await db.users.count_documents({})
        pops = await db.users.count_documents({"role": "DETAILLANT"})
        offers30 = await db.detaillant_offers.count_documents({"created_at": {"$gte": since}})
        auctions_active = await db.auctions.count_documents({"status": "ACTIVE"})
        orders30 = await db.orders.count_documents({"created_at": {"$gte": since}})
        return (f"Comptes : {users} (dont {pops} POP'S). Offres POP'S 30 j : {offers30}. "
                f"Enchères COOP'ACT actives : {auctions_active}. Commandes 30 j : {orders30}.")
    except Exception:
        return ""


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


EXPERT_LABELS = {"research": "Recherche et analyse", "veille": "Veille réglementaire",
                 "strategy": "Stratégie commerciale", "contract": "Rédaction du contrat",
                 "contract_review": "Analyse du contrat"}

_VERB = r"(r[ée]dige\w*|[ée]cris|pr[ée]pare\w*|g[ée]n[èe]re\w*|propose\w*|[ée]labore\w*|sugg[èe]re\w*|d[ée]finis\w*|construis\w*|fais|assiste\w*|aide)"
EXPERT_HINTS = [
    ("contract", re.compile(_VERB + r"[\s\S]{0,80}\b(contrat|avenant)\b|\b(contrat|avenant)\b[\s\S]{0,40}" + _VERB, re.I)),
    ("veille", re.compile(r"\bveille\b", re.I)),
    ("strategy", re.compile(_VERB + r"[\s\S]{0,80}strat[ée]gie|strat[ée]gie commerciale", re.I)),
    ("research", re.compile(r"fais (une |la )?recherche|recherche (sur|externe)|benchmark|[ée]tude de march[ée]|analyse de march[ée]", re.I)),
]


def _quick_mode(message: str):
    for kind, rx in EXPERT_HINTS:
        if rx.search(message):
            return kind
    return None


async def _launch_expert(db, mode: str, query: str, lang: str, session_id: str, admin: dict, message: str) -> dict:
    internal = await _business_snapshot(db) if mode == "strategy" else ""
    task_id = str(uuid.uuid4())
    await db.oracle_admin_tasks.insert_one(
        {"id": task_id, "admin_id": admin["id"], "kind": mode, "query": query,
         "status": "RUNNING", "created_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(_run_expert_task(task_id, mode, query, lang, internal,
                                         session_id, admin["id"], message))
    return {"answer": f"⏳ {EXPERT_LABELS[mode]} en cours — je consulte les sources externes, "
                      "le résultat arrive dans quelques instants…",
            "suggestions": [], "proposal": None,
            "task": {"id": task_id, "kind": mode}, "session_id": session_id}


async def _run_expert_task(task_id: str, kind: str, query: str, lang: str, internal: str,
                           session_id: str, admin_id: str, message: str):
    db = get_database()
    try:
        answer = await _expert(kind, query, lang, internal)
        await db.oracle_admin_tasks.update_one(
            {"id": task_id},
            {"$set": {"status": "DONE", "answer": answer,
                      "finished_at": datetime.now(timezone.utc).isoformat()}})
        await _store_exchange(db, session_id, admin_id, message, answer)
    except Exception as exc:
        logger.exception("Tâche experte %s échouée", kind)
        await db.oracle_admin_tasks.update_one(
            {"id": task_id}, {"$set": {"status": "FAILED", "error": str(exc)[:300]}})


@oracle_admin_router.post("/command")
async def oracle_admin_command(body: CommandBody, admin: dict = Depends(require_admin)):
    db = get_database()
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Commande vide")
    session_id = body.session_id or f"oadmin_{uuid.uuid4().hex[:16]}"
    from ai_guide_i18n import LANG_NAMES, norm_lang
    lang = norm_lang(body.lang)
    quick = _quick_mode(message)
    if quick:
        return await _launch_expert(db, quick, message, lang, session_id, admin, message)
    history = await db.ai_guide_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1}
    ).sort("created_at", -1).limit(8).to_list(8)
    history_txt = "\n".join(
        f"{'Admin' if m['role'] == 'user' else 'Oracle'}: {m['content'][:400]}" for m in reversed(history))
    context = await _context_pack(db)
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
    if mode in EXPERT_MODES:
        return await _launch_expert(db, mode, parsed.get("query") or message, lang, session_id, admin, message)

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
    if action == "whatsapp_template_campaign":
        from whatsapp_service import whatsapp_status, send_whatsapp_batch
        st = await whatsapp_status()
        if not st["configured"]:
            raise HTTPException(status_code=503, detail=f"WhatsApp (Brevo) non prêt — {st['reason']}")
        tpl = await db.whatsapp_templates.find_one({"id": params.get("template_id")}, {"_id": 0})
        if not tpl:
            raise HTTPException(status_code=404, detail="Modèle WhatsApp introuvable")
        message = tpl["body"]
        for k, v in (params.get("variables") or {}).items():
            message = message.replace("{{%s}}" % k, str(v))
        audience = str(params.get("audience") or "")
        phones = []
        if audience.startswith("phones:"):
            phones = [p.strip() for p in audience[7:].split(",") if re.fullmatch(r"\+?[1-9]\d{7,14}", p.strip())]
        elif audience == "pops":
            async for p in db.detaillant_profiles.find({"phone": {"$nin": ["", None]}}, {"_id": 0, "phone": 1}):
                ph = re.sub(r"[\s.-]", "", p["phone"])
                if re.fullmatch(r"\+?[1-9]\d{7,14}", ph):
                    phones.append(ph)
        if not phones:
            raise HTTPException(status_code=400, detail="Aucun numéro E.164 valide dans l'audience.")
        phones = list(dict.fromkeys(phones))[:100]
        try:
            res = await send_whatsapp_batch(phones, message, st["sender"])
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Échec envoi WhatsApp via Brevo : {exc}")
        ref = res.get("messageId") or res.get("id") or ""
        return (f"Campagne WhatsApp « {tpl['title']} » envoyée via Brevo à {len(phones)} destinataire(s)"
                + (f" — réf. {ref}" if ref else "") + ".")
    if action == "whatsapp_campaign":
        from whatsapp_service import whatsapp_status, send_whatsapp_batch
        st = await whatsapp_status()
        if not st["configured"]:
            raise HTTPException(status_code=503, detail=f"WhatsApp (Brevo) non prêt — {st['reason']}")
        audience = str(params.get("audience") or "")
        phones = []
        if audience.startswith("phones:"):
            phones = [p.strip() for p in audience[7:].split(",") if re.fullmatch(r"\+?[1-9]\d{7,14}", p.strip())]
        elif audience == "pops":
            async for p in db.detaillant_profiles.find({"phone": {"$nin": ["", None]}}, {"_id": 0, "phone": 1}):
                ph = re.sub(r"[\s.-]", "", p["phone"])
                if re.fullmatch(r"\+?[1-9]\d{7,14}", ph):
                    phones.append(ph)
        if not phones:
            raise HTTPException(status_code=400, detail="Aucun numéro E.164 valide dans l'audience.")
        phones = list(dict.fromkeys(phones))[:100]
        try:
            res = await send_whatsapp_batch(phones, params["message"], st["sender"])
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Échec envoi WhatsApp via Brevo : {exc}")
        ref = res.get("messageId") or res.get("id") or ""
        return (f"Campagne WhatsApp envoyée via Brevo à {len(phones)} destinataire(s)"
                + (f" — réf. {ref}" if ref else "") + ".")
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


@oracle_admin_router.get("/task/{task_id}")
async def oracle_admin_task(task_id: str, admin: dict = Depends(require_admin)):
    db = get_database()
    t = await db.oracle_admin_tasks.find_one({"id": task_id, "admin_id": admin["id"]}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return t


@oracle_admin_router.post("/analyze-contract")
async def oracle_admin_analyze_contract(file: UploadFile = File(...),
                                        session_id: Optional[str] = Form(None),
                                        lang: str = Form("fr"),
                                        admin: dict = Depends(require_admin)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Déposez un fichier PDF.")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF trop volumineux (max 15 Mo).")

    def _extract(b: bytes) -> str:
        from io import BytesIO
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(b))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:40])

    try:
        text = await run_in_threadpool(_extract, data)
    except Exception:
        raise HTTPException(status_code=400, detail="PDF illisible — vérifiez le fichier.")
    text = re.sub(r"\n{3,}", "\n\n", text or "").strip()
    if len(text) < 200:
        raise HTTPException(status_code=400, detail="Texte introuvable dans ce PDF (scan sans OCR ?).")
    db = get_database()
    from ai_guide_i18n import norm_lang
    sid = session_id or f"oadmin_{uuid.uuid4().hex[:16]}"
    message = f"Analyse du contrat déposé : {file.filename}"
    query = f"Contrat « {file.filename} » à analyser :\n{text[:24000]}"
    task_id = str(uuid.uuid4())
    await db.oracle_admin_tasks.insert_one(
        {"id": task_id, "admin_id": admin["id"], "kind": "contract_review", "query": message,
         "status": "RUNNING", "created_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(_run_expert_task(task_id, "contract_review", query, norm_lang(lang),
                                         "", sid, admin["id"], message))
    return {"answer": "⏳ Analyse du contrat en cours — clauses à risque, déséquilibres et recommandations "
                      "arrivent dans quelques instants…",
            "suggestions": [], "proposal": None,
            "task": {"id": task_id, "kind": "contract_review"}, "session_id": sid}


@oracle_admin_router.get("/contract-pdf/{task_id}")
async def oracle_admin_contract_pdf(task_id: str, admin: dict = Depends(require_admin)):
    db = get_database()
    t = await db.oracle_admin_tasks.find_one(
        {"id": task_id, "admin_id": admin["id"], "kind": "contract", "status": "DONE"}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Contrat introuvable ou non terminé")
    from oracle_contract_pdf import build_contract_pdf
    pdf = await run_in_threadpool(build_contract_pdf, t.get("answer", ""), t.get("query", ""))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="contrat-oscop-oracle.pdf"'})


@oracle_admin_router.get("/whatsapp-campaigns")
async def oracle_admin_whatsapp_campaigns(admin: dict = Depends(require_admin)):
    from whatsapp_service import BREVO, _headers, is_whatsapp_configured
    if not is_whatsapp_configured():
        return {"campaigns": [], "configured": False}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BREVO}/whatsappCampaigns?limit=50", headers=_headers())
    if r.status_code == 204 or not (r.text or "").strip():
        return {"campaigns": [], "configured": True}
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Brevo injoignable pour les campagnes WhatsApp")
    out = []
    for camp in (r.json().get("campaigns") or []):
        stats = camp.get("stats") or {}
        sent = stats.get("sent") or 0
        delivered = stats.get("delivered") or 0
        read = stats.get("read") or 0
        out.append({
            "id": camp.get("id"), "name": camp.get("campaignName") or camp.get("name") or "",
            "status": camp.get("campaignStatus") or camp.get("status") or "",
            "scheduled_at": camp.get("scheduledAt") or camp.get("createdAt") or "",
            "template_id": camp.get("templateId"),
            "sent": sent, "delivered": delivered, "read": read,
            "errors": stats.get("error") or stats.get("errors") or 0,
            "delivery_rate": round(delivered / sent * 100, 1) if sent else 0,
            "read_rate": round(read / sent * 100, 1) if sent else 0,
        })
    return {"campaigns": out, "configured": True}


@oracle_admin_router.get("/veille-digests")
async def oracle_admin_veille_digests(q: Optional[str] = None, admin: dict = Depends(require_admin)):
    db = get_database()
    flt = {"note": {"$regex": re.escape(q.strip()), "$options": "i"}} if q and q.strip() else {}
    items = await db.oracle_veille_digests.find(flt, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    return {"digests": items}


@oracle_admin_router.get("/audit")
async def oracle_admin_audit(admin: dict = Depends(require_admin)):
    db = get_database()
    items = await db.oracle_admin_audit.find(
        {}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"audit": items}

cron_router = APIRouter(prefix="/api/cron", tags=["cron"])


def _check_cron_auth(authorization):
    import hmac
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not secret or not token or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="unauthorized")


DEFAULT_VEILLE_THEMES = ["bouclier qualité-prix", "octroi de mer", "vie chère",
                         "ESS et coopératives", "commerce coopératif"]


async def _get_veille_themes(db) -> list:
    doc = await db.veille_settings.find_one({"id": "veille"}, {"_id": 0})
    themes = (doc or {}).get("themes") or []
    return themes if themes else DEFAULT_VEILLE_THEMES


@oracle_admin_router.get("/veille-themes")
async def oracle_admin_get_veille_themes(admin: dict = Depends(require_admin)):
    db = get_database()
    return {"themes": await _get_veille_themes(db), "defaults": DEFAULT_VEILLE_THEMES}


class VeilleThemesBody(BaseModel):
    themes: list


@oracle_admin_router.put("/veille-themes")
async def oracle_admin_put_veille_themes(body: VeilleThemesBody, admin: dict = Depends(require_admin)):
    themes = [str(t).strip()[:60] for t in (body.themes or []) if str(t).strip()][:10]
    if not themes:
        raise HTTPException(status_code=400, detail="Indiquez au moins un thème de veille.")
    db = get_database()
    await db.veille_settings.update_one(
        {"id": "veille"},
        {"$set": {"themes": themes, "updated_by": admin.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True, "themes": themes}


async def _weekly_veille_job():
    db = get_database()
    try:
        themes = await _get_veille_themes(db)
        note = await _expert(
            "veille",
            "évolutions réglementaires récentes en Outre-mer français sur les thèmes suivis par la "
            "coopérative : " + ", ".join(themes), "fr")
        from brevo_service import send_email
        admins = await db.users.find(
            {"role": {"$in": ["SUPER_ADMIN", "oscop_super_admin", "ADMIN"]}, "email": {"$nin": ["", None]}},
            {"_id": 0, "email": 1, "name": 1}).to_list(20)
        week = datetime.now(timezone.utc).strftime("Semaine du %d/%m/%Y")
        safe = note.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = ("<div style='font-family:Helvetica,Arial,sans-serif;max-width:640px;margin:auto'>"
                "<p style='color:#B8860B;font-weight:bold;font-size:13px'>O'SCOP × ORACLE — VEILLE "
                "RÉGLEMENTAIRE HEBDOMADAIRE</p>"
                f"<p style='color:#555;font-size:12px'>{week} — note générée automatiquement par Oracle "
                "(sources externes consultées). À faire valider par un conseil juridique.</p>"
                f"<pre style='white-space:pre-wrap;font-family:inherit;font-size:13px;color:#1F2A3A;"
                f"line-height:1.5'>{safe}</pre></div>")
        sent = 0
        for a in admins:
            try:
                await send_email(a["email"], a.get("name"),
                                 f"Veille réglementaire Outre-mer — {week}", html, tags=["veille-hebdo"])
                sent += 1
            except Exception:
                logger.warning("Veille hebdo : envoi échoué pour %s", a.get("email"))
        await db.oracle_veille_digests.insert_one(
            {"id": str(uuid.uuid4()), "week": week, "note": note, "sent": sent,
             "created_at": datetime.now(timezone.utc).isoformat()})
        logger.info("Veille hebdo envoyée à %s admin(s)", sent)
    except Exception:
        logger.exception("Veille hebdo échouée")


@cron_router.post("/weekly-veille")
async def cron_weekly_veille(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    _check_cron_auth(request.headers.get("authorization"))
    try:
        body = await request.json()
    except Exception:
        body = {}
    run_id = request.headers.get("x-webhook-id") or body.get("run_id") or str(uuid.uuid4())
    db = get_database()
    if await db.cron_runs.find_one({"run_id": run_id, "job": "weekly-veille"}):
        return {"ok": True, "duplicate": True}
    await db.cron_runs.insert_one({"run_id": run_id, "job": "weekly-veille",
                                   "created_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(_weekly_veille_job())
    return {"ok": True}
