"""Checkout O'SCOP direct : commande client + facture O'SCOP + encaissement Stripe O'SCOP."""
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from stripe_accounts import get_stripe_key

logger = logging.getLogger(__name__)
oscop_checkout_router = APIRouter(prefix="/api/oscop-checkout", tags=["Checkout O'SCOP"])
db = None


def set_oscop_checkout_database(database):
    global db
    db = database


OSCOP_SELLER = "SCIC SAS OBJECTIF SCOP OUTREMER"
FORBIDDEN_METHODS = {"CREDISCOP", "CREDI_SCOP", "SERVICE_CREDITS"}


class SessionCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10000)
    include_logistics: bool = False
    customer_email: EmailStr
    customer_name: str
    origin_url: str
    payment_method: str = "CARD"


async def next_invoice_number() -> str:
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"oscop_invoice_{year}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return f"FAC-OSCOP-{year}-{doc['seq']:04d}"


async def _get_offer(product_id: str) -> dict:
    prod = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not prod:
        prod = await db.catalog_products.find_one({"id": product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if prod.get("sale_model") != "OSCOP_DIRECT_RESALE":
        raise HTTPException(status_code=409, detail="Cette offre n'est pas vendue par O'SCOP")
    if not prod.get("oscop_price_ht_cents"):
        raise HTTPException(status_code=409, detail="Prix de vente O'SCOP non défini sur cette offre")
    return prod


@oscop_checkout_router.get("/offer/{product_id}")
async def get_oscop_offer(product_id: str):
    prod = await _get_offer(product_id)
    return {
        "product_id": product_id,
        "name": prod.get("name"),
        "seller": OSCOP_SELLER,
        "price_ht_cents": prod["oscop_price_ht_cents"],
        "vat_rate": prod.get("oscop_vat_rate", 8.5),
        "logistics_available": bool(prod.get("oscop_logistics_available")),
        "logistics_price_ht_cents": prod.get("oscop_logistics_price_ht_cents", 0),
        "cgv_url": "/conditions-vente-oscop",
    }


@oscop_checkout_router.post("/session")
async def create_session(payload: SessionCreate):
    if payload.payment_method.upper() in FORBIDDEN_METHODS:
        raise HTTPException(status_code=409, detail="CREDI'SCOP-I ne peut jamais servir à payer des produits ou de la logistique")
    prod = await _get_offer(payload.product_id)
    goods_ht = prod["oscop_price_ht_cents"] * payload.quantity
    logistics_ht = 0
    if payload.include_logistics:
        if not prod.get("oscop_logistics_available"):
            raise HTTPException(status_code=409, detail="Logistique LOGI'SCOP non disponible sur cette offre")
        logistics_ht = int(prod.get("oscop_logistics_price_ht_cents", 0))
    vat_rate = float(prod.get("oscop_vat_rate", 8.5))
    total_ht = goods_ht + logistics_ht
    vat_cents = round(total_ht * vat_rate / 100)
    total_ttc = total_ht + vat_cents

    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=500, detail="Compte Stripe O'SCOP non configuré")
    line_items = [{
        "price_data": {"currency": "eur", "unit_amount": prod["oscop_price_ht_cents"] + round(prod["oscop_price_ht_cents"] * vat_rate / 100),
                       "product_data": {"name": f"{prod.get('name')} — vendu par O'SCOP (TTC)"}},
        "quantity": payload.quantity,
    }]
    if logistics_ht:
        line_items.append({
            "price_data": {"currency": "eur", "unit_amount": logistics_ht + round(logistics_ht * vat_rate / 100),
                           "product_data": {"name": "Logistique intégrée LOGI'SCOP (TTC)"}},
            "quantity": 1,
        })
    try:
        session = stripe.checkout.Session.create(
            api_key=key,
            mode="payment",
            line_items=line_items,
            customer_email=payload.customer_email,
            success_url=f"{payload.origin_url}/oscop-checkout/retour?order_id={order_id}",
            cancel_url=f"{payload.origin_url}/catalogue",
            metadata={"oscop_order_id": order_id, "seller": "OSCOP"},
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {getattr(exc, 'user_message', None) or str(exc)}")

    order = {
        "id": order_id,
        "order_number": f"CMD-OSCOP-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}",
        "sale_model": "OSCOP_DIRECT_RESALE",
        "seller_entity": OSCOP_SELLER,
        "invoice_issuer": OSCOP_SELLER,
        "payment_recipient": OSCOP_SELLER,
        "product_id": payload.product_id,
        "product_name": prod.get("name"),
        "quantity": payload.quantity,
        "include_logistics": payload.include_logistics,
        "goods_ht_cents": goods_ht,
        "logistics_ht_cents": logistics_ht,
        "vat_rate": vat_rate,
        "vat_cents": vat_cents,
        "total_ttc_cents": total_ttc,
        "customer_email": payload.customer_email,
        "customer_name": payload.customer_name,
        "stripe_session_id": session.id,
        "status": "pending_payment",
        "invoice_number": None,
        "roles_snapshot": {
            "seller": OSCOP_SELLER, "invoicer": OSCOP_SELLER, "collector": OSCOP_SELLER,
            "logistics_operator": "LOGI'SCOP (établissement de la SCIC SAS OBJECTIF SCOP OUTREMER)" if payload.include_logistics else "Client",
            "immutable": True, "created_at": now.isoformat(),
        },
        "created_at": now.isoformat(),
    }
    await db.oscop_client_orders.insert_one(dict(order))
    return {"order_id": order_id, "checkout_url": session.url,
            "total_ttc_cents": total_ttc, "goods_ht_cents": goods_ht, "logistics_ht_cents": logistics_ht}


@oscop_checkout_router.get("/status/{order_id}")
async def get_order_status(order_id: str):
    order = await db.oscop_client_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] == "pending_payment":
        key = get_stripe_key("oscop")
        try:
            session = stripe.checkout.Session.retrieve(order["stripe_session_id"], api_key=key)
        except stripe.error.StripeError:
            session = None
        if session and session.payment_status == "paid":
            invoice_number = await next_invoice_number()
            now = datetime.now(timezone.utc).isoformat()
            await db.oscop_client_orders.update_one(
                {"id": order_id},
                {"$set": {"status": "paid", "invoice_number": invoice_number, "paid_at": now,
                          "psp_reference": session.payment_intent}})
            order.update({"status": "paid", "invoice_number": invoice_number, "paid_at": now})
    return order
