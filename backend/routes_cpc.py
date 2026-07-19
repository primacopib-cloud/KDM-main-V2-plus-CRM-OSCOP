"""CPC — Crédits de Participation aux Consultations : packs, achat Stripe (webhook only), registre, factures.
Les CPC sont des unités de service O'SCOP : nominatifs, non transférables, non convertibles, jamais un moyen de paiement."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import stripe
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from auth import get_current_user_id
from cpc_ledger import add_cpc_movement, get_cpc_account, freeze_cpc_account
from vat import compute_vat

logger = logging.getLogger(__name__)

cpc_router = APIRouter(prefix="/api/cpc", tags=["cpc"])

db = None

DEFAULT_PACKS = [
    {"id": "cpc-pack-50", "label": "Pack Découverte", "credits": 50, "price_ht_cents": 2500},
    {"id": "cpc-pack-150", "label": "Pack Régulier", "credits": 150, "price_ht_cents": 6000},
    {"id": "cpc-pack-500", "label": "Pack Centrale", "credits": 500, "price_ht_cents": 15000},
]


def set_cpc_database(database):
    global db
    db = database


def _stripe_key() -> str:
    from stripe_accounts import get_stripe_key
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=503, detail="Stripe O'SCOP non configuré")
    return key


async def ensure_default_packs():
    for p in DEFAULT_PACKS:
        await db.cpc_packs.update_one(
            {"id": p["id"]},
            {"$setOnInsert": {**p, "active": True, "validity_months": 12,
                              "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True)


async def _require_vendor(user_id: str) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "email": 1, "role": 1,
                                                     "name": 1, "full_name": 1, "country": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if (user.get("role") or "").lower() == "vendor":
        return user
    vendor = await db.vendors.find_one({"email": user.get("email")}, {"_id": 0, "id": 1})
    if not vendor:
        raise HTTPException(status_code=403, detail="Réservé aux Vendeurs Pro actifs")
    return user


async def _user_country(user: dict) -> str:
    if user.get("country"):
        return user["country"]
    ob = await db.vendor_onboarding.find_one({"email": user.get("email"), "status": {"$in": ["PAID", "SIGNED", "ACTIVATED"]}},
                                             {"_id": 0, "country": 1})
    return (ob or {}).get("country") or "GP"


# ---------- Vendeur ----------

@cpc_router.get("/packs")
async def list_packs():
    await ensure_default_packs()
    items = await db.cpc_packs.find({"active": True}, {"_id": 0}).sort("credits", 1).to_list(20)
    return {"items": items}


@cpc_router.get("/me")
async def my_cpc(user_id: str = Depends(get_current_user_id)):
    acc = await get_cpc_account(user_id)
    return {"balance": acc.get("cpc_balance", 0), "status": acc.get("status", "ACTIF")}


@cpc_router.get("/me/ledger")
async def my_ledger(user_id: str = Depends(get_current_user_id)):
    items = await db.cpc_ledger.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


class CheckoutBody(BaseModel):
    pack_id: str
    origin_url: str


@cpc_router.post("/checkout")
async def cpc_checkout(body: CheckoutBody, user_id: str = Depends(get_current_user_id)):
    user = await _require_vendor(user_id)
    pack = await db.cpc_packs.find_one({"id": body.pack_id, "active": True}, {"_id": 0})
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    country = await _user_country(user)
    vat = compute_vat(pack["price_ht_cents"], country)
    pid = str(uuid.uuid4())
    origin = body.origin_url.rstrip("/")
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="payment", payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur", "unit_amount": vat["ttc_cents"],
                "product_data": {"name": f"CPC — {pack['label']} ({pack['credits']} crédits) — service numérique O'SCOP"},
            }, "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/vendor?tab=cpc&cpc_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/vendor?tab=cpc&cpc_cancelled=1",
        metadata={"kind": "CPC_PACK", "user_id": user_id, "pack_id": pack["id"],
                  "credits": str(pack["credits"]), "territory": country, "internal_ref": pid})
    now = datetime.now(timezone.utc)
    await db.cpc_purchases.insert_one({
        "id": pid, "user_id": user_id, "email": user.get("email"),
        "pack_id": pack["id"], "pack_label": pack["label"], "credits": pack["credits"],
        "price_ht_cents": pack["price_ht_cents"], "vat_rate": vat["rate"],
        "vat_cents": vat["vat_cents"], "ttc_cents": vat["ttc_cents"], "country": country,
        "validity_months": pack.get("validity_months", 12),
        "expires_at": (now + relativedelta(months=pack.get("validity_months", 12))).isoformat(),
        "stripe_session_id": session.id, "status": "PENDING", "created_at": now.isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


@cpc_router.get("/purchase-status/{session_id}")
async def purchase_status(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Statut d'un achat — le crédit n'a lieu QUE via le webhook Stripe, jamais ici."""
    p = await db.cpc_purchases.find_one({"stripe_session_id": session_id, "user_id": user_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Achat introuvable")
    acc = await get_cpc_account(user_id)
    return {"status": p["status"], "credits": p["credits"], "balance": acc.get("cpc_balance", 0),
            "invoice_number": p.get("invoice_number")}


@cpc_router.get("/me/invoices")
async def my_cpc_invoices(user_id: str = Depends(get_current_user_id)):
    items = await db.cpc_invoices.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).limit(100).to_list(100)
    return {"items": items}


@cpc_router.get("/me/invoices/{number}/pdf")
async def my_cpc_invoice_pdf(number: str, user_id: str = Depends(get_current_user_id)):
    inv = await db.cpc_invoices.find_one({"number": number, "user_id": user_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    from vendor_invoice_pdf import build_invoice_pdf
    return Response(content=build_invoice_pdf(inv), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'})


# ---------- Webhook Stripe (appelé par routes_payment après vérification de signature) ----------

async def _next_cpc_invoice_number() -> str:
    from pymongo import ReturnDocument
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"cpc_invoice_{year}"}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER)
    return f"FACT-CPC-{year}-{doc['seq']:04d}"


async def _issue_cpc_invoice(purchase: dict) -> Optional[str]:
    try:
        from vat import vat_label
        user = await db.users.find_one({"id": purchase["user_id"]}, {"_id": 0, "name": 1, "full_name": 1, "company": 1})
        vendor = await db.vendors.find_one({"email": purchase["email"]}, {"_id": 0, "company_name": 1, "siret": 1})
        number = await _next_cpc_invoice_number()
        inv = {
            "number": number, "ob_id": purchase["id"], "kind": "cpc_pack", "user_id": purchase["user_id"],
            "label": f"{purchase['pack_label']} — {purchase['credits']} CPC (service numérique O'SCOP)",
            "company": (vendor or {}).get("company_name") or (user or {}).get("company") or (user or {}).get("full_name") or purchase["email"],
            "legal_form": None, "siret": (vendor or {}).get("siret"),
            "country": purchase["country"], "email": purchase["email"],
            "ht_cents": purchase["price_ht_cents"], "vat_rate": purchase["vat_rate"],
            "vat_cents": purchase["vat_cents"], "ttc_cents": purchase["ttc_cents"],
            "vat_label": vat_label(purchase["country"]), "ext_ref": purchase["stripe_session_id"],
            "date": datetime.now(timezone.utc).isoformat(),
        }
        await db.cpc_invoices.insert_one({**inv})
        try:
            import base64
            from vendor_invoice_pdf import build_invoice_pdf
            from brevo_service import send_email
            pdf = build_invoice_pdf(inv)
            await send_email(
                to_email=purchase["email"], to_name=inv["company"],
                subject=f"Votre facture {number} — Pack CPC O'SCOP",
                html_content=f"<p>Bonjour,</p><p>Votre achat de <strong>{purchase['credits']} CPC</strong> est confirmé. "
                             f"Facture <strong>{number}</strong> ci-jointe ({purchase['ttc_cents'] / 100:.2f} € TTC).</p>"
                             f"<p style='color:#777;font-size:12px;'>Les CPC sont des unités d'accès aux services numériques "
                             f"de consultation O'SCOP — non transférables, non convertibles en euros.</p>",
                tags=["cpc-invoice"],
                attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{number}.pdf"}])
        except Exception as exc:
            logger.warning("Email facture CPC %s : %s", number, exc)
        return number
    except Exception as exc:
        logger.warning("Facture CPC pour achat %s : %s", purchase.get("id"), exc)
        return None


async def handle_cpc_stripe_event(event: dict) -> bool:
    """Traite les événements Stripe CPC. Retourne True si l'événement concernait les CPC."""
    etype = event["type"]
    obj = event["data"]["object"]
    if etype == "checkout.session.completed":
        if (obj.get("metadata") or {}).get("kind") != "CPC_PACK":
            return False
        if obj.get("payment_status") != "paid":
            return True
        purchase = await db.cpc_purchases.find_one({"stripe_session_id": obj["id"]}, {"_id": 0})
        if not purchase:
            logger.warning("Webhook CPC : achat introuvable pour session %s", obj["id"])
            return True
        entry = await add_cpc_movement(
            purchase["user_id"], "PACK_PURCHASE", purchase["credits"],
            idempotency_key=f"sess:{obj['id']}:credit",
            reason=f"Achat {purchase['pack_label']} ({purchase['credits']} CPC)",
            pack_id=purchase["pack_id"], stripe_session_id=obj["id"], stripe_event_id=event.get("id"))
        if entry:
            number = await _issue_cpc_invoice(purchase)
            await db.cpc_purchases.update_one({"id": purchase["id"]}, {"$set": {
                "status": "SETTLED", "settled_at": datetime.now(timezone.utc).isoformat(),
                "payment_intent": obj.get("payment_intent"), "invoice_number": number}})
        return True
    if etype == "checkout.session.expired":
        if (obj.get("metadata") or {}).get("kind") != "CPC_PACK":
            return False
        await db.cpc_purchases.update_one({"stripe_session_id": obj["id"], "status": "PENDING"},
                                          {"$set": {"status": "EXPIRED"}})
        return True
    if etype in ("charge.refunded", "charge.dispute.created"):
        pi = obj.get("payment_intent")
        if not pi:
            return False
        purchase = await db.cpc_purchases.find_one({"payment_intent": pi, "status": "SETTLED"}, {"_id": 0})
        if not purchase:
            return False
        acc = await get_cpc_account(purchase["user_id"])
        qty = min(acc.get("cpc_balance", 0), purchase["credits"])
        label = "Remboursement" if etype == "charge.refunded" else "Contestation (chargeback)"
        if qty > 0:
            await add_cpc_movement(
                purchase["user_id"], "STRIPE_REVERSAL", -qty,
                idempotency_key=f"evt:{event.get('id')}:reversal",
                reason=f"{label} Stripe — annulation des CPC non consommés ({purchase['pack_label']})",
                pack_id=purchase["pack_id"], stripe_event_id=event.get("id"), allow_frozen=True)
        if qty < purchase["credits"]:
            await freeze_cpc_account(purchase["user_id"],
                                     f"{label} : {purchase['credits'] - qty} CPC déjà consommés — régularisation requise")
        await db.cpc_purchases.update_one({"id": purchase["id"]}, {"$set": {
            "status": "REVERSED", "reversed_at": datetime.now(timezone.utc).isoformat(), "reversal_type": etype}})
        return True
    return False
