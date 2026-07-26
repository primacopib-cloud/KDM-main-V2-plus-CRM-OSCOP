"""Promotions de crédits (bonus & réductions) gérées par le super admin — /api/admin/credit-promotions."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

promotions_router = APIRouter(prefix="/api/admin/credit-promotions", tags=["Credit Promotions"])
public_promotions_router = APIRouter(prefix="/api/public", tags=["Credit Promotions"])

db = None


def set_promotions_database(database) -> None:
    global db
    db = database


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class PromotionPayload(BaseModel):
    name: str
    promo_type: str  # bonus_purchase | discount_action
    value_percent: float
    scope_profile: str = "all"      # all | vendor | buyer | pass
    scope_territory: str = "ALL"    # ALL | GUADELOUPE | MARTINIQUE | ...
    scope_category: str = "all"     # all | slug catégorie produit
    scope_action: str = "all"       # all | action du barème
    scope_product_type: str = "all"  # all | type de produit (texte)
    scope_brand: str = ""            # marque ciblée (texte, vide = toutes)
    scope_relay: str = "all"         # all | nom du relais LOLODRIVE
    min_quantity: int = 0            # quantité minimale de produits
    audience: str = "all"            # all | emails
    audience_emails: list[str] = []  # destinataires de la campagne
    countdown_enabled: bool = False
    countdown_pages: list[str] = []  # landing | catalog | pass | kdmarche | member_spaces
    countdown_labels: list[str] = []  # mentions clignotantes (EXCLUSIVITÉ, SPÉCIAL NOËL...)
    countdown_alert_days: int = 10   # alerte rouge à J-x du terme
    starts_at: str | None = None    # ISO — début de l'offre flash
    ends_at: str | None = None      # ISO — fin de l'offre flash
    active: bool = True


def _matches(promo: dict, profile: str, territory: str | None, category: str | None, action: str | None) -> bool:
    if promo.get("archived") or not promo.get("active"):
        return False
    now = datetime.now(timezone.utc).isoformat()
    if promo.get("starts_at") and now < promo["starts_at"]:
        return False
    if promo.get("ends_at") and now > promo["ends_at"]:
        return False
    if promo.get("scope_profile", "all") not in ("all", profile):
        return False
    if promo.get("scope_territory", "ALL") != "ALL" and territory and promo["scope_territory"] != territory:
        return False
    if promo.get("scope_territory", "ALL") != "ALL" and not territory:
        return False
    if promo.get("scope_category", "all") != "all" and promo["scope_category"] != (category or ""):
        return False
    if promo.get("scope_action", "all") != "all" and promo["scope_action"] != (action or ""):
        return False
    return True


def matches_product(promo: dict, product_type: str | None = None, brand: str | None = None,
                    relay: str | None = None, quantity: int | None = None) -> bool:
    """Critères produit additionnels (type, marque, relais, quantité minimale)."""
    if promo.get("scope_product_type", "all") != "all" and promo["scope_product_type"].lower() != (product_type or "").lower():
        return False
    if promo.get("scope_brand") and promo["scope_brand"].lower() != (brand or "").lower():
        return False
    if promo.get("scope_relay", "all") != "all" and promo["scope_relay"] != (relay or ""):
        return False
    if promo.get("min_quantity", 0) and (quantity or 0) < promo["min_quantity"]:
        return False
    return True


async def get_discount_percent(action: str, profile: str = "vendor",
                               territory: str | None = None, category: str | None = None) -> float:
    """Meilleure réduction active applicable à une consommation."""
    best = 0.0
    async for promo in db.credit_promotions.find({"promo_type": "discount_action", "active": True, "archived": {"$ne": True}}):
        if _matches(promo, profile, territory, category, action):
            best = max(best, float(promo.get("value_percent") or 0))
    return min(best, 100.0)


async def get_purchase_bonus_percent(profile: str = "vendor", territory: str | None = None) -> float:
    """Meilleur bonus actif applicable à un achat de pack de crédits."""
    best = 0.0
    async for promo in db.credit_promotions.find({"promo_type": "bonus_purchase", "active": True, "archived": {"$ne": True}}):
        if _matches(promo, profile, territory, None, None):
            best = max(best, float(promo.get("value_percent") or 0))
    return best


def apply_discount(cost: int, percent: float) -> int:
    return max(0, math.ceil(cost * (1 - percent / 100)))


@public_promotions_router.get("/catalog-promos")
async def public_catalog_promos():
    """Promos actives (hors campagnes email) exposées pour les badges du catalogue."""
    now = datetime.now(timezone.utc).isoformat()
    docs = await db.credit_promotions.find(
        {"active": True, "archived": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1, "promo_type": 1, "value_percent": 1,
         "scope_category": 1, "scope_product_type": 1, "scope_brand": 1,
         "starts_at": 1, "ends_at": 1, "audience": 1}).to_list(50)
    docs = [p for p in docs
            if (not p.get("starts_at") or p["starts_at"] <= now)
            and (not p.get("ends_at") or p["ends_at"] >= now)
            and p.get("audience", "all") != "emails"]
    for p in docs:
        p.pop("audience", None)
    return {"promotions": docs}


@promotions_router.get("")
async def list_promotions(include_archived: bool = False, _: dict = Depends(_admin)):
    query = {} if include_archived else {"archived": {"$ne": True}}
    docs = await db.credit_promotions.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"promotions": docs, "total": len(docs)}


@promotions_router.post("")
async def create_promotion(payload: PromotionPayload, admin: dict = Depends(_admin)):
    if payload.promo_type not in ("bonus_purchase", "discount_action"):
        raise HTTPException(status_code=400, detail="Type invalide")
    if not 0 < payload.value_percent <= 100:
        raise HTTPException(status_code=400, detail="Pourcentage invalide (1-100)")
    doc = {
        "id": str(uuid.uuid4()), **payload.model_dump(), "archived": False,
        "created_by": admin["email"], "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.credit_promotions.insert_one({**doc})
    return {"status": "SUCCESS", "promotion": doc}


@promotions_router.put("/{promo_id}")
async def update_promotion(promo_id: str, payload: PromotionPayload, admin: dict = Depends(_admin)):
    result = await db.credit_promotions.update_one(
        {"id": promo_id},
        {"$set": {**payload.model_dump(), "updated_by": admin["email"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}


@promotions_router.post("/{promo_id}/archive")
async def archive_promotion(promo_id: str, _: dict = Depends(_admin)):
    result = await db.credit_promotions.update_one(
        {"id": promo_id}, {"$set": {"archived": True, "active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}


@promotions_router.delete("/{promo_id}")
async def delete_promotion(promo_id: str, _: dict = Depends(_admin)):
    result = await db.credit_promotions.delete_one({"id": promo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    return {"status": "SUCCESS"}

@promotions_router.post("/{promo_id}/send-campaign")
async def send_promotion_campaign(promo_id: str, admin: dict = Depends(_admin)):
    """Envoie la promotion par email aux destinataires édités (campagne Brevo)."""
    import os
    promo = await db.credit_promotions.find_one({"id": promo_id}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    emails = [e.strip().lower() for e in (promo.get("audience_emails") or []) if e.strip()]
    if not emails:
        raise HTTPException(status_code=400, detail="Aucun email édité sur cette promotion (audience « emails »)")
    from brevo_service import send_email
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    kind = "bonus de crédits à l'achat" if promo["promo_type"] == "bonus_purchase" else "réduction"
    window = ""
    if promo.get("ends_at"):
        window = f"<p>⏱ Offre valable jusqu'au <b>{promo['ends_at'][:10]}</b> — ne tardez pas !</p>"
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:560px'>"
        f"<h2 style='color:#451F6B'>⚡ {promo['name']}</h2>"
        f"<p>Profitez de <b>{promo['value_percent']:g} % de {kind}</b> sur la coopérative KDMARCHÉ × O'SCOP.</p>"
        f"{window}"
        f"<p><a href='{base}' style='background:#5B2E8C;color:#fff;padding:11px 20px;border-radius:8px;"
        "text-decoration:none'>J'en profite</a></p>"
        "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — offre réservée, ne pas transférer</p></div>")
    sent = 0
    for email in emails:
        try:
            await send_email(to_email=email, to_name=None,
                             subject=f"⚡ {promo['name']} — {promo['value_percent']:g} % pour vous",
                             html_content=html, tags=["promo-campaign", f"promo-{promo_id}"])
            sent += 1
        except Exception:
            pass
    await db.credit_promotions.update_one({"id": promo_id}, {"$set": {
        "campaign_sent_at": datetime.now(timezone.utc).isoformat(), "campaign_sent_count": sent}})
    return {"status": "SUCCESS", "sent": sent, "total": len(emails)}

@promotions_router.get("/{promo_id}/campaign-stats")
async def campaign_stats(promo_id: str, admin: dict = Depends(_admin)):
    """Statistiques Brevo (envois, ouvertures, clics) de la campagne de cette promotion."""
    import os
    import httpx
    promo = await db.credit_promotions.find_one({"id": promo_id}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    if not promo.get("campaign_sent_at"):
        raise HTTPException(status_code=400, detail="Aucune campagne envoyée pour cette promotion")
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Clé Brevo absente")
    start = promo["campaign_sent_at"][:10]
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
                params={"tag": f"promo-{promo_id}", "startDate": start, "endDate": end},
                headers={"api-key": api_key, "accept": "application/json"})
        data = r.json() if r.status_code == 200 else {}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Brevo injoignable : {exc}")
    return {"sent": promo.get("campaign_sent_count", 0),
            "delivered": data.get("delivered", 0),
            "opens": data.get("uniqueOpens", data.get("opens", 0)),
            "clicks": data.get("uniqueClicks", data.get("clicks", 0)),
            "campaign_sent_at": promo["campaign_sent_at"]}
