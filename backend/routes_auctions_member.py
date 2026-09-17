"""Enchères produits à prix descendant — côté membre : salle des enchères, plan obligatoire, mises, victoire."""
import logging
import uuid
from datetime import timedelta
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
import auction_helpers as ah

logger = logging.getLogger(__name__)

auctions_member_router = APIRouter(prefix="/api/auctions", tags=["auctions-member"])


def _stripe_key() -> str:
    from stripe_accounts import get_stripe_key
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=503, detail="Stripe O'SCOP non configuré")
    return key


# ---------- Salle des enchères (publique, filtres enrichis) ----------

@auctions_member_router.get("/community-stats")
async def community_stats():
    """Compteurs publics de la page marque : Coop'acteurs actifs et lots remportés."""
    now_iso = ah.now_utc().isoformat()
    coopacteurs = await ah.db.auction_accounts.count_documents({"valid_until": {"$gt": now_iso}})
    lots_won = await ah.db.auctions.count_documents({"status": "WON"})
    total_bids = await ah.db.auction_bids.count_documents({})
    return {"coopacteurs": coopacteurs, "lots_won": lots_won, "total_bids": total_bids}


@auctions_member_router.get("/public")
async def public_auctions(status: str = "", category: str = "", type_id: str = "",
                          source: str = "", q: str = ""):
    await ah.sync_auction_statuses()
    try:
        from auction_emails import run_auction_ending_alerts
        await run_auction_ending_alerts()
    except Exception as exc:
        logger.warning("Alertes fin imminente : %s", exc)
    query: dict = {"status": {"$in": ["SCHEDULED", "LIVE", "WON", "EXPIRED"]}}
    if category:
        query["category_id"] = category
    if type_id:
        query["type_id"] = type_id
    if source:
        query["source"] = source.upper()
        query["source_visible"] = True
    if q.strip():
        query["title"] = {"$regex": q.strip(), "$options": "i"}
    labels = await ah.taxonomy_labels()
    items = [ah.serialize_member(a, labels)
             async for a in ah.db.auctions.find(query, {"_id": 0}).sort("starts_at", 1).limit(100)]
    if status:
        items = [a for a in items if a["status"] == status.upper()]
    cats = await ah.db.auction_categories.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    types = await ah.db.auction_types.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    return {"items": items, "categories": cats, "types": types,
            "sources": [{"code": s, "label": ah.SOURCE_LABELS[s]} for s in ah.SOURCES],
            "credits_per_eur": ah.CREDITS_PER_EUR}


@auctions_member_router.get("/points")
async def pickup_points():
    pts = await ah.db.lolodrive_points.find(
        {}, {"_id": 0, "id": 1, "name": 1, "code": 1, "address": 1}).sort("name", 1).to_list(50)
    return {"items": pts}


# ---------- Plans CREDI'SCOP-Enchères (achat Stripe) ----------

@auctions_member_router.get("/plans")
async def member_plans():
    from routes_auctions_admin import ensure_auction_defaults
    await ensure_auction_defaults()
    items = await ah.db.auction_plans.find({"active": True}, {"_id": 0}).sort("price_ht_cents", 1).to_list(20)
    return {"items": items}


class PlanCheckoutBody(BaseModel):
    plan_id: str
    origin_url: str


@auctions_member_router.post("/plans/checkout")
async def plan_checkout(body: PlanCheckoutBody, user_id: str = Depends(get_current_user_id)):
    plan = await ah.db.auction_plans.find_one({"id": body.plan_id, "active": True}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    user = await ah.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    from vat import compute_vat
    vat = compute_vat(plan["price_ht_cents"], "GP")
    origin = body.origin_url.rstrip("/")
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="payment", payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur", "unit_amount": vat["ttc_cents"],
                "product_data": {"name": f"{plan['label']} — {plan['credits']} crédits COOP'ACT "
                                         f"({plan['validity_days']} j, service numérique O'SCOP)"},
            }, "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/encheres?auction_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/encheres?auction_cancelled=1",
        metadata={"kind": "AUCTION_PLAN", "user_id": user_id, "plan_id": plan["id"]})
    now = ah.now_utc().isoformat()
    await ah.db.auction_pass_purchases.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "email": user.get("email"),
        "plan_id": plan["id"], "plan_label": plan["label"], "credits": plan["credits"],
        "validity_days": plan["validity_days"], "ttc_cents": vat["ttc_cents"],
        "stripe_session_id": session.id, "status": "PENDING", "created_at": now})
    return {"checkout_url": session.url, "session_id": session.id}


@auctions_member_router.get("/plans/status")
async def plan_status(session_id: str, user_id: str = Depends(get_current_user_id)):
    purchase = await ah.db.auction_pass_purchases.find_one(
        {"stripe_session_id": session_id, "user_id": user_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Achat introuvable")
    if purchase["status"] == "PENDING":
        stripe.api_base = "https://api.stripe.com"
        session = stripe.checkout.Session.retrieve(session_id, api_key=_stripe_key())
        if session.payment_status == "paid":
            res = await ah.db.auction_pass_purchases.update_one(
                {"stripe_session_id": session_id, "status": "PENDING"},
                {"$set": {"status": "ACTIVE", "paid_at": ah.now_utc().isoformat()}})
            if res.modified_count:
                await _activate_plan(user_id, purchase)
                purchase["status"] = "ACTIVE"
    return {"status": purchase["status"], "plan_label": purchase["plan_label"]}


async def _activate_plan(user_id: str, purchase: dict):
    now = ah.now_utc()
    account = await ah.db.auction_accounts.find_one({"user_id": user_id}, {"_id": 0})
    base = ah.parse_dt((account or {}).get("valid_until"))
    start = base if base and base > now else now
    valid_until = start + timedelta(days=purchase["validity_days"])
    await ah.db.auction_accounts.update_one(
        {"user_id": user_id},
        {"$inc": {"credits": purchase["credits"]},
         "$set": {"plan_id": purchase["plan_id"], "plan_label": purchase["plan_label"],
                  "valid_until": valid_until.isoformat(), "updated_at": now.isoformat()},
         "$setOnInsert": {"created_at": now.isoformat()}}, upsert=True)
    await ah.db.auction_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "type": "PLAN_PURCHASE",
        "amount": purchase["credits"], "label": f"Achat {purchase['plan_label']}",
        "created_at": now.isoformat()})
    logger.info("Plan enchères activé : %s crédits pour %s", purchase["credits"], user_id)


@auctions_member_router.get("/me")
async def my_auction_account(user_id: str = Depends(get_current_user_id)):
    # Filet de sécurité : réconcilie les achats de plan PENDING récents auprès de Stripe
    async for pu in ah.db.auction_pass_purchases.find(
            {"user_id": user_id, "status": "PENDING"}, {"_id": 0}).sort("created_at", -1).limit(3):
        try:
            stripe.api_base = "https://api.stripe.com"
            session = stripe.checkout.Session.retrieve(pu["stripe_session_id"], api_key=_stripe_key())
            if session.payment_status == "paid":
                res = await ah.db.auction_pass_purchases.update_one(
                    {"stripe_session_id": pu["stripe_session_id"], "status": "PENDING"},
                    {"$set": {"status": "ACTIVE", "paid_at": ah.now_utc().isoformat()}})
                if res.modified_count:
                    await _activate_plan(user_id, pu)
        except Exception as exc:
            logger.warning("Réconciliation achat plan %s : %s", pu.get("stripe_session_id"), exc)
    account = await ah.get_auction_account(user_id)
    # QR d'enlèvement : token lazy pour les lots gagnés qui n'en ont pas encore
    async for w in ah.db.auctions.find(
            {"status": "WON", "winner.user_id": user_id, "winner.pickup_token": {"$exists": False}},
            {"_id": 0, "id": 1}):
        await ah.db.auctions.update_one({"id": w["id"]}, {"$set": {"winner.pickup_token": uuid.uuid4().hex}})
    wins = [ah.serialize_member(a) async for a in ah.db.auctions.find(
        {"status": "WON", "winner.user_id": user_id}, {"_id": 0}).sort("winner.won_at", -1).limit(20)]
    extra_by_id = {}
    async for a in ah.db.auctions.find(
            {"status": "WON", "winner.user_id": user_id},
            {"_id": 0, "id": 1, "winner.pickup_token": 1, "pickup_confirmed_at": 1}):
        extra_by_id[a["id"]] = a
    for w in wins:
        ex = extra_by_id.get(w["id"], {})
        w["pickup_token"] = (ex.get("winner") or {}).get("pickup_token")
        w["pickup_confirmed_at"] = ex.get("pickup_confirmed_at")
    reviewed = {r["auction_id"] async for r in ah.db.detaillant_shop_reviews.find(
        {"author_user_id": user_id}, {"_id": 0, "auction_id": 1})}
    for w in wins:
        w["shop_reviewed"] = w["id"] in reviewed
    fulfillments = {}
    async for a in ah.db.auctions.find(
            {"status": "WON", "winner.user_id": user_id}, {"_id": 0, "id": 1, "fulfillment": 1}):
        if a.get("fulfillment"):
            fulfillments[a["id"]] = a["fulfillment"]
    for w in wins:
        w["fulfillment"] = fulfillments.get(w["id"])
    bids = await ah.db.auction_bids.find(
        {"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    if bids:
        refs = {a["id"]: a async for a in ah.db.auctions.find(
            {"id": {"$in": list({b["auction_id"] for b in bids})}},
            {"_id": 0, "id": 1, "reference": 1, "title": 1})}
        for b in bids:
            ref = refs.get(b["auction_id"], {})
            b["auction_reference"] = ref.get("reference")
            b["auction_title"] = ref.get("title")
    ledger = await ah.db.auction_credit_ledger.find(
        {"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    return {"account": account, "active": ah.account_active(account), "wins": wins,
            "bids": bids, "ledger": ledger}


@auctions_member_router.get("/brands/follows")
async def my_brand_follows(user_id: str = Depends(get_current_user_id)):
    follows = [f["brand"] async for f in ah.db.brand_followers.find(
        {"member_id": user_id}, {"_id": 0, "brand": 1})]
    return {"follows": follows}


class BrandFollowBody(BaseModel):
    brand: str


@auctions_member_router.post("/brands/follow")
async def toggle_brand_follow(body: BrandFollowBody, user_id: str = Depends(get_current_user_id)):
    """Suivre / ne plus suivre une marque pour être alerté quand un lot arrive en salle."""
    brand = body.brand.strip()
    if not brand:
        raise HTTPException(status_code=400, detail="Marque invalide")
    existing = await ah.db.brand_followers.find_one({"member_id": user_id, "brand": brand})
    if existing:
        await ah.db.brand_followers.delete_one({"_id": existing["_id"]})
        return {"following": False}
    await ah.db.brand_followers.insert_one({
        "id": str(uuid.uuid4()), "member_id": user_id, "brand": brand,
        "created_at": ah.now_utc().isoformat()})
    return {"following": True}


# ---------- Alerte prix cible ----------

class PriceAlertBody(BaseModel):
    target_eur: float = 0


@auctions_member_router.get("/price-alerts")
async def my_price_alerts(user_id: str = Depends(get_current_user_id)):
    alerts = await ah.db.auction_price_alerts.find(
        {"user_id": user_id, "triggered": {"$ne": True}},
        {"_id": 0, "auction_id": 1, "target_eur": 1, "created_at": 1}).to_list(200)
    ids = [a["auction_id"] for a in alerts]
    lots = {a["id"]: a async for a in ah.db.auctions.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "title": 1, "reference": 1,
                               "current_price_eur": 1, "value_eur": 1, "status": 1})}
    for a in alerts:
        lot = lots.get(a["auction_id"]) or {}
        a["title"] = lot.get("title")
        a["reference"] = lot.get("reference")
        a["status"] = lot.get("status")
        a["current_price_eur"] = (round(float(lot.get("current_price_eur") or lot.get("value_eur") or 0), 2)
                                  if lot else None)
    return {"alerts": alerts}


@auctions_member_router.post("/{auction_id}/price-alert")
async def set_price_alert(auction_id: str, body: PriceAlertBody,
                          user_id: str = Depends(get_current_user_id)):
    """Définit (ou retire si cible <= 0) un prix cible : cloche + email quand le prix l'atteint."""
    a = await ah.db.auctions.find_one(
        {"id": auction_id}, {"_id": 0, "current_price_eur": 1, "value_eur": 1})
    if not a:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    if body.target_eur <= 0:
        await ah.db.auction_price_alerts.delete_many({"auction_id": auction_id, "user_id": user_id})
        return {"active": False}
    cur = round(float(a.get("current_price_eur") or a.get("value_eur") or 0), 2)
    target = round(float(body.target_eur), 2)
    if target >= cur:
        raise HTTPException(status_code=400,
                            detail=f"La cible doit être inférieure au prix actuel ({cur:.2f} €)")
    await ah.db.auction_price_alerts.update_one(
        {"auction_id": auction_id, "user_id": user_id},
        {"$set": {"target_eur": target, "triggered": False,
                  "created_at": ah.now_utc().isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True)
    return {"active": True, "target_eur": target}


# ---------- Suivi de boutiques POP'S ----------

@auctions_member_router.get("/shops/follows")
async def my_shop_follows(user_id: str = Depends(get_current_user_id)):
    follows = [f["detaillant_user_id"] async for f in ah.db.detaillant_followers.find(
        {"member_id": user_id}, {"_id": 0, "detaillant_user_id": 1})]
    return {"follows": follows}


@auctions_member_router.post("/shops/{detaillant_user_id}/follow")
async def toggle_shop_follow(detaillant_user_id: str, user_id: str = Depends(get_current_user_id)):
    """Suivre / ne plus suivre un POP'S pour être alerté de ses nouveaux lots."""
    existing = await ah.db.detaillant_followers.find_one(
        {"member_id": user_id, "detaillant_user_id": detaillant_user_id})
    if existing:
        await ah.db.detaillant_followers.delete_one({"_id": existing["_id"]})
        return {"following": False}
    await ah.db.detaillant_followers.insert_one({
        "id": str(uuid.uuid4()), "member_id": user_id, "detaillant_user_id": detaillant_user_id,
        "created_at": ah.now_utc().isoformat()})
    return {"following": True}


# ---------- Avis boutique (après enlèvement) ----------

class ShopReviewBody(BaseModel):
    rating: int
    comment: str = ""


@auctions_member_router.post("/{auction_id}/shop-review")
async def shop_review(auction_id: str, body: ShopReviewBody, user_id: str = Depends(get_current_user_id)):
    """Le gagnant note la boutique après l'enlèvement de son lot détaillant."""
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="Note entre 1 et 5")
    a = await ah.db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not a or (a.get("winner") or {}).get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    if a.get("source") != "DETAILLANT" or not a.get("detaillant_offer_id"):
        raise HTTPException(status_code=400, detail="Seuls les lots boutique peuvent être notés")
    if not a.get("pickup_confirmed_at"):
        raise HTTPException(status_code=409, detail="Notez la boutique après l'enlèvement du lot")
    if await ah.db.detaillant_shop_reviews.find_one({"auction_id": auction_id}):
        raise HTTPException(status_code=409, detail="Vous avez déjà noté cette boutique")
    offer = await ah.db.detaillant_offers.find_one(
        {"id": a["detaillant_offer_id"]}, {"_id": 0, "user_id": 1, "company_name": 1})
    if not offer:
        raise HTTPException(status_code=404, detail="Boutique introuvable")
    await ah.db.detaillant_shop_reviews.insert_one({
        "id": str(uuid.uuid4()), "auction_id": auction_id, "auction_reference": a.get("reference"),
        "detaillant_user_id": offer["user_id"], "company_name": offer.get("company_name"),
        "author_user_id": user_id, "rating": body.rating, "comment": body.comment.strip()[:500],
        "created_at": ah.now_utc().isoformat()})
    agg = await ah.db.detaillant_shop_reviews.aggregate([
        {"$match": {"detaillant_user_id": offer["user_id"]}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]).to_list(1)
    avg, count = round(agg[0]["avg"], 1), agg[0]["count"]
    await ah.db.detaillant_profiles.update_one(
        {"user_id": offer["user_id"]}, {"$set": {"rating_avg": avg, "rating_count": count}})
    offer_ids = [o["id"] async for o in ah.db.detaillant_offers.find(
        {"user_id": offer["user_id"]}, {"_id": 0, "id": 1})]
    await ah.db.auctions.update_many(
        {"detaillant_offer_id": {"$in": offer_ids}},
        {"$set": {"retailer.rating_avg": avg, "retailer.rating_count": count}})
    from routes_detaillant import recalc_gold_pops
    await recalc_gold_pops()
    return {"ok": True, "rating_avg": avg, "rating_count": count}


# ---------- Mises & victoire ----------

async def _require_active_account(user_id: str) -> dict:
    account = await ah.get_auction_account(user_id)
    if not ah.account_active(account):
        raise HTTPException(status_code=403,
                            detail="Un plan CREDI'SCOP-COOP'ACT actif est obligatoire pour coop'acter")
    return account


async def _live_auction(auction_id: str) -> dict:
    a = await ah.db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="COOP'ACT introuvable")
    if ah.effective_status(a) != "LIVE":
        raise HTTPException(status_code=409, detail="Ce COOP'ACT n'est pas en cours")
    return a


async def _deduct_credits(user_id: str, amount: int, label: str) -> bool:
    res = await ah.db.auction_accounts.update_one(
        {"user_id": user_id, "credits": {"$gte": amount}}, {"$inc": {"credits": -amount}})
    if res.modified_count == 0:
        return False
    await ah.db.auction_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "type": "SPEND",
        "amount": -amount, "label": label, "created_at": ah.now_utc().isoformat()})
    return True


async def _refund_credits(user_id: str, amount: int, label: str):
    await ah.db.auction_accounts.update_one({"user_id": user_id}, {"$inc": {"credits": amount}})
    await ah.db.auction_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "type": "REFUND",
        "amount": amount, "label": label, "created_at": ah.now_utc().isoformat()})


@auctions_member_router.post("/{auction_id}/bid")
async def place_bid(auction_id: str, user_id: str = Depends(get_current_user_id)):
    await _require_active_account(user_id)
    a = await _live_auction(auction_id)
    cost = int(a.get("bid_cost_credits") or 10)
    if not await _deduct_credits(user_id, cost, f"Coop'Act {a['reference']}"):
        raise HTTPException(status_code=402, detail="Crédits COOP'ACT insuffisants — rechargez votre plan")
    for _ in range(2):
        cur = float(a.get("current_price_eur") or a["value_eur"])
        new_price = max(float(a.get("floor_eur") or 0), round(cur - float(a["price_drop_eur"]), 2))
        res = await ah.db.auctions.update_one(
            {"id": auction_id, "status": "LIVE", "current_price_eur": cur},
            {"$set": {"current_price_eur": new_price}, "$inc": {"bids_count": 1}})
        if res.modified_count:
            await ah.db.auction_bids.insert_one({
                "id": str(uuid.uuid4()), "auction_id": auction_id, "user_id": user_id,
                "credits_spent": cost, "price_after_eur": new_price,
                "created_at": ah.now_utc().isoformat()})
            try:
                from auction_emails import check_price_alerts
                await check_price_alerts(auction_id)
            except Exception:
                pass
            return {"ok": True, "price_eur": new_price, "price_credits": ah.eur_to_credits(new_price),
                    "bids_count": a.get("bids_count", 0) + 1}
        a = await _live_auction(auction_id)
    await _refund_credits(user_id, cost, f"Mise non aboutie {a['reference']}")
    raise HTTPException(status_code=409, detail="Trop d'activité sur ce COOP'ACT — réessayez")


@auctions_member_router.post("/{auction_id}/accept")
async def accept_price(auction_id: str, user_id: str = Depends(get_current_user_id)):
    await _require_active_account(user_id)
    a = await _live_auction(auction_id)
    price_eur = round(float(a.get("current_price_eur") or a["value_eur"]), 2)
    price_credits = ah.eur_to_credits(price_eur)
    if not await _deduct_credits(user_id, price_credits, f"Prix accepté enchère {a['reference']}"):
        raise HTTPException(status_code=402,
                            detail=f"Il faut {price_credits} crédits pour accepter ce prix — rechargez votre plan")
    user = await ah.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1, "first_name": 1})
    winner = {"user_id": user_id, "email": user.get("email"),
              "name": user.get("contact_name") or user.get("first_name") or user.get("email"),
              "price_eur": price_eur, "price_credits": price_credits,
              "won_at": ah.now_utc().isoformat(),
              "pickup_token": uuid.uuid4().hex}
    res = await ah.db.auctions.update_one(
        {"id": auction_id, "status": "LIVE"},
        {"$set": {"status": "WON", "winner": winner}})
    if res.modified_count == 0:
        await _refund_credits(user_id, price_credits, f"Enchère déjà remportée {a['reference']}")
        raise HTTPException(status_code=409, detail="Trop tard — un autre membre vient de remporter ce COOP'ACT")
    from auction_emails import send_winner_email, notify_admin_win, notify_detaillant_win
    await send_winner_email({**a, "winner": winner})
    await notify_admin_win({**a, "winner": winner})
    await notify_detaillant_win({**a, "winner": winner})
    return {"ok": True, "won": True, "price_eur": price_eur, "price_credits": price_credits}


# ---------- Choix du gagnant : retrait LOLODRIVE ou livraison ----------

class FulfillmentBody(BaseModel):
    mode: str  # PICKUP | DELIVERY
    lolo_point_id: Optional[str] = None
    address: Optional[str] = None


@auctions_member_router.post("/{auction_id}/fulfillment")
async def choose_fulfillment(auction_id: str, body: FulfillmentBody,
                             user_id: str = Depends(get_current_user_id)):
    a = await ah.db.auctions.find_one({"id": auction_id, "status": "WON"}, {"_id": 0})
    if not a or (a.get("winner") or {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Réservé au gagnant de ce COOP'ACT")
    if body.mode not in ("PICKUP", "DELIVERY"):
        raise HTTPException(status_code=400, detail="mode: PICKUP ou DELIVERY")
    fulfillment = {"mode": body.mode, "chosen_at": ah.now_utc().isoformat()}
    if body.mode == "PICKUP":
        point = await ah.db.lolodrive_points.find_one({"id": body.lolo_point_id}, {"_id": 0, "id": 1, "name": 1})
        if not point:
            raise HTTPException(status_code=400, detail="Choisissez un point relais LOLODRIVE valide")
        fulfillment.update({"lolo_point_id": point["id"], "point_name": point["name"]})
    else:
        if not (body.address or "").strip():
            raise HTTPException(status_code=400, detail="Adresse de livraison requise")
        fulfillment["address"] = body.address.strip()[:300]
    await ah.db.auctions.update_one({"id": auction_id}, {"$set": {"fulfillment": fulfillment}})
    from auction_emails import notify_admin_fulfillment
    await notify_admin_fulfillment(a, fulfillment)
    return {"ok": True, "fulfillment": fulfillment}
