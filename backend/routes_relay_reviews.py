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


class ReplyBody(BaseModel):
    reply: str


async def _serialize_reviews(point_code: str) -> list:
    reviews = await db.relay_reviews.find(
        {"point_code": point_code},
        {"_id": 0, "id": 1, "user_id": 1, "rating": 1, "comment": 1, "reply": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(50)
    out = []
    for r in reviews:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "contact_name": 1})
        first = (((u or {}).get("contact_name") or "Titulaire PASS").split() or ["Titulaire"])[0]
        out.append({"id": r["id"], "author": first, "rating": r["rating"],
                    "comment": r.get("comment") or "", "reply": r.get("reply"),
                    "date": str(r.get("created_at", ""))[:10]})
    return out


@relay_reviews_router.get("/relay-reviews/list/{point_code}")
async def list_reviews(point_code: str):
    """Avis publics d'un relais (avec réponses du gérant)."""
    return {"reviews": await _serialize_reviews(point_code)}


@relay_reviews_router.get("/manager/my-reviews")
async def manager_my_reviews(user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0, "code": 1, "name": 1})
    if not point:
        raise HTTPException(status_code=403, detail="Aucun relais géré par ce compte")
    reviews = await _serialize_reviews(point["code"])
    avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None
    return {"point": point, "reviews": reviews, "avg": avg, "count": len(reviews)}


@relay_reviews_router.post("/manager/my-reviews/{review_id}/reply")
async def reply_review(review_id: str, body: ReplyBody, user: dict = Depends(get_current_user)):
    """Réponse publique du gérant à un avis de son relais."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0, "code": 1})
    if not point:
        raise HTTPException(status_code=403, detail="Aucun relais géré par ce compte")
    reply = (body.reply or "").strip()[:500]
    if not reply:
        raise HTTPException(status_code=400, detail="Réponse vide")
    res = await db.relay_reviews.update_one(
        {"id": review_id, "point_code": point["code"]},
        {"$set": {"reply": reply, "replied_at": datetime.utcnow()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Avis introuvable pour ce relais")
    return {"ok": True}


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
