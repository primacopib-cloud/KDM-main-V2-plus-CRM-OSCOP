"""Abonnement annuel API coopérative (2 500 €) : Stripe, clé API auto, facture acquittée O'SCOP, registre superadmin."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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
    # Renouvellement après expiration : réactive la clé existante du relais (déjà configurée dans son ERP)
    raw_key, key_id, key_prefix = None, None, None
    prev_exp = await db.api_subscriptions.find_one(
        {"user_id": sub["user_id"], "status": "EXPIRED", "api_key_id": {"$exists": True}, "api_key": {"$exists": True}},
        sort=[("valid_until", -1)])
    if prev_exp:
        res = await db.api_keys.update_one({"id": prev_exp["api_key_id"]}, {"$set": {"is_active": True}})
        if res.matched_count:
            raw_key, key_id, key_prefix = prev_exp["api_key"], prev_exp["api_key_id"], prev_exp.get("api_key_prefix")
            logger.info("Clé API réactivée après renouvellement : %s (%s)", key_prefix, sub["email"])
    if not raw_key:
        raw_key = f"kdm_live_{secrets.token_hex(24)}"
    start = datetime.now(timezone.utc)
    early_renewal = False
    prev = await db.api_subscriptions.find_one(
        {"user_id": sub["user_id"], "status": "ACTIVE", "id": {"$ne": sub_id}}, sort=[("valid_until", -1)])
    if prev and str(prev.get("valid_until") or "") > start.isoformat():
        start = datetime.fromisoformat(prev["valid_until"])
        early_renewal = True
    valid_until = (start + timedelta(days=365)).isoformat()
    if not key_id:
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
        key_id, key_prefix = key_doc["id"], key_doc["prefix"]
    await db.api_subscriptions.update_one({"id": sub_id}, {"$set": {
        "status": "ACTIVE", "paid_at": _now(), "valid_until": valid_until,
        "early_renewal": early_renewal,
        "api_key": raw_key, "api_key_id": key_id, "api_key_prefix": key_prefix}})
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
                                         {"_id": 0, "month_usage": 1, "monthly_quota": 1, "usage_month": 1,
                                          "requests_count": 1, "webhook_url": 1, "webhook_events": 1,
                                          "webhook_paused": 1})
        if key:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            sub["usage"] = {
                "month_usage": key.get("month_usage", 0) if key.get("usage_month") == current_month else 0,
                "monthly_quota": key.get("monthly_quota") or 100000,
                "requests_count": key.get("requests_count", 0),
            }
            sub["webhook_url"] = key.get("webhook_url") or ""
            sub["webhook_events"] = key.get("webhook_events") or ["paid", "preparing", "ready", "fulfilled"]
            sub["webhook_paused"] = bool(key.get("webhook_paused"))
    return {"subscription": sub, "is_relay": is_relay}


VALID_WEBHOOK_EVENTS = ["paid", "preparing", "ready", "fulfilled"]


class WebhookUrlBody(BaseModel):
    webhook_url: str
    events: list[str] | None = None
    paused: bool | None = None


async def _my_active_sub(user: dict) -> dict:
    sub = await db.api_subscriptions.find_one(
        {"user_id": user["id"], "status": "ACTIVE", "api_key_id": {"$exists": True}}, sort=[("paid_at", -1)])
    if not sub or not _is_active(sub):
        raise HTTPException(status_code=404, detail="Aucun abonnement API actif")
    return sub


@api_sub_router.put("/api-subscription/me/webhook")
async def set_my_webhook(body: WebhookUrlBody, user: dict = Depends(_member)):
    """L'abonné configure lui-même l'URL webhook de sa clé (vide = retirer) — pause possible sans rien perdre."""
    url = body.webhook_url.strip()
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL invalide (http/https requis)")
    sub = await _my_active_sub(user)
    import secrets as _s
    key = await db.api_keys.find_one({"id": sub["api_key_id"]}, {"_id": 0, "webhook_secret": 1})
    upd = {"webhook_url": url}
    if body.events is not None:
        events = [e for e in body.events if e in VALID_WEBHOOK_EVENTS]
        if not events:
            raise HTTPException(status_code=400, detail="Sélectionnez au moins un événement")
        upd["webhook_events"] = events
    if body.paused is not None:
        upd["webhook_paused"] = body.paused
        upd["webhook_paused_at"] = datetime.now(timezone.utc).isoformat() if body.paused else None
    if key is not None and not key.get("webhook_secret"):
        upd["webhook_secret"] = f"whsec_{_s.token_hex(16)}"
    await db.api_keys.update_one({"id": sub["api_key_id"]}, {"$set": upd})
    return {"ok": True, "webhook_url": url, "events": upd.get("webhook_events"),
            "webhook_paused": upd.get("webhook_paused")}


@api_sub_router.post("/api-subscription/me/webhook/test")
async def test_my_webhook(user: dict = Depends(_member)):
    """« Tester mon webhook » : envoie un événement d'exemple signé à l'endpoint du relais."""
    sub = await _my_active_sub(user)
    key = await db.api_keys.find_one({"id": sub["api_key_id"]}, {"_id": 0})
    if not key or not key.get("webhook_url"):
        raise HTTPException(status_code=400, detail="Configurez d'abord l'URL de votre webhook")
    from erp_webhooks import send_test_event
    return await send_test_event(key)


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


@api_sub_router.get("/admin/api-subscriptions/calls")
async def api_subscription_call_log(limit: int = 50, q: str = "", _: dict = Depends(require_admin)):
    """Journal des derniers appels API des abonnés (support technique) — filtre q sur email/endpoint."""
    limit = max(1, min(limit, 200))
    subs = await db.api_subscriptions.find(
        {"api_key_id": {"$exists": True}},
        {"_id": 0, "api_key_id": 1, "email": 1, "reference": 1}).to_list(500)
    by_key = {s["api_key_id"]: s for s in subs}
    if not by_key:
        return {"calls": []}
    logs = await db.api_call_logs.find(
        {"key_id": {"$in": list(by_key)}}, {"_id": 0}).sort("ts", -1).to_list(500)
    needle = (q or "").strip().lower()
    calls = []
    for l in logs:
        s = by_key[l["key_id"]]
        if needle and needle not in s["email"].lower() and needle not in (l.get("path") or "").lower() \
                and needle not in (s.get("reference") or "").lower():
            continue
        calls.append({"email": s["email"], "reference": s["reference"],
                      "method": l.get("method"), "path": l.get("path"), "ts": l.get("ts")})
        if len(calls) >= limit:
            break
    return {"calls": calls}


@api_sub_router.get("/admin/api-subscriptions/stats")
async def api_subscription_stats(_: dict = Depends(require_admin)):
    """Appels API par jour (30 derniers jours) — suivi de l'adoption de l'offre."""
    key_ids = [s["api_key_id"] async for s in db.api_subscriptions.find(
        {"api_key_id": {"$exists": True}}, {"_id": 0, "api_key_id": 1})]
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    daily_map = {}
    endpoint_map = {}
    if key_ids:
        async for l in db.api_call_logs.find(
                {"key_id": {"$in": key_ids}, "ts": {"$gte": since}}, {"_id": 0, "ts": 1, "path": 1}):
            d = str(l.get("ts") or "")[:10]
            if d:
                daily_map[d] = daily_map.get(d, 0) + 1
            p = (l.get("path") or "").replace("/api/public/v1", "")
            if p:
                endpoint_map[p] = endpoint_map.get(p, 0) + 1
    top_endpoints = sorted(
        ({"path": p, "count": c} for p, c in endpoint_map.items()),
        key=lambda x: -x["count"])[:5]
    days = []
    today = datetime.now(timezone.utc).date()
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        days.append({"day": d, "count": daily_map.get(d, 0)})
    return {"daily": days, "total_30d": sum(x["count"] for x in days), "top_endpoints": top_endpoints}


@api_sub_router.get("/admin/api-subscriptions/webhook-deliveries")
async def api_subscription_webhook_deliveries(limit: int = 50, _: dict = Depends(require_admin)):
    """Dernières livraisons webhook des relais abonnés (succès/échec) — diagnostic intégration."""
    limit = max(1, min(limit, 200))
    subs = await db.api_subscriptions.find(
        {"api_key_id": {"$exists": True}},
        {"_id": 0, "api_key_id": 1, "email": 1, "reference": 1}).to_list(500)
    by_key = {s["api_key_id"]: s for s in subs}
    if not by_key:
        return {"deliveries": []}
    logs = await db.webhook_deliveries.find(
        {"key_id": {"$in": list(by_key)}}).sort("ts", -1).to_list(limit)
    return {"deliveries": [{
        "delivery_id": str(d["_id"]),
        "email": by_key[d["key_id"]]["email"], "reference": by_key[d["key_id"]]["reference"],
        "event": d.get("event"), "order_id": d.get("order_id"), "url": d.get("url"),
        "status_code": d.get("status_code"), "ok": d.get("ok", False), "attempt": d.get("attempt", 0),
        "error": d.get("error"), "ts": d.get("ts"),
    } for d in logs]}


class RetryBody(BaseModel):
    delivery_id: str


@api_sub_router.post("/admin/api-subscriptions/webhook-deliveries/retry")
async def retry_webhook_delivery(body: RetryBody, _: dict = Depends(require_admin)):
    """Relance une livraison webhook depuis l'historique (payload reconstruit à l'état actuel)."""
    from bson import ObjectId
    try:
        oid = ObjectId(body.delivery_id)
    except Exception:
        raise HTTPException(status_code=400, detail="delivery_id invalide") from None
    d = await db.webhook_deliveries.find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="Livraison introuvable")
    key = await db.api_keys.find_one({"id": d["key_id"]}, {"_id": 0})
    if not key or not key.get("webhook_url"):
        raise HTTPException(status_code=409, detail="Clé sans URL webhook — reconfigurez-la avant de relancer")
    from erp_webhooks import dispatch_lolodrive_order_event, send_test_event
    if (d.get("event") or "").startswith("lolodrive."):
        order = await db.lolodrive_orders.find_one({"id": d.get("order_id")}, {"_id": 0, "status": 1})
        if not order:
            raise HTTPException(status_code=409, detail="Commande d'origine introuvable")
        extra = {"status": order.get("status")} if d["event"] == "lolodrive.order.status" else None
        await dispatch_lolodrive_order_event(d["order_id"], event=d["event"], extra=extra)
        last = await db.webhook_deliveries.find_one(
            {"key_id": d["key_id"], "order_id": d["order_id"]}, sort=[("ts", -1)])
        return {"ok": bool(last and last.get("ok")), "status_code": (last or {}).get("status_code"),
                "error": (last or {}).get("error")}
    result = await send_test_event(key)
    return result


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
