"""Alerte email quand un produit favori LOLODRIVE passe en promo."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _matches_product(promo: dict, product: dict) -> bool:
    cat = (promo.get("scope_category") or "all").lower()
    if cat != "all":
        names = {str(product.get(k, "")).lower() for k in ("category_id", "category_name", "category") if product.get(k)}
        if cat not in names:
            return False
    pt = (promo.get("scope_product_type") or "all").lower()
    if pt != "all" and pt != (product.get("product_type") or "").lower():
        return False
    brand = (promo.get("scope_brand") or "").lower()
    if brand and brand != (product.get("brand") or "").lower():
        return False
    return True


async def _active_discount_promos(db) -> list:
    now_iso = datetime.now(timezone.utc).isoformat()
    docs = await db.credit_promotions.find(
        {"active": True, "archived": {"$ne": True}, "promo_type": "discount_action"},
        {"_id": 0}).to_list(50)
    return [p for p in docs
            if (not p.get("starts_at") or p["starts_at"] <= now_iso)
            and (not p.get("ends_at") or p["ends_at"] >= now_iso)
            and p.get("audience", "all") != "emails"]


async def run_favorite_promo_alerts(db) -> int:
    promos = await _active_discount_promos(db)
    if not promos:
        return 0
    from brevo_service import send_email, _wrap_html
    sent = 0
    async for fav in db.lolodrive_favorites.find({}, {"_id": 0}):
        skus = fav.get("skus") or []
        if not skus:
            continue
        user = await db.users.find_one({"id": fav["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if not user or not user.get("email"):
            continue
        products = await db.lolodrive_products.find(
            {"sku": {"$in": skus}, "is_active": {"$ne": False}}, {"_id": 0}).to_list(100)
        hits = []
        for prod in products:
            best = None
            for promo in promos:
                if _matches_product(promo, prod) and (best is None or (promo.get("value_percent") or 0) > (best.get("value_percent") or 0)):
                    best = promo
            if not best:
                continue
            key = f"{best['id']}:{prod['sku']}"
            if await db.favorite_promo_notified.find_one({"user_id": fav["user_id"], "key": key}):
                continue
            hits.append((prod, best, key))
        if not hits:
            continue
        first = ((user.get("contact_name") or "").split() or [""])[0]
        rows = "".join(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{p['name']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;color:#b45309'><b>-{pr.get('value_percent'):g} %</b></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>"
            f"{round(p.get('price_public_cents', 0) * (1 - (pr.get('value_percent') or 0) / 100)) / 100:.2f} €</td></tr>"
            for p, pr, _ in hits)
        subject = f"⭐ {len(hits)} de vos favoris LOLODRIVE en promo !"
        body = f"""
          <p>Bonjour{f' {first}' if first else ''},</p>
          <p>Bonne nouvelle : des produits que vous avez épinglés dans le catalogue LOLODRIVE passent en promotion :</p>
          <table style='width:100%;border-collapse:collapse;font-size:13px'>
            <tr style='color:#888;font-size:11px;text-transform:uppercase'>
              <th style='text-align:left;padding:6px 10px'>Produit</th>
              <th style='text-align:right;padding:6px 10px'>Remise</th>
              <th style='text-align:right;padding:6px 10px'>Prix promo</th>
            </tr>
            {rows}
          </table>
          <p style='margin-top:14px'>Retrouvez-les en tête de votre catalogue LOLODRIVE (onglet ⭐ Mes favoris).</p>
        """
        try:
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"{len(hits)} de vos produits favoris LOLODRIVE sont en promo.",
                tags=["favorite_promo_alert"])
            for _, _, key in hits:
                await db.favorite_promo_notified.insert_one(
                    {"user_id": fav["user_id"], "key": key, "notified_at": datetime.utcnow()})
            sent += 1
        except Exception as exc:
            logger.warning("Alerte promo favoris %s échouée : %s", user["email"], exc)
    if sent:
        logger.info("Alertes promo favoris envoyées : %s", sent)
    return sent


ALERT_TAGS = {"PROMO": "Promo", "SOLDE": "Solde", "DESTOCKAGE": "Déstockage"}


async def run_favorite_tag_alerts(db) -> int:
    """Alerte email quand un produit favori reçoit une étiquette Promo/Solde/Déstockage (cron 10 min)."""
    tagged = await db.lolodrive_products.find(
        {"tag": {"$in": list(ALERT_TAGS)}, "is_active": {"$ne": False}}, {"_id": 0}).to_list(300)
    if not tagged:
        return 0
    by_sku = {p["sku"]: p for p in tagged}
    from brevo_service import send_email, _wrap_html
    sent = 0
    async for fav in db.lolodrive_favorites.find({}, {"_id": 0}):
        skus = [s for s in (fav.get("skus") or []) if s in by_sku]
        if not skus:
            continue
        user = await db.users.find_one({"id": fav["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if not user or not user.get("email"):
            continue
        hits = []
        for sku in skus:
            p = by_sku[sku]
            until = p.get("tag_until")
            key = f"TAG:{p['tag']}:{sku}:{until.strftime('%Y-%m-%d') if until else 'open'}"
            if await db.favorite_promo_notified.find_one({"user_id": fav["user_id"], "key": key}):
                continue
            hits.append((p, key))
        if not hits:
            continue
        first = ((user.get("contact_name") or "").split() or [""])[0]
        rows = "".join(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{p['name']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:center;color:#b91c1c'><b>{ALERT_TAGS[p['tag']]}</b></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{p.get('price_public_cents', 0) / 100:.2f} €</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;color:#888'>"
            f"{('fin le ' + p['tag_until'].strftime('%d/%m/%Y')) if p.get('tag_until') else '—'}</td></tr>"
            for p, _ in hits)
        subject = f"🔥 {len(hits)} de vos favoris LOLODRIVE en promo !"
        body = f"""
          <p>Bonjour{f' {first}' if first else ''},</p>
          <p>Des produits que vous avez épinglés en favoris viennent de recevoir une étiquette promo :</p>
          <table style='width:100%;border-collapse:collapse;font-size:13px'>
            <tr style='color:#888;font-size:11px;text-transform:uppercase'>
              <th style='text-align:left;padding:6px 10px'>Produit</th>
              <th style='text-align:center;padding:6px 10px'>Étiquette</th>
              <th style='text-align:right;padding:6px 10px'>Prix</th>
              <th style='text-align:right;padding:6px 10px'>Durée</th>
            </tr>
            {rows}
          </table>
          <p style='margin-top:14px'>Retrouvez-les dans le rayon 🔥 Promos &amp; Soldes en tête de votre catalogue LOLODRIVE.</p>
        """
        try:
            await send_email(
                to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"{len(hits)} de vos produits favoris LOLODRIVE viennent de passer en promo.",
                tags=["favorite_tag_alert"])
            for _, key in hits:
                await db.favorite_promo_notified.insert_one(
                    {"user_id": fav["user_id"], "key": key, "notified_at": datetime.utcnow()})
            sent += 1
        except Exception as exc:
            logger.warning("Alerte étiquette favoris %s échouée : %s", user["email"], exc)
    if sent:
        logger.info("Alertes étiquette favoris envoyées : %s", sent)
    return sent
