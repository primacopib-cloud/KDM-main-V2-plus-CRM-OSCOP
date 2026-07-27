"""Annulation automatique des commandes Drive jamais retirées 48 h après leur mise à disposition."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def _restock_order(db, order):
    """Ré-incrémente le stock des articles si celui-ci avait été décrémenté."""
    if not order.get("stock_applied"):
        return
    from pymongo import ReturnDocument
    from routes_relay_products import log_stock_movement
    point_code = None
    if order.get("lolo_point_id"):
        pt = await db.lolodrive_points.find_one({"id": order["lolo_point_id"]}, {"_id": 0, "code": 1})
        point_code = (pt or {}).get("code")
    for l in order.get("items", []):
        res = await db.lolodrive_products.find_one_and_update(
            {"sku": l["sku"], "stock_qty": {"$ne": None}},
            [{"$set": {"stock_qty": {"$add": [{"$ifNull": ["$stock_qty", 0]}, l.get("qty", 0)]}}}],
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "stock_qty": 1})
        if res is not None:
            await log_stock_movement(l["sku"], l.get("name", l["sku"]), "RESTOCK", l.get("qty", 0),
                                     res["stock_qty"], point_code, order.get("order_number"))
    await db.lolodrive_orders.update_one({"id": order["id"]}, {"$set": {"stock_applied": False}})


async def run_auto_cancellations(db, now=None) -> int:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(hours=48)
    cancelled = 0
    async for o in db.lolodrive_orders.find({
            "status": "READY", "channel": {"$ne": "COUNTER"},
            "ready_at": {"$lte": cutoff}}, {"_id": 0}):
        num = o.get("order_number")
        point_name = "votre relais LOLODRIVE"
        if o.get("lolo_point_id"):
            pt = await db.lolodrive_points.find_one({"id": o["lolo_point_id"]}, {"_id": 0, "name": 1})
            if pt:
                point_name = pt["name"]
        try:
            await _restock_order(db, o)
            await db.lolodrive_orders.update_one(
                {"id": o["id"]},
                {"$set": {"status": "CANCELLED", "cancelled_at": now, "updated_at": now,
                          "cancel_reason": "NO_PICKUP_48H", "auto_cancelled": True}})
            user = await db.users.find_one({"id": o.get("user_id")},
                                           {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
            if user:
                await _notify_client(user, o, num, point_name)
            cancelled += 1
            logger.info("Commande %s annulée automatiquement (non retirée 48h)", num)
        except Exception as exc:
            logger.warning("Annulation auto %s échouée : %s", num, exc)
    if cancelled:
        logger.info("Annulations auto non-retrait : %d", cancelled)
    return cancelled


async def _notify_client(user, order, num, point_name):
    from brevo_service import send_email, send_sms, _wrap_html
    first = ((user.get("contact_name") or "").split() or [""])[0]
    penalty = order.get("no_pickup_penalty_uc")
    pen_html = ""
    if penalty:
        pen_html = (f"<p style='color:#777;font-size:12px'>La pénalité de non-retrait de "
                    f"<strong>{penalty:g} UC ({penalty / 10:.2f} €)</strong> reste applicable.</p>")
    if user.get("email"):
        subject = f"❌ Commande {num} annulée — non retirée sous 48 h"
        body = f"""
          <p>Bonjour{f' {first}' if first else ''},</p>
          <p>Votre commande <strong>{num}</strong> préparée chez <strong>{point_name}</strong>
          n'a pas été retirée dans les 48 heures suivant sa mise à disposition.</p>
          <p>Elle a donc été <strong style='color:#dc2626'>annulée</strong> et ses articles ont été
          remis en vente.</p>
          {pen_html}
          <p>Vous pouvez repasser commande à tout moment sur votre espace PASS.</p>
          <p style='color:#999;font-size:11px;margin-top:12px'>Réseau LOLODRIVE by O'SCOP.</p>
        """
        await send_email(to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"Commande {num} annulee : non retiree sous 48h ({point_name}). "
                                      f"Les articles ont ete remis en vente.",
                         tags=["auto_cancel_no_pickup"])
    if user.get("phone"):
        try:
            await send_sms(user["phone"],
                           f"LOLODRIVE : votre commande {num} non retiree sous 48h a ete annulee "
                           f"({point_name}). Les articles sont remis en vente.",
                           tag="auto_cancel_no_pickup")
        except Exception as exc:
            logger.warning("SMS annulation auto %s : %s", num, exc)
