"""Abonnements mensuels avec CPC inclus (Stripe LIVE, mode subscription).
CPC inclus : type SUBSCRIPTION_GRANT, validité 3 mois (expiration via cron cpc_purchases)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import stripe
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from lolodrive_helpers import require_admin
from cpc_ledger import add_cpc_movement
from vat import compute_vat

logger = logging.getLogger(__name__)

cpc_subs_router = APIRouter(prefix="/api/cpc/subscription", tags=["cpc-subscriptions"])
cpc_plans_admin_router = APIRouter(prefix="/api/admin/cpc/plans", tags=["cpc-plans-admin"])

db = None

DEFAULT_PLANS = [
    {"id": "cpc-plan-pro", "label": "Pro", "price_ht_cents": 4900, "monthly_cpc": 60},
    {"id": "cpc-plan-expert", "label": "Expert", "price_ht_cents": 11900, "monthly_cpc": 200},
    {"id": "cpc-plan-reseau", "label": "Réseau", "price_ht_cents": 24900, "monthly_cpc": 600},
]
INCLUDED_CPC_VALIDITY_MONTHS = 3


def set_cpc_subs_database(database):
    global db
    db = database


async def ensure_default_plans():
    for p in DEFAULT_PLANS:
        await db.cpc_plans.update_one(
            {"id": p["id"]},
            {"$setOnInsert": {**p, "active": True, "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True)


@cpc_subs_router.get("/plans")
async def list_plans():
    await ensure_default_plans()
    items = await db.cpc_plans.find({"active": True}, {"_id": 0}).sort("price_ht_cents", 1).to_list(20)
    return {"items": items}


@cpc_subs_router.get("/me")
async def my_subscription(user_id: str = Depends(get_current_user_id)):
    sub = await db.cpc_subscriptions.find_one(
        {"user_id": user_id, "status": {"$in": ["PENDING", "ACTIVE", "CANCELLING", "PAST_DUE"]}},
        {"_id": 0}, sort=[("created_at", -1)])
    return {"subscription": sub}


class SubCheckoutBody(BaseModel):
    plan_id: str
    origin_url: str


@cpc_subs_router.post("/checkout")
async def subscription_checkout(body: SubCheckoutBody, user_id: str = Depends(get_current_user_id)):
    from routes_cpc import _require_vendor, _user_country, _stripe_key
    user = await _require_vendor(user_id)
    plan = await db.cpc_plans.find_one({"id": body.plan_id, "active": True}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Formule introuvable")
    existing = await db.cpc_subscriptions.find_one(
        {"user_id": user_id, "status": {"$in": ["ACTIVE", "CANCELLING", "PAST_DUE"]}}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="Un abonnement CPC est déjà actif — résiliez-le avant de changer de formule")
    country = await _user_country(user)
    vat = compute_vat(plan["price_ht_cents"], country)
    origin = body.origin_url.rstrip("/")
    meta = {"kind": "CPC_SUBSCRIPTION", "user_id": user_id, "plan_id": plan["id"],
            "monthly_cpc": str(plan["monthly_cpc"]), "territory": country}
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="subscription", payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur", "unit_amount": vat["ttc_cents"],
                "recurring": {"interval": "month"},
                "product_data": {"name": f"Abonnement CPC {plan['label']} — {plan['monthly_cpc']} CPC/mois (service numérique O'SCOP)"},
            }, "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/vendor?tab=cpc&sub_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/vendor?tab=cpc&sub_cancelled=1",
        metadata=meta, subscription_data={"metadata": meta})
    now = datetime.now(timezone.utc).isoformat()
    await db.cpc_subscriptions.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "email": user.get("email"),
        "plan_id": plan["id"], "plan_label": plan["label"], "monthly_cpc": plan["monthly_cpc"],
        "price_ht_cents": plan["price_ht_cents"], "ttc_cents": vat["ttc_cents"], "country": country,
        "stripe_session_id": session.id, "stripe_subscription_id": None,
        "status": "PENDING", "created_at": now})
    return {"checkout_url": session.url, "session_id": session.id}


@cpc_subs_router.post("/cancel")
async def cancel_subscription(user_id: str = Depends(get_current_user_id)):
    from routes_cpc import _stripe_key
    sub = await db.cpc_subscriptions.find_one(
        {"user_id": user_id, "status": {"$in": ["ACTIVE", "PAST_DUE"]}}, {"_id": 0}, sort=[("created_at", -1)])
    if not sub or not sub.get("stripe_subscription_id"):
        raise HTTPException(status_code=404, detail="Aucun abonnement actif")
    stripe.api_base = "https://api.stripe.com"
    stripe.Subscription.modify(sub["stripe_subscription_id"], api_key=_stripe_key(), cancel_at_period_end=True)
    await db.cpc_subscriptions.update_one({"id": sub["id"]}, {"$set": {
        "status": "CANCELLING", "cancel_requested_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "status": "CANCELLING",
            "message": "Résiliation programmée à la fin de la période en cours — les CPC déjà crédités restent utilisables jusqu'à leur expiration."}


# ---------- Webhook (appelé par routes_payment après vérification de signature) ----------

def _invoice_meta(obj: dict) -> dict:
    return ((obj.get("subscription_details") or {}).get("metadata")
            or ((obj.get("parent") or {}).get("subscription_details") or {}).get("metadata")
            or {})


async def handle_cpc_subscription_event(event: dict) -> bool:
    """Traite les événements Stripe d'abonnement CPC. Retourne True si l'événement était concerné."""
    etype = event["type"]
    obj = event["data"]["object"]
    if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
        if (obj.get("metadata") or {}).get("kind") != "CPC_SUBSCRIPTION":
            return False
        await db.cpc_subscriptions.update_one({"stripe_session_id": obj["id"]}, {"$set": {
            "status": "ACTIVE", "stripe_subscription_id": obj.get("subscription"),
            "stripe_customer_id": obj.get("customer"),
            "activated_at": datetime.now(timezone.utc).isoformat()}})
        return True
    if etype == "invoice.paid":
        meta = _invoice_meta(obj)
        if meta.get("kind") != "CPC_SUBSCRIPTION":
            return False
        user_id, plan_id = meta["user_id"], meta["plan_id"]
        monthly = int(meta.get("monthly_cpc", 0))
        plan = await db.cpc_plans.find_one({"id": plan_id}, {"_id": 0}) or {"label": plan_id}
        entry = await add_cpc_movement(
            user_id, "SUBSCRIPTION_GRANT", monthly,
            idempotency_key=f"subinv:{obj['id']}",
            reason=f"Abonnement {plan['label']} — {monthly} CPC inclus (validité {INCLUDED_CPC_VALIDITY_MONTHS} mois)",
            pack_id=plan_id, stripe_event_id=event.get("id"))
        if entry:
            now = datetime.now(timezone.utc)
            await db.cpc_purchases.insert_one({
                "id": f"subcpc-{obj['id']}", "user_id": user_id, "email": obj.get("customer_email"),
                "pack_id": plan_id, "pack_label": f"Abonnement {plan['label']} (CPC inclus)",
                "credits": monthly, "price_ht_cents": 0, "vat_rate": 0, "vat_cents": 0, "ttc_cents": 0,
                "country": meta.get("territory"), "validity_months": INCLUDED_CPC_VALIDITY_MONTHS,
                "expires_at": (now + relativedelta(months=INCLUDED_CPC_VALIDITY_MONTHS)).isoformat(),
                "stripe_session_id": None, "stripe_invoice_id": obj["id"],
                "status": "SETTLED", "settled_at": now.isoformat(), "created_at": now.isoformat()})
            await db.cpc_subscriptions.update_one(
                {"user_id": user_id, "status": {"$in": ["PENDING", "ACTIVE", "PAST_DUE", "CANCELLING"]}},
                {"$set": {"last_invoice_id": obj["id"], "last_credited_at": now.isoformat()}})
            logger.info("Abonnement CPC : +%d CPC crédités pour %s (facture %s)", monthly, user_id, obj["id"])
        return True
    if etype == "invoice.payment_failed":
        meta = _invoice_meta(obj)
        if meta.get("kind") != "CPC_SUBSCRIPTION":
            return False
        await db.cpc_subscriptions.update_one(
            {"user_id": meta["user_id"], "status": {"$in": ["ACTIVE", "CANCELLING"]}},
            {"$set": {"status": "PAST_DUE", "past_due_at": datetime.now(timezone.utc).isoformat()}})
        return True
    if etype == "customer.subscription.deleted":
        if (obj.get("metadata") or {}).get("kind") != "CPC_SUBSCRIPTION":
            return False
        await db.cpc_subscriptions.update_one({"stripe_subscription_id": obj["id"]}, {"$set": {
            "status": "CANCELLED", "cancelled_at": datetime.now(timezone.utc).isoformat()}})
        return True
    return False


# ---------- Admin ----------

class PlanBody(BaseModel):
    label: str
    price_ht_cents: int
    monthly_cpc: int
    active: bool = True


@cpc_plans_admin_router.get("")
async def admin_plans(admin: dict = Depends(require_admin)):
    await ensure_default_plans()
    items = await db.cpc_plans.find({}, {"_id": 0}).sort("price_ht_cents", 1).to_list(20)
    subs = await db.cpc_subscriptions.find({"status": {"$in": ["ACTIVE", "CANCELLING", "PAST_DUE"]}},
                                           {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items, "subscriptions": subs}


@cpc_plans_admin_router.put("/{plan_id}")
async def update_plan(plan_id: str, body: PlanBody, admin: dict = Depends(require_admin)):
    """Sans effet rétroactif : les abonnements en cours conservent leur prix Stripe."""
    if body.price_ht_cents <= 0 or body.monthly_cpc <= 0:
        raise HTTPException(status_code=400, detail="Valeurs invalides")
    res = await db.cpc_plans.update_one({"id": plan_id}, {"$set": {
        **body.dict(), "updated_by": admin.get("email"),
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Formule introuvable")
    return {"ok": True}
