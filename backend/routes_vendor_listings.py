"""Vitrine des publications CommunityPlace du membre connecté (offres & demandes) + relance de lien de paiement."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id

logger = logging.getLogger(__name__)
vendor_listings_router = APIRouter(prefix="/api/vendor", tags=["Mes publications"])
db = None


def set_vendor_listings_database(database):
    global db
    db = database


async def _me(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    return user


@vendor_listings_router.get("/my-listings")
async def my_listings(user: dict = Depends(_me)):
    """Publications CommunityPlace du membre connecté, avec statut et paiement."""
    email = (user.get("email") or "").lower()
    items = await db.purchase_needs.find(
        {"email": email},
        {"_id": 0, "id": 1, "reference": 1, "product": 1, "quantity": 1, "territory": 1,
         "listing_type": 1, "status": 1, "created_at": 1, "assigned_vendor": 1, "assigned_role": 1,
         "communityplace": 1, "communityplace_fee_eur": 1, "communityplace_payment_status": 1,
         "communityplace_paid_at": 1, "vendor_price_eur": 1, "grouping_closed": 1},
    ).sort("created_at", -1).to_list(100)
    return {"listings": items, "count": len(items)}


@vendor_listings_router.post("/my-listings/{need_id}/pay-link")
async def my_listing_pay_link(need_id: str, user: dict = Depends(_me)):
    """Regénère un lien de paiement Stripe frais pour une publication impayée du membre."""
    email = (user.get("email") or "").lower()
    need = await db.purchase_needs.find_one({"id": need_id, "email": email})
    if not need:
        raise HTTPException(status_code=404, detail="Publication introuvable")
    if not need.get("communityplace") or need.get("communityplace_payment_status") != "PENDING":
        raise HTTPException(status_code=409, detail="Aucun paiement en attente pour cette publication")
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    fee_eur = float(need.get("communityplace_fee_eur") or 50)
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=email,
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(fee_eur * 100),
                     "product_data": {"name": f"Frais de publication CommunityPlace — {need['reference']} {need['product']}"}},
                     "quantity": 1}],
        metadata={"purchase_need_id": need_id, "kind": "COMMUNITYPLACE_FEE"},
        success_url=f"{base}/paiement/retour?session_id={{CHECKOUT_SESSION_ID}}&kind=COMMUNITYPLACE&ref={need['reference']}",
        cancel_url=f"{base}/?communityplace_cancelled=1",
    )
    await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "communityplace_checkout_id": session.id,
        "communityplace_paylink_at": datetime.now(timezone.utc).isoformat()}})
    return {"checkout_url": session.url, "fee_eur": fee_eur}
