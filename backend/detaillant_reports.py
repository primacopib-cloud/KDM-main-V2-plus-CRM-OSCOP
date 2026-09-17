"""Tâches planifiées Détaillant : alerte DLC proche + bilan mensuel des ventes avec CSV."""
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DLC_ALERT_DAYS = 30


def _now():
    return datetime.now(timezone.utc)


async def run_detaillant_dlc_alerts(db):
    """Cloche superadmin quand un lot périssable en salle approche de sa DLC (<30 j), idempotent."""
    limit = (_now() + timedelta(days=DLC_ALERT_DAYS)).date().isoformat()
    sent = 0
    async for a in db.auctions.find(
            {"source": "DETAILLANT", "status": {"$in": ["SCHEDULED", "LIVE"]},
             "dlc": {"$ne": None, "$lte": limit}, "dlc_alert_sent": {"$ne": True}}, {"_id": 0}):
        res = await db.auctions.update_one(
            {"id": a["id"], "dlc_alert_sent": {"$ne": True}}, {"$set": {"dlc_alert_sent": True}})
        if res.modified_count == 0:
            continue
        try:
            days = (datetime.fromisoformat(a["dlc"]).date() - _now().date()).days
        except ValueError:
            days = "?"
        try:
            from core_deps import create_notification
            await create_notification(
                "detaillant_dlc_alert", f"⏳ DLC proche — {a.get('reference')}",
                f"Le lot périssable « {a.get('title')} » ({(a.get('retailer') or {}).get('company_name', '')}) "
                f"atteint sa DLC le {'-'.join(reversed(a['dlc'].split('-')))} ({days} j). "
                "Ajustez le prix ou la programmation en salle.",
                {"auction_id": a["id"]})
            sent += 1
        except Exception as exc:
            logger.warning("Alerte DLC %s : %s", a.get("reference"), exc)
    if sent:
        logger.info("Alertes DLC détaillant envoyées : %s", sent)
    return sent


async def run_convention_version_reminders(db):
    """Cloche au POP'S dont la convention signée n'est plus à la version en vigueur (max 1/7 jours)."""
    from convention_cession import CONVENTION_VERSION
    now = _now()
    limit = (now - timedelta(days=7)).isoformat()
    sent = 0
    convs = await db.detaillant_conventions.find(
        {"version": {"$ne": CONVENTION_VERSION},
         "$or": [{"last_version_reminder_at": {"$exists": False}},
                 {"last_version_reminder_at": {"$lt": limit}}]},
        {"_id": 0, "user_id": 1, "version": 1}).to_list(200)
    for cv in convs:
        await db.detaillant_conventions.update_one(
            {"user_id": cv["user_id"]}, {"$set": {"last_version_reminder_at": now.isoformat()}})
        try:
            from core_deps import create_notification
            await create_notification(
                "convention_resign",
                "📜 Nouvelle convention cadre à signer",
                (f"La convention cadre POP'S COOP'ACT a été mise à jour (version {CONVENTION_VERSION} — "
                 f"vous avez signé la {cv['version']}). Merci de la re-signer depuis votre espace POP'S."),
                target_roles=[], target_user_id=cv["user_id"],
                data={"action_url": "/espace-detaillant"})
            sent += 1
        except Exception as exc:
            logger.warning("Relance convention %s : %s", cv["user_id"], exc)
        try:
            user = await db.users.find_one(
                {"id": cv["user_id"]}, {"_id": 0, "email": 1, "company_name": 1})
            if user and user.get("email"):
                import os
                base = os.environ.get("FRONTEND_URL", "").rstrip("/")
                from brevo_service import send_email, _wrap_html
                name = user.get("company_name") or ""
                subject = f"📜 Nouvelle convention cadre POP'S COOP'ACT à signer (v{CONVENTION_VERSION})"
                body = (
                    f"<p style='font-size:14px;'>Bonjour {name},</p>"
                    "<p style='font-size:14px;'>La convention cadre de partenariat POP'S COOP'ACT a été "
                    f"mise à jour (version <b>{CONVENTION_VERSION}</b> — vous avez signé la "
                    f"<b>{cv['version']}</b>). Merci de la relire et de la re-signer.</p>"
                    f"<p style='font-size:14px;'><a href='{base}/espace-detaillant' "
                    "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                    "text-decoration:none;font-weight:bold;'>Signer la nouvelle version</a></p>")
                await send_email(user["email"], name or None, subject, _wrap_html(subject, body),
                                 text_content=f"Nouvelle convention cadre POP'S v{CONVENTION_VERSION} à "
                                              f"re-signer : {base}/espace-detaillant",
                                 tags=["convention-resign"])
        except Exception as exc:
            logger.warning("Email relance convention %s : %s", cv["user_id"], exc)
    return sent


async def run_cession_sign_reminders(db):
    """Cloche au POP'S dont une offre PENDING attend la signature de sa fiche de cession (max 1/24 h)."""
    now = _now()
    limit_created = (now - timedelta(hours=2)).isoformat()
    limit_remind = (now - timedelta(hours=24)).isoformat()
    sent = 0
    cessions = await db.detaillant_cessions.find(
        {"status": "DRAFT", "created_at": {"$lt": limit_created},
         "$or": [{"last_sign_reminder_at": {"$exists": False}},
                 {"last_sign_reminder_at": {"$lt": limit_remind}}]},
        {"_id": 0, "id": 1, "offer_id": 1, "user_id": 1, "reference": 1}).to_list(100)
    for c in cessions:
        offer = await db.detaillant_offers.find_one(
            {"id": c["offer_id"]}, {"_id": 0, "status": 1, "product_name": 1})
        await db.detaillant_cessions.update_one(
            {"id": c["id"]}, {"$set": {"last_sign_reminder_at": now.isoformat()}})
        if not offer or offer.get("status") != "PENDING":
            continue
        try:
            from core_deps import create_notification
            await create_notification(
                "cession_sign_reminder",
                f"✍️ Fiche de cession à signer — {offer['product_name']}",
                (f"Votre offre « {offer['product_name']} » ne peut pas être validée tant que la fiche "
                 f"de cession {c['reference']} n'est pas signée. Ouvrez votre espace POP'S pour la signer."),
                target_roles=[], target_user_id=c["user_id"],
                data={"action_url": "/espace-detaillant"})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel signature cession %s : %s", c["reference"], exc)
    return sent


async def run_detaillant_weekly_recaps(db, force: bool = False):
    """Chaque lundi : email récap hebdo à chaque POP'S — ventes, followers et avis de la semaine."""
    now = _now()
    if not force and now.weekday() != 0:
        return 0
    week_key = (now - timedelta(days=7)).strftime("%G-W%V")
    flag = f"detaillant_weekly_recap_{week_key}"
    if not force and await db.system_flags.find_one({"key": flag}):
        return 0
    since = (now - timedelta(days=7)).isoformat()
    sent = 0
    user_ids = await db.detaillant_offers.distinct("user_id")
    for uid in user_ids:
        offer_ids = [o["id"] async for o in db.detaillant_offers.find({"user_id": uid}, {"_id": 0, "id": 1})]
        won = await db.auctions.find(
            {"detaillant_offer_id": {"$in": offer_ids}, "status": "WON",
             "winner.won_at": {"$gte": since}},
            {"_id": 0, "title": 1, "reference": 1, "winner": 1}).to_list(200)
        new_followers = await db.detaillant_followers.count_documents(
            {"detaillant_user_id": uid, "created_at": {"$gte": since}})
        reviews = await db.detaillant_shop_reviews.find(
            {"detaillant_user_id": uid, "created_at": {"$gte": since}},
            {"_id": 0, "rating": 1, "comment": 1}).to_list(100)
        if not won and not new_followers and not reviews:
            continue
        user = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "company_name": 1})
        if not user or not user.get("email"):
            continue
        revenue = round(sum((a.get("winner") or {}).get("price_eur") or 0 for a in won), 2)
        avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None
        await db.detaillant_weekly_recaps.update_one(
            {"user_id": uid, "week_key": week_key},
            {"$set": {"sales_count": len(won), "revenue_eur": revenue,
                      "new_followers": new_followers, "reviews_count": len(reviews),
                      "rating_avg": avg, "created_at": now.isoformat()},
             "$setOnInsert": {"id": str(uuid.uuid4())}}, upsert=True)
        name = user.get("company_name") or ""
        sales_html = ""
        if won:
            items = "".join(
                f"<li style='font-size:13px;'>{a.get('title')} — <b>"
                f"{((a.get('winner') or {}).get('price_eur') or 0):.2f} €</b>"
                f" · {(a.get('winner') or {}).get('name') or ''}</li>" for a in won)
            sales_html = f"<p style='font-size:13px;margin-bottom:4px;'><b>Lots vendus :</b></p><ul>{items}</ul>"
        reviews_html = ""
        if reviews:
            items = "".join(
                f"<li style='font-size:13px;'>{'★' * int(r['rating'])} — {r.get('comment') or ''}</li>"
                for r in reviews[:5])
            reviews_html = f"<p style='font-size:13px;margin-bottom:4px;'><b>Nouveaux avis :</b></p><ul>{items}</ul>"
        try:
            from brevo_service import send_email, _wrap_html
            subject = "🗓️ Votre récap hebdo POP'S — ventes, followers et avis"
            body = (
                f"<p style='font-size:14px;'>Bonjour {name},</p>"
                "<p style='font-size:14px;'>Voici votre activité COOP'ACT des 7 derniers jours :</p>"
                "<table style='font-size:13px;border-collapse:collapse'>"
                f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Lots vendus</td>"
                f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(won)}</b></td></tr>"
                f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Chiffre de la semaine</td>"
                f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{revenue:,.2f} €</b></td></tr>"
                f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Nouveaux followers</td>"
                f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{new_followers}</b></td></tr>"
                f"<tr><td style='padding:4px 10px'>Nouveaux avis</td>"
                f"<td style='padding:4px 10px;text-align:right'><b>{len(reviews)}"
                f"{f' (moyenne {avg}/5)' if avg else ''}</b></td></tr></table>"
                + sales_html + reviews_html +
                "<p style='font-size:12px;color:#B8A98F;'><b>POP'S — Vendeur éphémère en salle COOP'ACT</b>, "
                "agir ensemble pour la juste valeur.</p>")
            await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Récap hebdo POP'S : {len(won)} vente(s) ({revenue} €), "
                                          f"{new_followers} nouveau(x) follower(s), {len(reviews)} avis.",
                             tags=["detaillant-weekly-recap"])
            sent += 1
        except Exception as exc:
            logger.warning("Récap hebdo POP'S %s : %s", user.get("email"), exc)
    if not force:
        await db.system_flags.insert_one({"key": flag, "at": now.isoformat()})
    return sent


async def run_detaillant_monthly_reports(db, force: bool = False):
    """Chaque 1er du mois : email à chaque détaillant — récap de ses ventes du mois écoulé + CSV joint."""
    now = _now()
    if not force and now.day != 1:
        return 0
    prev = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    flag = f"detaillant_monthly_report_{prev}"
    if not force and await db.system_flags.find_one({"key": flag}):
        return 0
    sent = 0
    user_ids = await db.detaillant_offers.distinct("user_id")
    for uid in user_ids:
        offer_ids = [o["id"] async for o in db.detaillant_offers.find({"user_id": uid}, {"_id": 0, "id": 1})]
        lots = await db.auctions.find(
            {"detaillant_offer_id": {"$in": offer_ids},
             "$or": [{"starts_at": {"$regex": f"^{prev}"}}, {"winner.won_at": {"$regex": f"^{prev}"}}]},
            {"_id": 0}).to_list(300)
        if not lots:
            continue
        user = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "company_name": 1})
        if not user or not user.get("email"):
            continue
        won = [a for a in lots if a.get("status") == "WON"]
        revenue = round(sum((a.get("winner") or {}).get("price_eur") or 0 for a in won), 2)
        bids = sum(a.get("bids_count", 0) for a in lots)
        esc = lambda v: '"' + str(v if v is not None else "").replace('"', '""') + '"'
        rows = [";".join(esc(h) for h in ["Référence", "Lot", "Statut", "Mises", "Gagnant", "Montant (€)", "Début", "Fin"])]
        for a in lots:
            w = a.get("winner") or {}
            rows.append(";".join(esc(v) for v in [
                a.get("reference"), a.get("title"), a.get("status"), a.get("bids_count", 0),
                w.get("name") or "", f"{w.get('price_eur'):.2f}" if w.get("price_eur") else "",
                (a.get("starts_at") or "")[:10], (a.get("ends_at") or "")[:10]]))
        name = user.get("company_name") or ""
        try:
            from brevo_service import send_email, _wrap_html
            subject = f"📊 Bilan mensuel de vos ventes COOP'ACT — {prev}"
            body = (f"<p style='font-size:14px;'>Bonjour {name},</p>"
                    f"<p style='font-size:14px;'>Voici le bilan de vos lots en salle COOP'ACT pour <b>{prev}</b> :</p>"
                    "<table style='font-size:13px;border-collapse:collapse'>"
                    f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Lots en salle</td>"
                    f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(lots)}</b></td></tr>"
                    f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Mises reçues</td>"
                    f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{bids}</b></td></tr>"
                    f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Lots remportés</td>"
                    f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(won)}</b></td></tr>"
                    f"<tr><td style='padding:4px 10px'>Montant total</td>"
                    f"<td style='padding:4px 10px;text-align:right'><b>{revenue:,.2f} €</b></td></tr></table>"
                    "<p style='font-size:13px;'>Le détail de chaque lot est joint en CSV pour votre comptabilité.</p>"
                    "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, agir ensemble pour la juste valeur.</p>")
            attachments = [{"content": base64.b64encode(("\ufeff" + "\r\n".join(rows)).encode("utf-8")).decode(),
                            "name": f"ventes-coopact-{prev}.csv"}]
            await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                             html_content=_wrap_html(subject, body),
                             text_content=f"Bilan COOP'ACT {prev} : {len(lots)} lots, {bids} mises, "
                                          f"{len(won)} remportés, {revenue} €.",
                             tags=["detaillant-monthly-report"], attachments=attachments)
            sent += 1
        except Exception as exc:
            logger.warning("Bilan mensuel détaillant %s : %s", user.get("email"), exc)
    if not force:
        await db.system_flags.update_one(
            {"key": flag}, {"$set": {"key": flag, "at": now.isoformat(), "month": prev}}, upsert=True)
    if sent:
        logger.info("Bilans mensuels détaillants %s envoyés : %s", prev, sent)
    return sent
