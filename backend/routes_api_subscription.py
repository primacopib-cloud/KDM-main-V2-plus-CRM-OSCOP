"""Abonnement annuel API coopérative (2 500 €) : Stripe, clé API auto, facture acquittée O'SCOP, registre superadmin."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
api_sub_router = APIRouter(prefix="/api", tags=["Abonnement API"])
db = None

API_ANNUAL_PRICE_EUR = 2500.0
API_KEY_SCOPES = ["catalog:read", "orders:read", "territories:read", "stock:write"]
RENEW_WINDOW_DAYS = 30


def set_api_subscription_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _member(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    return user


def _is_active(sub: dict) -> bool:
    return sub.get("status") == "ACTIVE" and str(sub.get("valid_until") or "") >= _now()


def _is_renewable(sub: dict) -> bool:
    """Renouvelable si l'abonnement actif expire dans moins de 30 jours."""
    limit = (datetime.now(timezone.utc) + timedelta(days=RENEW_WINDOW_DAYS)).isoformat()
    return _is_active(sub) and str(sub.get("valid_until") or "") <= limit


async def _require_relay_manager(user: dict):
    """L'abonnement API est réservé aux relais LOLODRIVE (gestion de leur catalogue)."""
    if (user.get("role") or "").upper() == "GERANT_LOLO_POINT":
        return
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0, "id": 1})
    if not point:
        raise HTTPException(status_code=403,
                            detail="Abonnement réservé aux relais LOLODRIVE (gérants de LOLO POINT)")


@api_sub_router.post("/api-subscription/checkout")
async def api_subscription_checkout(user: dict = Depends(_member)):
    """Le membre connecté souscrit l'abonnement annuel API (montant fixé côté serveur)."""
    await _require_relay_manager(user)
    email = (user.get("email") or "").lower()
    existing = await db.api_subscriptions.find_one({"user_id": user["id"]}, sort=[("created_at", -1)])
    if existing and _is_active(existing) and not _is_renewable(existing):
        raise HTTPException(status_code=409, detail="Vous disposez déjà d'un abonnement API actif")
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    if existing and existing.get("status") == "PENDING_PAYMENT":
        sub_id, reference = existing["id"], existing["reference"]
    else:
        sub_id = str(uuid.uuid4())
        reference = f"API-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        await db.api_subscriptions.insert_one({
            "id": sub_id, "reference": reference, "user_id": user["id"], "email": email,
            "company": user.get("company_name") or user.get("company") or "",
            "contact_name": user.get("contact_name") or user.get("name") or "",
            "amount_eur": API_ANNUAL_PRICE_EUR, "status": "PENDING_PAYMENT", "created_at": _now(),
        })
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=email,
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(API_ANNUAL_PRICE_EUR * 100),
                     "product_data": {"name": f"Abonnement annuel API coopérative O'SCOP — {reference}"}},
                     "quantity": 1}],
        metadata={"api_subscription_id": sub_id, "member_email": email, "kind": "API_SUBSCRIPTION"},
        success_url=f"{base}/coop-api?api_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/coop-api?api_cancelled=1",
    )
    await db.api_subscriptions.update_one({"id": sub_id}, {"$set": {
        "stripe_session_id": session.id, "pending_at": _now()}})
    return {"checkout_url": session.url, "session_id": session.id, "amount_eur": API_ANNUAL_PRICE_EUR}


async def _activate(sub_id: str):
    """Active l'abonnement (idempotent) : clé API réelle + facture acquittée O'SCOP + email Brevo."""
    sub = await db.api_subscriptions.find_one({"id": sub_id})
    if not sub or sub.get("status") == "ACTIVE":
        return
    raw_key = f"kdm_live_{secrets.token_hex(24)}"
    start = datetime.now(timezone.utc)
    prev = await db.api_subscriptions.find_one(
        {"user_id": sub["user_id"], "status": "ACTIVE", "id": {"$ne": sub_id}}, sort=[("valid_until", -1)])
    if prev and str(prev.get("valid_until") or "") > start.isoformat():
        start = datetime.fromisoformat(prev["valid_until"])
    valid_until = (start + timedelta(days=365)).isoformat()
    key_doc = {
        "id": str(uuid.uuid4()), "name": f"Abonnement API — {sub['email']}",
        "prefix": raw_key[:16] + "…",
        "key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
        "scopes": API_KEY_SCOPES, "partner_email": sub["email"],
        "monthly_quota": 100000, "month_usage": 0,
        "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "webhook_url": "", "webhook_secret": f"whsec_{secrets.token_hex(16)}",
        "is_active": True, "requests_count": 0, "last_used_at": None,
        "created_by": "api-subscription", "subscription_id": sub_id,
        "created_at": _now(),
    }
    await db.api_keys.insert_one(dict(key_doc))
    await db.api_subscriptions.update_one({"id": sub_id}, {"$set": {
        "status": "ACTIVE", "paid_at": _now(), "valid_until": valid_until,
        "api_key": raw_key, "api_key_id": key_doc["id"], "api_key_prefix": key_doc["prefix"]}})
    sub = await db.api_subscriptions.find_one({"id": sub_id}, {"_id": 0})
    try:
        import base64
        from brevo_service import send_email, _wrap_html
        from communityplace_invoice import build_api_subscription_invoice_pdf
        pdf = build_api_subscription_invoice_pdf(sub)
        base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
        await send_email(
            to_email=sub["email"], to_name=sub.get("contact_name"),
            subject=f"🔑 Votre clé API coopérative est prête — abonnement {sub['reference']} activé",
            html_content=_wrap_html("Abonnement API activé", (
                f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                f"<p style='font-size:14px;'>Votre paiement de <b>{API_ANNUAL_PRICE_EUR:,.2f} €</b> est confirmé. "
                f"Votre abonnement annuel à l'<b>API coopérative O'SCOP</b> ({sub['reference']}) est actif "
                f"jusqu'au <b>{valid_until[8:10]}/{valid_until[5:7]}/{valid_until[:4]}</b>.</p>"
                "<p style='font-size:14px;'>Voici votre <b>clé API personnelle</b> (à utiliser dans le header "
                "<code>X-API-Key</code>) :</p>"
                f"<p style='background:#1F0A33;color:#B6E27A;padding:14px;border-radius:10px;"
                f"font-family:monospace;font-size:13px;word-break:break-all;'>{raw_key}</p>"
                "<p style='font-size:12px;color:#666;'>Conservez cette clé en lieu sûr et ne la partagez pas. "
                "Elle reste consultable à tout moment dans votre espace sur la page API.</p>"
                "<p style='font-size:14px;'>Votre <b>facture acquittée O'SCOP</b> est jointe à cet email.</p>"
                f"<p style='text-align:center;'><a href='{base}/coop-api' "
                "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                "padding:12px 26px;border-radius:12px;text-decoration:none;'>Accéder à mon abonnement API</a></p>")),
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"facture-{sub['reference']}.pdf"}],
            tags=["api-subscription"])
    except Exception as exc:
        logger.warning("Email abonnement API non envoyé : %s", exc)


@api_sub_router.get("/api-subscription/checkout-status/{session_id}")
async def api_subscription_checkout_status(session_id: str, user: dict = Depends(_member)):
    sub = await db.api_subscriptions.find_one({"stripe_session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Session inconnue")
    if sub.get("status") != "ACTIVE":
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid":
                await _activate(sub["id"])
                sub = await db.api_subscriptions.find_one({"stripe_session_id": session_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("Statut checkout abonnement API : %s", exc)
    return {"status": sub.get("status"), "reference": sub.get("reference"),
            "valid_until": sub.get("valid_until"), "amount_eur": sub.get("amount_eur")}


@api_sub_router.post("/public/api-subscription/webhook")
async def api_subscription_webhook(payload: dict):
    """Webhook Stripe : checkout.session.completed → activation abonnement + clé + facture."""
    if payload.get("type") != "checkout.session.completed":
        return {"received": True}
    obj = (payload.get("data") or {}).get("object") or {}
    sub_id = (obj.get("metadata") or {}).get("api_subscription_id")
    if sub_id and obj.get("payment_status") == "paid":
        await _activate(sub_id)
    return {"received": True}


@api_sub_router.get("/api-subscription/me")
async def my_api_subscription(user: dict = Depends(_member)):
    sub = await db.api_subscriptions.find_one(
        {"user_id": user["id"], "status": "ACTIVE"}, {"_id": 0, "stripe_session_id": 0}, sort=[("paid_at", -1)])
    is_relay = True
    try:
        await _require_relay_manager(user)
    except HTTPException:
        is_relay = False
    if not sub:
        return {"subscription": None, "is_relay": is_relay}
    sub["expired"] = not _is_active(sub)
    sub["renewable"] = _is_renewable(sub) or sub["expired"]
    if sub.get("api_key_id"):
        key = await db.api_keys.find_one({"id": sub["api_key_id"]},
                                         {"_id": 0, "month_usage": 1, "monthly_quota": 1, "usage_month": 1, "requests_count": 1})
        if key:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            sub["usage"] = {
                "month_usage": key.get("month_usage", 0) if key.get("usage_month") == current_month else 0,
                "monthly_quota": key.get("monthly_quota") or 100000,
                "requests_count": key.get("requests_count", 0),
            }
    return {"subscription": sub, "is_relay": is_relay}


@api_sub_router.get("/api-subscription/me/invoice.pdf")
async def my_api_subscription_invoice(user: dict = Depends(_member)):
    sub = await db.api_subscriptions.find_one(
        {"user_id": user["id"], "status": "ACTIVE"}, {"_id": 0}, sort=[("paid_at", -1)])
    if not sub:
        raise HTTPException(status_code=404, detail="Aucun abonnement API payé")
    from fastapi.responses import Response
    from communityplace_invoice import build_api_subscription_invoice_pdf
    pdf = build_api_subscription_invoice_pdf(sub)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=facture-{sub['reference']}.pdf"})


@api_sub_router.get("/admin/api-subscriptions")
async def list_api_subscriptions_admin(_: dict = Depends(require_admin)):
    """Registre superadmin des abonnements API (clé visible, statut, validité)."""
    items = await db.api_subscriptions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    pending = [i for i in items if i.get("status") == "PENDING_PAYMENT" and i.get("stripe_session_id")][:10]
    if pending:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        for i in pending:
            try:
                s = stripe.checkout.Session.retrieve(i["stripe_session_id"])
                if s.payment_status == "paid":
                    await _activate(i["id"])
                    i["status"] = "ACTIVE"
            except Exception as exc:
                logger.warning("Check paiement abonnement API %s : %s", i["id"], exc)
    total = round(sum(float(i.get("amount_eur") or 0) for i in items if i.get("status") == "ACTIVE"), 2)
    return {"items": items, "active_count": sum(1 for i in items if i.get("status") == "ACTIVE"),
            "total_eur": total, "annual_price_eur": API_ANNUAL_PRICE_EUR}


@api_sub_router.get("/admin/api-subscriptions/export")
async def export_api_subscriptions_csv(_: dict = Depends(require_admin)):
    """Export CSV comptabilité du registre des abonnements API."""
    items = await db.api_subscriptions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    rows = ["reference;email;societe;montant_eur;statut;souscrit_le;paye_le;valide_jusqu_au;cle_prefixe"]
    for s in items:
        rows.append(";".join([
            s.get("reference") or "", s.get("email") or "",
            (s.get("company") or "").replace(";", ","),
            f"{float(s.get('amount_eur') or 0):.2f}",
            s.get("status") or "",
            str(s.get("created_at") or "")[:10], str(s.get("paid_at") or "")[:10],
            str(s.get("valid_until") or "")[:10], s.get("api_key_prefix") or ""]))
    from fastapi.responses import Response
    csv = "\ufeff" + "\n".join(rows)
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=abonnements-api.csv"})


@api_sub_router.get("/admin/api-subscriptions/{sub_id}/invoice.pdf")
async def admin_api_subscription_invoice(sub_id: str, _: dict = Depends(require_admin)):
    sub = await db.api_subscriptions.find_one({"id": sub_id, "status": "ACTIVE"}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    from fastapi.responses import Response
    from communityplace_invoice import build_api_subscription_invoice_pdf
    pdf = build_api_subscription_invoice_pdf(sub)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=facture-{sub['reference']}.pdf"})
