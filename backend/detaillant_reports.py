"""Tâches planifiées Détaillant : alerte DLC proche + bilan mensuel des ventes avec CSV."""
import base64
import logging
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
