"""ENCHÈR'IA — agent IA des enchères : relances automatiques des vendeurs silencieux + rapport d'adjudication IA."""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

db = None


def set_encheria_database(database):
    global db
    db = database


async def process_encheria(database) -> None:
    """Scheduler : relance les vendeurs sans offre à J-2 de la clôture des consultations publiées."""
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(database)
    if not s.get("encheria_enabled"):
        return
    now = datetime.now(timezone.utc)
    horizon = (now + timedelta(days=2)).isoformat()
    consults = await database.consultations.find(
        {"status": {"$in": ["PUBLIEE", "EN_COURS", "INSCRIPTIONS_OUVERTES"]},
         "closes_at": {"$gt": now.isoformat(), "$lt": horizon},
         "encheria_relance_sent": {"$ne": True}}, {"_id": 0}).to_list(20)
    for c in consults:
        try:
            bidders = set(await database.bids.distinct("vendor_id", {"consultation_id": c["id"]}))
            vendors = await database.vendors.find({"status": "approved"}, {"_id": 0, "id": 1, "email": 1, "company_name": 1}).to_list(200)
            silent = [v for v in vendors if v["id"] not in bidders and v.get("email")][:50]
            if silent:
                from brevo_service import send_email
                closes = (c.get("closes_at") or "")[:10]
                for v in silent:
                    try:
                        await send_email(
                            to_email=v["email"], to_name=v.get("company_name"),
                            subject=f"⏳ Dernière ligne droite — consultation « {c.get('title', c['id'])} » clôture le {closes}",
                            html_content=(
                                "<div style='font-family:Arial,sans-serif;max-width:560px'>"
                                f"<h2 style='color:#5B2E8C'>ENCHÈR'IA vous rappelle une opportunité</h2>"
                                f"<p style='font-size:14px'>La consultation <strong>{c.get('title', c['id'])}</strong> "
                                f"se clôture le <strong>{closes}</strong> et vous n'avez pas encore déposé d'offre.</p>"
                                "<p style='font-size:13px;color:#555'>Connectez-vous à votre espace vendeur pour soumettre votre meilleure proposition.</p>"
                                "<p style='color:#999;font-size:11px;margin-top:16px'>Agent ENCHÈR'IA — KDMARCHÉ × O'SCOP</p></div>"),
                            tags=["encheria-relance"])
                    except Exception as exc:
                        logger.warning("ENCHÈR'IA relance échouée %s : %s", v["email"], exc)
            await database.consultations.update_one({"id": c["id"]}, {"$set": {"encheria_relance_sent": True}})
            from consultation_audit import audit
            await audit("ENCHERIA_RELANCE", "encheria", c["id"], {"vendors_relanced": len(silent)})
            logger.info("ENCHÈR'IA : %s vendeur(s) relancé(s) pour %s", len(silent), c["id"])
        except Exception as exc:
            logger.error("ENCHÈR'IA relance consultation %s échouée : %s", c.get("id"), exc)


async def generate_adjudication_report(cid: str) -> None:
    """À la clôture : analyse IA des offres + recommandation, stockée et notifiée."""
    try:
        from ai_agents_settings import get_agents_settings
        s = await get_agents_settings(db)
        if not s.get("encheria_enabled"):
            return
        c = await db.consultations.find_one({"id": cid}, {"_id": 0})
        if not c:
            return
        bids = await db.bids.find({"consultation_id": cid}, {"_id": 0}).to_list(100)
        bids_txt = "\n".join(
            f"- Vendeur {b.get('vendor_id')} : montant {b.get('amount_cents', b.get('amount', '?'))} , délai {b.get('lead_time_days', '?')} j, note: {str(b.get('comment', ''))[:120]}"
            for b in bids) or "Aucune offre déposée."
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"encheria-{uuid.uuid4()}",
            system_message=("Tu es ENCHÈR'IA, analyste expert des enchères inversées B2B de la Communityplace "
                            "KDMARCHÉ × O'SCOP. Produis un rapport d'adjudication clair et structuré en français."),
        ).with_model("openai", "gpt-5.4")
        prompt = (
            f"Consultation « {c.get('title', cid)} » ({cid}) clôturée. Critères : {c.get('criteria', 'prix, délai, qualité')}.\n"
            f"Offres reçues :\n{bids_txt}\n\n"
            "Rédige le rapport d'adjudication : 1) Synthèse (2 phrases), 2) Analyse comparative des offres, "
            "3) Risques identifiés, 4) Recommandation motivée (quelle offre retenir ou relancer). "
            "Si aucune offre : recommande des actions concrètes de relance. Max 350 mots.")
        report = str(await chat.send_message(UserMessage(text=prompt))).strip()
        from ai_usage import log_ai_usage
        await log_ai_usage(db, "encheria_report", cid)
        await db.encheria_reports.insert_one({
            "id": str(uuid.uuid4()), "consultation_id": cid, "title": c.get("title", cid),
            "bids_count": len(bids), "report": report,
            "created_at": datetime.now(timezone.utc).isoformat()})
        from consultation_audit import audit
        await audit("ENCHERIA_REPORT", "encheria", cid, {"bids_count": len(bids)})
        logger.info("ENCHÈR'IA : rapport d'adjudication généré pour %s (%s offres)", cid, len(bids))
    except Exception as exc:
        logger.error("ENCHÈR'IA rapport %s échoué : %s", cid, exc)
