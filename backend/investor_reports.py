"""Rapport mensuel investisseurs (superadmin) et relance échéance J-3."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
TEAM_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


def _now():
    return datetime.now(timezone.utc)


def _next_due(period_start_iso: str) -> datetime:
    ps = datetime.fromisoformat(period_start_iso)
    return ps.replace(year=ps.year + 1, month=1) if ps.month == 12 else ps.replace(month=ps.month + 1)


async def run_investor_monthly_report(db, force: bool = False):
    """Chaque début de mois : récap abonnements, encaissements et financements au superadmin."""
    now = _now()
    if not force and now.day != 1:
        return 0
    month_tag = now.strftime("%Y-%m")
    if not force and await db.system_flags.find_one({"key": f"investor_monthly_report_{month_tag}"}):
        return 0
    prev = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    accounts = await db.investor_accounts.find({}, {"_id": 0}).to_list(500)
    by_plan, by_status = {}, {}
    for a in accounts:
        by_plan[a["plan_code"]] = by_plan.get(a["plan_code"], 0) + 1
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    invoices = await db.investor_invoices.find({"issued_at": {"$regex": f"^{prev}"}}, {"_id": 0}).to_list(500)
    encaisse = sum(i["amount_eur"] for i in invoices)
    financings = await db.invest_credit_ledger.find(
        {"type": "FINANCING", "created_at": {"$regex": f"^{prev}"}}, {"_id": 0}).to_list(1000)
    financed_uc = -sum(e["amount_uc"] for e in financings)
    from brevo_service import send_email, _wrap_html
    rows_plan = "".join(f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>{p}</td>"
                        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'>{n}</td></tr>"
                        for p, n in sorted(by_plan.items()))
    html = _wrap_html("Rapport mensuel investisseurs", (
        f"<p style='font-size:14px;'>Récapitulatif du mois <b>{prev}</b> :</p>"
        f"<table style='font-size:13px;border-collapse:collapse'>"
        f"<tr><th style='text-align:left;padding:4px 10px'>Plan</th><th style='padding:4px 10px'>Abonnés</th></tr>{rows_plan}</table>"
        f"<p style='font-size:13px;'>Statuts : " +
        " · ".join(f"<b>{s}</b> : {n}" for s, n in sorted(by_status.items())) + "</p>"
        f"<p style='font-size:13px;'>Encaissements abonnements : <b>{encaisse:,.0f} €</b> ({len(invoices)} facture(s))</p>"
        f"<p style='font-size:13px;'>Financements CREDI'SCOP-INVEST : <b>{financed_uc:,.0f} uc</b> "
        f"({len(financings)} opération(s))</p>").replace(",", " "))
    recipients = {TEAM_EMAIL.lower()}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    sent = 0
    for email in recipients:
        try:
            await send_email(to_email=email, to_name=None,
                             subject=f"📊 Rapport mensuel investisseurs — {prev}",
                             html_content=html, tags=["investor-report"])
            sent += 1
        except Exception as exc:
            logger.warning("Rapport investisseurs vers %s : %s", email, exc)
    await db.system_flags.update_one({"key": f"investor_monthly_report_{month_tag}"},
                                     {"$set": {"sent_at": _now().isoformat(), "recipients": sent}}, upsert=True)
    return sent


async def run_investor_annual_statements(db, force_year: int | None = None):
    """Début janvier : envoie à chaque investisseur son relevé annuel fiscal PDF de l'année écoulée."""
    now = _now()
    if force_year is None and not (now.month == 1 and now.day <= 3):
        return 0
    year = force_year or now.year - 1
    if not force_year and await db.system_flags.find_one({"key": f"investor_annual_statement_{year}"}):
        return 0
    import base64
    from investor_billing import build_annual_statement_pdf
    from brevo_service import send_email, _wrap_html
    sent = 0
    async for a in db.investor_accounts.find({}, {"_id": 0}):
        user = await db.users.find_one({"id": a["user_id"]})
        if not user or not user.get("email"):
            continue
        invoices = await db.investor_invoices.find(
            {"user_id": a["user_id"], "issued_at": {"$regex": f"^{year}"}}, {"_id": 0}).sort("issued_at", 1).to_list(50)
        financings = await db.invest_credit_ledger.find(
            {"user_id": a["user_id"], "type": "FINANCING", "created_at": {"$regex": f"^{year}"}},
            {"_id": 0}).sort("created_at", 1).to_list(500)
        repayments = await db.investor_repayments.find(
            {"user_id": a["user_id"], "paid_at": {"$regex": f"^{year}"}}, {"_id": 0}).sort("paid_at", 1).to_list(300)
        if not invoices and not financings and not repayments:
            continue
        try:
            pdf = build_annual_statement_pdf(user, a, year, invoices, financings, repayments)
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"),
                subject=f"📄 Votre relevé annuel fiscal investisseur {year}",
                html_content=_wrap_html("Relevé annuel", (
                    f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Veuillez trouver en pièce jointe votre relevé annuel <b>{year}</b> "
                    "(abonnements, financements CREDI'SCOP-INVEST et remboursements) pour votre déclaration comptable.</p>")),
                attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"releve-annuel-{year}.pdf"}],
                tags=["investor-report"])
            sent += 1
        except Exception as exc:
            logger.warning("Relevé annuel %s : %s", user.get("email"), exc)
    await db.system_flags.update_one({"key": f"investor_annual_statement_{year}"},
                                     {"$set": {"sent_at": _now().isoformat(), "count": sent}}, upsert=True)
    return sent


async def run_rib_missing_reminders(db):
    """Relance l'investisseur sans RIB téléversé 7 jours après son adhésion."""
    now = _now()
    sent = 0
    async for a in db.investor_accounts.find({"status": {"$in": ["ACTIVE", "PAST_DUE"]}}, {"_id": 0}):
        if a.get("rib_reminder_sent"):
            continue
        created = datetime.fromisoformat(a["created_at"])
        if now - created < timedelta(days=7):
            continue
        bank = await db.investor_bank_details.find_one({"user_id": a["user_id"]})
        if bank and bank.get("rib_filename"):
            continue
        user = await db.users.find_one({"id": a["user_id"]})
        if not user or not user.get("email"):
            continue
        try:
            from brevo_service import send_email, _wrap_html
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"),
                subject="📎 Pensez à téléverser votre RIB pour recevoir vos remboursements",
                html_content=_wrap_html("RIB manquant", (
                    f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                    "<p style='font-size:14px;'>Votre espace investisseur est actif depuis plus de 7 jours "
                    "mais votre <b>RIB n'a pas encore été téléversé</b>. Sans RIB validé, aucun remboursement "
                    "d'investissement ne peut vous être versé. Rendez-vous dans votre espace, section "
                    "« Mes coordonnées bancaires », pour le téléverser en PDF ou PNG.</p>")),
                tags=["investor-banking"])
            await db.investor_accounts.update_one({"id": a["id"]}, {"$set": {"rib_reminder_sent": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Relance RIB manquant %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Relances RIB manquant : %d email(s)", sent)
    return sent


async def run_investor_j3_reminders(db):
    """Relance J-3 : prévient l'investisseur 3 jours avant son prélèvement mensuel."""
    now = _now()
    sent = 0
    async for a in db.investor_accounts.find({"status": {"$in": ["ACTIVE", "PAST_DUE"]}}, {"_id": 0}):
        due = _next_due(a["period_start"])
        if not (timedelta(0) < due - now <= timedelta(days=3)):
            continue
        period_key = a["period_start"][:7]
        if a.get("j3_reminder_period") == period_key:
            continue
        user = await db.users.find_one({"id": a["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if not user or not user.get("email"):
            continue
        plan = await db.investor_plans.find_one({"id": a["plan_id"]}) or {}
        try:
            from brevo_service import send_email, _wrap_html
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"),
                subject=f"⏳ Prélèvement de votre abonnement investisseur {a['plan_code']} dans 3 jours",
                html_content=_wrap_html("Échéance à venir", (
                    f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Le prélèvement mensuel de votre abonnement "
                    f"<b>{a['plan_code']}</b> ({plan.get('price_eur', 0):,.0f} €) aura lieu le "
                    f"<b>{due.strftime('%d/%m/%Y')}</b>. Merci de vérifier que votre carte bancaire "
                    "est valide et approvisionnée afin d'éviter toute interruption de votre capacité "
                    "CREDI'SCOP-INVEST.</p>").replace(",", " ")),
                tags=["investor-billing"],
            )
            await db.investor_accounts.update_one({"id": a["id"]}, {"$set": {"j3_reminder_period": period_key}})
            sent += 1
        except Exception as exc:
            logger.warning("Relance J-3 investisseur %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Relance J-3 investisseurs : %d email(s)", sent)
    return sent
