"""Besoins d'achat visiteurs : dépôt public, assignation vendeur, CommunityPlace."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
purchase_needs_router = APIRouter(prefix="/api", tags=["Besoins d'achat"])
db = None


def set_purchase_needs_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc).isoformat()


class PurchaseNeedCreate(BaseModel):
    company: str = Field(min_length=2)
    contact_name: str = Field(min_length=2)
    email: EmailStr
    phone: str = Field(min_length=6)
    territory: str
    product: str = Field(min_length=3)
    quantity: str
    budget_eur: float | None = None
    deadline: str | None = None
    description: str | None = None


@purchase_needs_router.post("/public/purchase-needs")
async def create_purchase_need(body: PurchaseNeedCreate):
    now = datetime.now(timezone.utc)
    ref = f"BA-{now.strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"
    doc = {"id": str(uuid.uuid4()), "reference": ref, **body.model_dump(), "status": "NEW",
           "assigned_vendor": None, "communityplace": False, "created_at": _now()}
    await db.purchase_needs.insert_one(dict(doc))
    try:
        from brevo_service import send_email, _wrap_html
        import os
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        await send_email(
            to_email=team, to_name=None,
            subject=f"🛒 Nouveau besoin d'achat {ref} — {body.product} ({body.company})",
            html_content=_wrap_html("Besoin d'achat reçu", (
                f"<p style='font-size:14px;'><b>{body.company}</b> ({body.contact_name}, {body.email}, "
                f"{body.phone}) — territoire {body.territory}<br/>Produit : <b>{body.product}</b> · "
                f"Quantité : {body.quantity}"
                + (f" · Budget : {body.budget_eur:,.0f} €".replace(",", " ") if body.budget_eur else "") +
                f"<br/>{body.description or ''}</p><p>À traiter dans le superadmin, onglet Demandes.</p>")),
            tags=["purchase-need"])
        await send_email(
            to_email=body.email, to_name=body.contact_name,
            subject=f"✅ Votre besoin d'achat est enregistré — suivi n° {ref}",
            html_content=_wrap_html("Besoin d'achat reçu", (
                f"<p style='font-size:14px;'>Bonjour {body.contact_name},</p>"
                f"<p style='font-size:14px;'>Votre besoin d'achat <b>{body.product}</b> (quantité {body.quantity}, "
                f"territoire {body.territory}) est bien enregistré sous le numéro de suivi "
                f"<b style='font-size:16px;'>{ref}</b>.<br/>La Centrale O'SCOP l'étudie et revient vers vous : "
                "conservez ce numéro pour tout échange.</p>")),
            tags=["purchase-need"])
    except Exception as exc:
        logger.warning("Notif besoin d'achat : %s", exc)
    return {"received": True, "id": doc["id"], "reference": ref}


@purchase_needs_router.get("/public/purchase-needs/track/{reference}")
async def track_purchase_need(reference: str):
    need = await db.purchase_needs.find_one({"reference": reference.upper().strip()}, {"_id": 0})
    if not need:
        raise HTTPException(status_code=404, detail="Numéro de suivi inconnu")
    return {"reference": need["reference"], "status": need["status"], "product": need["product"],
            "communityplace": need.get("communityplace", False),
            "vendor_price_eur": need.get("vendor_price_eur"), "created_at": need["created_at"]}


@purchase_needs_router.get("/admin/purchase-needs")
async def list_purchase_needs(_: dict = Depends(require_admin)):
    return {"needs": await db.purchase_needs.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)}


class AssignBody(BaseModel):
    vendor_email: EmailStr


@purchase_needs_router.post("/admin/purchase-needs/{need_id}/assign")
async def assign_purchase_need(need_id: str, body: AssignBody, admin: dict = Depends(require_admin)):
    need = await db.purchase_needs.find_one({"id": need_id})
    if not need:
        raise HTTPException(status_code=404, detail="Besoin introuvable")
    vendor = await db.users.find_one({"email": body.vendor_email.lower()})
    if not vendor:
        raise HTTPException(status_code=404, detail="Aucun utilisateur avec cet email vendeur")
    await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "status": "ASSIGNED", "assigned_vendor": body.vendor_email.lower(),
        "assigned_by": admin.get("email"), "assigned_at": _now()}})
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=body.vendor_email, to_name=vendor.get("contact_name"),
            subject=f"📦 Besoin d'achat assigné — {need['product']}",
            html_content=_wrap_html("Besoin d'achat assigné", (
                f"<p style='font-size:14px;'>Un besoin d'achat vous a été assigné par la Centrale O'SCOP :</p>"
                f"<p style='font-size:14px;'><b>{need['product']}</b> · quantité {need['quantity']} · "
                f"territoire {need['territory']}<br/>Demandeur : {need['company']} ({need['contact_name']}, "
                f"{need['email']}, {need['phone']})"
                + (f"<br/>Budget : {need['budget_eur']:,.0f} €".replace(",", " ") if need.get("budget_eur") else "") +
                f"<br/>{need.get('description') or ''}</p>")),
            tags=["purchase-need"])
    except Exception as exc:
        logger.warning("Email vendeur assignation : %s", exc)
    return {"status": "ASSIGNED", "assigned_vendor": body.vendor_email.lower()}


@purchase_needs_router.post("/admin/purchase-needs/{need_id}/communityplace")
async def publish_communityplace(need_id: str, payload: dict | None = None, admin: dict = Depends(require_admin)):
    """Publie sur la CommunityPlace payante : lien de paiement Stripe envoyé au demandeur."""
    need = await db.purchase_needs.find_one({"id": need_id})
    if not need:
        raise HTTPException(status_code=404, detail="Besoin introuvable")
    fee_eur = float((payload or {}).get("fee_eur") or 50)
    import os
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=need["email"],
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(fee_eur * 100),
                     "product_data": {"name": f"Frais de publication CommunityPlace — {need['reference']} {need['product']}"}},
                     "quantity": 1}],
        metadata={"purchase_need_id": need_id, "kind": "COMMUNITYPLACE_FEE"},
        success_url=f"{base}/?communityplace_paid={need['reference']}",
        cancel_url=f"{base}/?communityplace_cancelled=1",
    )
    await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "communityplace": True, "communityplace_at": _now(),
        "communityplace_by": admin.get("email"),
        "communityplace_fee_eur": fee_eur, "communityplace_payment_status": "PENDING",
        "communityplace_checkout_id": session.id}})
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=need["email"], to_name=need["contact_name"],
            subject=f"💳 Publication CommunityPlace de votre besoin {need['reference']} — {fee_eur:,.0f} €".replace(",", " "),
            html_content=_wrap_html("Publication CommunityPlace", (
                f"<p style='font-size:14px;'>Bonjour {need['contact_name']},</p>"
                f"<p style='font-size:14px;'>Votre besoin d'achat <b>{need['reference']} — {need['product']}</b> "
                f"est retenu pour publication sur la <b>CommunityPlace</b>. Les frais de publication s'élèvent à "
                f"<b>{fee_eur:,.0f} €</b>.</p>"
                f"<p style='text-align:center;'><a href='{session.url}' style='display:inline-block;background:#D9B35A;"
                "color:#1F0A33;font-weight:bold;padding:12px 26px;border-radius:12px;text-decoration:none;'>"
                "Payer les frais de publication</a></p>").replace(",", " ")),
            tags=["purchase-need"])
    except Exception as exc:
        logger.warning("Email frais CommunityPlace : %s", exc)
    return {"communityplace": True, "fee_eur": fee_eur, "checkout_url": session.url}


def _need_current_user():
    from routes_investor_plans import _current_user
    return _current_user


@purchase_needs_router.get("/vendor/purchase-needs")
async def vendor_purchase_needs(user: dict = Depends(_need_current_user())):
    needs = await db.purchase_needs.find(
        {"assigned_vendor": (user.get("email") or "").lower()}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"needs": needs}


class VendorResponse(BaseModel):
    decision: str
    price_eur: float | None = None
    note: str | None = None


@purchase_needs_router.post("/vendor/purchase-needs/{need_id}/respond")
async def vendor_respond(need_id: str, body: VendorResponse, user: dict = Depends(_need_current_user())):
    if body.decision not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="decision: accept ou decline")
    need = await db.purchase_needs.find_one({"id": need_id, "assigned_vendor": (user.get("email") or "").lower()})
    if not need:
        raise HTTPException(status_code=404, detail="Besoin non assigné à ce vendeur")
    if body.decision == "accept" and (not body.price_eur or body.price_eur <= 0):
        raise HTTPException(status_code=400, detail="Une proposition de prix est requise pour accepter")
    new_status = "VENDOR_ACCEPTED" if body.decision == "accept" else "VENDOR_DECLINED"
    await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "status": new_status, "vendor_price_eur": body.price_eur, "vendor_note": body.note,
        "vendor_responded_at": _now()}})
    try:
        from brevo_service import send_email, _wrap_html
        import os
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        if body.decision == "accept":
            subject = f"✅ Besoin {need['reference']} accepté par le vendeur — {body.price_eur:,.0f} €".replace(",", " ")
            html = (f"<p style='font-size:14px;'>Le vendeur <b>{user.get('email')}</b> accepte le besoin "
                    f"<b>{need['reference']} — {need['product']}</b> avec une proposition de "
                    f"<b>{body.price_eur:,.0f} €</b>.".replace(",", " ")
                    + (f"<br/>Note : {body.note}" if body.note else "") + "</p>")
        else:
            subject = f"❌ Besoin {need['reference']} décliné par le vendeur"
            html = (f"<p style='font-size:14px;'>Le vendeur <b>{user.get('email')}</b> décline le besoin "
                    f"<b>{need['reference']} — {need['product']}</b>."
                    + (f"<br/>Motif : {body.note}" if body.note else "") + "</p>")
        await send_email(to_email=team, to_name=None, subject=subject,
                         html_content=_wrap_html("Réponse vendeur", html), tags=["purchase-need"])
    except Exception as exc:
        logger.warning("Email réponse vendeur : %s", exc)
    return {"status": new_status, "price_eur": body.price_eur}
