"""Plans d'abonnement investisseur (ULTIMATE/VIP/ELITE), paiement Stripe, espace CREDI'SCOP-INVEST."""
from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from admin_guard import require_admin
from auth import get_current_user_id, get_password_hash

logger = logging.getLogger(__name__)
investor_plans_router = APIRouter(prefix="/api/investor-plans", tags=["investor-plans"])
db = None


def set_investor_plans_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc)


def _stripe_key():
    return os.environ.get("STRIPE_API_KEY")


DEFAULT_PLANS = [
    {"id": "plan-ultimate", "code": "ULTIMATE", "name": "ULTIMATE", "price_eur": 50000, "monthly_invest_uc": 4000000,
     "description": "Abonnement mensuel investisseur — accès complet aux opérations d'achat-revente et à la tranche logistique.",
     "options": ["Data room", "Qualification fournisseur", "Analyse économique", "Analyse logistique",
                 "Bon d'Engagement", "Workflow de paiement", "Reporting", "Clôture"],
     "visible": True},
    {"id": "plan-vip", "code": "VIP", "name": "VIP", "price_eur": 100000, "monthly_invest_uc": 8000000,
     "description": "Abonnement mensuel investisseur VIP — capacité de financement renforcée et accompagnement dédié.",
     "options": ["Data room", "Qualification fournisseur", "Analyse économique", "Analyse logistique",
                 "Bon d'Engagement", "Workflow de paiement", "Reporting", "Clôture"],
     "visible": True},
    {"id": "plan-elite", "code": "ELITE", "name": "ELITE", "price_eur": 300000, "monthly_invest_uc": 24000000,
     "description": "Abonnement mensuel investisseur ELITE — capacité maximale multi-territoires et priorité sur les opérations.",
     "options": ["Data room", "Qualification fournisseur", "Analyse économique", "Analyse logistique",
                 "Bon d'Engagement", "Workflow de paiement", "Reporting", "Clôture"],
     "visible": True},
]

CREDIT_PACKS = [
    {"key": "PACK-250K", "price_eur": 250000, "credits_uc": 1250000, "label": "Pack 250 000 € → 1 250 000 uc"},
    {"key": "PACK-600K", "price_eur": 600000, "credits_uc": 3900000, "label": "Pack 600 000 € → 3 900 000 uc"},
]


async def _ensure_seed():
    if await db.investor_plans.count_documents({}) == 0:
        for p in DEFAULT_PLANS:
            await db.investor_plans.insert_one({**p, "created_at": _now().isoformat()})


async def _admin(user_id: str = Depends(get_current_user_id)):
    return await require_admin(user_id)


async def _current_user(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    return user


@investor_plans_router.get("")
async def list_visible_plans():
    await _ensure_seed()
    plans = await db.investor_plans.find({"visible": True}, {"_id": 0}).sort("price_eur", 1).to_list(20)
    return {"plans": plans, "packs": CREDIT_PACKS}


@investor_plans_router.get("/admin")
async def admin_list_plans(_: dict = Depends(_admin)):
    await _ensure_seed()
    return {"plans": await db.investor_plans.find({}, {"_id": 0}).sort("price_eur", 1).to_list(20)}


class PlanUpdate(BaseModel):
    name: str | None = None
    price_eur: int | None = Field(default=None, ge=1)
    monthly_invest_uc: int | None = Field(default=None, ge=1)
    description: str | None = None
    options: list[str] | None = None
    visible: bool | None = None


@investor_plans_router.put("/admin/{plan_id}")
async def admin_update_plan(plan_id: str, body: PlanUpdate, _: dict = Depends(_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    r = await db.investor_plans.update_one({"id": plan_id}, {"$set": {**updates, "updated_at": _now().isoformat()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    return await db.investor_plans.find_one({"id": plan_id}, {"_id": 0})


@investor_plans_router.delete("/admin/{plan_id}")
async def admin_delete_plan(plan_id: str, _: dict = Depends(_admin)):
    r = await db.investor_plans.delete_one({"id": plan_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    return {"deleted": True}


class InvestorApplication(BaseModel):
    legal_name: str
    country: str
    phone_prefix: str
    phone: str
    siren: str
    email: str
    plan_id: str


@investor_plans_router.post("/apply")
async def apply_and_checkout(body: InvestorApplication, request: Request):
    """Candidature investisseur + session de paiement Stripe pour l'abonnement mensuel."""
    plan = await db.investor_plans.find_one({"id": body.plan_id, "visible": True})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non disponible")
    app_id = str(uuid.uuid4())
    stripe.api_key = _stripe_key()
    origin = request.headers.get("origin") or os.environ.get("FRONTEND_URL", "")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price_data": {"currency": "eur", "unit_amount": plan["price_eur"] * 100,
                                    "recurring": {"interval": "month"},
                                    "product_data": {"name": f"Abonnement investisseur {plan['name']} — mensuel"}},
                     "quantity": 1}],
        success_url=f"{origin}/espace-investisseur?invest_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/espace-investisseur?invest_cancelled=1",
        customer_email=body.email,
        metadata={"kind": "INVESTOR_PLAN", "application_id": app_id, "plan_id": plan["id"]},
    )
    await db.investor_applications.insert_one({
        "id": app_id, **body.model_dump(), "plan_code": plan["code"],
        "status": "PENDING_PAYMENT", "stripe_session_id": session.id,
        "created_at": _now().isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


@investor_plans_router.get("/checkout-status/{session_id}")
async def checkout_status(session_id: str):
    """Vérifie le paiement ; crée l'espace investisseur avec identifiant provisoire."""
    application = await db.investor_applications.find_one({"stripe_session_id": session_id})
    if not application:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    if application["status"] == "ACTIVE":
        return {"status": "ACTIVE", "email": application["email"], "already_processed": True}
    stripe.api_key = _stripe_key()
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return {"status": "PENDING", "payment_status": session.payment_status}
    plan = await db.investor_plans.find_one({"id": application["plan_id"]})
    temp_password = f"Invest-{secrets.token_hex(4)}"
    existing = await db.users.find_one({"email": application["email"]})
    if existing:
        user_id = existing["id"]
        await db.users.update_one({"id": user_id}, {"$set": {"role": "investor"}})
        temp_password = None
    else:
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": user_id, "email": application["email"], "name": application["legal_name"],
            "contact_name": application["legal_name"], "password_hash": get_password_hash(temp_password),
            "role": "investor", "must_change_password": True, "created_at": _now().isoformat(),
        })
    await db.investor_accounts.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "application_id": application["id"],
        "plan_id": plan["id"], "plan_code": plan["code"], "monthly_invest_uc": plan["monthly_invest_uc"],
        "period_start": _now().isoformat(), "status": "ACTIVE", "created_at": _now().isoformat(),
    })
    await db.invest_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "type": "MONTHLY_ALLOCATION",
        "label": f"Allocation mensuelle plan {plan['code']}", "amount_uc": plan["monthly_invest_uc"],
        "created_at": _now().isoformat(),
    })
    await db.investor_applications.update_one({"id": application["id"]}, {"$set": {"status": "ACTIVE", "user_id": user_id}})
    return {"status": "ACTIVE", "email": application["email"], "temp_password": temp_password,
            "plan": plan["code"], "must_change_password": temp_password is not None}


@investor_plans_router.post("/webhook")
async def stripe_webhook(request: Request):
    """Renouvellement mensuel : allocation à chaque facture payée, relance email en cas d'échec de carte."""
    payload = await request.json()
    event_type = payload.get("type", "")
    obj = payload.get("data", {}).get("object", {})
    email = (obj.get("customer_email") or (obj.get("customer_details") or {}).get("email") or "").lower()
    if not email:
        return {"received": True}
    user = await db.users.find_one({"email": email})
    account = user and await db.investor_accounts.find_one({"user_id": user["id"]})
    if not account:
        return {"received": True}
    if event_type == "invoice.paid" and obj.get("billing_reason") == "subscription_cycle":
        await db.invest_credit_ledger.insert_one({
            "id": str(uuid.uuid4()), "user_id": user["id"], "type": "MONTHLY_ALLOCATION",
            "label": f"Renouvellement abonnement {account['plan_code']} (facture payée)",
            "amount_uc": account["monthly_invest_uc"], "created_at": _now().isoformat(),
        })
        await db.investor_accounts.update_one({"id": account["id"]}, {"$set": {
            "status": "ACTIVE", "period_start": _now().isoformat(), "payment_failures": 0}})
        plan = await db.investor_plans.find_one({"id": account["plan_id"]}) or {"price_eur": 0}
        from investor_billing import send_monthly_invoice
        await send_monthly_invoice(db, user, account, plan)
    elif event_type == "invoice.payment_failed":
        failures = int(account.get("payment_failures", 0)) + 1
        suspended = failures >= 2
        new_status = "SUSPENDED" if suspended else "PAST_DUE"
        await db.investor_accounts.update_one({"id": account["id"]}, {"$set": {
            "status": new_status, "payment_failures": failures}})
        try:
            from brevo_service import send_email, _wrap_html
            if suspended:
                subject = "🚫 Capacité de financement suspendue — 2 échecs de prélèvement"
                body = (f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                        f"<p style='font-size:14px;'>Après <b>2 échecs de prélèvement consécutifs</b> de votre "
                        f"abonnement <b>{account['plan_code']}</b>, votre capacité de financement "
                        "CREDI'SCOP-INVEST est <b>suspendue</b>. Mettez à jour votre carte bancaire : "
                        "elle sera rétablie automatiquement au prochain paiement réussi.</p>")
            else:
                subject = "⚠ Échec du prélèvement de votre abonnement investisseur KDMARCHÉ"
                body = (f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                        f"<p style='font-size:14px;'>Le prélèvement mensuel de votre abonnement <b>{account['plan_code']}</b> a échoué. "
                        "Une nouvelle tentative automatique sera effectuée. Attention : un second échec "
                        "suspendra votre capacité de financement CREDI'SCOP-INVEST.</p>")
            await send_email(to_email=email, to_name=user.get("contact_name"), subject=subject,
                             html_content=_wrap_html("Suspension" if suspended else "Échec de paiement", body),
                             tags=["investor-billing"])
        except Exception as exc:
            logger.error("Relance échec paiement investisseur : %s", exc)
    return {"received": True}


@investor_plans_router.get("/my-credits")
async def my_invest_credits(user: dict = Depends(_current_user)):
    """Solde CREDI'SCOP-INVEST temps réel, historique et alertes."""
    account = await db.investor_accounts.find_one(
        {"user_id": user["id"], "status": {"$in": ["ACTIVE", "PAST_DUE", "SUSPENDED"]}}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Aucun abonnement investisseur actif")

    # Reset mensuel automatique du compteur au quota du plan
    period_start = datetime.fromisoformat(account["period_start"])
    now = _now()
    if (now.year, now.month) != (period_start.year, period_start.month):
        ledger_now = await db.invest_credit_ledger.find({"user_id": user["id"]}, {"_id": 0, "amount_uc": 1}).to_list(500)
        current_balance = sum(e["amount_uc"] for e in ledger_now)
        adjust = account["monthly_invest_uc"] - current_balance
        if adjust != 0:
            await db.invest_credit_ledger.insert_one({
                "id": str(uuid.uuid4()), "user_id": user["id"], "type": "MONTHLY_RESET",
                "label": f"Remise à niveau mensuelle plan {account['plan_code']}",
                "amount_uc": adjust, "created_at": now.isoformat(),
            })
        await db.investor_accounts.update_one({"id": account["id"]}, {"$set": {"period_start": now.isoformat()}})
    ledger = await db.invest_credit_ledger.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    allocated = sum(e["amount_uc"] for e in ledger if e["amount_uc"] > 0)
    consumed = -sum(e["amount_uc"] for e in ledger if e["amount_uc"] < 0)
    balance = allocated - consumed
    quota = account["monthly_invest_uc"]
    usage_pct = round(consumed / quota * 100, 1) if quota else 0
    alert = "REACHED" if balance <= 0 else ("ALMOST" if usage_pct >= 90 else None)
    return {"plan": account["plan_code"], "monthly_invest_uc": quota, "allocated_uc": allocated,
            "consumed_uc": consumed, "balance_uc": balance, "usage_percent": usage_pct,
            "alert": alert, "packs": CREDIT_PACKS, "history": ledger,
            "account_status": account["status"]}


class ConsumeRequest(BaseModel):
    amount_uc: int = Field(ge=1)
    label: str


@investor_plans_router.post("/consume")
async def consume_credits(body: ConsumeRequest, user: dict = Depends(_current_user)):
    account = await db.investor_accounts.find_one({"user_id": user["id"], "status": "ACTIVE"})
    if not account:
        raise HTTPException(status_code=404, detail="Aucun abonnement investisseur actif")
    await db.invest_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "type": "CONSUMPTION",
        "label": body.label, "amount_uc": -body.amount_uc, "created_at": _now().isoformat(),
    })
    from investor_billing import check_low_quota_alert
    await check_low_quota_alert(db, user["id"])
    return await my_invest_credits(user)


@investor_plans_router.get("/admin/subscribers")
async def admin_list_subscribers(_: dict = Depends(_admin)):
    """Liste des investisseurs abonnés : plan, statut de paiement, prochaine échéance."""
    accounts = await db.investor_accounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    out = []
    for a in accounts:
        user = await db.users.find_one({"id": a["user_id"]}, {"_id": 0, "email": 1, "name": 1, "contact_name": 1})
        ledger = await db.invest_credit_ledger.find({"user_id": a["user_id"]}, {"amount_uc": 1}).to_list(1000)
        ps = datetime.fromisoformat(a["period_start"])
        next_due = (ps.replace(year=ps.year + 1, month=1) if ps.month == 12
                    else ps.replace(month=ps.month + 1))
        out.append({
            "user_id": a["user_id"], "email": (user or {}).get("email"),
            "name": (user or {}).get("contact_name") or (user or {}).get("name"),
            "plan_code": a["plan_code"], "status": a["status"],
            "monthly_invest_uc": a["monthly_invest_uc"],
            "balance_uc": sum(e["amount_uc"] for e in ledger),
            "period_start": a["period_start"], "next_due": next_due.isoformat(),
        })
    return {"subscribers": out}


@investor_plans_router.get("/my-financings/pdf")
async def my_financings_pdf(user: dict = Depends(_current_user)):
    """Export PDF comptable des financements acceptés."""
    from fastapi.responses import Response
    from investor_billing import build_financings_pdf
    account = await db.investor_accounts.find_one({"user_id": user["id"]})
    if not account:
        raise HTTPException(status_code=404, detail="Aucun abonnement investisseur")
    entries = await db.invest_credit_ledger.find(
        {"user_id": user["id"], "type": "FINANCING"}, {"_id": 0}).sort("created_at", 1).to_list(500)
    pdf = build_financings_pdf(user, account, entries)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=financements-crediscop-invest.pdf"})


@investor_plans_router.get("/my-invoices")
async def my_invoices(user: dict = Depends(_current_user)):
    """Archive des factures mensuelles de l'investisseur."""
    invoices = await db.investor_invoices.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("issued_at", -1).to_list(200)
    return {"invoices": invoices}


@investor_plans_router.get("/my-invoices/{invoice_id}/pdf")
async def my_invoice_pdf(invoice_id: str, user: dict = Depends(_current_user)):
    from fastapi.responses import Response
    from investor_billing import build_subscription_invoice_pdf
    invoice = await db.investor_invoices.find_one({"id": invoice_id, "user_id": user["id"]}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    pdf = build_subscription_invoice_pdf(invoice)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={invoice['number']}.pdf"})


class BankDetails(BaseModel):
    holder: str
    iban: str
    bic: str


@investor_plans_router.get("/bank-details")
async def get_bank_details(user: dict = Depends(_current_user)):
    doc = await db.investor_bank_details.find_one({"user_id": user["id"]}, {"_id": 0, "rib_content": 0})
    return {"bank_details": doc, "has_rib": bool(doc and doc.get("rib_filename"))}


@investor_plans_router.put("/bank-details")
async def save_bank_details(body: BankDetails, user: dict = Depends(_current_user)):
    iban = body.iban.replace(" ", "").upper()
    if len(iban) < 15 or len(iban) > 34:
        raise HTTPException(status_code=400, detail="IBAN invalide")
    await db.investor_bank_details.update_one(
        {"user_id": user["id"]},
        {"$set": {"holder": body.holder.strip(), "iban": iban, "bic": body.bic.strip().upper(),
                  "updated_at": _now().isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "user_id": user["id"], "created_at": _now().isoformat()}},
        upsert=True)
    return {"saved": True}


class RibUpload(BaseModel):
    filename: str
    content_base64: str


@investor_plans_router.post("/bank-details/rib")
async def upload_rib(body: RibUpload, user: dict = Depends(_current_user)):
    """Téléversement du RIB en PDF ou PNG (max 5 Mo)."""
    ext = body.filename.rsplit(".", 1)[-1].lower() if "." in body.filename else ""
    if ext not in ("pdf", "png"):
        raise HTTPException(status_code=400, detail="Format accepté : PDF ou PNG uniquement")
    if len(body.content_base64) > 7_000_000:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo)")
    await db.investor_bank_details.update_one(
        {"user_id": user["id"]},
        {"$set": {"rib_filename": body.filename, "rib_content": body.content_base64,
                  "rib_status": "PENDING", "rib_uploaded_at": _now().isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "user_id": user["id"], "created_at": _now().isoformat()}},
        upsert=True)
    return {"uploaded": True, "filename": body.filename}


@investor_plans_router.get("/bank-details/rib")
async def download_rib(user: dict = Depends(_current_user)):
    import base64 as b64
    from fastapi.responses import Response
    doc = await db.investor_bank_details.find_one({"user_id": user["id"]})
    if not doc or not doc.get("rib_content"):
        raise HTTPException(status_code=404, detail="Aucun RIB téléversé")
    media = "application/pdf" if doc["rib_filename"].lower().endswith(".pdf") else "image/png"
    return Response(content=b64.b64decode(doc["rib_content"]), media_type=media,
                    headers={"Content-Disposition": f"attachment; filename={doc['rib_filename']}"})


@investor_plans_router.post("/buy-pack")
async def buy_credit_pack(payload: dict, request: Request, user: dict = Depends(_current_user)):
    pack = next((p for p in CREDIT_PACKS if p["key"] == payload.get("pack_key")), None)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack inconnu")
    stripe.api_key = _stripe_key()
    origin = request.headers.get("origin") or os.environ.get("FRONTEND_URL", "")
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {"currency": "eur", "unit_amount": pack["price_eur"] * 100,
                                    "product_data": {"name": f"Crédits INVEST — {pack['label']}"}},
                     "quantity": 1}],
        success_url=f"{origin}/espace-investisseur?pack_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/espace-investisseur?pack_cancelled=1",
        customer_email=user.get("email"),
        metadata={"kind": "INVEST_PACK", "pack_key": pack["key"], "user_id": user["id"]},
    )
    await db.invest_pack_sessions.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "pack_key": pack["key"],
        "credits_uc": pack["credits_uc"], "stripe_session_id": session.id,
        "status": "PENDING", "created_at": _now().isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


@investor_plans_router.get("/pack-status/{session_id}")
async def pack_status(session_id: str, user: dict = Depends(_current_user)):
    ps = await db.invest_pack_sessions.find_one({"stripe_session_id": session_id, "user_id": user["id"]})
    if not ps:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    if ps["status"] == "CREDITED":
        return {"status": "CREDITED", "credits_uc": ps["credits_uc"]}
    stripe.api_key = _stripe_key()
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return {"status": "PENDING"}
    await db.invest_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "type": "PACK_PURCHASE",
        "label": f"Achat {ps['pack_key']}", "amount_uc": ps["credits_uc"], "created_at": _now().isoformat(),
    })
    await db.invest_pack_sessions.update_one({"id": ps["id"]}, {"$set": {"status": "CREDITED"}})
    return {"status": "CREDITED", "credits_uc": ps["credits_uc"]}
