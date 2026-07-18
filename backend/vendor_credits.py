"""Système de crédits vendeur : barème administrable + consommation + attribution — /api/vendor/credits, /api/admin/credit-pricing."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

credits_router = APIRouter(prefix="/api", tags=["Vendor Credits"])

db = None

DEFAULT_PRICING = [
    ("product_submission", 5, "Création de fiche produit"),
    ("photo_upload", 1, "Téléversement d'une photo"),
    ("ai_image_generation", 10, "Génération d'image IA"),
    ("ai_image_enhance", 8, "Amélioration d'image IA"),
    ("ai_video_generation", 50, "Génération de spot vidéo IA"),
]


def set_vendor_credits_database(database) -> None:
    global db
    db = database


async def seed_credit_pricing() -> None:
    if await db.credit_pricing.count_documents({}) == 0:
        await db.credit_pricing.insert_many([
            {"id": str(uuid.uuid4()), "action": a, "cost": c, "label": lbl}
            for a, c, lbl in DEFAULT_PRICING
        ])


async def get_action_cost(action: str) -> int:
    doc = await db.credit_pricing.find_one({"action": action})
    if doc:
        return int(doc["cost"])
    return dict((a, c) for a, c, _ in DEFAULT_PRICING).get(action, 0)


async def consume_credits(vendor_id: str, action: str, detail: str = "",
                          category: str | None = None, territory: str | None = None) -> int:
    """Décrémente les crédits du vendeur (réductions promo appliquées) ; 402 si solde insuffisant."""
    from credit_promotions import get_discount_percent, apply_discount

    cost = await get_action_cost(action)
    if cost <= 0:
        return 0
    discount = await get_discount_percent(action, "vendor", territory, category)
    cost = apply_discount(cost, discount)
    if cost <= 0:
        return 0
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "credits": 1})
    balance = int((vendor or {}).get("credits") or 0)
    if balance < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Crédits insuffisants ({balance} restants, {cost} requis). Contactez l'administrateur.",
        )
    await db.vendors.update_one({"id": vendor_id}, {"$inc": {"credits": -cost}})
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "owner_type": "vendor",
        "action": action, "cost": cost, "detail": detail,
        "category": category, "territory": territory,
        "discount_percent": discount or 0,
        "balance_after": balance - cost,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    if balance >= LOW_CREDIT_THRESHOLD > balance - cost:
        import asyncio
        asyncio.get_event_loop().create_task(_send_low_credit_alert(vendor_id, balance - cost))
    return cost


LOW_CREDIT_THRESHOLD = 10


async def _send_low_credit_alert(vendor_id: str, balance: int) -> None:
    """Email au vendeur quand son solde passe sous le seuil (envoyé une fois par franchissement)."""
    try:
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        if not is_brevo_configured():
            return
        vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "email": 1, "contact_name": 1}) or {}
        if not vendor.get("email"):
            return
        import os
        link = os.environ.get("FRONTEND_URL", "") + "/espace-vendeur"
        body = (
            f"<p>Bonjour {vendor.get('contact_name', '')},</p>"
            f"<p>Votre solde de crédits KDMARCHÉ est descendu à <strong>{balance} crédits</strong>.</p>"
            "<p>Pour continuer à créer des fiches produits, téléverser des photos et utiliser le Studio IA, "
            f"rechargez votre solde depuis votre <a href='{link}'>Espace Vendeur</a> (badge crédits en haut à droite).</p>"
        )
        await send_email(
            to_email=vendor["email"], to_name=vendor.get("contact_name"),
            subject=f"⚠️ Solde de crédits faible ({balance} restants) — KDMARCHÉ",
            html_content=_wrap_html("Solde de crédits faible", body),
            tags=["low-credits"],
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Low credit alert failed")


async def refund_credits(vendor_id: str, action: str, detail: str = "") -> None:
    """Rembourse le coût d'une action après un échec technique."""
    cost = await get_action_cost(action)
    if cost <= 0:
        return
    await db.vendors.update_one({"id": vendor_id}, {"$inc": {"credits": cost}})
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "credits": 1})
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "action": f"refund_{action}",
        "cost": -cost, "detail": detail or "Remboursement suite à échec technique",
        "balance_after": int((vendor or {}).get("credits") or 0),
        "at": datetime.now(timezone.utc).isoformat(),
    })


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


@credits_router.get("/vendor/credits/{vendor_id}")
async def get_vendor_credits(vendor_id: str):
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "credits": 1, "company_name": 1})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")
    pricing = await db.credit_pricing.find({}, {"_id": 0}).to_list(20)
    tx = await db.credit_transactions.find({"vendor_id": vendor_id}, {"_id": 0}) \
        .sort("at", -1).limit(50).to_list(50)
    return {"credits": int(vendor.get("credits") or 0), "pricing": pricing, "transactions": tx}


class PricingUpdate(BaseModel):
    action: str
    cost: int


@credits_router.get("/admin/credit-pricing")
async def list_credit_pricing(_: dict = Depends(_admin)):
    return {"pricing": await db.credit_pricing.find({}, {"_id": 0}).to_list(20)}


@credits_router.put("/admin/credit-pricing")
async def update_credit_pricing(payload: PricingUpdate, admin: dict = Depends(_admin)):
    if payload.cost < 0:
        raise HTTPException(status_code=400, detail="Coût invalide")
    result = await db.credit_pricing.update_one(
        {"action": payload.action},
        {"$set": {"cost": payload.cost, "updated_by": admin["email"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Action inconnue")
    return {"status": "SUCCESS", "action": payload.action, "cost": payload.cost}


class GrantCreditsPayload(BaseModel):
    amount: int


@credits_router.get("/admin/vendors-credits")
async def list_vendors_credits(_: dict = Depends(_admin)):
    vendors = await db.vendors.find(
        {}, {"_id": 0, "id": 1, "company_name": 1, "contact_name": 1, "email": 1, "credits": 1, "status": 1}
    ).to_list(200)
    return {"vendors": vendors, "total": len(vendors)}


@credits_router.post("/admin/vendors/{vendor_id}/credits")
async def grant_vendor_credits(vendor_id: str, payload: GrantCreditsPayload, admin: dict = Depends(_admin)):
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "credits": 1})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")
    await db.vendors.update_one({"id": vendor_id}, {"$inc": {"credits": payload.amount}})
    new_balance = int((vendor.get("credits") or 0)) + payload.amount
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "action": "admin_grant",
        "cost": -payload.amount, "detail": f"Attribution par {admin['email']}",
        "balance_after": new_balance, "at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "SUCCESS", "credits": new_balance}
