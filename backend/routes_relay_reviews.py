"""Avis relais LOLODRIVE (notation post-retrait par les titulaires du PASS)."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lolodrive_helpers import get_current_user

relay_reviews_router = APIRouter(prefix="/api/lolodrive", tags=["Relay Reviews"])
db = None


def set_relay_reviews_database(database):
    global db
    db = database


class ReviewBody(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


@relay_reviews_router.get("/relay-reviews/pending")
async def pending_reviews(user: dict = Depends(get_current_user)):
    """Retraits effectués en relais pas encore notés par l'utilisateur."""
    orders = await db.lolodrive_orders.find(
        {"user_id": user["id"], "status": "FULFILLED", "lolo_point_id": {"$ne": None}},
        {"_id": 0, "id": 1, "order_number": 1, "lolo_point_id": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(20)
    reviewed = {r["order_id"] async for r in db.relay_reviews.find(
        {"user_id": user["id"]}, {"_id": 0, "order_id": 1})}
    pending = []
    for o in orders:
        if o["id"] in reviewed:
            continue
        point = await db.lolodrive_points.find_one({"id": o["lolo_point_id"]}, {"_id": 0, "name": 1, "code": 1})
        if point:
            pending.append({"order_id": o["id"], "order_number": o["order_number"],
                            "point_code": point["code"], "point_name": point["name"]})
    return {"pending": pending[:3]}


@relay_reviews_router.post("/relay-reviews")
async def submit_review(body: ReviewBody, user: dict = Depends(get_current_user)):
    order = await db.lolodrive_orders.find_one({"id": body.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order.get("status") != "FULFILLED" or not order.get("lolo_point_id"):
        raise HTTPException(status_code=400, detail="Seuls les retraits effectués en relais peuvent être notés")
    if await db.relay_reviews.find_one({"order_id": body.order_id}):
        raise HTTPException(status_code=409, detail="Ce retrait a déjà été noté")
    point = await db.lolodrive_points.find_one({"id": order["lolo_point_id"]}, {"_id": 0, "code": 1})
    await db.relay_reviews.insert_one({
        "id": str(uuid.uuid4()), "order_id": body.order_id, "user_id": user["id"],
        "point_id": order["lolo_point_id"], "point_code": point["code"] if point else None,
        "rating": body.rating, "comment": (body.comment or "").strip()[:500],
        "created_at": datetime.utcnow(),
    })
    return {"ok": True}


@relay_reviews_router.get("/relay-reviews/stats")
async def review_stats():
    """Note moyenne + nombre d'avis par relais (public)."""
    rows = await db.relay_reviews.aggregate([
        {"$group": {"_id": "$point_code", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]).to_list(200)
    return {"stats": {r["_id"]: {"avg": round(r["avg"], 1), "count": r["count"]} for r in rows if r["_id"]}}
