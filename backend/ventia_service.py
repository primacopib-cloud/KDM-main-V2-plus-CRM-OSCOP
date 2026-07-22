"""VENT'IA — assistant de vente : descriptions produits IA, conseils prix, relance paniers abandonnés."""
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from checkout_common import get_current_user_checkout

logger = logging.getLogger(__name__)
ventia_router = APIRouter(prefix="/api/vendor/ai", tags=["ventia"])
db = None


def set_ventia_database(database):
    global db
    db = database


class ProductCopyBody(BaseModel):
    name: str
    category: Optional[str] = ""
    brand: Optional[str] = ""
    region: Optional[str] = ""


async def _require_ventia(database):
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(database)
    if not s.get("ventia_enabled"):
        raise HTTPException(status_code=403, detail="VENT'IA est désactivé — demandez à l'administrateur de l'activer")


@ventia_router.post("/product-copy")
async def product_copy(body: ProductCopyBody, user: dict = Depends(get_current_user_checkout)):
    await _require_ventia(db)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nom du produit requis")
    import json as _json
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"ventia-{uuid.uuid4()}",
        system_message="Tu es VENT'IA, expert e-commerce B2B de la marketplace coopérative KDMARCHÉ × O'SCOP (Outre-mer). Réponds UNIQUEMENT en JSON valide.",
    ).with_model("openai", "gpt-5.4")
    prompt = (
        f"Produit : {body.name}. Catégorie : {body.category or 'non précisée'}. "
        f"Marque : {body.brand or 'non précisée'}. Origine : {body.region or 'non précisée'}.\n"
        "Génère un JSON avec exactement ces clés :\n"
        '- "description" : fiche produit vendeuse pour acheteurs professionnels (restaurateurs, commerces, collectivités), 60-110 mots, français, met en avant qualité/origine/usages pro, sans superlatifs creux\n'
        '- "price_advice" : conseil de positionnement prix B2B en 1 phrase (fourchette indicative ou stratégie marge/volume adaptée au produit)\n'
        "JSON brut uniquement, sans markdown."
    )
    try:
        raw = str(await chat.send_message(UserMessage(text=prompt))).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = _json.loads(raw)
        from ai_usage import log_ai_usage
        await log_ai_usage(db, "product_copy", body.name)
        return {"description": (data.get("description") or "").strip(),
                "price_advice": (data.get("price_advice") or "").strip()}
    except Exception as exc:
        logger.error("VENT'IA product-copy échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Génération IA indisponible, réessayez")


@ventia_router.post("/product-image")
async def product_image(body: ProductCopyBody, user: dict = Depends(get_current_user_checkout)):
    """Génère un visuel produit d'illustration par IA (quand le vendeur n'a pas de photo)."""
    await _require_ventia(db)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nom du produit requis")
    quota = int(os.environ.get("VENTIA_IMAGE_DAILY_QUOTA", "5"))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    used = await db.ventia_image_usage.count_documents({"user_id": user["id"], "date": today})
    if used >= quota:
        raise HTTPException(status_code=429,
                            detail=f"Quota quotidien atteint ({quota} visuels IA/jour) — réessayez demain")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "ventia")
    os.makedirs(upload_dir, exist_ok=True)
    try:
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"ventia-img-{uuid.uuid4()}",
            system_message="You are a professional product photographer.",
        )
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        msg = UserMessage(text=(
            f"Professional e-commerce product photo, clean studio lighting, neutral warm background, "
            f"appetizing and premium look, square format, no text or watermark. Product: {body.name}. "
            f"Category: {body.category or 'food'}. Origin: {body.region or 'French Caribbean'}."))
        _t, images = await chat.send_message_multimodal_response(msg)
        if not images:
            raise ValueError("no image")
        import base64
        fname = f"produit-{uuid.uuid4().hex[:10]}.png"
        with open(os.path.join(upload_dir, fname), "wb") as f:
            f.write(base64.b64decode(images[0]["data"]))
        await db.ventia_image_usage.insert_one({"user_id": user["id"], "date": today,
                                                "product_name": body.name.strip()[:120],
                                                "created_at": datetime.utcnow()})
        from ai_usage import log_ai_usage
        await log_ai_usage(db, "product_image", body.name)
        return {"image_url": f"/api/uploads/ventia/{fname}", "quota_remaining": quota - used - 1}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("VENT'IA product-image échoué : %s", exc)
        raise HTTPException(status_code=502, detail="Génération d'image indisponible, réessayez")


async def process_abandoned_carts(database) -> None:
    """Relance par email les paniers actifs inactifs depuis 24h (une seule relance par panier)."""
    from ai_agents_settings import get_agents_settings
    s = await get_agents_settings(database)
    if not s.get("ventia_enabled"):
        return
    cutoff = datetime.utcnow() - timedelta(hours=24)
    carts = await database.carts.find({
        "status": "ACTIVE",
        "items.0": {"$exists": True},
        "updated_at": {"$lt": cutoff},
        "ventia_reminder_sent": {"$ne": True},
    }).to_list(20)
    if not carts:
        return
    from brevo_service import send_email
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    sent = 0
    for cart in carts:
        members = await database.org_memberships.find({"org_id": cart["org_id"]}).to_list(3)
        user_ids = [m["user_id"] for m in members]
        users = await database.users.find({"id": {"$in": user_ids}}, {"email": 1, "first_name": 1}).to_list(3)
        items_html = "".join(
            f"<li>{i.get('product_name')} × {i.get('quantity')}</li>" for i in cart.get("items", [])[:3])
        html = ("<div style='font-family:Arial,sans-serif;max-width:560px'>"
                "<p>Bonjour,</p><p>Votre panier KDMARCHÉ vous attend toujours :</p>"
                f"<ul>{items_html}</ul>"
                "<p>Les stocks coopératifs partent vite — finalisez votre commande en 2 minutes.</p>"
                f"<p><a href='{base}/catalogue' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Reprendre mon panier</a></p>"
                "<p style='color:#999;font-size:10px;margin-top:18px'>VENT'IA — KDMARCHÉ × O'SCOP</p></div>")
        for u in users:
            try:
                await send_email(to_email=u["email"], to_name=u.get("first_name"),
                                 subject="🛒 Votre panier KDMARCHÉ vous attend", html_content=html,
                                 tags=["ventia-cart-reminder"])
                sent += 1
            except Exception as exc:
                logger.warning("VENT'IA relance panier échouée %s : %s", u.get("email"), exc)
        await database.carts.update_one({"id": cart["id"]}, {"$set": {"ventia_reminder_sent": True}})
    if sent:
        logger.info("VENT'IA : %s relance(s) panier abandonné envoyées", sent)
