"""Avis produits des adhérents (1-5 étoiles + commentaire) — publication directe, suppression admin."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

reviews_router = APIRouter(prefix="/api/v2/catalog")

db = None


def set_reviews_database(database):
    global db
    db = database


ADMIN_ROLES = {"SUPER_ADMIN", "ADMIN", "admin", "oscop_super_admin", "kdm_b2b_admin"}


def _is_admin(user: dict) -> bool:
    return bool(user.get("is_admin")) or (user.get("role") in ADMIN_ROLES)


async def _optional_user(request: Request):
    from auth import extract_user_id_from_request
    try:
        user_id = extract_user_id_from_request(request)
        if not user_id:
            return None
        return await db.users.find_one({"id": user_id})
    except Exception:
        return None


class ReviewBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


async def _recompute_product_rating(product_id: str):
    pipeline = [
        {"$match": {"product_id": product_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    res = await db.product_reviews.aggregate(pipeline).to_list(1)
    avg = round(res[0]["avg"], 1) if res else None
    count = res[0]["count"] if res else 0
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"rating_avg": avg, "rating_count": count}},
    )
    return avg, count


@reviews_router.get("/products/{product_id}/reviews")
async def list_reviews(product_id: str, request: Request):
    """Liste des avis d'un produit (public). Indique si l'utilisateur connecté peut noter."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1,
                                                              "rating_avg": 1, "rating_count": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    user = await _optional_user(request)
    reviews = await db.product_reviews.find(
        {"product_id": product_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for r in reviews:
        r["mine"] = bool(user) and r.get("user_id") == user.get("id")
        r.pop("user_id", None)
    return {
        "product_id": product_id,
        "product_name": product.get("name"),
        "avg": product.get("rating_avg"),
        "count": product.get("rating_count") or 0,
        "reviews": reviews,
        "can_review": bool(user),
        "is_admin": bool(user) and _is_admin(user),
    }


async def _notify_vendor_of_review(product: dict, reviewer_name: str, rating: int, created: bool):
    """Notifie le(s) compte(s) vendeur qu'un avis a été déposé sur son produit."""
    vendor_id = product.get("vendor_id")
    if not vendor_id:
        return
    from core_deps import create_notification
    vendor_users = await db.users.find({"vendor_id": vendor_id}, {"_id": 0, "id": 1}).to_list(10)
    stars = "★" * rating + "☆" * (5 - rating)
    for vu in vendor_users:
        await create_notification(
            notification_type="product_review_received",
            title=f"{'Nouvel avis' if created else 'Avis mis à jour'} {rating}/5 sur « {product.get('name')} »",
            message=f"{reviewer_name} a {'déposé' if created else 'modifié'} un avis {stars} sur votre produit.",
            target_roles=[],
            target_user_id=vu["id"],
            data={"link": "/vendor", "product_id": product.get("id"), "rating": rating},
        )


@reviews_router.post("/products/{product_id}/reviews")
async def upsert_review(product_id: str, body: ReviewBody, request: Request):
    """Crée ou met à jour l'avis de l'adhérent connecté (1 avis par produit)."""
    user = await _optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Connectez-vous pour donner votre avis")
    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1, "vendor_id": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    now = datetime.now(timezone.utc).isoformat()
    user_name = user.get("contact_name") or user.get("company_name") or (user.get("email") or "").split("@")[0]
    existing = await db.product_reviews.find_one({"product_id": product_id, "user_id": user["id"]})
    if existing:
        await db.product_reviews.update_one(
            {"id": existing["id"]},
            {"$set": {"rating": body.rating, "comment": (body.comment or "").strip() or None,
                      "user_name": user_name, "updated_at": now}},
        )
        review_id = existing["id"]
        created = False
    else:
        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        await db.product_reviews.insert_one({
            "id": review_id,
            "product_id": product_id,
            "user_id": user["id"],
            "user_name": user_name,
            "rating": body.rating,
            "comment": (body.comment or "").strip() or None,
            "created_at": now,
        })
        created = True
    avg, count = await _recompute_product_rating(product_id)
    try:
        await _notify_vendor_of_review(product, user_name, body.rating, created)
    except Exception as exc:
        logger.warning("Notification vendeur avis non créée (%s) : %s", product_id, exc)
    return {"success": True, "review_id": review_id, "created": created, "avg": avg, "count": count}


@reviews_router.get("/vendors/{vendor_id}/reviews-stats")
async def vendor_reviews_stats(vendor_id: str):
    """Stats des avis pour les produits d'un vendeur (note moyenne, tendance 30j, détail par produit)."""
    from datetime import timedelta
    products = await db.products.find(
        {"vendor_id": vendor_id},
        {"_id": 0, "id": 1, "name": 1, "sku": 1, "rating_avg": 1, "rating_count": 1},
    ).to_list(200)
    ids = [p["id"] for p in products]
    reviews = await db.product_reviews.find(
        {"product_id": {"$in": ids}}, {"_id": 0, "user_id": 0}
    ).sort("created_at", -1).to_list(500)

    total = len(reviews)
    overall_avg = round(sum(r["rating"] for r in reviews) / total, 1) if total else None
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent = [r for r in reviews if (r.get("created_at") or "") >= cutoff]
    older = [r for r in reviews if (r.get("created_at") or "") < cutoff]
    recent_avg = round(sum(r["rating"] for r in recent) / len(recent), 1) if recent else None
    older_avg = round(sum(r["rating"] for r in older) / len(older), 1) if older else None

    names = {p["id"]: p for p in products}
    latest = [{
        "id": r["id"], "product_name": names.get(r["product_id"], {}).get("name"),
        "user_name": r.get("user_name"), "rating": r["rating"],
        "comment": r.get("comment"), "created_at": r.get("created_at"),
    } for r in reviews[:5]]

    return {
        "overall_avg": overall_avg,
        "total_reviews": total,
        "recent_count": len(recent),
        "recent_avg": recent_avg,
        "previous_avg": older_avg,
        "trend": (round(recent_avg - older_avg, 1) if recent_avg is not None and older_avg is not None else None),
        "products": [p for p in products if p.get("rating_count")],
        "latest_reviews": latest,
    }


@reviews_router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, request: Request):
    """Supprime un avis (auteur ou admin)."""
    user = await _optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")
    review = await db.product_reviews.find_one({"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Avis non trouvé")
    if review.get("user_id") != user.get("id") and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Vous ne pouvez pas supprimer cet avis")
    await db.product_reviews.delete_one({"id": review_id})
    avg, count = await _recompute_product_rating(review["product_id"])
    return {"success": True, "avg": avg, "count": count}
