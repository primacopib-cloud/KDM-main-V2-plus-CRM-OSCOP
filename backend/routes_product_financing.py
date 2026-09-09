"""Financement produits investisseurs : inscription superadmin (marge O'SCOP), paiement Stripe, mention « Vendu et facturé par O'SCOP »."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lolodrive_helpers import require_admin
from auth import get_current_user_id

logger = logging.getLogger(__name__)
financing_router = APIRouter(prefix="/api", tags=["Financement produits"])
db = None


def set_product_financing_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _investor(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    role = (user.get("role") or "").upper()
    if not (user.get("is_investor") or user.get("is_admin") or role in {"SUPER_ADMIN", "ADMIN"}):
        raise HTTPException(status_code=403, detail="Réservé aux investisseurs")
    return user


class FinancingProductCreate(BaseModel):
    product_id: str | None = None
    name: str | None = None
    base_price_eur: float = Field(gt=0, le=10_000_000)
    margin_percent: float = Field(ge=0, le=500)
    description: str | None = None


class FinancingProductUpdate(BaseModel):
    base_price_eur: float | None = Field(default=None, gt=0, le=10_000_000)
    margin_percent: float | None = Field(default=None, ge=0, le=500)


def _total(base: float, margin: float) -> float:
    return round(base * (1 + margin / 100), 2)


@financing_router.get("/admin/financing-products/catalog")
async def financing_catalog_products(_: dict = Depends(require_admin)):
    """Produits du catalogue sélectionnables pour le financement."""
    items = await db.products.find(
        {"status": "ACTIVE"}, {"_id": 0, "id": 1, "name": 1, "sku": 1}).sort("name", 1).to_list(200)
    return {"products": items}


@financing_router.post("/admin/financing-products")
async def create_financing_product(body: FinancingProductCreate, admin: dict = Depends(require_admin)):
    """Le superadmin inscrit un produit au financement avec sa marge bénéficiaire."""
    name, sku = body.name, None
    if body.product_id:
        prod = await db.products.find_one({"id": body.product_id}, {"_id": 0, "name": 1, "sku": 1})
        if not prod:
            raise HTTPException(status_code=404, detail="Produit catalogue introuvable")
        name, sku = prod["name"], prod.get("sku")
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Nom du produit requis")
    doc = {
        "id": str(uuid.uuid4()),
        "reference": f"FIN-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}",
        "product_id": body.product_id, "name": name.strip(), "sku": sku,
        "description": body.description,
        "base_price_eur": round(body.base_price_eur, 2),
        "margin_percent": round(body.margin_percent, 2),
        "total_price_eur": _total(body.base_price_eur, body.margin_percent),
        "status": "OPEN", "created_by": admin.get("email"), "created_at": _now(),
    }
    await db.financing_products.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@financing_router.get("/admin/financing-products")
async def list_financing_products_admin(_: dict = Depends(require_admin)):
    items = await db.financing_products.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    pending = [i for i in items if i.get("status") == "PENDING_PAYMENT" and i.get("stripe_session_id")][:10]
    if pending:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        for i in pending:
            try:
                s = stripe.checkout.Session.retrieve(i["stripe_session_id"])
                if s.payment_status == "paid":
                    await _mark_paid(i["id"], i.get("pending_by"))
                    i["status"] = "PAID"
            except Exception as exc:
                logger.warning("Check paiement financement %s : %s", i["id"], exc)
    return {"products": items}


@financing_router.put("/admin/financing-products/{fp_id}")
async def update_financing_product(fp_id: str, body: FinancingProductUpdate, admin: dict = Depends(require_admin)):
    """Ajuste prix / marge bénéficiaire — uniquement avant paiement."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if fp.get("status") == "PAID":
        raise HTTPException(status_code=409, detail="Déjà payé — la marge ne peut plus être modifiée")
    base = body.base_price_eur if body.base_price_eur is not None else fp["base_price_eur"]
    margin = body.margin_percent if body.margin_percent is not None else fp["margin_percent"]
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "base_price_eur": round(base, 2), "margin_percent": round(margin, 2),
        "total_price_eur": _total(base, margin),
        "updated_by": admin.get("email"), "updated_at": _now()}})
    return await db.financing_products.find_one({"id": fp_id}, {"_id": 0})


@financing_router.delete("/admin/financing-products/{fp_id}")
async def delete_financing_product(fp_id: str, _: dict = Depends(require_admin)):
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if fp.get("status") == "PAID":
        raise HTTPException(status_code=409, detail="Déjà payé — suppression impossible")
    await db.financing_products.delete_one({"id": fp_id})
    return {"ok": True}


@financing_router.get("/investor/financing-products")
async def list_financing_products_investor(user: dict = Depends(_investor)):
    items = await db.financing_products.find(
        {}, {"_id": 0, "created_by": 0, "stripe_session_id": 0}).sort("created_at", -1).to_list(200)
    me = (user.get("email") or "").lower()
    for i in items:
        i["is_mine"] = (i.get("paid_by") or i.get("pending_by") or "").lower() == me
        if i.get("status") != "PAID":
            i.pop("paid_by", None)
        i.pop("pending_by", None)
    return {"products": items}


@financing_router.post("/investor/financing-products/{fp_id}/pay")
async def pay_financing_product(fp_id: str, user: dict = Depends(_investor)):
    """L'investisseur paie le produit inscrit au financement (Stripe)."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if fp.get("status") == "PAID":
        raise HTTPException(status_code=409, detail="Produit déjà payé — vendu et facturé par O'SCOP")
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=user.get("email"),
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(round(fp["total_price_eur"] * 100)),
                     "product_data": {"name": f"Financement produit — {fp['reference']} {fp['name']}"}},
                     "quantity": 1}],
        metadata={"financing_product_id": fp_id, "investor_email": user.get("email") or "", "kind": "PRODUCT_FINANCING"},
        success_url=f"{base}/espace-investisseur?finprod_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/espace-investisseur?finprod_cancelled=1",
    )
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "status": "PENDING_PAYMENT", "stripe_session_id": session.id,
        "pending_by": (user.get("email") or "").lower(), "pending_at": _now()}})
    return {"checkout_url": session.url, "session_id": session.id, "total_price_eur": fp["total_price_eur"]}


async def _mark_paid(fp_id: str, investor_email: str | None):
    """Marque payé (idempotent) + facture acquittée O'SCOP par email."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp or fp.get("status") == "PAID":
        return
    email = (investor_email or fp.get("pending_by") or "").lower()
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "status": "PAID", "paid_at": _now(), "paid_by": email}})
    if not email:
        return
    try:
        from communityplace_invoice import build_financing_invoice_pdf
        from brevo_service import send_email, _wrap_html
        import base64
        fp = await db.financing_products.find_one({"id": fp_id}, {"_id": 0})
        pdf = build_financing_invoice_pdf(fp)
        await send_email(
            to_email=email, to_name=None,
            subject=f"🧾 Facture acquittée O'SCOP — financement {fp['reference']} ({fp['name']})",
            html_content=_wrap_html("Facture acquittée", (
                "<p style='font-size:14px;'>Bonjour,</p>"
                f"<p>Votre paiement du financement <b>{fp['reference']} — {fp['name']}</b> "
                f"({fp['total_price_eur']:.2f} €) est confirmé. Ce produit est désormais "
                "<b>vendu et facturé par O'SCOP</b>.</p>"
                "<p>Vous trouverez ci-joint votre <b>facture acquittée</b>. Merci de votre confiance 🤝</p>")),
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"facture-{fp['reference']}.pdf"}],
            tags=["financing-invoice"])
    except Exception as e:
        logger.warning("Facture financement non envoyée : %s", e)


@financing_router.get("/investor/financing-products/checkout-status/{session_id}")
async def financing_checkout_status(session_id: str, user: dict = Depends(_investor)):
    fp = await db.financing_products.find_one({"stripe_session_id": session_id}, {"_id": 0})
    if not fp:
        raise HTTPException(status_code=404, detail="Session inconnue")
    if fp.get("status") != "PAID":
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid":
                await _mark_paid(fp["id"], (s.get("metadata") or {}).get("investor_email"))
                fp = await db.financing_products.find_one({"stripe_session_id": session_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("Statut checkout financement : %s", exc)
    return {"status": fp.get("status"), "reference": fp.get("reference"), "name": fp.get("name"),
            "total_price_eur": fp.get("total_price_eur")}


@financing_router.post("/public/financing-products/webhook")
async def financing_webhook(payload: dict):
    """Webhook Stripe : checkout.session.completed → produit payé + facture acquittée."""
    if payload.get("type") != "checkout.session.completed":
        return {"received": True}
    obj = (payload.get("data") or {}).get("object") or {}
    fp_id = (obj.get("metadata") or {}).get("financing_product_id")
    if fp_id and obj.get("payment_status") == "paid":
        await _mark_paid(fp_id, (obj.get("metadata") or {}).get("investor_email"))
    return {"received": True}
