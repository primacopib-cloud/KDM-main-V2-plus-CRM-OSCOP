"""Alerte admin : campagne proche de sa clôture (<48h) avec des lots actifs sans aucune offre."""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

db = None

ACTIVE_STATUSES = ["PUBLIEE", "INSCRIPTIONS_OUVERTES", "EN_COURS"]


def _parse(dt: str):
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def check_campaign_closure_alerts(database) -> int:
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=48)
    alerted = 0
    async for camp in db.campaigns.find({"no_offer_alert_sent": {"$ne": True}}, {"_id": 0}):
        closes = _parse(camp.get("closes_at"))
        if not closes or not (now < closes <= horizon):
            continue
        from routes_bids import _latest_valid_bids
        lots_no_offer = []
        async for c in db.consultations.find(
                {"campaign_id": camp["id"], "status": {"$in": ACTIVE_STATUSES}},
                {"_id": 0, "id": 1, "ref": 1, "title": 1, "status": 1}):
            if not await _latest_valid_bids(c["id"]):
                lots_no_offer.append(c)
        if not lots_no_offer:
            continue
        refs = ", ".join(l["ref"] for l in lots_no_offer)
        hours_left = int((closes - now).total_seconds() // 3600)
        try:
            from core_deps import create_notification
            await create_notification(
                "campaign_no_offer",
                f"Campagne « {camp['name']} » : {len(lots_no_offer)} lot(s) sans offre",
                f"Clôture dans ~{hours_left}h — aucun fournisseur n'a déposé d'offre sur : {refs}. "
                "Envisagez une relance des vendeurs ou un report du calendrier.",
                target_roles=["oscop_super_admin", "kdm_b2b_admin"],
                data={"link": "/superadmin", "campaign_id": camp["id"]})
        except Exception as exc:
            logger.warning("Notif campagne %s : %s", camp["id"], exc)
        try:
            from brevo_service import send_email
            from email_alerts import ADMIN_ALERT_EMAIL
            admin_email = __import__("os").environ.get("ADMIN_ALERT_EMAIL", ADMIN_ALERT_EMAIL)
            lots_html = "".join(f"<li><strong>{l['ref']}</strong> — {l['title']} ({l['status'].replace('_', ' ')})</li>"
                                for l in lots_no_offer)
            await send_email(
                to_email=admin_email, to_name="Admin KDMARCHÉ × O'SCOP",
                subject=f"⚠️ Campagne « {camp['name']} » : clôture dans ~{hours_left}h sans offre",
                html_content=f"""<h2 style="color:#451F6B;">Campagne proche de la clôture — lots sans offre</h2>
                <p>La campagne <strong>{camp['name']}</strong> se clôture le
                <strong>{str(camp.get('closes_at'))[:16].replace('T', ' ')}</strong> (dans ~{hours_left}h)
                et <strong>{len(lots_no_offer)} lot(s)</strong> actifs n'ont reçu aucune offre :</p>
                <ul>{lots_html}</ul>
                <p>Envisagez une relance ciblée des vendeurs ou un report du calendrier de campagne.</p>""",
                tags=["campaign-no-offer-alert"])
        except Exception as exc:
            logger.warning("Email alerte campagne %s : %s", camp["id"], exc)
        await db.campaigns.update_one({"id": camp["id"]}, {"$set": {
            "no_offer_alert_sent": True, "no_offer_alert_at": now.isoformat()}})
        alerted += 1
    if alerted:
        logger.info("Alertes campagne sans offre : %d envoyées", alerted)
    return alerted
