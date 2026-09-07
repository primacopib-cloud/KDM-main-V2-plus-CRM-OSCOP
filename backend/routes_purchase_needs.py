"""Besoins d'achat visiteurs : dépôt public, assignation vendeur, CommunityPlace."""
from __future__ import annotations

import logging
import uuid
import re
import os
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
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
    images: List[str] | None = Field(default=None, max_length=2)


class NeedItem(BaseModel):
    product: str = Field(min_length=3)
    quantity: str
    budget_eur: float | None = None
    description: str | None = None
    images: List[str] | None = Field(default=None, max_length=2)


class PurchaseNeedBatch(BaseModel):
    company: str = Field(min_length=2)
    contact_name: str = Field(min_length=2)
    email: EmailStr
    phone: str = Field(min_length=6)
    territory: str
    country_code: str | None = None
    deadline: str | None = None
    items: List[NeedItem] = Field(min_length=1, max_length=10)


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


def _qty_num(qty: str) -> int:
    m = re.search(r"\d+", str(qty or ""))
    return int(m.group()) if m else 0


@purchase_needs_router.post("/public/purchase-needs/upload-image")
async def upload_need_image(file: UploadFile = File(...)):
    """Photos produit du besoin d'achat (max 2 Mo, 2 par produit côté form)."""
    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPG ou WEBP")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 2 Mo)")
    filename = f"need-{uuid.uuid4().hex[:10]}.{allowed[file.content_type]}"
    from upload_storage import save_upload
    url = await save_upload(f"needs/{filename}", content, file.content_type)
    return {"ok": True, "url": url}


@purchase_needs_router.post("/public/purchase-needs/batch")
async def create_purchase_needs_batch(body: PurchaseNeedBatch):
    """Multi-produits : une demande créée PAR produit (le tarif de publication s'applique par demande)."""
    now = datetime.now(timezone.utc)
    refs = []
    for item in body.items:
        ref = f"BA-{now.strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"
        doc = {"id": str(uuid.uuid4()), "reference": ref,
               "company": body.company, "contact_name": body.contact_name, "email": body.email,
               "phone": body.phone, "territory": body.territory, "country_code": body.country_code, "deadline": body.deadline,
               "product": item.product, "quantity": item.quantity, "budget_eur": item.budget_eur,
               "description": item.description, "images": item.images or [],
               "status": "NEW", "assigned_vendor": None, "communityplace": False, "created_at": _now()}
        await db.purchase_needs.insert_one(dict(doc))
        refs.append({"reference": ref, "product": item.product})
    n = len(refs)
    try:
        from brevo_service import send_email, _wrap_html
        import os
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        rows = "".join(f"<li><b>{r['reference']}</b> — {r['product']}</li>" for r in refs)
        await send_email(
            to_email=team, to_name=None,
            subject=f"🛒 {n} besoin(s) d'achat — {body.company}",
            html_content=_wrap_html("Besoins d'achat reçus", (
                f"<p style='font-size:14px;'><b>{body.company}</b> ({body.contact_name}, {body.email}, "
                f"{body.phone}) — territoire {body.territory}</p><ul style='font-size:14px;'>{rows}</ul>"
                f"<p>À traiter dans le superadmin, onglet Demandes.</p>")),
            tags=["purchase-need"])
        await send_email(
            to_email=body.email, to_name=body.contact_name,
            subject=f"✅ Vos {n} besoins d'achat sont enregistrés" if n > 1 else f"✅ Votre besoin d'achat est enregistré — suivi n° {refs[0]['reference']}",
            html_content=_wrap_html("Besoins d'achat reçus", (
                f"<p style='font-size:14px;'>Bonjour {body.contact_name},</p>"
                f"<p style='font-size:14px;'>Vos demandes sont enregistrées (une demande par produit) :</p>"
                f"<ul style='font-size:14px;'>{rows}</ul>"
                f"<p style='font-size:14px;'>Le tarif de publication CommunityPlace s'applique par demande "
                f"(× {n}). Conservez ces numéros pour tout échange.</p>")),
            tags=["purchase-need"])
    except Exception as e:
        logger.warning(f"batch need emails failed: {e}")
    return {"ok": True, "count": n, "references": refs}


@purchase_needs_router.post("/admin/purchase-needs/{need_id}/close-grouping")
async def close_grouping(need_id: str, admin: dict = Depends(require_admin)):
    """Clôture le groupage d'une demande et notifie demandeur + tous les participants."""
    need = await db.purchase_needs.find_one({"id": need_id})
    if not need:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if need.get("grouping_closed"):
        raise HTTPException(status_code=409, detail="Groupage déjà clôturé")
    await db.purchase_needs.update_one(
        {"id": need_id}, {"$set": {"grouping_closed": True, "grouping_closed_at": _now()}})
    joiners = need.get("joiners") or []
    total = f"{need['quantity']} + {int(need.get('joined_quantity') or 0)}"
    notified = 0
    try:
        from brevo_service import send_email, _wrap_html
        html = _wrap_html("Groupage clôturé", (
            f"<p style='font-size:14px;'>Le groupage de la demande <b>{need['product']}</b> "
            f"(suivi <b>{need['reference']}</b>) est clôturé.</p>"
            f"<p style='font-size:14px;'>Volume final groupé : <b>{total}</b> "
            f"({len(joiners)} participant{'s' if len(joiners) > 1 else ''}).<br/>"
            f"La Centrale O'SCOP négocie désormais les meilleures conditions et revient vers vous.</p>"))
        recipients = [{"email": need.get("email"), "name": need.get("contact_name")}] + \
                     [{"email": j.get("email"), "name": None} for j in joiners]
        for r in recipients:
            if not r["email"]:
                continue
            try:
                await send_email(to_email=r["email"], to_name=r["name"],
                                 subject=f"📦 Groupage clôturé — {need['reference']} ({need['product']})",
                                 html_content=html, tags=["purchase-need-close"])
                notified += 1
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"close grouping emails failed: {e}")
    return {"ok": True, "grouping_closed": True, "notified": notified}


TERRITORY_FLAG = {"Guadeloupe": "GP", "Martinique": "MQ", "Guyane": "GF", "La Réunion": "RE",
                  "Mayotte": "YT", "Saint-Martin": "MF"}


@purchase_needs_router.get("/public/community-board")
async def community_board(q: str | None = None):
    """Demandes de produits publiées (CommunityPlace) pour l'accueil, avec drapeau territoire."""
    needs = await db.purchase_needs.find(
        {"communityplace": True}, {"_id": 0, "email": 0, "phone": 0}).sort("created_at", -1).to_list(60)
    out = []
    for n in needs:
        if q and q.lower() not in f"{n['product']} {n['territory']} {n.get('company', '')}".lower():
            continue
        init = _qty_num(n.get("quantity"))
        joined = int(n.get("joined_quantity") or 0)
        goal = max(init * 2, init + joined, 10)
        out.append({"reference": n["reference"], "product": n["product"], "quantity": n["quantity"],
                    "territory": n["territory"],
                    "flag": (n.get("country_code") or TERRITORY_FLAG.get(n["territory"], "FR")),
                    "status": n["status"], "created_at": n["created_at"],
                    "joiners_count": len(n.get("joiners") or []),
                    "joined_quantity": joined,
                    "current_quantity": init + joined,
                    "goal_quantity": goal,
                    "grouping_closed": bool(n.get("grouping_closed")),
                    "photos_count": len(n.get("images") or []),
                    "photos": (n.get("images") or [])[:2]})
    return {"demands": out}


class JoinNeedBody(BaseModel):
    email: EmailStr
    quantity: int = Field(1, ge=1, le=10000)


@purchase_needs_router.post("/public/purchase-needs/{reference}/join")
async def join_purchase_need(reference: str, body: JoinNeedBody):
    """Un visiteur rejoint une demande publiée pour grouper les volumes."""
    need = await db.purchase_needs.find_one({"reference": reference, "communityplace": True})
    if not need:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if need.get("grouping_closed"):
        raise HTTPException(status_code=409, detail="Le groupage de cette demande est clôturé.")
    if any(j.get("email") == body.email.lower() for j in (need.get("joiners") or [])):
        raise HTTPException(status_code=409, detail="Vous avez déjà rejoint cette demande.")
    from datetime import datetime, timezone
    await db.purchase_needs.update_one(
        {"reference": reference},
        {"$push": {"joiners": {"email": body.email.lower(), "quantity": body.quantity,
                               "joined_at": datetime.now(timezone.utc).isoformat()}},
         "$inc": {"joined_quantity": body.quantity}})
    updated = await db.purchase_needs.find_one({"reference": reference}, {"_id": 0, "joiners": 1, "joined_quantity": 1})
    j_count = len(updated.get("joiners") or [])
    j_qty = int(updated.get("joined_quantity") or 0)
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=body.email.lower(), to_name=None,
            subject=f"🤝 Vous avez rejoint la demande groupée {reference} — {need['product']}",
            html_content=_wrap_html("Demande groupée rejointe", (
                f"<p style='font-size:14px;'>Bonjour,</p>"
                f"<p style='font-size:14px;'>Vous avez rejoint la demande d'achat groupée "
                f"<b>{need['product']}</b> (territoire {need['territory']}) sous le numéro de suivi "
                f"<b style='font-size:16px;'>{reference}</b>.</p>"
                f"<p style='font-size:14px;'>Votre quantité : <b>{body.quantity}</b><br/>"
                f"Volume groupé actuel : <b>{need['quantity']} + {j_qty}</b> "
                f"({j_count} participant{'s' if j_count > 1 else ''})</p>"
                f"<p style='font-size:14px;'>La Centrale O'SCOP vous tiendra informé de l'avancement : "
                f"conservez ce numéro pour tout échange.</p>")),
            tags=["purchase-need-join"])
        if need.get("email"):
            await send_email(
                to_email=need["email"], to_name=need.get("contact_name"),
                subject=f"📈 Votre demande {reference} groupe les volumes — +{body.quantity} qté",
                html_content=_wrap_html("Nouveau participant sur votre demande", (
                    f"<p style='font-size:14px;'>Bonjour {need.get('contact_name', '')},</p>"
                    f"<p style='font-size:14px;'>Bonne nouvelle : un nouveau participant vient de rejoindre votre "
                    f"demande <b>{need['product']}</b> (suivi <b>{reference}</b>) pour <b>+{body.quantity}</b> en quantité.</p>"
                    f"<p style='font-size:14px;'>Volume groupé actuel : <b>{need['quantity']} + {j_qty}</b> "
                    f"({j_count} participant{'s' if j_count > 1 else ''}). Plus le volume grandit, "
                    f"meilleures sont les conditions négociées par la Centrale O'SCOP.</p>")),
                tags=["purchase-need-join"])
    except Exception as e:
        logger.warning(f"join emails failed: {e}")
    return {"ok": True, "reference": reference,
            "joiners_count": j_count,
            "joined_quantity": j_qty}


@purchase_needs_router.get("/admin/purchase-needs/stats/csv")
async def communityplace_stats_csv(_: dict = Depends(require_admin)):
    """Export CSV comptabilité : revenus mensuels frais de publication CommunityPlace."""
    from fastapi.responses import Response
    data = await communityplace_stats(_)
    lines = ["mois;revenus_eur"] + [f"{m['month']};{m['revenue_eur']:.2f}" for m in data["months"]]
    lines.append(f"TOTAL;{data['total_eur']:.2f}")
    csv = "\ufeff" + "\n".join(lines)
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=revenus_communityplace.csv"})


@purchase_needs_router.get("/admin/purchase-needs/stats")
async def communityplace_stats(_: dict = Depends(require_admin)):
    """Revenus mensuels des frais de publication CommunityPlace encaissés."""
    paid = await db.purchase_needs.find(
        {"communityplace_payment_status": "PAID"},
        {"_id": 0, "communityplace_fee_eur": 1, "communityplace_paid_at": 1}).to_list(1000)
    months: dict = {}
    for p in paid:
        m = (p.get("communityplace_paid_at") or "")[:7]
        months[m] = months.get(m, 0) + float(p.get("communityplace_fee_eur") or 0)
    return {"months": [{"month": m, "revenue_eur": v} for m, v in sorted(months.items(), reverse=True)],
            "total_eur": sum(months.values()), "count": len(paid)}


@purchase_needs_router.get("/admin/purchase-needs")
async def list_purchase_needs(_: dict = Depends(require_admin)):
    needs = await db.purchase_needs.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)
    # Confirmation lazy des paiements CommunityPlace en attente
    pending = [n for n in needs if n.get("communityplace_payment_status") == "PENDING" and n.get("communityplace_checkout_id")][:10]
    if pending:
        import os
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        for n in pending:
            try:
                s = stripe.checkout.Session.retrieve(n["communityplace_checkout_id"])
                if s.payment_status == "paid":
                    await db.purchase_needs.update_one({"id": n["id"]}, {"$set": {
                        "communityplace_payment_status": "PAID", "communityplace_paid_at": _now()}})
                    n["communityplace_payment_status"] = "PAID"
            except Exception as exc:
                logger.warning("Check paiement CommunityPlace %s : %s", n["id"], exc)
    return {"needs": needs}


@purchase_needs_router.post("/public/purchase-needs/webhook")
async def communityplace_webhook(payload: dict):
    """Webhook Stripe : checkout.session.completed → besoin marqué payé."""
    if payload.get("type") != "checkout.session.completed":
        return {"received": True}
    obj = (payload.get("data") or {}).get("object") or {}
    need_id = (obj.get("metadata") or {}).get("purchase_need_id")
    if need_id and obj.get("payment_status") == "paid":
        await db.purchase_needs.update_one({"id": need_id}, {"$set": {
            "communityplace_payment_status": "PAID", "communityplace_paid_at": _now()}})
    return {"received": True}


@purchase_needs_router.get("/public/purchase-needs/accept-offer/{reference}")
async def accept_vendor_offer(reference: str):
    """Acceptation en ligne de l'offre vendeur → redirection vers l'adhésion pro."""
    import os
    from fastapi.responses import RedirectResponse
    need = await db.purchase_needs.find_one({"reference": reference.upper().strip()})
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    if need and need.get("status") == "VENDOR_ACCEPTED":
        await db.purchase_needs.update_one({"id": need["id"]}, {"$set": {
            "status": "OFFER_ACCEPTED", "offer_accepted_at": _now()}})
    return RedirectResponse(url=f"{base}/tarifs?besoin={reference}")


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
                f"<br/>{need.get('description') or ''}</p>"
                + ("".join(
                    f"<img src='{(os.environ.get('FRONTEND_URL') or 'https://centrale.objectifscopoutremer.com') + u if u.startswith('/') else u}' "
                    f"alt='photo produit' style='max-width:220px;border-radius:10px;margin:4px 6px 4px 0;' />"
                    for u in (need.get("images") or [])) if need.get("images") else ""))),
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
            api_base = os.environ.get("BACKEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            await send_email(
                to_email=need["email"], to_name=need["contact_name"],
                subject=f"💼 Offre reçue pour votre besoin {need['reference']} — {body.price_eur:,.0f} €".replace(",", " "),
                html_content=_wrap_html("Proposition de prix", (
                    f"<p style='font-size:14px;'>Bonjour {need['contact_name']},</p>"
                    f"<p style='font-size:14px;'>Un vendeur référencé de la Centrale O'SCOP propose "
                    f"<b style='font-size:16px;'>{body.price_eur:,.0f} €</b> pour votre besoin "
                    f"<b>{need['reference']} — {need['product']}</b> (quantité {need['quantity']})."
                    + (f"<br/>Note du vendeur : {body.note}" if body.note else "") + "</p>"
                    f"<p style='text-align:center;'><a href='{api_base}/api/public/purchase-needs/accept-offer/{need['reference']}' "
                    "style='display:inline-block;background:#8CC63E;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Accepter l'offre et adhérer à la Centrale</a></p>"
                    "<p style='font-size:12px;color:#888;'>L'acceptation vous dirige vers l'adhésion professionnelle "
                    "KDMARCHÉ × O'SCOP, nécessaire pour finaliser l'achat.</p>").replace(",", " ")),
                tags=["purchase-need"])
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
