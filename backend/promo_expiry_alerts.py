"""Relance vendeur 3 jours avant l'expiration de la dernière promo d'un produit."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_vendor_promo_renewal_reminders(db) -> int:
    """Pour chaque produit dont la promo la plus tardive expire sous 3 jours :
    notifie le vendeur (in-app + email) une seule fois par date d'expiration."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=3, hours=12)
    sent = 0
    async for zp in db.zone_prices.find(
            {"is_active": True, "promo_end": {"$gt": now, "$lte": horizon}}, {"_id": 0}):
        product_id, zone, promo_end = zp["product_id"], zp["zone_code"], zp["promo_end"]
        latest = await db.zone_prices.find_one(
            {"product_id": product_id, "is_active": True, "promo_end": {"$gt": promo_end}},
            {"_id": 0, "zone_code": 1})
        if latest:
            continue  # une promo plus tardive existe : pas encore la fin
        product = await db.products.find_one({"id": product_id},
                                             {"_id": 0, "name": 1, "sku": 1, "vendor_id": 1,
                                              "promo_renewal_reminded_at": 1})
        if not product or not product.get("vendor_id"):
            continue
        if product.get("promo_renewal_reminded_at") == promo_end.isoformat():
            continue  # déjà relancé pour cette date
        days_left = max(1, int(-(-(promo_end - now).total_seconds() // 86400)))
        user = await db.users.find_one({"vendor_id": product["vendor_id"]}, {"_id": 0, "id": 1})
        body = (f"Votre promotion sur « {product.get('name')} » (zone {zone}) se termine dans {days_left} jour(s). "
                "C'est votre dernière promo active pour ce produit : sans prolongation, il repassera au tarif standard "
                "et pourra disparaître de la vitrine promo du catalogue.")
        try:
            from core_deps import create_notification
            await create_notification("promo_expiry", f"Fin de promo dans {days_left} j — {product.get('name')}",
                                      body, target_roles=["direct"], target_user_id=user["id"],
                                      data={"link": "/vendor?tab=products"})
        except Exception as exc:
            logger.warning("Notif relance promo %s : %s", product_id, exc)
        vendor = await db.vendors.find_one({"id": product["vendor_id"]}, {"_id": 0, "email": 1, "company_name": 1})
        if vendor and vendor.get("email"):
            try:
                from brevo_service import send_email
                await send_email(
                    to_email=vendor["email"], to_name=vendor.get("company_name"),
                    subject=f"⏳ Promo en fin de course — {product.get('name')} : {days_left} jour(s) restant(s)",
                    html_content=(f"<p>Bonjour,</p><p>{body}</p>"
                                  "<p>Pour la prolonger, contactez votre gestionnaire de catalogue ou ajustez-la "
                                  "depuis votre espace vendeur.</p>"
                                  "<p>L'équipe CommunityPlace — O'SCOP × KDMARCHÉ</p>"),
                    tags=["promo-expiry-reminder"])
            except Exception as exc:
                logger.warning("Email relance promo %s : %s", product_id, exc)
        await db.products.update_one({"id": product_id},
                                     {"$set": {"promo_renewal_reminded_at": promo_end.isoformat()}})
        sent += 1
    if sent:
        logger.info("Relances promo vendeur : %d envoyées", sent)
    return sent
