"""Bonus fidélité 'Client fiable' : récompense UC des clients Drive sans aucun non-retrait sur 6 mois."""
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
PERIOD_DAYS = 180


async def run_reliable_client_bonus(db, now=None, force=False) -> int:
    now = now or datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    if not force:
        last = await db.lolodrive_settings.find_one({"key": "reliable_bonus_last_run"}, {"_id": 0})
        if last and last.get("value") == today:
            return 0
        await db.lolodrive_settings.update_one(
            {"key": "reliable_bonus_last_run"}, {"$set": {"value": today}}, upsert=True)
    from routes_lolodrive_taxonomy import get_fees_config_doc
    cfg = (await get_fees_config_doc()).get("reliable_bonus") or {}
    bonus_uc = float(cfg.get("bonus_uc") or 0)
    min_orders = int(cfg.get("min_orders") or 5)
    if bonus_uc <= 0:
        return 0
    since = now - timedelta(days=PERIOD_DAYS)
    counts = await db.lolodrive_orders.aggregate([
        {"$match": {"status": "FULFILLED", "channel": {"$ne": "COUNTER"},
                    "fulfilled_at": {"$gte": since}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": min_orders}}}]).to_list(2000)
    awarded = 0
    for c in counts:
        uid = c["_id"]
        if await db.lolodrive_orders.find_one(
                {"user_id": uid, "no_pickup_reminder_sent_at": {"$gte": since}}, {"_id": 1}):
            continue
        if await db.reliable_bonus_awards.find_one({"user_id": uid, "awarded_at": {"$gte": since}}):
            continue
        try:
            from lolodrive_helpers import get_or_create_wallet
            wallet = await get_or_create_wallet(uid)
            await db.lolodrive_wallets.update_one(
                {"id": wallet["id"]}, {"$inc": {"balance_uc": bonus_uc}, "$set": {"updated_at": now}})
            await db.lolodrive_wallet_ledger.insert_one({
                "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
                "amount_uc": bonus_uc, "reason": "RELIABLE_CLIENT_BONUS", "created_at": now})
            await db.reliable_bonus_awards.insert_one(
                {"id": str(uuid.uuid4()), "user_id": uid, "amount_uc": bonus_uc,
                 "orders_count": c["n"], "awarded_at": now})
            await _notify_client(db, uid, bonus_uc, c["n"])
            awarded += 1
        except Exception as exc:
            logger.warning("Bonus client fiable %s : %s", uid, exc)
    if awarded:
        logger.info("Bonus client fiable attribués : %d (+%g UC chacun)", awarded, bonus_uc)
    return awarded


async def _notify_client(db, user_id, bonus_uc, orders_count):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    if not user or not user.get("email"):
        return
    from brevo_service import send_email, _wrap_html
    first = ((user.get("contact_name") or "").split() or [""])[0]
    subject = f"🏅 Badge Client Fiable — +{bonus_uc:g} UC offerts !"
    body = f"""
      <p>Bonjour{f' {first}' if first else ''},</p>
      <p>Félicitations ! Sur les 6 derniers mois, vous avez retiré <strong>{orders_count} commande(s)</strong>
      sans aucun non-retrait. Vous décrochez le badge <strong>🏅 Client Fiable</strong>.</p>
      <div style='background:rgba(217,179,90,0.08);border:1px solid rgba(217,179,90,0.35);border-radius:12px;padding:14px;margin:12px 0'>
        <p style='margin:0'>Votre récompense : <strong style='color:#D9B35A'>+{bonus_uc:g} UC ({bonus_uc / 10:.2f} €)</strong>
        créditée sur votre CREDI'SCOP.</p>
      </div>
      <p>Merci de votre fiabilité — continuez ainsi, le badge se renouvelle tous les 6 mois !</p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Badge Client Fiable : +{bonus_uc:g} UC credites sur votre CREDI'SCOP. Merci !",
                     tags=["reliable_client_bonus"])
