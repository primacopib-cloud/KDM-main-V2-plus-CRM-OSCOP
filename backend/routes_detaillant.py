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
DEPOSIT_RATE_PCT = 2.5        # coût de dépôt : 2,5 % de la valeur du lot (en crédits, 10 cr = 1 €)
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
            "deposit_rate_pct": DEPOSIT_RATE_PCT,
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


CREDIT_PACKS = {"P100": 100, "P300": 300, "P500": 500}  # taux : 10 crédits = 1 €


class CreditsCheckoutBody(BaseModel):
    pack: str
    origin_url: str


@detaillant_router.post("/credits/checkout")
async def detaillant_credits_checkout(body: CreditsCheckoutBody, user: dict = Depends(get_current_user)):
    from routes_cpc import _stripe_key
    credits = CREDIT_PACKS.get(body.pack)
    if not credits:
        raise HTTPException(status_code=400, detail="Pack de crédits invalide")
    price_cents = credits * 10  # 10 crédits/€
    origin = body.origin_url.rstrip("/")
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="payment", payment_method_types=["card"],
        line_items=[{
            "price_data": {"currency": "eur", "unit_amount": price_cents,
                           "product_data": {"name": f"Recharge {credits} crédits COOP'ACT — Espace Détaillant"}},
            "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/espace-detaillant?credits_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/espace-detaillant?credits_cancelled=1",
        metadata={"kind": "DETAILLANT_CREDITS", "user_id": user["id"], "credits": str(credits)})
    await db.detaillant_credit_topups.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "credits": credits,
        "price_cents": price_cents, "stripe_session_id": session.id,
        "status": "PENDING", "created_at": _now().isoformat()})
    return {"checkout_url": session.url, "session_id": session.id}


@detaillant_router.post("/credits/activate")
async def detaillant_credits_activate(body: ActivateBody, user: dict = Depends(get_current_user)):
    from routes_cpc import _stripe_key
    topup = await db.detaillant_credit_topups.find_one(
        {"stripe_session_id": body.session_id, "user_id": user["id"]}, {"_id": 0})
    if not topup:
        raise HTTPException(status_code=404, detail="Recharge introuvable")
    if topup["status"] == "PAID":
        return {"ok": True, "already": True, "credits": topup["credits"]}
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.retrieve(body.session_id, api_key=_stripe_key())
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Paiement non confirmé")
    res = await db.detaillant_credit_topups.update_one(
        {"id": topup["id"], "status": "PENDING"}, {"$set": {"status": "PAID", "paid_at": _now().isoformat()}})
    if res.modified_count:
        await db.auction_accounts.update_one(
            {"user_id": user["id"]},
            {"$inc": {"credits": topup["credits"]},
             "$setOnInsert": {"user_id": user["id"], "valid_until": (_now() + timedelta(days=31)).isoformat()}},
            upsert=True)
    return {"ok": True, "credits": topup["credits"]}


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
    lot_price: float = 0            # prix de référence du lot (devise ci-dessous)
    currency: str = "EUR"           # code ISO 4217 (monde entier)
    discount_mode: str = "PERCENT"  # PERCENT | AMOUNT
    discount_value: float = 15
    scheduled_start: Optional[str] = None  # ISO — programmation avec countdown


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
    # Prix du lot et réduction obligatoire d'au moins -15 %
    if body.lot_price <= 0:
        raise HTTPException(status_code=400, detail="Indiquez le prix de référence du lot")
    if not (body.currency or "").strip() or len(body.currency.strip()) != 3:
        raise HTTPException(status_code=400, detail="Devise invalide (code ISO à 3 lettres)")
    if body.discount_mode not in ("PERCENT", "AMOUNT"):
        raise HTTPException(status_code=400, detail="Mode de réduction invalide")
    if body.discount_mode == "PERCENT":
        discount_amount = round(body.lot_price * body.discount_value / 100, 2)
        discount_pct = body.discount_value
    else:
        discount_amount = round(body.discount_value, 2)
        discount_pct = round(discount_amount / body.lot_price * 100, 2)
    if discount_pct < 15:
        raise HTTPException(status_code=400,
                            detail=f"La réduction doit être d'au moins 15 % du prix du lot (actuellement {discount_pct:.1f} %)")
    if discount_amount >= body.lot_price:
        raise HTTPException(status_code=400, detail="La réduction ne peut pas dépasser le prix du lot")
    final_price = round(body.lot_price - discount_amount, 2)
    scheduled_start = None
    if body.scheduled_start:
        try:
            dt = datetime.fromisoformat(body.scheduled_start.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= _now():
                raise ValueError
            scheduled_start = dt.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Date de programmation invalide (elle doit être future)")
    product = await db.lolodrive_products.find_one({"sku": body.product_sku}, {"_id": 0, "sku": 1, "name": 1, "category": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable dans le catalogue LOLODRIVE en vigueur")
    month_key = _now().strftime("%Y-%m")
    used = await db.detaillant_offers.count_documents(
        {"user_id": user["id"], "month_key": month_key, "status": {"$ne": "REJECTED"}})
    import math
    per_lot_credits = max(1, math.ceil(body.lot_price * DEPOSIT_RATE_PCT / 100 * 10))  # 10 cr = 1 €
    cost = body.qty_lots * per_lot_credits
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
        "lot_price": round(body.lot_price, 2), "currency": body.currency.strip().upper(),
        "discount_mode": body.discount_mode, "discount_value": body.discount_value,
        "discount_amount": discount_amount, "discount_pct": discount_pct,
        "final_price": final_price, "scheduled_start": scheduled_start,
        "status": "PENDING", "month_key": month_key,
        "created_at": _now().isoformat()}
    await db.detaillant_offers.insert_one({**offer})
    return offer


class ReviewBody(BaseModel):
    action: str  # APPROVE | REJECT
    note: Optional[str] = None


@detaillant_admin_router.get("/stats")
async def admin_detaillant_stats(admin: dict = Depends(require_admin)):
    """Statistiques détaillants pour le superadmin."""
    total = await db.users.count_documents({"role": "DETAILLANT"})
    now_iso = _now().isoformat()
    active_subs = await db.detaillant_subscriptions.count_documents(
        {"status": "ACTIVE", "valid_until": {"$gt": now_iso}})
    by_status = {}
    async for r in db.detaillant_offers.aggregate([
        {"$group": {"_id": "$status", "n": {"$sum": 1}, "credits": {"$sum": "$cost_credits"}}}]):
        by_status[r["_id"]] = {"count": r["n"], "credits": r["credits"]}
    lots_scheduled = await db.auctions.count_documents({"source": "DETAILLANT"})
    lots_won = await db.auctions.count_documents({"source": "DETAILLANT", "status": "WON"})
    top = []
    async for r in db.detaillant_offers.aggregate([
        {"$match": {"status": {"$ne": "REJECTED"}}},
        {"$group": {"_id": "$company_name", "offers": {"$sum": 1}, "lots": {"$sum": "$qty_lots"},
                    "credits": {"$sum": "$cost_credits"}}},
        {"$sort": {"offers": -1}}, {"$limit": 5}]):
        top.append({"company_name": r["_id"], "offers": r["offers"], "lots": r["lots"], "credits": r["credits"]})
    credits_spent = sum(v["credits"] for k, v in by_status.items() if k != "REJECTED")
    revenue_subs_eur = active_subs * SUB_PRICE_CENTS / 100
    return {"detaillants": total, "active_subscriptions": active_subs,
            "monthly_sub_revenue_eur": revenue_subs_eur,
            "offers_by_status": by_status, "credits_spent": credits_spent,
            "lots_in_salle": lots_scheduled, "lots_won": lots_won, "top_retailers": top}


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
    created_refs = []
    if body.action == "REJECT":
        await db.auction_accounts.update_one(
            {"user_id": offer["user_id"]}, {"$inc": {"credits": offer.get("cost_credits", 0)}})
        updates["credits_refunded"] = offer.get("cost_credits", 0)
    else:
        # Programmation automatique en salle COOP'ACT : 1 opération SCHEDULED par lot
        import auction_helpers as ah
        product = await db.lolodrive_products.find_one({"sku": offer["product_sku"]}, {"_id": 0})
        if offer.get("final_price"):
            value_eur = round(float(offer["final_price"]), 2)
        else:
            unit_cents = (product or {}).get("price_public_cents") or (product or {}).get("price_pass_cents") or 1000
            value_eur = round(unit_cents * 3 / 100, 2)  # lot ×3
        prof = await db.detaillant_profiles.find_one({"user_id": offer["user_id"]}, {"_id": 0})
        retailer = {"company_name": offer.get("company_name"), "country_code": offer.get("country_code"),
                    "locality": offer.get("locality"),
                    "pickup_slots": (prof or {}).get("pickup_slots", [])}
        starts = _now() + timedelta(days=1)
        if offer.get("scheduled_start"):
            try:
                sched = datetime.fromisoformat(offer["scheduled_start"])
                if sched > _now():
                    starts = sched
            except ValueError:
                pass
        ends = starts + timedelta(days=7)
        desc = offer["description"]
        if offer.get("lot_price"):
            desc += (f" — Prix boutique : {offer['lot_price']} {offer.get('currency', 'EUR')}, "
                     f"réduction -{offer.get('discount_pct', 0):.0f} % → {offer['final_price']} {offer.get('currency', 'EUR')}")
        if offer.get("composed_detail"):
            desc += f" — Composition : {offer['composed_detail']}"
        for i in range(int(offer.get("qty_lots") or 1)):
            ref = f"AUC-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            await db.auctions.insert_one({
                "id": str(uuid.uuid4()), "reference": ref,
                "title": f"Lot ×3 — {offer['product_name']}" + (f" ({i + 1}/{offer['qty_lots']})" if offer["qty_lots"] > 1 else ""),
                "image_url": (product or {}).get("image_url"),
                "description": desc,
                "source": "DETAILLANT", "source_visible": True,
                "retailer": retailer,
                "product_id": offer["product_sku"], "category_id": None, "type_id": None,
                "value_eur": value_eur, "floor_eur": 0, "bid_cost_credits": 10, "price_drop_eur": 1.0,
                "starts_at": starts.isoformat(), "ends_at": ends.isoformat(),
                "recurrence": "NONE", "featured": False,
                "status": "SCHEDULED", "current_price_eur": value_eur, "bids_count": 0,
                "detaillant_offer_id": offer_id,
                "created_by": admin.get("email"), "created_at": _now().isoformat()})
            created_refs.append(ref)
        updates["auction_refs"] = created_refs
    await db.detaillant_offers.update_one({"id": offer_id}, {"$set": updates})
    msg = (f"Votre offre a été validée : {len(created_refs)} opération(s) programmée(s) en salle COOP'ACT ({', '.join(created_refs)})."
           if body.action == "APPROVE"
           else f"Votre offre a été refusée. {offer.get('cost_credits', 0)} crédits vous ont été remboursés.")
    if body.action == "REJECT" and body.note:
        msg += f" Motif : {body.note}"
    # Email Brevo au détaillant
    try:
        client = await db.users.find_one({"id": offer["user_id"]}, {"_id": 0, "email": 1, "company_name": 1})
        if client and client.get("email"):
            from brevo_service import send_email, _wrap_html
            subj = f"Offre {offer['product_name']} — {'validée ✓' if body.action == 'APPROVE' else 'refusée'}"
            html = _wrap_html("Décision sur votre offre de lots",
                              f"<p>Bonjour {client.get('company_name') or ''},</p><p>{msg}</p>")
            await send_email(client["email"], client.get("company_name"), subj, html,
                             tags=["detaillant-offer-decision"])
    except Exception as exc:
        logger.warning("Email décision détaillant: %s", exc)
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
