"""Validation RIB admin, virements de remboursement, portail carte Stripe, relevé annuel fiscal."""
from __future__ import annotations

import base64 as b64
import logging
import os
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

import routes_investor_plans as rip
from routes_investor_plans import _admin, _current_user

logger = logging.getLogger(__name__)
investor_banking_router = APIRouter(prefix="/api/investor-plans", tags=["investor-banking"])


def _now():
    return datetime.now(timezone.utc)


def _db():
    return rip.db


# ---------- Validation RIB (superadmin) ----------

@investor_banking_router.get("/admin/rib-list")
async def admin_rib_list(_: dict = Depends(_admin)):
    docs = await _db().investor_bank_details.find(
        {"rib_filename": {"$exists": True}}, {"_id": 0, "rib_content": 0}).sort("rib_uploaded_at", -1).to_list(200)
    out = []
    for d in docs:
        user = await _db().users.find_one({"id": d["user_id"]}, {"_id": 0, "email": 1, "name": 1, "contact_name": 1})
        out.append({**d, "email": (user or {}).get("email"),
                    "investor_name": (user or {}).get("contact_name") or (user or {}).get("name")})
    return {"ribs": out}


@investor_banking_router.get("/admin/rib/{user_id}")
async def admin_download_rib(user_id: str, _: dict = Depends(_admin)):
    doc = await _db().investor_bank_details.find_one({"user_id": user_id})
    if not doc or not doc.get("rib_content"):
        raise HTTPException(status_code=404, detail="Aucun RIB téléversé")
    media = "application/pdf" if doc["rib_filename"].lower().endswith(".pdf") else "image/png"
    return Response(content=b64.b64decode(doc["rib_content"]), media_type=media,
                    headers={"Content-Disposition": f"inline; filename={doc['rib_filename']}"})


class RibDecision(BaseModel):
    decision: str
    note: str | None = None


@investor_banking_router.post("/admin/rib/{user_id}/decision")
async def admin_rib_decision(user_id: str, body: RibDecision, admin: dict = Depends(_admin)):
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision: approve ou reject")
    new_status = "APPROVED" if body.decision == "approve" else "REJECTED"
    r = await _db().investor_bank_details.update_one(
        {"user_id": user_id, "rib_filename": {"$exists": True}},
        {"$set": {"rib_status": new_status, "rib_decided_by": admin.get("email"),
                  "rib_decided_at": _now().isoformat(), "rib_note": body.note}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="RIB non trouvé")
    user = await _db().users.find_one({"id": user_id})
    if user and user.get("email"):
        try:
            from brevo_service import send_email, _wrap_html
            if new_status == "APPROVED":
                subject = "✅ Votre RIB a été validé"
                body_html = ("<p style='font-size:14px;'>Votre RIB a été vérifié et <b>approuvé</b>. "
                             "Vos remboursements d'investissement pourront désormais être versés sur ce compte.</p>")
            else:
                subject = "❌ Votre RIB n'a pas pu être validé"
                body_html = ("<p style='font-size:14px;'>Votre RIB a été <b>refusé</b>"
                             + (f" : {body.note}" if body.note else "") +
                             ". Merci de téléverser un document lisible et à votre nom depuis votre espace.</p>")
            await send_email(to_email=user["email"], to_name=user.get("contact_name"),
                             subject=subject, html_content=_wrap_html("Validation RIB", body_html),
                             tags=["investor-banking"])
        except Exception as exc:
            logger.error("Email décision RIB : %s", exc)
    return {"rib_status": new_status}


# ---------- Virements de remboursement ----------

DEFAULT_THRESHOLD_EUR = 50000


async def _repayment_threshold():
    doc = await _db().investor_settings.find_one({"key": "repayment_double_approval_threshold_eur"})
    return float(doc["value"]) if doc else DEFAULT_THRESHOLD_EUR


async def _notify_repayment(user: dict, bank: dict, doc: dict):
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject=f"💶 Remboursement de {doc['amount_eur']:,.2f} € versé".replace(",", " "),
            html_content=_wrap_html("Remboursement versé", (
                f"<p style='font-size:14px;'>Un remboursement de <b>{doc['amount_eur']:,.2f} €</b> "
                f"a été versé sur votre IBAN se terminant par <b>…{bank['iban'][-4:]}</b>.<br/>"
                f"Référence de virement : <b>{doc['reference']}</b>"
                + (f"<br/>Opération : {doc['operation_ref']}" if doc.get("operation_ref") else "") +
                "</p>").replace(",", " ")),
            tags=["investor-banking"])
    except Exception as exc:
        logger.error("Email virement remboursement : %s", exc)


@investor_banking_router.get("/admin/repayment-settings")
async def get_repayment_settings(_: dict = Depends(_admin)):
    budget = await _db().investor_settings.find_one({"key": "monthly_repayment_budget_eur"})
    return {"double_approval_threshold_eur": await _repayment_threshold(),
            "monthly_budget_eur": float(budget["value"]) if budget else None}


@investor_banking_router.put("/admin/repayment-settings")
async def set_repayment_settings(payload: dict, _: dict = Depends(_admin)):
    out = {}
    if "double_approval_threshold_eur" in payload:
        threshold = float(payload["double_approval_threshold_eur"] or 0)
        if threshold <= 0:
            raise HTTPException(status_code=400, detail="Seuil invalide")
        await _db().investor_settings.update_one(
            {"key": "repayment_double_approval_threshold_eur"},
            {"$set": {"value": threshold, "updated_at": _now().isoformat()}}, upsert=True)
        out["double_approval_threshold_eur"] = threshold
    if "monthly_budget_eur" in payload:
        budget = float(payload["monthly_budget_eur"] or 0)
        if budget <= 0:
            raise HTTPException(status_code=400, detail="Budget invalide")
        await _db().investor_settings.update_one(
            {"key": "monthly_repayment_budget_eur"},
            {"$set": {"value": budget, "updated_at": _now().isoformat()}}, upsert=True)
        out["monthly_budget_eur"] = budget
    if not out:
        raise HTTPException(status_code=400, detail="Aucun paramètre fourni")
    return out


async def _month_confirmed_total(month_prefix: str) -> float:
    reps = await _db().investor_repayments.find(
        {"status": {"$ne": "PENDING_SECOND_APPROVAL"}, "paid_at": {"$regex": f"^{month_prefix}"}},
        {"amount_eur": 1}).to_list(2000)
    return sum(r["amount_eur"] for r in reps)


async def _check_monthly_budget():
    """Alerte superadmin si le total des remboursements du mois dépasse le budget défini."""
    budget_doc = await _db().investor_settings.find_one({"key": "monthly_repayment_budget_eur"})
    if not budget_doc:
        return
    budget = float(budget_doc["value"])
    month = _now().strftime("%Y-%m")
    total = await _month_confirmed_total(month)
    if total <= budget:
        return
    flag_key = f"repayment_budget_alert_{month}"
    if await _db().system_flags.find_one({"key": flag_key}):
        return
    try:
        from brevo_service import send_email, _wrap_html
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        recipients = {team.lower()}
        async for u in _db().users.find({"is_admin": True}, {"_id": 0, "email": 1}):
            if u.get("email"):
                recipients.add(u["email"].lower())
        html = _wrap_html("Plafond virements dépassé", (
            f"<p style='font-size:14px;'>⚠ Le total des remboursements investisseurs de <b>{month}</b> atteint "
            f"<b>{total:,.0f} €</b> et dépasse le budget mensuel défini de <b>{budget:,.0f} €</b>. "
            "Consultez le journal des virements dans le superadmin (onglet CREDI'SCOP).</p>").replace(",", " "))
        for email in recipients:
            await send_email(to_email=email, to_name=None,
                             subject=f"⚠ Plafond mensuel des virements dépassé — {month}",
                             html_content=html, tags=["investor-banking"])
        await _db().system_flags.update_one({"key": flag_key},
                                            {"$set": {"sent_at": _now().isoformat(), "total": total}}, upsert=True)
    except Exception as exc:
        logger.error("Alerte budget virements : %s", exc)


@investor_banking_router.get("/admin/repayment-prefill/{user_id}")
async def repayment_prefill(user_id: str, _: dict = Depends(_admin)):
    """Opérations financées par l'investisseur pour pré-remplir le virement."""
    entries = await _db().invest_credit_ledger.find(
        {"user_id": user_id, "type": "FINANCING"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    ops = [{"ledger_id": e["id"], "label": e.get("label") or "",
            "operation_ref": (e.get("label") or "").replace("Financement opération ", ""),
            "amount_eur": -e["amount_uc"], "financed_at": e["created_at"]} for e in entries]
    return {"operations": ops}


class RepaymentCreate(BaseModel):
    user_id: str
    amount_eur: float = Field(gt=0)
    reference: str
    operation_ref: str | None = None
    paid_at: str | None = None


@investor_banking_router.post("/admin/repayments")
async def admin_create_repayment(body: RepaymentCreate, admin: dict = Depends(_admin)):
    bank = await _db().investor_bank_details.find_one({"user_id": body.user_id})
    if not bank or bank.get("rib_status") != "APPROVED":
        raise HTTPException(status_code=400, detail="RIB non approuvé — validez le RIB avant tout remboursement")
    user = await _db().users.find_one({"id": body.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Investisseur non trouvé")
    threshold = await _repayment_threshold()
    needs_second = body.amount_eur > threshold
    doc = {
        "id": str(uuid.uuid4()), "user_id": body.user_id, "amount_eur": body.amount_eur,
        "reference": body.reference.strip(), "operation_ref": body.operation_ref,
        "iban": bank["iban"], "paid_at": body.paid_at or _now().isoformat(),
        "status": "PENDING_SECOND_APPROVAL" if needs_second else "CONFIRMED",
        "created_by": admin.get("email"), "created_at": _now().isoformat(),
    }
    await _db().investor_repayments.insert_one(dict(doc))
    if needs_second:
        return {"created": True, "repayment": doc,
                "message": f"Montant > {threshold:,.0f} € — confirmation d'un second admin requise".replace(",", " ")}
    await _notify_repayment(user, bank, doc)
    await _check_monthly_budget()
    return {"created": True, "repayment": doc}


@investor_banking_router.post("/admin/repayments/{rep_id}/approve")
async def approve_repayment(rep_id: str, admin: dict = Depends(_admin)):
    """Confirmation par un second admin (différent du créateur)."""
    rep = await _db().investor_repayments.find_one({"id": rep_id, "status": "PENDING_SECOND_APPROVAL"})
    if not rep:
        raise HTTPException(status_code=404, detail="Virement introuvable ou déjà confirmé")
    if (admin.get("email") or "").lower() == (rep.get("created_by") or "").lower():
        raise HTTPException(status_code=403, detail="La confirmation doit venir d'un second admin différent du créateur")
    await _db().investor_repayments.update_one({"id": rep_id}, {"$set": {
        "status": "CONFIRMED", "approved_by": admin.get("email"), "approved_at": _now().isoformat()}})
    user = await _db().users.find_one({"id": rep["user_id"]})
    bank = await _db().investor_bank_details.find_one({"user_id": rep["user_id"]})
    if user and bank:
        await _notify_repayment(user, bank, rep)
    await _check_monthly_budget()
    return {"status": "CONFIRMED"}


@investor_banking_router.post("/admin/repayments/{rep_id}/reconcile")
async def reconcile_repayment(rep_id: str, admin: dict = Depends(_admin)):
    """Marque un virement comme rapproché avec le relevé bancaire réel (toggle)."""
    rep = await _db().investor_repayments.find_one({"id": rep_id})
    if not rep:
        raise HTTPException(status_code=404, detail="Virement introuvable")
    if rep.get("status") == "PENDING_SECOND_APPROVAL":
        raise HTTPException(status_code=400, detail="Virement non confirmé — impossible de le rapprocher")
    reconciled = not rep.get("reconciled")
    updates = ({"reconciled": True, "reconciled_by": admin.get("email"), "reconciled_at": _now().isoformat()}
               if reconciled else {"reconciled": False, "reconciled_by": None, "reconciled_at": None})
    await _db().investor_repayments.update_one({"id": rep_id}, {"$set": updates})
    return {"reconciled": reconciled}


@investor_banking_router.get("/admin/investor-360/{user_id}")
async def investor_360(user_id: str, _: dict = Depends(_admin)):
    """Fiche unique : abonnement, crédits, financements, RIB, virements, factures."""
    user = await _db().users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Investisseur non trouvé")
    account = await _db().investor_accounts.find_one({"user_id": user_id}, {"_id": 0})
    ledger = await _db().invest_credit_ledger.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    balance = sum(e["amount_uc"] for e in ledger)
    financings = [e for e in ledger if e["type"] == "FINANCING"]
    bank = await _db().investor_bank_details.find_one({"user_id": user_id}, {"_id": 0, "rib_content": 0})
    repayments = await _db().investor_repayments.find({"user_id": user_id}, {"_id": 0}).sort("paid_at", -1).to_list(200)
    invoices = await _db().investor_invoices.find({"user_id": user_id}, {"_id": 0}).sort("issued_at", -1).to_list(100)
    return {
        "investor": {"user_id": user_id, "email": user.get("email"),
                     "name": user.get("contact_name") or user.get("name")},
        "subscription": account,
        "credits": {"balance_uc": balance, "quota_uc": (account or {}).get("monthly_invest_uc"),
                    "consumed_uc": -sum(e["amount_uc"] for e in ledger if e["amount_uc"] < 0),
                    "entries": len(ledger)},
        "financings": {"count": len(financings), "total_uc": -sum(e["amount_uc"] for e in financings),
                       "items": financings[:20]},
        "bank": bank,
        "repayments": {"count": len(repayments),
                       "total_eur": sum(r["amount_eur"] for r in repayments if r.get("status") != "PENDING_SECOND_APPROVAL"),
                       "items": repayments[:20]},
        "invoices": {"count": len(invoices), "total_eur": sum(i["amount_eur"] for i in invoices),
                     "items": invoices[:12]},
    }


@investor_banking_router.get("/admin/investor-360/{user_id}/pdf")
async def investor_360_pdf(user_id: str, admin: dict = Depends(_admin)):
    """Fiche 360 en PDF pour les comités d'investissement."""
    from investor_billing import build_investor_360_pdf
    data = await investor_360(user_id, admin)
    pdf = build_investor_360_pdf(data)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=fiche-investisseur-360-{user_id[:8]}.pdf"})


@investor_banking_router.get("/admin/repayments")
async def admin_list_repayments(user_id: str | None = None, _: dict = Depends(_admin)):
    q = {"user_id": user_id} if user_id else {}
    reps = await _db().investor_repayments.find(q, {"_id": 0}).sort("paid_at", -1).to_list(300)
    for r in reps:
        u = await _db().users.find_one({"id": r["user_id"]}, {"_id": 0, "email": 1})
        r["investor_email"] = (u or {}).get("email")
    return {"repayments": reps}


@investor_banking_router.get("/admin/repayments/export.csv")
async def export_repayments_csv(_: dict = Depends(_admin)):
    import csv
    from io import StringIO
    reps = await _db().investor_repayments.find({}, {"_id": 0}).sort("paid_at", -1).to_list(1000)
    buf = StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Date", "Investisseur", "Montant EUR", "Référence", "Opération", "IBAN", "Statut", "Rapproché", "Créé par", "Confirmé par"])
    for r in reps:
        u = await _db().users.find_one({"id": r["user_id"]}, {"_id": 0, "email": 1})
        w.writerow([r["paid_at"][:10], (u or {}).get("email", ""), f"{r['amount_eur']:.2f}".replace(".", ","),
                    r["reference"], r.get("operation_ref") or "", r.get("iban", ""),
                    r.get("status", "CONFIRMED"), "OUI" if r.get("reconciled") else "NON",
                    r.get("created_by", ""), r.get("approved_by", "")])
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=journal-virements-remboursements.csv"})


@investor_banking_router.get("/my-repayments")
async def my_repayments(user: dict = Depends(_current_user)):
    reps = await _db().investor_repayments.find(
        {"user_id": user["id"], "status": {"$ne": "PENDING_SECOND_APPROVAL"}},
        {"_id": 0}).sort("paid_at", -1).to_list(200)
    return {"repayments": reps, "total_eur": sum(r["amount_eur"] for r in reps)}


# ---------- Portail carte Stripe ----------

@investor_banking_router.post("/billing-portal")
async def create_billing_portal(request: Request, user: dict = Depends(_current_user)):
    """Portail Stripe pour mettre à jour la carte bancaire de l'abonnement."""
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    customers = stripe.Customer.list(email=user["email"], limit=1)
    if not customers.data:
        raise HTTPException(status_code=404, detail="Aucun abonnement carte bancaire trouvé pour ce compte")
    origin = request.headers.get("origin") or os.environ.get("FRONTEND_URL", "")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customers.data[0].id, return_url=f"{origin}/espace-investisseur")
    except stripe.error.InvalidRequestError:
        cfg = stripe.billing_portal.Configuration.create(
            features={"payment_method_update": {"enabled": True},
                      "invoice_history": {"enabled": True}},
            business_profile={"headline": "KDMARCHÉ × O'SCOP — Abonnement investisseur"})
        session = stripe.billing_portal.Session.create(
            customer=customers.data[0].id, configuration=cfg.id,
            return_url=f"{origin}/espace-investisseur")
    return {"portal_url": session.url}


# ---------- Relevé annuel fiscal ----------

@investor_banking_router.get("/my-annual-statement/{year}/pdf")
async def my_annual_statement(year: int, user: dict = Depends(_current_user)):
    from investor_billing import build_annual_statement_pdf
    account = await _db().investor_accounts.find_one({"user_id": user["id"]})
    if not account:
        raise HTTPException(status_code=404, detail="Aucun abonnement investisseur")
    invoices = await _db().investor_invoices.find(
        {"user_id": user["id"], "issued_at": {"$regex": f"^{year}"}}, {"_id": 0}).sort("issued_at", 1).to_list(50)
    financings = await _db().invest_credit_ledger.find(
        {"user_id": user["id"], "type": "FINANCING", "created_at": {"$regex": f"^{year}"}},
        {"_id": 0}).sort("created_at", 1).to_list(500)
    repayments = await _db().investor_repayments.find(
        {"user_id": user["id"], "paid_at": {"$regex": f"^{year}"}}, {"_id": 0}).sort("paid_at", 1).to_list(300)
    pdf = build_annual_statement_pdf(user, account, year, invoices, financings, repayments)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=releve-annuel-{year}.pdf"})
