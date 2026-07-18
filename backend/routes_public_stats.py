"""Statistiques publiques temps réel pour la page vitrine KDMARCHÉ — /api/public/kdmarche-stats."""
from fastapi import APIRouter

public_stats_router = APIRouter(prefix="/api/public", tags=["Public Stats"])

db = None


def set_public_stats_database(database) -> None:
    global db
    db = database


@public_stats_router.get("/kdmarche-videos")
async def kdmarche_videos(limit: int = 6):
    """Galerie publique des spots vidéo IA générés par les vendeurs (jobs DONE uniquement)."""
    limit = min(max(limit, 1), 12)
    jobs = await db.ai_video_jobs.find(
        {"status": "DONE", "video_url": {"$ne": None}}, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    videos = []
    for job in jobs:
        product = await db.vendor_products.find_one(
            {"id": job["product_id"]}, {"_id": 0, "name": 1}) or {}
        vendor = await db.vendors.find_one(
            {"id": job["vendor_id"]}, {"_id": 0, "company_name": 1}) or {}
        videos.append({
            "id": job["id"],
            "video_url": job["video_url"],
            "product_name": product.get("name", "Produit"),
            "vendor_name": vendor.get("company_name", "Vendeur KDMARCHÉ"),
            "created_at": job.get("created_at"),
        })
    return {"videos": videos, "total": len(videos)}


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
