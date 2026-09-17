"""Espace Détaillant : abonnement 390 €/mois, accès salle COOP'ACT, dépôt d'offres de lots."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import stripe
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
detaillant_router = APIRouter(prefix="/api/detaillant", tags=["detaillant"])
detaillant_public_router = APIRouter(prefix="/api/detaillant", tags=["detaillant-public"])
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
    updates = {**body.dict(), "updated_at": _now().isoformat()}
    # Géocodage best-effort (Nominatim) pour situer le POP'S sur la carte monde
    if body.locality:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=6) as cli:
                r = await cli.get("https://nominatim.openstreetmap.org/search",
                                  params={"q": f"{body.locality}, {body.country_code}", "format": "json", "limit": 1},
                                  headers={"User-Agent": "kdmarche-oscop/1.0"})
                hits = r.json()
                if hits:
                    updates["lat"] = float(hits[0]["lat"])
                    updates["lng"] = float(hits[0]["lon"])
        except Exception as exc:
            logger.warning("Géocodage POP'S %s : %s", body.locality, exc)
    res = await db.detaillant_profiles.update_one(
        {"user_id": user["id"]}, {"$set": updates})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Profil détaillant introuvable")
    return {"ok": True, "lat": updates.get("lat"), "lng": updates.get("lng")}


@detaillant_public_router.get("/shops/public")
async def detaillant_shops_public():
    """POP'S publics : carte monde + palmarès des boutiques les mieux notées."""
    shops = []
    async for p in db.detaillant_profiles.find(
            {"company_name": {"$nin": [None, ""]}},
            {"_id": 0, "user_id": 1, "company_name": 1, "locality": 1, "country_code": 1,
             "rating_avg": 1, "rating_count": 1, "lat": 1, "lng": 1, "gold": 1}):
        reviews = await db.detaillant_shop_reviews.find(
            {"detaillant_user_id": p["user_id"]},
            {"_id": 0, "rating": 1, "comment": 1, "reply": 1, "created_at": 1}
        ).sort("created_at", -1).limit(3).to_list(3)
        last = await db.detaillant_offers.find_one(
            {"user_id": p["user_id"], "status": {"$ne": "REJECTED"}},
            {"_id": 0, "category": 1}, sort=[("created_at", -1)])
        cats = await db.detaillant_offers.distinct(
            "category", {"user_id": p["user_id"], "status": {"$ne": "REJECTED"}, "category": {"$nin": [None, ""]}})
        shops.append({**p, "reviews": reviews, "category": (last or {}).get("category"), "categories": cats})
    shops.sort(key=lambda s: (-(s.get("rating_avg") or 0), -(s.get("rating_count") or 0)))
    return {"shops": shops}


async def recalc_gold_pops():
    """Badge Or : le POP'S n°1 du palmarès voit ses lots marqués retailer.gold en salle."""
    prev = await db.detaillant_profiles.find_one({"gold": True}, {"_id": 0, "user_id": 1})
    prev_uid = prev["user_id"] if prev else None
    top = await db.detaillant_profiles.find(
        {"rating_count": {"$gt": 0}}, {"_id": 0, "user_id": 1}
    ).sort([("rating_avg", -1), ("rating_count", -1)]).limit(1).to_list(1)
    gold_uid = top[0]["user_id"] if top else None
    await db.auctions.update_many(
        {"source": "DETAILLANT", "retailer.gold": True, "retailer.detaillant_user_id": {"$ne": gold_uid}},
        {"$set": {"retailer.gold": False}})
    if gold_uid:
        await db.auctions.update_many(
            {"source": "DETAILLANT", "retailer.detaillant_user_id": gold_uid},
            {"$set": {"retailer.gold": True}})
        await db.detaillant_profiles.update_many({"gold": True, "user_id": {"$ne": gold_uid}}, {"$set": {"gold": False}})
        await db.detaillant_profiles.update_one({"user_id": gold_uid}, {"$set": {"gold": True}})
    if gold_uid != prev_uid:
        await _notify_gold_change(prev_uid, gold_uid)
    return gold_uid


async def _notify_gold_change(prev_uid, gold_uid):
    """Email + cloche : félicite le POP'S qui gagne le badge or, prévient celui qui le perd."""
    from core_deps import create_notification
    from brevo_service import send_email, _wrap_html

    async def contact(uid):
        prof = await db.detaillant_profiles.find_one({"user_id": uid}, {"_id": 0, "company_name": 1})
        u = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
        return (prof or {}).get("company_name") or "", (u or {}).get("email")

    try:
        if gold_uid:
            name, email = await contact(gold_uid)
            msg = (f"Félicitations {name} ! Vous êtes le POP'S n°1 du palmarès : le badge "
                   "« 🏆 POP'S d'Or » est désormais affiché sur tous vos lots en salle COOP'ACT.")
            await create_notification(
                notification_type="pops_gold_won", title="🏆 Vous êtes le POP'S d'Or !",
                message=msg, target_roles=[], target_user_id=gold_uid,
                data={"action_url": "/espace-detaillant"})
            if email:
                await send_email(email, name or None, "🏆 Félicitations — vous êtes le POP'S d'Or !",
                                 _wrap_html("POP'S d'Or", f"<p style='font-size:14px;'>{msg}</p>"
                                            "<p style='font-size:14px;'>Continuez à soigner vos enlèvements : ce badge se gagne avis après avis.</p>"),
                                 tags=["pops-gold"])
        if prev_uid:
            name, email = await contact(prev_uid)
            msg = (f"{name}, un autre POP'S vient de prendre la tête du palmarès : le badge "
                   "« 🏆 POP'S d'Or » a changé de boutique. Récoltez de nouveaux avis 5 étoiles pour le reconquérir !")
            await create_notification(
                notification_type="pops_gold_lost", title="Le badge POP'S d'Or a changé de main",
                message=msg, target_roles=[], target_user_id=prev_uid,
                data={"action_url": "/espace-detaillant"})
            if email:
                await send_email(email, name or None, "Le badge POP'S d'Or a changé de main",
                                 _wrap_html("POP'S d'Or", f"<p style='font-size:14px;'>{msg}</p>"),
                                 tags=["pops-gold"])
    except Exception as exc:
        logger.warning("Notif changement POP'S d'Or : %s", exc)


@detaillant_public_router.get("/shops/public/{detaillant_user_id}")
async def pops_shop_page(detaillant_user_id: str):
    """Mini page publique d'un POP'S : profil, lots en cours, avis."""
    prof = await db.detaillant_profiles.find_one(
        {"user_id": detaillant_user_id},
        {"_id": 0, "user_id": 1, "company_name": 1, "locality": 1, "country_code": 1,
         "rating_avg": 1, "rating_count": 1, "pickup_slots": 1, "created_at": 1, "gold": 1})
    if not prof or not prof.get("company_name"):
        raise HTTPException(status_code=404, detail="Boutique POP'S introuvable")
    import auction_helpers as ah
    offer_ids = [o["id"] async for o in db.detaillant_offers.find(
        {"user_id": detaillant_user_id}, {"_id": 0, "id": 1})]
    lots = []
    async for a in db.auctions.find(
            {"detaillant_offer_id": {"$in": offer_ids}}, {"_id": 0}).sort("starts_at", -1).limit(20):
        if ah.effective_status(a) in ("SCHEDULED", "LIVE"):
            lots.append(ah.serialize_member(a))
    reviews = await db.detaillant_shop_reviews.find(
        {"detaillant_user_id": detaillant_user_id},
        {"_id": 0, "rating": 1, "comment": 1, "reply": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    sold = []
    async for a in db.auctions.find(
            {"detaillant_offer_id": {"$in": offer_ids}, "status": "WON"},
            {"_id": 0, "reference": 1, "title": 1, "winner.price_eur": 1, "winner.won_at": 1,
             "pickup_confirmed_at": 1}).sort("winner.won_at", -1).limit(8):
        w = a.get("winner") or {}
        sold.append({"reference": a["reference"], "title": a["title"], "price_eur": w.get("price_eur"),
                     "won_at": w.get("won_at"), "picked_up": bool(a.get("pickup_confirmed_at"))})
    followers = await db.detaillant_followers.count_documents({"detaillant_user_id": detaillant_user_id})
    return {"shop": prof, "lots": lots, "reviews": reviews, "sold": sold, "followers": followers}


@detaillant_public_router.get("/shops/share/{detaillant_user_id}", response_class=HTMLResponse)
async def pops_shop_share(detaillant_user_id: str):
    """Aperçu riche (Open Graph) de la vitrine POP'S pour WhatsApp/Facebook + redirection."""
    prof = await db.detaillant_profiles.find_one(
        {"user_id": detaillant_user_id},
        {"_id": 0, "company_name": 1, "locality": 1, "rating_avg": 1, "rating_count": 1, "gold": 1})
    if not prof or not prof.get("company_name"):
        raise HTTPException(status_code=404, detail="Boutique POP'S introuvable")
    import os
    import html as h
    import auction_helpers as ah
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    target = f"{base}/pops/{detaillant_user_id}"
    followers = await db.detaillant_followers.count_documents({"detaillant_user_id": detaillant_user_id})
    offer_ids = [o["id"] async for o in db.detaillant_offers.find(
        {"user_id": detaillant_user_id}, {"_id": 0, "id": 1})]
    img = ""
    live_count = 0
    async for a in db.auctions.find(
            {"detaillant_offer_id": {"$in": offer_ids}}, {"_id": 0}).sort("starts_at", -1).limit(20):
        if ah.effective_status(a) in ("SCHEDULED", "LIVE"):
            live_count += 1
            if not img and a.get("image_url"):
                img = a["image_url"]
    if img.startswith("/"):
        img = f"{base}{img}"
    gold = "🏆 POP'S d'Or · " if prof.get("gold") else ""
    rating = (f"★ {float(prof['rating_avg']):.1f} ({prof.get('rating_count', 0)} avis) · "
              if prof.get("rating_avg") else "")
    title = h.escape(f"{prof['company_name']} — boutique POP'S en salle COOP'ACT")
    desc = h.escape(f"{gold}{rating}{followers} follower(s) · {live_count} lot(s) en salle — "
                    "des lots à prix descendant, le premier qui accepte remporte !")
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "<meta property='og:type' content='website'>"
        f"<meta property='og:title' content='{title}'>"
        f"<meta property='og:description' content='{desc}'>"
        + (f"<meta property='og:image' content='{h.escape(img)}'>" if img else "")
        + f"<meta property='og:url' content='{target}'>"
        "<meta name='twitter:card' content='summary_large_image'>"
        f"<meta http-equiv='refresh' content='0;url={target}'>"
        f"</head><body><script>location.replace('{target}')</script></body></html>")


@detaillant_router.get("/weekly-recaps")
async def detaillant_my_weekly_recaps(user: dict = Depends(get_current_user)):
    """Historique des récaps hebdo du POP'S, semaine par semaine."""
    recaps = await db.detaillant_weekly_recaps.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("week_key", -1).limit(26).to_list(26)
    return {"recaps": recaps}


@detaillant_router.get("/followers/stats")
async def detaillant_followers_stats(user: dict = Depends(get_current_user)):
    """Communauté du POP'S : total de followers + évolution mensuelle."""
    total = await db.detaillant_followers.count_documents({"detaillant_user_id": user["id"]})
    monthly = []
    async for r in db.detaillant_followers.aggregate([
        {"$match": {"detaillant_user_id": user["id"]}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 7]}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}}, {"$limit": 12}]):
        monthly.append({"month": r["_id"], "new": r["n"]})
    return {"total": total, "monthly": monthly}


@detaillant_router.get("/reviews")
async def detaillant_my_reviews(user: dict = Depends(get_current_user)):
    reviews = await db.detaillant_shop_reviews.find(
        {"detaillant_user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"reviews": reviews}


class ReplyBody(BaseModel):
    reply: str


@detaillant_router.post("/reviews/{review_id}/reply")
async def detaillant_reply_review(review_id: str, body: ReplyBody, user: dict = Depends(get_current_user)):
    """Réponse publique du POP'S à un avis reçu."""
    if len(body.reply.strip()) < 2:
        raise HTTPException(status_code=400, detail="Réponse trop courte")
    res = await db.detaillant_shop_reviews.update_one(
        {"id": review_id, "detaillant_user_id": user["id"]},
        {"$set": {"reply": body.reply.strip()[:500], "replied_at": _now().isoformat()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Avis introuvable")
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
    if not await db.detaillant_conventions.find_one({"user_id": user["id"]}):
        raise HTTPException(status_code=403,
                            detail="Signez d'abord la convention cadre de partenariat POP'S COOP'ACT")
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


async def _send_pops_welcome_email(user_id: str):
    """Email de bienvenue POP'S avec la convention cadre signée jointe en PDF."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "company_name": 1})
    if not user or not user.get("email"):
        return
    prof = await db.detaillant_profiles.find_one({"user_id": user_id}, {"_id": 0, "company_name": 1}) or {}
    name = prof.get("company_name") or user.get("company_name") or ""
    pdf, sig = await _convention_pdf_bytes(user_id)
    attachments = None
    if pdf:
        import base64
        attachments = [{"content": base64.b64encode(pdf).decode(), "name": "convention-pops-coopact.pdf"}]
    from brevo_service import send_email, _wrap_html
    subject = "🎉 Bienvenue dans le réseau POP'S — votre abonnement COOP'ACT est actif !"
    body = (
        f"<p style='font-size:14px;'>Bonjour {name},</p>"
        "<p style='font-size:14px;'>Votre abonnement <b>POP'S — Vendeur éphémère en salle COOP'ACT</b> "
        "(390 €/mois, 3 dépôts d'offres inclus) est désormais <b>actif</b>. Bienvenue !</p>"
        "<ul style='font-size:13px;'>"
        "<li>Déposez vos offres depuis votre espace POP'S (remise minimum 15 %).</li>"
        "<li>Chaque lot fait l'objet d'une fiche de cession à signer avant validation.</li>"
        "<li>Suivez vos ventes, followers et avis — récap hebdo chaque lundi.</li></ul>"
        + ("<p style='font-size:13px;'>Vous trouverez ci-joint votre <b>convention cadre de partenariat "
           f"signée</b> (par {sig['signer_name']}, horodatée).</p>" if pdf else "")
        + "<p style='font-size:12px;color:#B8A98F;'>KDMARCHÉ × O'SCOP — agir ensemble pour la juste valeur.</p>")
    await send_email(user["email"], name or None, subject, _wrap_html(subject, body),
                     text_content="Votre abonnement POP'S COOP'ACT est actif. Convention signée jointe.",
                     tags=["pops-welcome"], attachments=attachments)


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
    try:
        await _send_pops_welcome_email(user["id"])
    except Exception as exc:
        logger.warning("Email bienvenue POP'S %s : %s", user["id"], exc)
    return {"ok": True, "valid_until": valid_until}


async def _require_active_sub(user_id: str):
    sub = await db.detaillant_subscriptions.find_one(
        {"user_id": user_id, "status": "ACTIVE"}, {"_id": 0, "valid_until": 1}, sort=[("created_at", -1)])
    if not (sub and datetime.fromisoformat(sub["valid_until"]) > _now()):
        raise HTTPException(status_code=403, detail="Abonnement Détaillant (390 €/mois) requis pour déposer des offres")


class OfferBody(BaseModel):
    product_sku: str
    lot_type: str = "SAME"      # SAME = lot x3 même produit, COMPOSED = lot composé
    product_skus: List[str] = []  # lot composé : jusqu'à 3 produits différents du catalogue
    qty_lots: int = 1
    description: str
    category: Optional[str] = None
    composed_detail: Optional[str] = None
    lot_price: float = 0            # prix de référence du lot (devise ci-dessous)
    currency: str = "EUR"           # code ISO 4217 (monde entier)
    discount_mode: str = "PERCENT"  # PERCENT | AMOUNT
    discount_value: float = 15
    scheduled_start: Optional[str] = None  # ISO — programmation avec countdown
    photo_main: Optional[str] = None       # photo principale (obligatoire)
    photos: List[str] = []                 # jusqu'à 2 photos facultatives
    condition: str = "NEW"                 # NEW | USED
    warranty: Optional[str] = None         # garantie produit
    dlc: Optional[str] = None              # DLC ISO — obligatoire si produit périssable (min. +3 mois)


@detaillant_router.post("/photos")
async def detaillant_upload_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Téléverse une photo de lot (PNG/JPEG/WebP, 5 Mo max) et renvoie son URL."""
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPEG ou WebP")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Photo trop lourde (max 5 Mo)")
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    from upload_storage import save_upload
    url = await save_upload(f"detaillant/{user['id'][:8]}-{uuid.uuid4().hex[:10]}.{ext}", content, file.content_type)
    return {"url": url}


@detaillant_router.get("/catalog")
async def detaillant_catalog(user: dict = Depends(get_current_user)):
    products = await db.lolodrive_products.find(
        {"detaillant_active": {"$ne": False}},
        {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1, "brand_logo": 1, "image_url": 1, "perishable": 1}).sort("name", 1).to_list(300)
    return {"products": products}


@detaillant_public_router.get("/catalog/public")
async def detaillant_catalog_public():
    """Catalogue spécial Détaillant LOLODRIVE en vigueur — visible sans connexion sur la vitrine."""
    products = await db.lolodrive_products.find(
        {"detaillant_active": {"$ne": False}},
        {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1, "brand_logo": 1, "image_url": 1, "perishable": 1}).sort("name", 1).to_list(300)
    return {"products": products}


@detaillant_router.get("/offers")
async def detaillant_my_offers(user: dict = Depends(get_current_user)):
    offers = await db.detaillant_offers.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"offers": offers}


# ---------- Convention cadre POP'S ----------

@detaillant_router.get("/convention")
async def get_convention(user: dict = Depends(get_current_user)):
    from convention_cession import CONVENTION_VERSION, CONVENTION_PARTIES, CONVENTION_ARTICLES
    sig = await db.detaillant_conventions.find_one(
        {"user_id": user["id"]}, {"_id": 0, "signer_name": 1, "signed_at": 1, "version": 1})
    return {"version": CONVENTION_VERSION, "parties": CONVENTION_PARTIES,
            "articles": [{"title": t, "text": x} for t, x in CONVENTION_ARTICLES],
            "signed": bool(sig), "signature": sig}


class ConventionSignBody(BaseModel):
    signer_name: str


@detaillant_router.post("/convention/sign")
async def sign_convention(body: ConventionSignBody, user: dict = Depends(get_current_user)):
    from convention_cession import CONVENTION_VERSION
    name = body.signer_name.strip()
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Indiquez le nom complet du signataire")
    await db.detaillant_conventions.update_one(
        {"user_id": user["id"]},
        {"$set": {"signer_name": name, "version": CONVENTION_VERSION,
                  "signed_at": _now().isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4())}}, upsert=True)
    return {"ok": True, "signed": True}


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
    product = await db.lolodrive_products.find_one(
        {"sku": body.product_sku}, {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1, "brand_logo": 1, "perishable": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable dans le catalogue LOLODRIVE en vigueur")
    composed_products = [product]
    if body.lot_type == "COMPOSED" and body.product_skus:
        skus = list(dict.fromkeys([body.product_sku] + [s for s in body.product_skus if s]))[:3]
        composed_products = []
        for sku in skus:
            p = await db.lolodrive_products.find_one(
                {"sku": sku, "detaillant_active": {"$ne": False}},
                {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1, "brand_logo": 1, "perishable": 1})
            if not p:
                raise HTTPException(status_code=404, detail=f"Produit {sku} introuvable dans le catalogue en vigueur")
            composed_products.append(p)
    if not (body.photo_main or "").strip():
        raise HTTPException(status_code=400, detail="Une photo principale du lot est obligatoire")
    if body.condition not in ("NEW", "USED"):
        raise HTTPException(status_code=400, detail="État du produit invalide (neuf ou occasion)")
    dlc_iso = None
    if any(p.get("perishable") for p in composed_products):
        if not body.dlc:
            raise HTTPException(status_code=400, detail="DLC obligatoire pour ce produit périssable")
        try:
            dlc_dt = datetime.fromisoformat(body.dlc.replace("Z", "+00:00"))
            if dlc_dt.tzinfo is None:
                dlc_dt = dlc_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="DLC invalide")
        if dlc_dt < _now() + timedelta(days=90):
            raise HTTPException(status_code=400, detail="DLC insuffisante : minimum 3 mois pour un produit périssable")
        dlc_iso = dlc_dt.date().isoformat()
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
        "product_sku": product["sku"],
        "product_name": " + ".join(p["name"] for p in composed_products) if len(composed_products) > 1 else product["name"],
        "product_skus": [p["sku"] for p in composed_products],
        "category": body.category or product.get("category"),
        "product_brand": product.get("brand"), "product_brand_logo": product.get("brand_logo"),
        "lot_type": body.lot_type, "lot_size": 3, "qty_lots": body.qty_lots,
        "description": body.description.strip(),
        "composed_detail": (body.composed_detail or "").strip() or None,
        "cost_credits": cost, "extra_offer": extra,
        "lot_price": round(body.lot_price, 2), "currency": body.currency.strip().upper(),
        "discount_mode": body.discount_mode, "discount_value": body.discount_value,
        "discount_amount": discount_amount, "discount_pct": discount_pct,
        "final_price": final_price, "scheduled_start": scheduled_start,
        "photo_main": body.photo_main.strip(), "photos": [p for p in body.photos if p][:2],
        "photo_labels": [p["name"] for p in composed_products] if len(composed_products) > 1 else None,
        "condition": body.condition, "warranty": (body.warranty or "").strip() or None, "dlc": dlc_iso,
        "status": "PENDING", "month_key": month_key,
        "created_at": _now().isoformat()}
    await db.detaillant_offers.insert_one({**offer})
    # Fiche de cession universelle pré-remplie (à signer par le POP'S avant validation)
    from convention_cession import cession_declarations
    perishable = bool(product.get("perishable")) or any(p.get("perishable") for p in composed_products)
    cession = {
        "id": str(uuid.uuid4()), "reference": f"CES-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        "offer_id": offer["id"], "user_id": user["id"],
        "cedant": {"company_name": offer["company_name"], "locality": offer["locality"],
                   "country_code": offer["country_code"],
                   "siret": (prof or {}).get("siret", ""), "phone": (prof or {}).get("phone", "")},
        "cessionnaire": "OBJECTIF SCOP OUTREMER — SCIC SAS au capital de 10 500 €, "
                        "13 rue Rodrigue Youyoute, 97139 Les Abymes, représentée par Mme Félixia PIPEROL",
        "category": offer["category"], "condition": offer["condition"],
        "lot_designation": offer["product_name"], "lot_type": offer["lot_type"],
        "qty_lots": offer["qty_lots"],
        "products": [{"sku": p["sku"], "name": p["name"], "qty": 3 if len(composed_products) == 1 else 1,
                      "dlc": offer.get("dlc"), "condition": offer["condition"]} for p in composed_products],
        "valuation": {"lot_price": offer["lot_price"], "discount_pct": offer["discount_pct"],
                      "final_price": offer["final_price"], "currency": offer["currency"],
                      "warranty": offer.get("warranty")},
        "declarations": cession_declarations(offer["category"], perishable, offer["condition"]),
        "declarations_checked": [], "status": "DRAFT",
        "effective_from": None, "effective_until": None,
        "created_at": _now().isoformat()}
    await db.detaillant_cessions.insert_one({**cession})
    cession.pop("_id", None)
    offer["cession_reference"] = cession["reference"]
    return offer


@detaillant_router.get("/offers/{offer_id}/cession")
async def get_cession(offer_id: str, user: dict = Depends(get_current_user)):
    c = await db.detaillant_cessions.find_one(
        {"offer_id": offer_id, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Fiche de cession introuvable")
    return c


class CessionSignBody(BaseModel):
    signer_name: str
    declarations_checked: List[str] = []


@detaillant_router.post("/offers/{offer_id}/cession/sign")
async def sign_cession(offer_id: str, body: CessionSignBody, user: dict = Depends(get_current_user)):
    c = await db.detaillant_cessions.find_one(
        {"offer_id": offer_id, "user_id": user["id"]}, {"_id": 0, "declarations": 1})
    if not c:
        raise HTTPException(status_code=404, detail="Fiche de cession introuvable")
    name = body.signer_name.strip()
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Indiquez le nom complet du signataire")
    missing = [d for d in c["declarations"] if d not in body.declarations_checked]
    if missing:
        raise HTTPException(status_code=400,
                            detail=f"Cochez toutes les déclarations applicables ({len(missing)} manquante(s))")
    await db.detaillant_cessions.update_one(
        {"offer_id": offer_id, "user_id": user["id"]},
        {"$set": {"status": "SIGNED", "signer_name": name,
                  "declarations_checked": body.declarations_checked,
                  "signed_at": _now().isoformat()}})
    return {"ok": True, "status": "SIGNED"}


# ---------- PDF convention / cession + registre admin ----------

def _pdf_doc(title: str, blocks: list) -> bytes:
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    ss = getSampleStyleSheet()
    story = [Paragraph(escape(title), ss["Title"]), Spacer(1, 10)]
    for h, t in blocks:
        if h:
            story.append(Paragraph(escape(h), ss["Heading4"]))
        story.append(Paragraph(escape(t), ss["BodyText"]))
        story.append(Spacer(1, 4))
    doc.build(story)
    return buf.getvalue()


def _fmt_ts(iso):
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M UTC")


async def _convention_pdf_bytes(user_id: str):
    sig = await db.detaillant_conventions.find_one({"user_id": user_id}, {"_id": 0})
    if not sig:
        return None, None
    from convention_cession import CONVENTION_ARTICLES, CONVENTION_PARTIES, CONVENTION_VERSION
    prof = await db.detaillant_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    blocks = [("Entre les parties", CONVENTION_PARTIES),
              ("Partenaire signataire", f"{prof.get('company_name', '')} — {prof.get('locality', '')} "
                                       f"({prof.get('country_code', '')}) · SIREN/SIRET : {prof.get('siret') or '—'}")]
    blocks += list(CONVENTION_ARTICLES)
    blocks.append(("Signature électronique",
                   f"Signée par {sig['signer_name']} le {_fmt_ts(sig['signed_at'])} — version {sig['version']} — "
                   "horodatage plateforme COOP'ACT (art. 18.3 de la convention)."))
    return _pdf_doc(f"Convention cadre de partenariat POP'S COOP'ACT — v{CONVENTION_VERSION}", blocks), sig


@detaillant_router.get("/convention/pdf")
async def convention_pdf(user: dict = Depends(get_current_user)):
    from fastapi.responses import Response
    pdf, _sig = await _convention_pdf_bytes(user["id"])
    if not pdf:
        raise HTTPException(status_code=404, detail="Convention non signée")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=convention-pops-coopact.pdf"})


@detaillant_router.get("/offers/{offer_id}/cession/pdf")
async def cession_pdf(offer_id: str, user: dict = Depends(get_current_user)):
    from fastapi.responses import Response
    c = await db.detaillant_cessions.find_one(
        {"offer_id": offer_id, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Fiche de cession introuvable")
    pdf = _cession_pdf_bytes(c)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={c['reference']}.pdf"})


def _cession_pdf_bytes(c: dict) -> bytes:
    v = c["valuation"]
    products = " ; ".join(f"{p['sku']} — {p['name']} ×{p['qty']}"
                          f"{' (DLC ' + p['dlc'] + ')' if p.get('dlc') else ''}" for p in c["products"])
    blocks = [
        ("1. Références de l'opération",
         f"Référence de la cession : {c['reference']} · Établie le {_fmt_ts(c['created_at'])} · "
         f"Opérations : {', '.join(c.get('auction_refs') or []) or '—'}"),
        ("2. Parties à la cession",
         f"Cédant POP'S : {c['cedant']['company_name']} — {c['cedant']['locality']} ({c['cedant']['country_code']}) · "
         f"SIREN/SIRET : {c['cedant'].get('siret') or '—'}. Cessionnaire : {c['cessionnaire']}."),
        ("3. Nature du lot",
         f"{c['lot_designation']} — {c['qty_lots']} lot(s) ×3 {'(composé)' if c['lot_type'] == 'COMPOSED' else ''} · "
         f"Catégorie : {c.get('category') or '—'} · État : {'Neuf' if c['condition'] == 'NEW' else 'Occasion'}"),
        ("4. Détail des produits cédés", products),
        ("5. Valorisation financière",
         f"Prix boutique : {v['lot_price']} {v['currency']} · Remise : -{v['discount_pct']:.0f} % · "
         f"Prix final : {v['final_price']} {v['currency']}"
         + (f" · Garantie : {v['warranty']}" if v.get('warranty') else "")),
        ("6. Effet et expiration (horodatés)",
         f"Date d'effet (ouverture en salle) : {_fmt_ts(c.get('effective_from'))} · "
         f"Expiration (fin de l'offre) : {_fmt_ts(c.get('effective_until'))}"),
        ("7. Déclarations et contrôles applicables",
         " ; ".join(f"[x] {d}" if d in (c.get('declarations_checked') or []) else f"[ ] {d}"
                    for d in c["declarations"])),
        ("8. Signature",
         (f"Bon pour accord — signée par {c['signer_name']} le {_fmt_ts(c.get('signed_at'))} · "
          f"Statut : {c['status']}") if c.get("signer_name") else "Non signée — statut DRAFT"),
    ]
    return _pdf_doc(f"Fiche de cession de produits et lots — {c['reference']}", blocks)


@detaillant_admin_router.get("/cessions/{reference}/pdf")
async def admin_cession_pdf(reference: str, admin: dict = Depends(require_admin)):
    from fastapi.responses import Response
    c = await db.detaillant_cessions.find_one({"reference": reference}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Fiche de cession introuvable")
    pdf = _cession_pdf_bytes(c)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={c['reference']}.pdf"})


@detaillant_admin_router.get("/conventions")
async def admin_conventions_registry(admin: dict = Depends(require_admin)):
    """Archive des conventions cadre signées (superadmin)."""
    convs = await db.detaillant_conventions.find({}, {"_id": 0}).sort("signed_at", -1).limit(200).to_list(200)
    for cv in convs:
        prof = await db.detaillant_profiles.find_one(
            {"user_id": cv["user_id"]}, {"_id": 0, "company_name": 1, "locality": 1, "country_code": 1})
        u = await db.users.find_one({"id": cv["user_id"]}, {"_id": 0, "email": 1})
        cv["company_name"] = (prof or {}).get("company_name") or (u or {}).get("email") or cv["user_id"]
        cv["locality"] = (prof or {}).get("locality")
        cv["country_code"] = (prof or {}).get("country_code")
    return {"conventions": convs, "total": len(convs)}


@detaillant_admin_router.get("/cessions")
async def admin_cessions_registry(q: str = "", status: str = "", admin: dict = Depends(require_admin)):
    """Registre central des fiches de cession (recherche + filtre statut)."""
    query: dict = {}
    if status:
        query["status"] = status.upper()
    if q.strip():
        rx = {"$regex": q.strip(), "$options": "i"}
        query["$or"] = [{"reference": rx}, {"lot_designation": rx},
                        {"cedant.company_name": rx}, {"signer_name": rx}]
    items = await db.detaillant_cessions.find(query, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"cessions": items, "total": len(items)}


@detaillant_router.get("/sales")
async def detaillant_sales(user: dict = Depends(get_current_user)):
    """Résultats des lots du détaillant en salle : mises, gagnants, montants."""
    offer_ids = [o["id"] async for o in db.detaillant_offers.find({"user_id": user["id"]}, {"_id": 0, "id": 1})]
    sales = []
    async for a in db.auctions.find({"detaillant_offer_id": {"$in": offer_ids}}, {"_id": 0}).sort("starts_at", -1).limit(100):
        w = a.get("winner") or {}
        sales.append({
            "reference": a.get("reference"), "title": a.get("title"),
            "status": a.get("status"), "starts_at": a.get("starts_at"), "ends_at": a.get("ends_at"),
            "value_eur": a.get("value_eur"), "current_price_eur": a.get("current_price_eur"),
            "bids_count": a.get("bids_count", 0),
            "winner_name": w.get("name"), "won_price_eur": w.get("price_eur"), "won_at": w.get("won_at"),
            "picked_up": bool(a.get("pickup_confirmed_at")), "relisted": bool(a.get("relisted"))})
    totals = {"lots": len(sales), "bids": sum(s["bids_count"] for s in sales),
              "won": sum(1 for s in sales if s["status"] == "WON"),
              "revenue_eur": round(sum(s["won_price_eur"] or 0 for s in sales if s["status"] == "WON"), 2)}
    return {"sales": sales, "totals": totals}


@detaillant_router.post("/sales/{reference}/relist")
async def detaillant_relist(reference: str, user: dict = Depends(get_current_user)):
    """Reprogramme en un clic un lot expiré, sans nouveau dépôt de crédits."""
    a = await db.auctions.find_one({"reference": reference, "source": "DETAILLANT"}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    offer = await db.detaillant_offers.find_one(
        {"id": a.get("detaillant_offer_id"), "user_id": user["id"]}, {"_id": 0, "id": 1})
    if not offer:
        raise HTTPException(status_code=403, detail="Ce lot ne vous appartient pas")
    if a.get("status") != "EXPIRED":
        raise HTTPException(status_code=409, detail="Seul un lot expiré peut être relancé")
    if a.get("relisted"):
        raise HTTPException(status_code=409, detail="Ce lot a déjà été relancé")
    starts = _now() + timedelta(hours=1)
    new_ref = f"AUC-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    doc = {k: v for k, v in a.items() if k not in (
        "id", "reference", "status", "winner", "bids_count", "current_price_eur",
        "starts_at", "ends_at", "live_alert_sent", "ending_alert_sent", "ending_alert_at",
        "pickup_confirmed_at", "relisted", "created_at")}
    doc.update({"id": str(uuid.uuid4()), "reference": new_ref, "status": "SCHEDULED",
                "current_price_eur": a.get("value_eur"), "bids_count": 0,
                "starts_at": starts.isoformat(), "ends_at": (starts + timedelta(days=7)).isoformat(),
                "relisted_from": reference, "created_at": _now().isoformat()})
    await db.auctions.insert_one(doc)
    await db.auctions.update_one({"reference": reference}, {"$set": {"relisted": True}})
    return {"ok": True, "reference": new_ref, "starts_at": doc["starts_at"]}


class ReviewBody(BaseModel):
    action: str  # APPROVE | REJECT
    note: Optional[str] = None


class CatalogProductBody(BaseModel):
    sku: Optional[str] = None
    name: str
    category: str = ""
    brand: str = ""
    brand_logo: Optional[str] = None
    perishable: bool = False
    detaillant_active: bool = True
    image_url: Optional[str] = None


@detaillant_admin_router.post("/catalog/logo")
async def admin_upload_brand_logo(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    """Logo de marque (PNG/JPEG/WebP/SVG, 2 Mo max) pour un rendu premium en salle."""
    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPEG, WebP ou SVG")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo trop lourd (max 2 Mo)")
    from upload_storage import save_upload
    url = await save_upload(f"brands/{uuid.uuid4().hex[:12]}.{allowed[file.content_type]}", content, file.content_type)
    return {"url": url}


@detaillant_admin_router.get("/catalog")
async def admin_detaillant_catalog(admin: dict = Depends(require_admin)):
    """Catalogue produit en vigueur (géré par le superadmin)."""
    products = await db.lolodrive_products.find(
        {}, {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1, "brand_logo": 1, "image_url": 1,
             "perishable": 1, "detaillant_active": 1}).sort("name", 1).to_list(500)
    return {"products": products}


@detaillant_admin_router.post("/catalog")
async def admin_upsert_catalog_product(body: CatalogProductBody, admin: dict = Depends(require_admin)):
    if len(body.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Nom de produit trop court")
    sku = (body.sku or "").strip() or f"DET-{uuid.uuid4().hex[:8].upper()}"
    doc = {"sku": sku, "name": body.name.strip(), "category": body.category.strip(),
           "brand": body.brand.strip(), "brand_logo": body.brand_logo,
           "perishable": body.perishable, "detaillant_active": body.detaillant_active,
           "updated_at": _now().isoformat(), "updated_by": admin.get("email")}
    if body.image_url:
        doc["image_url"] = body.image_url
    await db.lolodrive_products.update_one(
        {"sku": sku}, {"$set": doc, "$setOnInsert": {"created_at": _now().isoformat()}}, upsert=True)
    return {"ok": True, "sku": sku}


@detaillant_admin_router.patch("/catalog/{sku}")
async def admin_toggle_catalog_product(sku: str, perishable: Optional[bool] = None,
                                       detaillant_active: Optional[bool] = None,
                                       admin: dict = Depends(require_admin)):
    updates = {}
    if perishable is not None:
        updates["perishable"] = perishable
    if detaillant_active is not None:
        updates["detaillant_active"] = detaillant_active
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    r = await db.lolodrive_products.update_one({"sku": sku}, {"$set": updates})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True}


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
    # Photographie produits : les plus proposés et les plus remportés en salle
    top_products = []
    async for r in db.detaillant_offers.aggregate([
        {"$match": {"status": {"$ne": "REJECTED"}}},
        {"$group": {"_id": "$product_name", "offers": {"$sum": 1}, "lots": {"$sum": "$qty_lots"}}},
        {"$sort": {"offers": -1}}, {"$limit": 6}]):
        top_products.append({"product": r["_id"], "offers": r["offers"], "lots": r["lots"]})
    top_won = []
    async for r in db.auctions.aggregate([
        {"$match": {"source": "DETAILLANT", "status": "WON"}},
        {"$group": {"_id": "$title", "won": {"$sum": 1},
                    "revenue_eur": {"$sum": "$winner.price_eur"}}},
        {"$sort": {"won": -1}}, {"$limit": 6}]):
        top_won.append({"product": r["_id"], "won": r["won"], "revenue_eur": round(r["revenue_eur"] or 0, 2)})
    return {"detaillants": total, "active_subscriptions": active_subs,
            "monthly_sub_revenue_eur": revenue_subs_eur,
            "offers_by_status": by_status, "credits_spent": credits_spent,
            "lots_in_salle": lots_scheduled, "lots_won": lots_won, "top_retailers": top,
            "top_products": top_products, "top_won": top_won}


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
    if body.action == "APPROVE":
        ces = await db.detaillant_cessions.find_one(
            {"offer_id": offer_id}, {"_id": 0, "status": 1})
        if ces and ces.get("status") == "DRAFT":
            raise HTTPException(status_code=409,
                                detail="Fiche de cession non signée par le POP'S — validation impossible")
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
        first_sub = await db.detaillant_subscriptions.find_one(
            {"user_id": offer["user_id"], "status": "ACTIVE"}, {"_id": 0, "created_at": 1}, sort=[("created_at", 1)])
        verified = False
        if first_sub and first_sub.get("created_at"):
            try:
                verified = datetime.fromisoformat(first_sub["created_at"]) <= _now() - timedelta(days=90)
            except ValueError:
                pass
        retailer = {"company_name": offer.get("company_name"), "country_code": offer.get("country_code"),
                    "locality": offer.get("locality"), "verified": verified,
                    "detaillant_user_id": offer["user_id"],
                    "rating_avg": (prof or {}).get("rating_avg"), "rating_count": (prof or {}).get("rating_count", 0),
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
        if offer.get("condition"):
            desc += f" — État : {'neuf' if offer['condition'] == 'NEW' else 'occasion'}"
        if offer.get("warranty"):
            desc += f" — Garantie : {offer['warranty']}"
        if offer.get("dlc"):
            desc += f" — DLC : {'-'.join(reversed(offer['dlc'].split('-')))}"
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
                "image_url": offer.get("photo_main") or (product or {}).get("image_url"),
                "brand": offer.get("product_brand") or (product or {}).get("brand"),
                "brand_logo": offer.get("product_brand_logo") or (product or {}).get("brand_logo"),
                "photos": [p for p in ([offer.get("photo_main")] + (offer.get("photos") or [])) if p],
                "photo_labels": offer.get("photo_labels"),
                "condition": offer.get("condition"), "warranty": offer.get("warranty"), "dlc": offer.get("dlc"),
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
        # Horodatage de la fiche de cession : effet = ouverture en salle, expiration = fin de l'offre
        if created_refs:
            lot0 = await db.auctions.find_one(
                {"reference": created_refs[0]}, {"_id": 0, "starts_at": 1, "ends_at": 1})
            await db.detaillant_cessions.update_one(
                {"offer_id": offer_id},
                {"$set": {"status": "EFFECTIVE", "auction_refs": created_refs,
                          "effective_from": (lot0 or {}).get("starts_at"),
                          "effective_until": (lot0 or {}).get("ends_at")}})
    await db.detaillant_offers.update_one({"id": offer_id}, {"$set": updates})
    if body.action == "APPROVE" and created_refs:
        await recalc_gold_pops()
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
    # Alerte aux membres qui suivent ce POP'S : nouveau(x) lot(s) en salle (cloche + email)
    if body.action == "APPROVE" and created_refs:
        try:
            from core_deps import create_notification
            follower_ids = [f["member_id"] async for f in db.detaillant_followers.find(
                {"detaillant_user_id": offer["user_id"]}, {"_id": 0, "member_id": 1})]
            msg_f = (f"Le POP'S {offer.get('company_name')} vient de déposer "
                     f"{len(created_refs)} lot(s) en salle COOP'ACT : {offer['product_name']}.")
            for member_id in follower_ids:
                await create_notification(
                    notification_type="pops_new_lot",
                    title=f"🛍️ Nouveau lot — {offer.get('company_name')}",
                    message=msg_f,
                    target_roles=[], target_user_id=member_id,
                    data={"action_url": "/encheres"})
            if follower_ids:
                from brevo_service import send_email, _wrap_html
                async for m in db.users.find(
                        {"id": {"$in": follower_ids}}, {"_id": 0, "email": 1, "first_name": 1, "company_name": 1}):
                    if not m.get("email"):
                        continue
                    name = m.get("first_name") or m.get("company_name") or ""
                    html = _wrap_html(
                        f"Nouveau lot chez {offer.get('company_name')}",
                        f"<p style='font-size:14px;'>Bonjour {name},</p>"
                        f"<p style='font-size:14px;'>{msg_f}</p>"
                        "<p style='font-size:14px;'>Rendez-vous en salle COOP'ACT pour coop'acter avant les autres !</p>")
                    await send_email(m["email"], name or None,
                                     f"🛍️ Nouveau lot — {offer.get('company_name')}", html,
                                     tags=["pops-new-lot"])
        except Exception as exc:
            logger.warning("Notif followers POP'S: %s", exc)
        # Alerte aux Coop'acteurs qui suivent la marque du produit (cloche + email, canaux réglables)
        try:
            brand = offer.get("product_brand")
            if brand:
                from core_deps import create_notification
                from routes_prefs import channel_allowed
                member_ids = list(dict.fromkeys([bf["member_id"] async for bf in db.brand_followers.find(
                    {"brand": brand}, {"_id": 0, "member_id": 1})]))
                for member_id in member_ids:
                    if not await channel_allowed(member_id, "brand_new_lot", "inapp"):
                        continue
                    await create_notification(
                        notification_type="brand_new_lot",
                        title=f"⭐ {brand} arrive en salle !",
                        message=(f"Un lot {brand} ({offer['product_name']}) vient d'être programmé "
                                 "en salle COOP'ACT. À vous de coop'acter !"),
                        target_roles=[], target_user_id=member_id,
                        data={"action_url": "/encheres"})
                if member_ids:
                    import os
                    from brevo_service import send_email, _wrap_html
                    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
                    room = f"{base}/encheres" if base else "/encheres"
                    lot = await db.auctions.find_one(
                        {"reference": created_refs[0]}, {"_id": 0, "starts_at": 1, "ends_at": 1}) or {}
                    starts = (lot.get("starts_at") or "")[:16].replace("T", " ")
                    ends = (lot.get("ends_at") or "")[:16].replace("T", " ")
                    dates_line = (f"<p style='font-size:13px;color:#6b5e4a;'>En salle du {starts} au {ends} (UTC).</p>"
                                  if starts and ends else "")
                    photo = offer.get("photo_main") or ""
                    if photo and photo.startswith("/") and base:
                        photo = f"{base}{photo}"
                    photo_html = (f"<p style='margin:0 0 12px;'><img src='{photo}' alt='{offer['product_name']}' "
                                  "style='max-width:260px;width:100%;border-radius:10px;'/></p>") if photo else ""
                    cur = offer.get("currency", "EUR")
                    price_html = (
                        f"<p style='font-size:14px;'>Prix boutique : <s>{offer.get('lot_price')} {cur}</s> → "
                        f"<b>{offer.get('final_price')} {cur}</b> "
                        f"<span style='color:#1a7f4b;font-weight:bold;'>(-{offer.get('discount_pct', 0):.0f} %)</span></p>")
                    subject = f"⭐ {brand} arrive en salle COOP'ACT !"
                    body_html = (
                        photo_html
                        + f"<p style='font-size:14px;'>Un lot <b>{brand}</b> — <b>{offer['product_name']}</b> "
                          f"vient d'être programmé en salle COOP'ACT par le POP'S <b>{offer.get('company_name')}</b>.</p>"
                        + price_html + dates_line
                        + f"<p style='font-size:14px;'><a href='{room}' "
                          "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                          "text-decoration:none;font-weight:bold;'>Voir en salle</a></p>"
                          "<p style='font-size:12px;color:#B8A98F;'>Vous recevez cet email car vous suivez la marque "
                          f"{brand}. Chaque Coop'Act fait baisser le prix !</p>")
                    async for m in db.users.find(
                            {"id": {"$in": member_ids}}, {"_id": 0, "id": 1, "email": 1, "first_name": 1, "company_name": 1}):
                        if not m.get("email"):
                            continue
                        if not await channel_allowed(m["id"], "brand_new_lot", "email"):
                            continue
                        name = m.get("first_name") or m.get("company_name") or ""
                        greeting = f"<p style='font-size:14px;'>Bonjour {name},</p>" if name else ""
                        try:
                            await send_email(m["email"], name or None, subject,
                                             _wrap_html(subject, greeting + body_html),
                                             tags=["brand-new-lot"])
                        except Exception as exc:
                            logger.warning("Email follower marque %s : %s", m.get("email"), exc)
        except Exception as exc:
            logger.warning("Notif followers marque: %s", exc)
    out = await db.detaillant_offers.find_one({"id": offer_id}, {"_id": 0})
    return out
