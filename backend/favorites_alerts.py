"""Alertes favoris : retour en stock & promo — notification in-app + email Brevo."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from brevo_service import send_email
from ws_manager import create_notification, send_notification

logger = logging.getLogger(__name__)

db = None


def set_favorites_alerts_database(database) -> None:
    global db
    db = database


ALERT_TEMPLATES = {
    "restock": {
        "title": "Produit de nouveau en stock",
        "message": "{product} est de nouveau disponible dans votre zone ({zone}).",
        "subject": "🛒 {product} est de retour en stock !",
    },
    "promo": {
        "title": "Promotion sur un favori",
        "message": "{product} passe à {new_price} € HT (au lieu de {old_price} €) — zone {zone}.",
        "subject": "🏷️ Promo sur {product} : {new_price} € HT",
    },
}


async def alert_favorites(product_id: str, zone_code: str, alert_type: str, extra: dict | None = None) -> int:
    """Notifie tous les acheteurs ayant ce produit en favori. Retourne le nb d'alertes envoyées."""
    extra = extra or {}
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        return 0

    tpl = ALERT_TEMPLATES[alert_type]
    fmt = {
        "product": product.get("name", "Votre produit favori"),
        "zone": zone_code,
        "new_price": f"{extra.get('new_price_cents', 0) / 100:.2f}",
        "old_price": f"{extra.get('old_price_cents', 0) / 100:.2f}",
    }
    title = tpl["title"]
    message = tpl["message"].format(**fmt)
    subject = tpl["subject"].format(**fmt)

    cursor = db.user_favorites.find({"favorites.product_id": product_id}, {"_id": 0, "user_id": 1, "favorites": 1})
    fav_docs = await cursor.to_list(1000)
    sent = 0
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for doc in fav_docs:
        user_id = doc["user_id"]
        entry = next((f for f in doc.get("favorites", []) if f.get("product_id") == product_id), None)
        if entry and entry.get("alerts_enabled", True) is False:
            continue
        already = await db.favorites_alerts_log.find_one({
            "user_id": user_id, "product_id": product_id,
            "alert_type": alert_type, "sent_at": {"$gte": cutoff},
        })
        if already:
            continue

        notification = await create_notification(
            notification_type=f"favorite_{alert_type}",
            title=title,
            message=message,
            target_user_id=user_id,
            data={"product_id": product_id, "zone_code": zone_code, **extra},
            priority="normal",
        )
        try:
            await send_notification(notification)
        except Exception as exc:
            logger.warning(f"WS favorite alert failed for {user_id}: {exc}")

        user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1, "first_name": 1})
        if user and user.get("email"):
            try:
                await send_email(
                    to_email=user["email"],
                    to_name=user.get("name") or user.get("first_name"),
                    subject=subject,
                    html_content=_email_html(title, message, product),
                    tags=["favorite-alert", alert_type],
                )
            except Exception as exc:
                logger.warning(f"Email favorite alert failed for {user['email']}: {exc}")

        await db.favorites_alerts_log.insert_one({
            "user_id": user_id, "product_id": product_id,
            "alert_type": alert_type, "zone_code": zone_code,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        sent += 1

    logger.info(f"Favorites alert '{alert_type}' for product {product_id}: {sent} notified")
    return sent


def _email_html(title: str, message: str, product: dict) -> str:
    return f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;padding:24px;background:#faf6ec;border-radius:12px;">
      <h2 style="color:#1f3a5f;margin-top:0;">{title}</h2>
      <p style="font-size:15px;color:#333;">{message}</p>
      <p style="margin:24px 0;">
        <a href="{_catalog_url()}" style="background:#D9B35A;color:#1f3a5f;padding:12px 24px;border-radius:24px;text-decoration:none;font-weight:bold;">
          Voir le catalogue
        </a>
      </p>
      <p style="font-size:12px;color:#888;">KDMARCHÉ × O'SCOP — alerte sur vos produits favoris.</p>
    </div>
    """


def _catalog_url() -> str:
    import os
    return f"{os.environ.get('FRONTEND_BASE_URL', '')}/catalogue"
