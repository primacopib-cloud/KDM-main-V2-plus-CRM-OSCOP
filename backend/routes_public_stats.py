"""Statistiques publiques temps réel pour la page vitrine KDMARCHÉ — /api/public/kdmarche-stats."""
from fastapi import APIRouter
from pydantic import BaseModel

public_stats_router = APIRouter(prefix="/api/public", tags=["Public Stats"])

db = None


def set_public_stats_database(database) -> None:
    global db
    db = database


@public_stats_router.get("/plans")
async def public_plans():
    """Plans d'abonnement publics : actifs, visibles et dans leur fenêtre de programmation."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    plans = await db.subscription_plans.find(
        {"active": True}, {"_id": 0, "created_by": 0}
    ).sort("sort_order", 1).to_list(50)
    result = []
    for p in plans:
        if not p.get("visible", True):
            continue
        if p.get("visible_from") and now < p["visible_from"]:
            continue
        if p.get("visible_until") and now > p["visible_until"]:
            continue
        result.append(p)
    return {"plans": result, "total": len(result)}


@public_stats_router.get("/kdmarche-videos")
async def kdmarche_videos(limit: int = 6):
    """Galerie publique des spots vidéo IA générés par les vendeurs (jobs DONE uniquement)."""
    limit = min(max(limit, 1), 12)
    from spot_diffusion import active_diffusion_product_ids
    allowed_products = await active_diffusion_product_ids()
    jobs = await db.ai_video_jobs.find(
        {"status": "DONE", "video_url": {"$ne": None}}, {"_id": 0}
    ).sort("created_at", -1).to_list(limit * 3)
    videos = []
    seen_products = set()
    for job in jobs:
        if job["product_id"] in seen_products or len(videos) >= limit:
            continue
        if allowed_products is not None and job["product_id"] not in allowed_products:
            continue
        seen_products.add(job["product_id"])
        product = await db.vendor_products.find_one(
            {"id": job["product_id"]}, {"_id": 0, "name": 1, "video_views": 1}) or {}
        vendor = await db.vendors.find_one(
            {"id": job["vendor_id"]}, {"_id": 0, "company_name": 1}) or {}
        videos.append({
            "id": job["id"],
            "product_id": job["product_id"],
            "video_url": job["video_url"],
            "language": job.get("language", "fr"),
            "product_name": product.get("name", "Produit"),
            "vendor_name": vendor.get("company_name", "Vendeur KDMARCHÉ"),
            "views": int(product.get("video_views") or 0),
            "created_at": job.get("created_at"),
        })
    return {"videos": videos, "total": len(videos)}


class VideoViewPayload(BaseModel):
    product_id: str


@public_stats_router.post("/kdmarche-video-view")
async def track_video_view(payload: VideoViewPayload):
    """Incrémente le compteur de vues du spot vidéo d'un produit."""
    result = await db.vendor_products.update_one(
        {"id": payload.product_id}, {"$inc": {"video_views": 1}})
    await db.products.update_one({"id": payload.product_id}, {"$inc": {"video_views": 1}})
    return {"ok": result.matched_count == 1}


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
