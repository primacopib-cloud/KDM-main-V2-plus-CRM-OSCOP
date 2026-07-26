"""Stats publiques par territoire (produits disponibles + adhérents) pour la carte interactive."""
from fastapi import APIRouter

zone_stats_router = APIRouter(prefix="/api/v2/catalog")

db = None

ZONES = ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "MAYOTTE"]


def set_zone_stats_database(database):
    global db
    db = database


@zone_stats_router.get("/zones-stats")
async def zones_stats():
    """Nombre de produits disponibles, adhérents approuvés et objectif par territoire (public)."""
    out = {}
    for z in ZONES:
        pids = await db.zone_prices.distinct("product_id", {"zone_code": z, "is_active": True})
        members = await db.orgs.count_documents({"status": "APPROVED", "territory": z})
        zone_doc = await db.zones_v2.find_one({"code": z}, {"_id": 0, "member_target": 1}) or {}
        out[z] = {"products": len(pids), "members": members, "target": zone_doc.get("member_target") or 20}
    return out
