"""Enchères produits à prix descendant — helpers partagés (statuts, prix, comptes, récurrence)."""
import logging
import uuid
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

db = None

CREDITS_PER_EUR = 10
SOURCES = ["LOLODRIVE", "VENDOR", "PARTNER", "KDMARCHE", "OSCOP", "DETAILLANT"]
RECURRENCES = ["NONE", "DAILY", "MONTHLY", "YEARLY"]
SOURCE_LABELS = {"LOLODRIVE": "LOLODRIVE", "VENDOR": "Vendeur", "PARTNER": "Partenaire",
                 "KDMARCHE": "KDMARCHÉ", "OSCOP": "O'SCOP", "DETAILLANT": "Boutique détaillante"}


def set_auction_database(database):
    global db
    db = database


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def eur_to_credits(eur: float) -> int:
    return int(round(eur * CREDITS_PER_EUR))


def effective_status(a: dict, at: datetime | None = None) -> str:
    """Statut dérivé des dates : SCHEDULED→LIVE→EXPIRED, sans toucher WON/CANCELLED."""
    st = a.get("status")
    if st in ("WON", "CANCELLED", "EXPIRED"):
        return st
    at = at or now_utc()
    starts, ends = parse_dt(a.get("starts_at")), parse_dt(a.get("ends_at"))
    if ends and ends <= at:
        return "EXPIRED"
    if starts and starts <= at:
        return "LIVE"
    return "SCHEDULED"


def _shift(dt: datetime, recurrence: str) -> datetime:
    if recurrence == "DAILY":
        return dt + relativedelta(days=1)
    if recurrence == "MONTHLY":
        return dt + relativedelta(months=1)
    return dt + relativedelta(years=1)


async def sync_auction_statuses():
    """Transitions paresseuses + relance des enchères récurrentes (clone SCHEDULED)."""
    at = now_utc()
    async for a in db.auctions.find(
            {"status": {"$in": ["SCHEDULED", "LIVE"]}}, {"_id": 0}):
        eff = effective_status(a, at)
        if eff != a["status"]:
            await db.auctions.update_one({"id": a["id"], "status": a["status"]},
                                         {"$set": {"status": eff, "updated_at": at.isoformat()}})
            if eff == "LIVE":
                try:
                    from auction_emails import notify_new_live_auction
                    await notify_new_live_auction(a)
                except Exception as exc:
                    logger.warning("Alerte nouveau COOP'ACT %s : %s", a.get("reference"), exc)
            a["status"] = eff
    async for a in db.auctions.find(
            {"status": {"$in": ["WON", "EXPIRED"]},
             "recurrence": {"$in": ["DAILY", "MONTHLY", "YEARLY"]},
             "recurrence_spawned": {"$ne": True}}, {"_id": 0}):
        starts, ends = parse_dt(a.get("starts_at")), parse_dt(a.get("ends_at"))
        if not starts or not ends:
            continue
        new_starts, new_ends = _shift(starts, a["recurrence"]), _shift(ends, a["recurrence"])
        while new_ends <= at:
            new_starts, new_ends = _shift(new_starts, a["recurrence"]), _shift(new_ends, a["recurrence"])
        clone = {k: v for k, v in a.items() if k not in (
            "id", "reference", "status", "winner", "fulfillment", "bids_count",
            "current_price_eur", "recurrence_spawned", "created_at", "updated_at",
            "live_alert_sent", "ending_alert_sent", "ending_alert_at")}
        clone.update({
            "id": str(uuid.uuid4()),
            "reference": f"AUC-{at.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            "status": "SCHEDULED", "bids_count": 0,
            "current_price_eur": a.get("value_eur"),
            "starts_at": new_starts.isoformat(), "ends_at": new_ends.isoformat(),
            "spawned_from": a["id"], "created_at": at.isoformat(),
        })
        await db.auctions.insert_one(clone)
        await db.auctions.update_one({"id": a["id"]}, {"$set": {"recurrence_spawned": True}})
        logger.info("Enchère récurrente relancée : %s → %s", a["reference"], clone["reference"])


async def get_auction_account(user_id: str) -> dict | None:
    return await db.auction_accounts.find_one({"user_id": user_id}, {"_id": 0})


def account_active(account: dict | None) -> bool:
    if not account:
        return False
    valid = parse_dt(account.get("valid_until"))
    return bool(valid and valid > now_utc())


def serialize_member(a: dict, labels: dict | None = None) -> dict:
    """Vue membre : plancher masqué, provenance masquée si source_visible=False."""
    labels = labels or {}
    price = a.get("current_price_eur", a.get("value_eur", 0))
    out = {
        "id": a["id"], "reference": a.get("reference"), "title": a.get("title"),
        "image_url": a.get("image_url"), "description": a.get("description") or "",
        "category_id": a.get("category_id"), "category_label": labels.get(f"cat:{a.get('category_id')}"),
        "type_id": a.get("type_id"), "type_label": labels.get(f"type:{a.get('type_id')}"),
        "source": a.get("source") if a.get("source_visible") else None,
        "source_label": SOURCE_LABELS.get(a.get("source")) if a.get("source_visible") else None,
        "value_eur": a.get("value_eur"), "value_credits": eur_to_credits(a.get("value_eur") or 0),
        "price_eur": round(price, 2), "price_credits": eur_to_credits(price),
        "bid_cost_credits": a.get("bid_cost_credits"), "price_drop_eur": a.get("price_drop_eur"),
        "starts_at": a.get("starts_at"), "ends_at": a.get("ends_at"),
        "recurrence": a.get("recurrence", "NONE"), "featured": bool(a.get("featured")),
        "status": effective_status(a), "bids_count": a.get("bids_count", 0),
        "photos": a.get("photos") or [],
        "condition": a.get("condition"), "warranty": a.get("warranty"), "dlc": a.get("dlc"),
    }
    if a.get("retailer") and a.get("source_visible"):
        out["retailer"] = a["retailer"]
    if out["status"] == "WON" and a.get("winner"):
        out["winner_name"] = a["winner"].get("name")
        out["winner_price_eur"] = a["winner"].get("price_eur")
    return out


async def taxonomy_labels() -> dict:
    labels = {}
    async for c in db.auction_categories.find({}, {"_id": 0, "id": 1, "label": 1}):
        labels[f"cat:{c['id']}"] = c["label"]
    async for t in db.auction_types.find({}, {"_id": 0, "id": 1, "label": 1}):
        labels[f"type:{t['id']}"] = t["label"]
    return labels
