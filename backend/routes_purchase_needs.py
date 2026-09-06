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
    doc = {"id": str(uuid.uuid4()), **body.model_dump(), "status": "NEW",
           "assigned_vendor": None, "communityplace": False, "created_at": _now()}
    await db.purchase_needs.insert_one(dict(doc))
    try:
        from brevo_service import send_email, _wrap_html
        import os
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        await send_email(
            to_email=team, to_name=None,
            subject=f"🛒 Nouveau besoin d'achat — {body.product} ({body.company})",
            html_content=_wrap_html("Besoin d'achat reçu", (
                f"<p style='font-size:14px;'><b>{body.company}</b> ({body.contact_name}, {body.email}, "
                f"{body.phone}) — territoire {body.territory}<br/>Produit : <b>{body.product}</b> · "
                f"Quantité : {body.quantity}"
                + (f" · Budget : {body.budget_eur:,.0f} €".replace(",", " ") if body.budget_eur else "") +
                f"<br/>{body.description or ''}</p><p>À traiter dans le superadmin, onglet Demandes.</p>")),
            tags=["purchase-need"])
    except Exception as exc:
        logger.warning("Notif besoin d'achat : %s", exc)
    return {"received": True, "id": doc["id"]}


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
async def publish_communityplace(need_id: str, admin: dict = Depends(require_admin)):
    r = await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "communityplace": True, "communityplace_at": _now(),
        "communityplace_by": admin.get("email")}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Besoin introuvable")
    return {"communityplace": True}
