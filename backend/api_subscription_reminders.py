"""Rappel d'expiration des abonnements API annuels — email J-30 avec lien de renouvellement (idempotent)."""
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def run_api_subscription_expiry_reminders(db) -> int:
    now = datetime.now(timezone.utc)
    limit = (now + timedelta(days=30)).isoformat()
    sent = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE",
        "expiry_reminder_sent": {"$ne": True},
        "valid_until": {"$gt": now.isoformat(), "$lte": limit},
    })
    async for sub in cursor:
        try:
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            vu = str(sub.get("valid_until") or "")
            days_left = max((datetime.fromisoformat(vu) - now).days, 0)
            await send_email(
                to_email=sub["email"], to_name=sub.get("contact_name"),
                subject=f"⏳ Votre abonnement API expire dans {days_left} jour(s) — renouvelez en un clic",
                html_content=_wrap_html("Renouvellement de votre abonnement API", (
                    f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Votre abonnement annuel à l'API coopérative "
                    f"(<b>{sub['reference']}</b>) arrive à échéance le "
                    f"<b>{vu[8:10]}/{vu[5:7]}/{vu[:4]}</b>.</p>"
                    "<p style='font-size:14px;'>Renouvelez dès maintenant pour conserver votre accès sans "
                    "interruption : votre nouvelle année démarrera à la fin de la période en cours.</p>"
                    f"<p style='text-align:center;'><a href='{base}/coop-api' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Renouveler mon abonnement — "
                    f"{float(sub.get('amount_eur') or 2500):,.0f} €</a></p>")),
                tags=["api-subscription-renewal"])
            await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {
                "expiry_reminder_sent": True, "expiry_reminder_at": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel expiration abonnement API %s : %s", sub.get("reference"), exc)
    if sent:
        logger.info("Rappels expiration abonnement API envoyés : %s", sent)
    return sent


async def send_quota_alert(db, key: dict, usage: int, quota: int) -> None:
    """Alerte 80 % du quota mensuel — envoyée une fois par mois et par clé (best-effort)."""
    try:
        from brevo_service import send_email, _wrap_html
        base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
        pct = round(usage / quota * 100)
        await send_email(
            to_email=key["partner_email"], to_name=None,
            subject=f"⚠️ Votre clé API a atteint {pct} % de son quota mensuel ({usage:,}/{quota:,} requêtes)",
            html_content=_wrap_html("Alerte quota API", (
                "<p style='font-size:14px;'>Bonjour,</p>"
                f"<p style='font-size:14px;'>Votre clé API <b>{key.get('prefix')}</b> a consommé "
                f"<b>{usage:,}</b> requêtes sur <b>{quota:,}</b> ce mois-ci ({pct} %).</p>"
                "<p style='font-size:14px;'>Au-delà du quota, les appels seront refusés jusqu'au début du "
                "mois suivant. Pensez à optimiser vos synchronisations ou contactez la Centrale pour "
                "ajuster votre quota.</p>"
                f"<p style='text-align:center;'><a href='{base}/coop-api' "
                "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                "padding:12px 26px;border-radius:12px;text-decoration:none;'>Voir ma consommation</a></p>")),
            tags=["api-quota-alert"])
        logger.info("Alerte quota 80%% envoyée : %s (%s/%s)", key.get("partner_email"), usage, quota)
    except Exception as exc:
        logger.warning("Alerte quota API : %s", exc)


def _fmt_order_dt(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value or "")[:16].replace("T", " ")


async def _build_weekly_orders_csv(db, orders: list, label: str) -> dict:
    """CSV comptable des commandes du relais (UTF-8 BOM, séparateur ';') joint aux résumés hebdo/mensuel."""
    import base64
    import csv
    import io
    user_ids = sorted({o.get("user_id") for o in orders if o.get("user_id")})
    customers = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}},
                                     {"_id": 0, "id": 1, "contact_name": 1, "company_name": 1, "phone": 1}):
            customers[u["id"]] = u
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["N° commande", "Date", "Statut", "Client", "Téléphone", "Articles",
                     "Total (€)", "Paiement", "Créneau retrait"])
    for o in sorted(orders, key=lambda x: str(x.get("created_at") or "")):
        cust = customers.get(o.get("user_id"), {})
        articles = sum(int(i.get("qty") or 0) for i in (o.get("items") or []))
        total = f"{(int(o.get('total_cents') or 0) / 100):.2f}".replace(".", ",")
        slot = " ".join(p for p in [str(o.get("pickup_date") or ""), str(o.get("pickup_slot_label") or "")] if p)
        writer.writerow([
            o.get("order_number") or "", _fmt_order_dt(o.get("created_at")), o.get("status") or "",
            cust.get("contact_name") or cust.get("company_name") or "", cust.get("phone") or "",
            articles, total, "UC (cagnotte)" if o.get("pay_with_uc") else "Carte bancaire", slot,
        ])
    return {"content": base64.b64encode(buf.getvalue().encode("utf-8-sig")).decode(),
            "name": f"commandes-relais-{label}.csv"}


async def run_api_weekly_reports(db, force: bool = False) -> int:
    """Résumé hebdomadaire (lundi) : commandes du relais + activité API de la semaine écoulée (idempotent)."""
    now = datetime.now(timezone.utc)
    if now.weekday() != 0 and not force:
        return 0
    week_key = now.strftime("%G-W%V")
    since = (now - timedelta(days=7)).isoformat()
    sent = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE", "api_key_id": {"$exists": True},
        "weekly_report_week": {"$ne": week_key},
    })
    async for sub in cursor:
        try:
            user = await db.users.find_one({"id": sub["user_id"]}, {"_id": 0, "id": 1})
            point = await db.lolodrive_points.find_one(
                {"manager_user_id": (user or {}).get("id")}, {"_id": 0, "id": 1, "name": 1})
            orders, total_cents, by_status = [], 0, {}
            if point:
                orders = await db.lolodrive_orders.find(
                    {"lolo_point_id": point["id"], "created_at": {"$gte": datetime.fromisoformat(since)}},
                    {"_id": 0, "order_number": 1, "created_at": 1, "status": 1, "user_id": 1, "items": 1,
                     "total_cents": 1, "pay_with_uc": 1, "pickup_date": 1, "pickup_slot_label": 1}).to_list(1000)
                total_cents = sum(int(o.get("total_cents") or 0) for o in orders)
                for o in orders:
                    by_status[o.get("status") or "?"] = by_status.get(o.get("status") or "?", 0) + 1
            api_calls = await db.api_call_logs.count_documents({"key_id": sub["api_key_id"], "ts": {"$gte": since}})
            hooks_ok = await db.webhook_deliveries.count_documents(
                {"key_id": sub["api_key_id"], "ts": {"$gte": since}, "ok": True})
            hooks_ko = await db.webhook_deliveries.count_documents(
                {"key_id": sub["api_key_id"], "ts": {"$gte": since}, "ok": False, "paused": {"$ne": True}})
            key = await db.api_keys.find_one({"id": sub["api_key_id"]},
                                             {"_id": 0, "webhook_url": 1, "webhook_paused": 1})
            hook_paused = bool((key or {}).get("webhook_paused")) and bool((key or {}).get("webhook_url"))
            csv_attachment = await _build_weekly_orders_csv(db, orders, week_key)
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            statuses = " · ".join(f"{k} : {v}" for k, v in sorted(by_status.items())) or "aucune"
            await send_email(
                to_email=sub["email"], to_name=sub.get("contact_name"),
                subject=f"📊 Votre semaine API — {len(orders)} commande(s) sur votre relais{' ' + point['name'] if point else ''}",
                html_content=_wrap_html("Résumé hebdomadaire — API coopérative", (
                    f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Voici l'activité de la semaine écoulée pour votre abonnement "
                    f"<b>{sub['reference']}</b>{' — relais <b>' + point['name'] + '</b>' if point else ''} :</p>"
                    "<ul style='font-size:14px;'>"
                    f"<li><b>{len(orders)}</b> commande(s) LOLODRIVE ({total_cents / 100:.2f} €) — {statuses}</li>"
                    f"<li><b>{api_calls}</b> appel(s) API effectué(s)</li>"
                    f"<li><b>{hooks_ok}</b> webhook(s) livré(s)" + (f" · <b style='color:#c0392b;'>{hooks_ko} en échec</b>" if hooks_ko else "") + "</li>"
                    + (f"<li><b style='color:#F5A623;'>⏸ Webhook en pause</b> — les notifications temps réel sont "
                       "suspendues ; votre configuration (URL et événements) est conservée.</li>" if hook_paused else "")
                    + "</ul>"
                    "<p style='font-size:13px;color:rgba(243,237,228,0.7);'>📎 Le détail comptable des commandes "
                    "de la semaine est joint à cet email (fichier CSV, ouvrable dans Excel).</p>"
                    f"<p style='text-align:center;'><a href='{base}/coop-api' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Voir mon espace API</a></p>")),
                tags=["api-weekly-report"],
                attachments=[csv_attachment])
            await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {"weekly_report_week": week_key}})
            sent += 1
        except Exception as exc:
            logger.warning("Résumé hebdo API %s : %s", sub.get("reference"), exc)
    if sent:
        logger.info("Résumés hebdo API envoyés : %s", sent)
    return sent


async def run_api_monthly_reports(db, force: bool = False) -> int:
    """Résumé mensuel consolidé (1er-5 du mois) : CSV comptable des commandes du mois écoulé (idempotent)."""
    now = datetime.now(timezone.utc)
    if now.day > 5 and not force:
        return 0
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)
    month_key = prev_start.strftime("%Y-%m")
    month_label = prev_start.strftime("%m/%Y")
    sent = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE", "api_key_id": {"$exists": True},
        "monthly_report_month": {"$ne": month_key},
    })
    async for sub in cursor:
        try:
            user = await db.users.find_one({"id": sub["user_id"]}, {"_id": 0, "id": 1})
            point = await db.lolodrive_points.find_one(
                {"manager_user_id": (user or {}).get("id")}, {"_id": 0, "id": 1, "name": 1})
            orders, total_cents, by_status = [], 0, {}
            if point:
                orders = await db.lolodrive_orders.find(
                    {"lolo_point_id": point["id"], "created_at": {"$gte": prev_start, "$lt": month_start}},
                    {"_id": 0, "order_number": 1, "created_at": 1, "status": 1, "user_id": 1, "items": 1,
                     "total_cents": 1, "pay_with_uc": 1, "pickup_date": 1, "pickup_slot_label": 1}).to_list(5000)
                total_cents = sum(int(o.get("total_cents") or 0) for o in orders)
                for o in orders:
                    by_status[o.get("status") or "?"] = by_status.get(o.get("status") or "?", 0) + 1
            csv_attachment = await _build_weekly_orders_csv(db, orders, month_key)
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            statuses = " · ".join(f"{k} : {v}" for k, v in sorted(by_status.items())) or "aucune"
            await send_email(
                to_email=sub["email"], to_name=sub.get("contact_name"),
                subject=f"🧾 Clôture {month_label} — {len(orders)} commande(s) sur votre relais{' ' + point['name'] if point else ''} (CSV joint)",
                html_content=_wrap_html("Résumé mensuel — clôture comptable", (
                    f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Voici le consolidé du mois de <b>{month_label}</b> pour votre abonnement "
                    f"<b>{sub['reference']}</b>{' — relais <b>' + point['name'] + '</b>' if point else ''} :</p>"
                    "<ul style='font-size:14px;'>"
                    f"<li><b>{len(orders)}</b> commande(s) LOLODRIVE — total <b>{total_cents / 100:.2f} €</b></li>"
                    f"<li>Ventilation par statut : {statuses}</li>"
                    "</ul>"
                    "<p style='font-size:13px;color:rgba(243,237,228,0.7);'>📎 Le détail complet des commandes du mois "
                    "est joint à cet email (fichier CSV, ouvrable dans Excel) pour votre clôture comptable.</p>"
                    f"<p style='text-align:center;'><a href='{base}/coop-api' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Voir mon espace API</a></p>")),
                tags=["api-monthly-report"],
                attachments=[csv_attachment])
            await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {"monthly_report_month": month_key}})
            sent += 1
        except Exception as exc:
            logger.warning("Résumé mensuel API %s : %s", sub.get("reference"), exc)
    if sent:
        logger.info("Résumés mensuels API envoyés : %s", sent)
    return sent


async def run_api_subscription_expirations(db) -> int:
    """Désactive la clé API des abonnements arrivés à expiration sans renouvellement (idempotent)."""
    now = datetime.now(timezone.utc).isoformat()
    deactivated = 0
    cursor = db.api_subscriptions.find({
        "status": "ACTIVE",
        "valid_until": {"$lt": now},
        "key_deactivated_at": {"$exists": False},
        "api_key_id": {"$exists": True},
    })
    async for sub in cursor:
        await db.api_keys.update_one({"id": sub["api_key_id"]}, {"$set": {"is_active": False}})
        await db.api_subscriptions.update_one({"id": sub["id"]}, {"$set": {
            "status": "EXPIRED", "key_deactivated_at": now}})
        deactivated += 1
        logger.info("Clé API désactivée (abonnement expiré) : %s (%s)", sub.get("reference"), sub.get("email"))
        try:
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            await send_email(
                to_email=sub["email"], to_name=sub.get("contact_name"),
                subject=f"🔴 Votre clé API a été désactivée — renouvelez pour la réactiver ({sub['reference']})",
                html_content=_wrap_html("Abonnement API expiré", (
                    f"<p style='font-size:14px;'>Bonjour {sub.get('contact_name') or ''},</p>"
                    f"<p style='font-size:14px;'>Votre abonnement annuel à l'API coopérative "
                    f"(<b>{sub['reference']}</b>) est arrivé à échéance : votre clé API a été "
                    "<b>désactivée</b> et les appels depuis votre outil sont bloqués.</p>"
                    "<p style='font-size:14px;'>Renouvelez dès maintenant : votre <b>clé existante sera "
                    "réactivée automatiquement</b>, sans rien reconfigurer.</p>"
                    f"<p style='text-align:center;'><a href='{base}/coop-api' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Renouveler mon abonnement — "
                    f"{float(sub.get('amount_eur') or 2500):,.0f} €</a></p>")),
                tags=["api-subscription-expired"])
        except Exception as exc:
            logger.warning("Email relance expiration %s : %s", sub.get("reference"), exc)
    return deactivated
