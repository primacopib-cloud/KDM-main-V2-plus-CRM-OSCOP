"""Statistiques publiques temps réel pour la page vitrine KDMARCHÉ — /api/public/kdmarche-stats."""
from fastapi import APIRouter

public_stats_router = APIRouter(prefix="/api/public", tags=["Public Stats"])

db = None


def set_public_stats_database(database) -> None:
    global db
    db = database


@public_stats_router.get("/kdmarche-stats")
async def kdmarche_stats():
    products = await db.products.count_documents({"status": "ACTIVE"})
    vendors = await db.vendors.count_documents({})
    zones = await db.zones_v2.count_documents({})
    orders = await db.orders.count_documents({}) + await db.lolodrive_orders.count_documents({})
    buyers = await db.users.count_documents({"role": {"$in": ["buyer", "customer_org_buyer", "customer_org_owner"]}})
    return {
        "products": products,
        "vendors": vendors,
        "zones": zones,
        "orders": orders,
        "buyers": buyers,
    }
