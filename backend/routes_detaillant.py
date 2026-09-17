"""Espace Détaillant : abonnement 390 €/mois, accès salle COOP'ACT, dépôt d'offres de lots."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
detaillant_router = APIRouter(prefix="/api/detaillant", tags=["detaillant"])
detaillant_admin_router = APIRouter(prefix="/api/admin/detaillant", tags=["detaillant-admin"])

db = None

SUB_PRICE_CENTS = 39000       # 390 €/mois TTC
INCLUDED_OFFERS_PER_MONTH = 3
CREDITS_PER_LOT = 23          # coût de dépôt par lot
EXTRA_OFFER_CREDITS_PER_LOT = 100  # au-delà des 3 offres incluses


def set_detaillant_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc)


class RegisterBody(BaseModel):
    email: str
    password: str
    company_name: str


class ProfileBody(BaseModel):
    company_name: str
    locality: str = ""
    country_code: str = "GP"
    phone_prefix: str = "+590"
    phone: str = ""
    contact_email: str = ""
    address: str = ""
    pickup_slots: List[str] = []


@detaillant_router.post("/register")
async def detaillant_register(body: RegisterBody):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe : 8 caractères minimum")
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    from auth import get_password_hash
    uid = f"user-detaillant-{uuid.uuid4().hex[:8]}"
    now = _now()
    await db.users.insert_one({
        "id": uid, "email": email, "password_hash": get_password_hash(body.password),
        "role": "DETAILLANT", "is_admin": False, "contact_name": body.company_name,
        "company_name": body.company_name, "first_name": None, "country": "GP",
        "siret": "", "phone": "", "subscription": "detaillant", "credits": 0,
        "created_at": now})
    await db.detaillant_profiles.insert_one({
        "user_id": uid, "company_name": body.company_name, "locality": "", "country_code": "GP",
        "phone_prefix": "+590", "phone": "", "contact_email": email, "address": "",
        "pickup_slots": [], "created_at": now.isoformat()})
    return {"ok": True, "email": email}


@detaillant_router.get("/profile")
async def detaillant_profile(user: dict = Depends(get_current_user)):
    prof = await db.detaillant_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not prof:
        raise HTTPException(status_code=404, detail="Profil détaillant introuvable")
    sub = await db.detaillant_subscriptions.find_one(
        {"user_id": user["id"], "status": "ACTIVE"}, {"_id": 0}, sort=[("created_at", -1)])
    active = bool(sub and datetime.fromisoformat(sub["valid_until"]) > _now())
    account = await db.auction_accounts.find_one({"user_id": user["id"]}, {"_id": 0, "credits": 1})
    month_key = _now().strftime("%Y-%m")
    used = await db.detaillant_offers.count_documents(
        {"user_id": user["id"], "month_key": month_key, "status": {"$ne": "REJECTED"}})
    return {"profile": prof, "subscription_active": active,
            "subscription": sub,
            "credits": (account or {}).get("credits", 0),
            "offers_used_this_month": used,
            "included_offers": INCLUDED_OFFERS_PER_MONTH,
            "credits_per_lot": CREDITS_PER_LOT,
            "extra_offer_credits_per_lot": EXTRA_OFFER_CREDITS_PER_LOT,
            "sub_price_cents": SUB_PRICE_CENTS}


@detaillant_router.put("/profile")
async def detaillant_update_profile(body: ProfileBody, user: dict = Depends(get_current_user)):
    res = await db.detaillant_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": {**body.dict(), "updated_at": _now().isoformat()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Profil détaillant introuvable")
    return {"ok": True}


class CheckoutBody(BaseModel):
    origin_url: str


@detaillant_router.post("/subscription/checkout")
async def detaillant_checkout(body: CheckoutBody, user: dict = Depends(get_current_user)):
    from routes_cpc import _stripe_key
    existing = await db.detaillant_subscriptions.find_one(
        {"user_id": user["id"], "status": "ACTIVE"}, {"_id": 0, "valid_until": 1})
    if existing and datetime.fromisoformat(existing["valid_until"]) > _now():
        raise HTTPException(status_code=409, detail="Votre abonnement Détaillant est déjà actif")
    origin = body.origin_url.rstrip("/")
    meta = {"kind": "DETAILLANT_SUBSCRIPTION", "user_id": user["id"]}
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="subscription", payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur", "unit_amount": SUB_PRICE_CENTS,
                "recurring": {"interval": "month"},
                "product_data": {"name": "Abonnement Détaillant — accès salle COOP'ACT, 3 offres de lots incluses/mois"},
            }, "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/espace-detaillant?sub_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/espace-detaillant?sub_cancelled=1",
        metadata=meta, subscription_data={"metadata": meta})
    await db.detaillant_subscriptions.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "email": user.get("email"),
        "price_cents": SUB_PRICE_CENTS, "stripe_session_id": session.id,
        "status": "PENDING", "created_at": _now().isoformat()})
    return {"checkout_url": session.url, "session_id": session.id}


class ActivateBody(BaseModel):
    session_id: str


@detaillant_router.post("/subscription/activate")
async def detaillant_activate(body: ActivateBody, user: dict = Depends(get_current_user)):
    from routes_cpc import _stripe_key
    sub = await db.detaillant_subscriptions.find_one(
        {"stripe_session_id": body.session_id, "user_id": user["id"]}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Session d'abonnement introuvable")
    if sub["status"] == "ACTIVE":
        return {"ok": True, "already": True}
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.retrieve(body.session_id, api_key=_stripe_key())
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Paiement non confirmé")
    valid_until = (_now() + timedelta(days=31)).isoformat()
    await db.detaillant_subscriptions.update_one(
        {"id": sub["id"]},
        {"$set": {"status": "ACTIVE", "valid_until": valid_until,
                  "stripe_subscription_id": session.get("subscription"),
                  "activated_at": _now().isoformat()}})
    return {"ok": True, "valid_until": valid_until}


async def _require_active_sub(user_id: str):
    sub = await db.detaillant_subscriptions.find_one(
        {"user_id": user_id, "status": "ACTIVE"}, {"_id": 0, "valid_until": 1}, sort=[("created_at", -1)])
    if not (sub and datetime.fromisoformat(sub["valid_until"]) > _now()):
        raise HTTPException(status_code=403, detail="Abonnement Détaillant (390 €/mois) requis pour déposer des offres")


class OfferBody(BaseModel):
    product_sku: str
    lot_type: str = "SAME"      # SAME = lot x3 même produit, COMPOSED = lot composé
    qty_lots: int = 1
    description: str
    category: Optional[str] = None
    composed_detail: Optional[str] = None


@detaillant_router.get("/catalog")
async def detaillant_catalog(user: dict = Depends(get_current_user)):
    products = await db.lolodrive_products.find(
        {}, {"_id": 0, "sku": 1, "name": 1, "category": 1, "image_url": 1}).sort("name", 1).to_list(300)
    return {"products": products}


@detaillant_router.get("/offers")
async def detaillant_my_offers(user: dict = Depends(get_current_user)):
    offers = await db.detaillant_offers.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"offers": offers}


@detaillant_router.post("/offers")
async def detaillant_create_offer(body: OfferBody, user: dict = Depends(get_current_user)):
    await _require_active_sub(user["id"])
    if body.qty_lots < 1 or body.qty_lots > 50:
        raise HTTPException(status_code=400, detail="Quantité de lots : entre 1 et 50")
    if body.lot_type not in ("SAME", "COMPOSED"):
        raise HTTPException(status_code=400, detail="Type de lot invalide")
    if len(body.description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Descriptif trop court (10 caractères minimum)")
    product = await db.lolodrive_products.find_one({"sku": body.product_sku}, {"_id": 0, "sku": 1, "name": 1, "category": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable dans le catalogue LOLODRIVE en vigueur")
    month_key = _now().strftime("%Y-%m")
    used = await db.detaillant_offers.count_documents(
        {"user_id": user["id"], "month_key": month_key, "status": {"$ne": "REJECTED"}})
    cost = body.qty_lots * CREDITS_PER_LOT
    extra = used >= INCLUDED_OFFERS_PER_MONTH
    if extra:
        cost += body.qty_lots * EXTRA_OFFER_CREDITS_PER_LOT
    res = await db.auction_accounts.update_one(
        {"user_id": user["id"], "credits": {"$gte": cost}}, {"$inc": {"credits": -cost}})
    if not res.modified_count:
        raise HTTPException(status_code=409,
                            detail=f"Crédits insuffisants : cette offre coûte {cost} crédits COOP'ACT")
    prof = await db.detaillant_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    offer = {
        "id": str(uuid.uuid4()), "user_id": user["id"],
        "company_name": (prof or {}).get("company_name", ""),
        "country_code": (prof or {}).get("country_code", ""),
        "locality": (prof or {}).get("locality", ""),
        "product_sku": product["sku"], "product_name": product["name"],
        "category": body.category or product.get("category"),
        "lot_type": body.lot_type, "lot_size": 3, "qty_lots": body.qty_lots,
        "description": body.description.strip(),
        "composed_detail": (body.composed_detail or "").strip() or None,
        "cost_credits": cost, "extra_offer": extra,
        "status": "PENDING", "month_key": month_key,
        "created_at": _now().isoformat()}
    await db.detaillant_offers.insert_one({**offer})
    return offer


class ReviewBody(BaseModel):
    action: str  # APPROVE | REJECT
    note: Optional[str] = None


@detaillant_admin_router.get("/offers")
async def admin_list_offers(status: str = "", admin: dict = Depends(require_admin)):
    q = {"status": status} if status else {}
    offers = await db.detaillant_offers.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"offers": offers}


@detaillant_admin_router.post("/offers/{offer_id}/review")
async def admin_review_offer(offer_id: str, body: ReviewBody, admin: dict = Depends(require_admin)):
    if body.action not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=400, detail="Action invalide")
    offer = await db.detaillant_offers.find_one({"id": offer_id}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offer["status"] != "PENDING":
        raise HTTPException(status_code=409, detail="Offre déjà traitée")
    new_status = "APPROVED" if body.action == "APPROVE" else "REJECTED"
    updates = {"status": new_status, "reviewed_at": _now().isoformat(),
               "reviewed_by": admin.get("id"), "review_note": (body.note or "").strip() or None}
    if body.action == "REJECT":
        await db.auction_accounts.update_one(
            {"user_id": offer["user_id"]}, {"$inc": {"credits": offer.get("cost_credits", 0)}})
        updates["credits_refunded"] = offer.get("cost_credits", 0)
    await db.detaillant_offers.update_one({"id": offer_id}, {"$set": updates})
    msg = ("Votre offre a été validée : elle sera programmée en salle COOP'ACT prochainement."
           if body.action == "APPROVE"
           else f"Votre offre a été refusée. {offer.get('cost_credits', 0)} crédits vous ont été remboursés.")
    if body.action == "REJECT" and body.note:
        msg += f" Motif : {body.note}"
    try:
        from core_deps import create_notification
        await create_notification(
            notification_type="detaillant_offer_reviewed",
            title=f"Offre {offer['product_name']} — {'validée' if body.action == 'APPROVE' else 'refusée'}",
            message=msg,
            target_roles=[],
            target_user_id=offer["user_id"],
            data={"offer_id": offer_id})
    except Exception as exc:
        logger.warning("Notif offre détaillant: %s", exc)
    out = await db.detaillant_offers.find_one({"id": offer_id}, {"_id": 0})
    return out
