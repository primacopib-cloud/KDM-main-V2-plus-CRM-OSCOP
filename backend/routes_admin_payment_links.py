"""Liens de paiement Stripe personnalisés créés par le super admin — /api/admin/payment-links."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from admin_guard import require_admin
from auth import get_current_user_id
from stripe_accounts import get_stripe_key

logger = logging.getLogger(__name__)

payment_links_router = APIRouter(prefix="/api/admin/payment-links", tags=["Admin Payment Links"])

db = None


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)

ACCOUNT_TYPES = {
    "VENDOR_PRO": "Adhésion Vendeur Pro",
    "BUYER_PRO": "Adhésion Acheteur Pro",
    "SPONSOR": "Sponsoring",
}


def set_payment_links_database(database) -> None:
    global db
    db = database


def _stripe_key() -> str:
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=500, detail="Clé Stripe non configurée")
    stripe.api_base = "https://api.stripe.com"
    return key


class CreateLinkPayload(BaseModel):
    email: EmailStr
    amount_eur: float = Field(..., gt=0)
    account_type: str
    description: Optional[str] = None


STRIPE_MAX_CENTS = 99_999_999  # 999 999,99 € — plafond Stripe par transaction


@payment_links_router.post("")
async def create_payment_link(payload: CreateLinkPayload, admin: dict = Depends(_admin)):
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Type de compte invalide (VENDOR_PRO, BUYER_PRO, SPONSOR)")
    amount_cents = int(round(payload.amount_eur * 100))
    if amount_cents > STRIPE_MAX_CENTS:
        raise HTTPException(
            status_code=400,
            detail="Montant maximum Stripe : 999 999,99 € par lien. Pour un total supérieur (ex : 1 000 000 €), créez plusieurs liens.")
    key = _stripe_key()
    label = ACCOUNT_TYPES[payload.account_type]
    product_name = f"KDMARCHÉ × O'SCOP — {label}" + (f" — {payload.description.strip()}" if payload.description else "")
    link_id = str(uuid.uuid4())
    try:
        price = stripe.Price.create(
            api_key=key, currency="eur", unit_amount=amount_cents,
            product_data={"name": product_name})
        plink = stripe.PaymentLink.create(
            api_key=key,
            line_items=[{"price": price.id, "quantity": 1}],
            restrictions={"completed_sessions": {"limit": 1}},
            metadata={"kind": "ADMIN_PAYMENT_LINK", "link_db_id": link_id,
                      "account_type": payload.account_type, "email": payload.email})
    except stripe.error.StripeError as exc:
        logger.error("Création lien Stripe échouée : %s", exc)
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {getattr(exc, 'user_message', None) or str(exc)}")
    url = f"{plink.url}?prefilled_email={quote(payload.email)}"
    doc = {
        "id": link_id, "email": payload.email, "amount_cents": amount_cents,
        "account_type": payload.account_type, "description": payload.description,
        "stripe_payment_link_id": plink.id, "url": url, "status": "pending",
        "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_payment_links.insert_one({**doc})
    logger.info("Lien de paiement admin créé : %s € pour %s (%s)", payload.amount_eur, payload.email, label)
    return doc


@payment_links_router.get("")
async def list_payment_links(_: dict = Depends(_admin)):
    links = await db.admin_payment_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"links": links, "account_types": ACCOUNT_TYPES}


@payment_links_router.post("/{link_id}/refresh")
async def refresh_payment_link(link_id: str, _: dict = Depends(_admin)):
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    if link["status"] == "paid":
        return link
    key = _stripe_key()
    try:
        sessions = stripe.checkout.Session.list(api_key=key, payment_link=link["stripe_payment_link_id"], limit=5)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {exc}")
    paid = next((s for s in sessions.data if s.payment_status == "paid"), None)
    if paid:
        await db.admin_payment_links.update_one(
            {"id": link_id},
            {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat(),
                      "stripe_session_id": paid.id}})
        link["status"] = "paid"
    return link


@payment_links_router.post("/{link_id}/deactivate")
async def deactivate_payment_link(link_id: str, _: dict = Depends(_admin)):
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    key = _stripe_key()
    try:
        stripe.PaymentLink.modify(link["stripe_payment_link_id"], api_key=key, active=False)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {exc}")
    await db.admin_payment_links.update_one({"id": link_id}, {"$set": {"status": "deactivated"}})
    return {"status": "SUCCESS"}
