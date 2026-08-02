"""Alertes de seuil de plafond RàR + envoi mensuel automatique du relevé PDF (cron)."""
import base64
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def _org_members(db, org_id: str) -> list:
    members = await db.org_memberships.find({"org_id": org_id}).to_list(3)
    return await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                               {"email": 1, "contact_name": 1}).to_list(3)


async def _org_name(db, org_id: str) -> str:
    org = await db.orgs.find_one({"id": org_id}, {"legal_name": 1, "name": 1}) or \
        await db.organizations.find_one({"id": org_id}, {"legal_name": 1, "name": 1}) or {}
    return org.get("legal_name") or org.get("name") or org_id


async def check_ceiling_alert(db, org_id: str):
    """Alerte email si le plafond disponible passe sous le seuil choisi ; réarme au-dessus."""
    if not org_id:
        return
    account = await db.rar_accounts.find_one({"org_id": org_id})
    threshold = (account or {}).get("alert_threshold_cents") or 0
    if not account or account.get("status") != "APPROVED" or threshold <= 0:
        return
    from routes_rar import rar_status_payload
    available = (await rar_status_payload(org_id))["available_cents"]
    if available >= threshold:
        if account.get("alert_active"):
            await db.rar_accounts.update_one({"org_id": org_id}, {"$set": {"alert_active": False}})
        return
    if account.get("alert_active"):
        return
    await db.rar_accounts.update_one(
        {"org_id": org_id}, {"$set": {"alert_active": True, "alert_sent_at": datetime.utcnow()}})
    await db.rar_alert_log.insert_one({
        "org_id": org_id, "threshold_cents": threshold, "available_cents": available,
        "sent_at": datetime.utcnow()})
    from brevo_service import send_email, _wrap_html
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    subject = "⚠️ Plafond Règlement à Réception Pro sous votre seuil d'alerte"
    body = (f"<p>Bonjour,</p><p>Votre plafond immédiatement disponible est passé à "
            f"<b>{available / 100:.2f} €</b>, sous le seuil d'alerte que vous avez fixé "
            f"(<b>{threshold / 100:.2f} €</b>).</p>"
            f"<p>Le plafond se rétablit automatiquement au fur et à mesure de l'encaissement de vos règlements.</p>"
            f"<p><a href='{base}/espace-acheteur' style='background:#D9B35A;color:#000;padding:10px 18px;"
            f"border-radius:10px;text-decoration:none;font-weight:bold'>Voir mon plafond</a></p>")
    for u in await _org_members(db, org_id):
        if not u.get("email"):
            continue
        try:
            await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                             html_content=_wrap_html(subject, body), text_content=subject,
                             tags=["rar_ceiling_alert"])
        except Exception as exc:
            logger.warning("Alerte plafond non envoyée %s : %s", u.get("email"), exc)
    logger.info("Alerte plafond envoyée org %s (dispo %s < seuil %s)", org_id, available, threshold)


async def run_monthly_statements(db, force_month: str = None) -> int:
    """Le 1er du mois : envoie le relevé PDF du mois écoulé aux acheteurs RàR actifs."""
    now = datetime.utcnow()
    if force_month:
        month = force_month
    else:
        if now.day != 1:
            return 0
        month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    sent = 0
    async for account in db.rar_accounts.find({"status": "APPROVED"}):
        org_id = account["org_id"]
        if await db.rar_statement_log.find_one({"org_id": org_id, "month": month}):
            continue
        from routes_rar_delivery import compute_ceiling_events
        events = [e for e in await compute_ceiling_events(org_id) if str(e["date"] or "")[:7] == month]
        if not events:
            continue
        org_name = await _org_name(db, org_id)
        from pdf_ceiling_statement import MONTHS_FR, build_ceiling_statement_pdf
        pdf = build_ceiling_statement_pdf(org_name, month, events, account.get("ceiling_cents") or 0)
        period = f"{MONTHS_FR[int(month[5:]) - 1]} {month[:4]}"
        from brevo_service import send_email, _wrap_html
        subject = f"📄 Votre relevé de plafond — {period}"
        body = (f"<p>Bonjour,</p><p>Veuillez trouver ci-joint votre relevé mensuel de plafond "
                f"<b>Règlement à Réception Pro</b> pour la période de <b>{period}</b> "
                f"({len(events)} mouvement(s)).</p>"
                f"<p>Ce document peut être joint à votre comptabilité.</p>")
        ok = False
        for u in await _org_members(db, org_id):
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_monthly_statement"],
                                 attachments=[{"content": base64.b64encode(pdf).decode(),
                                               "name": f"releve-plafond-{month}.pdf"}])
                ok = True
            except Exception as exc:
                logger.warning("Relevé mensuel non envoyé %s : %s", u.get("email"), exc)
        if ok:
            sent += 1
            await db.rar_statement_log.insert_one(
                {"org_id": org_id, "month": month, "events": len(events), "sent_at": datetime.utcnow()})
    if sent:
        logger.info("Relevés mensuels de plafond envoyés : %s (%s)", sent, month)
    return sent


async def run_annual_statements(db, force_year: str = None) -> int:
    """Début janvier : envoie le relevé annuel PDF de l'exercice écoulé aux acheteurs RàR actifs."""
    now = datetime.utcnow()
    if force_year:
        year = force_year
    else:
        if now.month != 1 or now.day > 5:
            return 0
        year = str(now.year - 1)
    sent = 0
    async for account in db.rar_accounts.find({"status": "APPROVED"}):
        org_id = account["org_id"]
        if await db.rar_statement_log.find_one({"org_id": org_id, "month": f"ANNUEL-{year}"}):
            continue
        from routes_rar_delivery import compute_ceiling_events
        events = [e for e in await compute_ceiling_events(org_id) if str(e["date"] or "")[:4] == year]
        if not events:
            continue
        org_name = await _org_name(db, org_id)
        from pdf_ceiling_statement import build_ceiling_annual_pdf
        pdf = build_ceiling_annual_pdf(org_name, year, events, account.get("ceiling_cents") or 0)
        from brevo_service import send_email, _wrap_html
        subject = f"📊 Votre relevé annuel de plafond — exercice {year}"
        body = (f"<p>Bonjour,</p><p>Veuillez trouver ci-joint votre relevé annuel de plafond "
                f"<b>Règlement à Réception Pro</b> pour l'exercice <b>{year}</b> "
                f"({len(events)} mouvement(s), synthèse mensuelle incluse).</p>"
                f"<p>Ce document récapitulatif peut être joint à votre bilan comptable.</p>")
        ok = False
        for u in await _org_members(db, org_id):
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_annual_statement"],
                                 attachments=[{"content": base64.b64encode(pdf).decode(),
                                               "name": f"releve-plafond-annuel-{year}.pdf"}])
                ok = True
            except Exception as exc:
                logger.warning("Relevé annuel non envoyé %s : %s", u.get("email"), exc)
        if ok:
            sent += 1
            await db.rar_statement_log.insert_one(
                {"org_id": org_id, "month": f"ANNUEL-{year}", "events": len(events), "sent_at": datetime.utcnow()})
    if sent:
        logger.info("Relevés annuels de plafond envoyés : %s (%s)", sent, year)
    return sent
