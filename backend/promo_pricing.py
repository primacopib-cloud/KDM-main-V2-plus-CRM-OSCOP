"""Application automatique des promotions ciblées au panier."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _user_profile(user: dict) -> str:
    if (user.get("member_type") or "") == "pass":
        return "pass"
    role = (user.get("role") or "").lower()
    return "vendor" if "vendor" in role else "buyer"


async def enrich_cart_response(db, response, cart: dict, user: dict):
    """Ajoute promo_percent/promo_name par ligne + remise totale sur la CartResponse."""
    try:
        from credit_promotions import _matches, matches_product
        now = datetime.now(timezone.utc).isoformat()
        promos = await db.credit_promotions.find({
            "promo_type": "discount_action", "active": True, "archived": {"$ne": True},
        }, {"_id": 0}).to_list(50)
        promos = [p for p in promos
                  if (not p.get("starts_at") or p["starts_at"] <= now)
                  and (not p.get("ends_at") or p["ends_at"] >= now)
                  and p.get("audience", "all") != "emails"]
        if not promos:
            return response
        profile = _user_profile(user)
        relay = ((user.get("pass_relay") or {}).get("name")) if isinstance(user.get("pass_relay"), dict) else None
        ids = [i.product_id for i in response.items]
        prods = {p["id"]: p async for p in db.products.find({"id": {"$in": ids}}, {"_id": 0})}
        total_discount = 0
        for item in response.items:
            prod = prods.get(item.product_id) or {}
            best = None
            for promo in promos:
                if not _matches(promo, profile, cart.get("zone_code"), prod.get("category") or prod.get("category_slug"), None):
                    continue
                if not matches_product(promo, prod.get("product_type") or prod.get("type"),
                                       prod.get("brand"), relay, item.quantity):
                    continue
                if best is None or promo["value_percent"] > best["value_percent"]:
                    best = promo
            if best:
                item.promo_percent = best["value_percent"]
                item.promo_name = best["name"]
                item.promo_discount_cents = round(item.line_total_ht_cents * best["value_percent"] / 100)
                total_discount += item.promo_discount_cents
        response.promo_discount_cents = total_discount
        if total_discount:
            response.total_after_promo_cents = max(response.total_ttc_cents - total_discount, 0)
    except Exception as exc:
        logger.warning("Application promos panier : %s", exc)
    return response
