"""Alerte retour en stock à la demande de l'acheteur (par produit et territoire)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from brevo_service import send_email, _wrap_html
from ws_manager import create_notification, send_notification

logger = logging.getLogger(__name__)

restock_alerts_router = APIRouter(prefix="/api/v2/catalog/restock-alerts", tags=["restock-alerts"])

db = None


def set_restock_alerts_database(database) -> None:
    global db
    db = database


from routes_catalog import get_current_user_catalog  # noqa: E402


class RestockAlertRequest(BaseModel):
    product_id: str
    zone_code: str


@restock_alerts_router.post("")
async def toggle_restock_alert(body: RestockAlertRequest, current_user: dict = Depends(get_current_user_catalog)):
    product = await db.products.find_one({"id": body.product_id}, {"_id": 0, "id": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    query = {"user_id": current_user["id"], "product_id": body.product_id, "zone_code": body.zone_code}
    existing = await db.restock_watchers.find_one(query)
    if existing:
        await db.restock_watchers.delete_one({"id": existing["id"]})
        return {"subscribed": False, "message": "Alerte retirée"}
    await db.restock_watchers.insert_one({
        **query,
        "id": str(uuid.uuid4()),
        "email": current_user.get("email"),
        "contact_name": current_user.get("contact_name") or current_user.get("name"),
        "product_name": product["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"subscribed": True, "message": f"Vous serez prévenu au retour de {product['name']} ({body.zone_code})"}


@restock_alerts_router.get("/mine")
async def my_restock_alerts(current_user: dict = Depends(get_current_user_catalog)):
    entries = await db.restock_watchers.find(
        {"user_id": current_user["id"]}, {"_id": 0, "product_id": 1, "zone_code": 1, "product_name": 1}
    ).to_list(200)
    return {"alerts": entries}


async def notify_restock_watchers(product_id: str, zone_code: str) -> int:
    """Notifie (in-app + email) les acheteurs abonnés au retour en stock, puis retire l'abonnement."""
    watchers = await db.restock_watchers.find({"product_id": product_id, "zone_code": zone_code}).to_list(500)
    sent = 0
    for w in watchers:
        title = "Produit de retour en stock"
        message = f"{w.get('product_name', 'Le produit')} est de nouveau disponible sur le territoire {zone_code}."
        try:
            notification = await create_notification(
                notification_type="restock_watch",
                title=title,
                message=message,
                target_user_id=w["user_id"],
                data={"product_id": product_id, "zone_code": zone_code},
                priority="normal",
            )
            await send_notification(notification)
        except Exception as exc:
            logger.warning("WS restock watch failed for %s: %s", w["user_id"], exc)
        if w.get("email"):
            body = f"""
              <h2 style="color:#D9B35A;margin:0 0 12px;font-size:18px;">Bonne nouvelle !</h2>
              <p style="color:rgba(255,255,255,0.8);font-size:14px;">
                Bonjour {w.get('contact_name') or ''},<br/><br/>
                <strong>{w.get('product_name', 'Le produit')}</strong> est de nouveau disponible
                sur le territoire <strong>{zone_code}</strong>.<br/>
                Rendez-vous sur le catalogue Pro KDMARCHÉ pour commander avant la prochaine rupture.
              </p>
            """
            try:
                await send_email(
                    to_email=w["email"], to_name=w.get("contact_name"),
                    subject=f"🛒 {w.get('product_name', 'Votre produit')} est de retour en stock ({zone_code})",
                    html_content=_wrap_html("Retour en stock", body),
                    tags=["restock-watch"],
                )
            except Exception as exc:
                logger.error("Restock watch email failed: %s", exc)
        await db.restock_watchers.delete_one({"id": w["id"]})
        sent += 1
    if sent:
        logger.info("Restock watch alerts for %s/%s: %d notified", product_id, zone_code, sent)
    return sent
