"""Avis relais LOLODRIVE (notation post-retrait par les titulaires du PASS)."""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lolodrive_helpers import get_current_user

logger = logging.getLogger(__name__)
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
    point = await db.lolodrive_points.find_one({"id": order["lolo_point_id"]}, {"_id": 0})
    await db.relay_reviews.insert_one({
        "id": str(uuid.uuid4()), "order_id": body.order_id, "user_id": user["id"],
        "point_id": order["lolo_point_id"], "point_code": point["code"] if point else None,
        "rating": body.rating, "comment": (body.comment or "").strip()[:500],
        "created_at": datetime.utcnow(),
    })
    try:
        await _notify_manager_new_review(point, user["id"], body.rating, (body.comment or "").strip()[:500])
    except Exception as exc:
        logger.warning("Notification nouvel avis échouée : %s", exc)
    return {"ok": True}


async def _notify_manager_new_review(point: Optional[dict], reviewer_id: str, rating: int, comment: str):
    """Email Brevo au gérant du relais dès qu'un avis est déposé."""
    if not point:
        return
    from brevo_service import send_email, _wrap_html
    to_email, to_name = None, None
    if point.get("manager_user_id"):
        mgr = await db.users.find_one({"id": point["manager_user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if mgr and mgr.get("email"):
            to_email, to_name = mgr["email"], mgr.get("contact_name")
    if not to_email:
        to_email = point.get("contact_email")
    if not to_email:
        return
    reviewer = await db.users.find_one({"id": reviewer_id}, {"_id": 0, "contact_name": 1})
    first = (((reviewer or {}).get("contact_name") or "Un titulaire PASS").split() or ["Un titulaire"])[0]
    stars = "★" * rating + "☆" * (5 - rating)
    subject = f"Nouvel avis {rating}/5 sur votre relais {point.get('name', '')}"
    hello = f" {to_name.split()[0]}" if to_name else ""
    comment_html = f"<p style='margin:8px 0 0;'>&laquo; {comment} &raquo;</p>" if comment else ""
    body_html = f"""
      <p>Bonjour{hello},</p>
      <p><strong>{first}</strong> vient de laisser un avis sur votre relais <strong>{point.get('name')}</strong> :</p>
      <div style='background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;'>
        <p style='margin:0;font-size:18px;color:#D9B35A;letter-spacing:2px;'>{stars} <strong>{rating}/5</strong></p>
        {comment_html}
      </div>
      <p>Vous pouvez y répondre publiquement depuis votre interface POS LOLODRIVE (bouton « Avis clients »).</p>
    """
    await send_email(
        to_email=to_email, to_name=to_name, subject=subject,
        html_content=_wrap_html(subject, body_html),
        text_content=f"{first} a laissé un avis {rating}/5 sur {point.get('name')} : {comment}",
        tags=["relay_review"],
    )


@relay_reviews_router.get("/relay-reviews/latest")
async def latest_reviews(limit: int = 6):
    """Derniers avis (toutes relais confondus) — vitrine PASS."""
    limit = max(1, min(limit, 12))
    reviews = await db.relay_reviews.find(
        {}, {"_id": 0, "id": 1, "user_id": 1, "point_code": 1, "rating": 1, "comment": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(limit)
    out = []
    for r in reviews:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "contact_name": 1})
        p = await db.lolodrive_points.find_one({"code": r.get("point_code")}, {"_id": 0, "name": 1, "city": 1})
        out.append({"id": r["id"],
                    "author": (((u or {}).get("contact_name") or "Titulaire PASS").split() or ["Titulaire"])[0],
                    "point_name": (p or {}).get("name") or r.get("point_code"),
                    "city": (p or {}).get("city"),
                    "rating": r["rating"], "comment": r.get("comment") or "",
                    "date": str(r.get("created_at", ""))[:10]})
    return {"reviews": out}


@relay_reviews_router.get("/relay-reviews/podium")
async def relay_podium():
    """Podium mensuel des relais les mieux notés (avis des 30 derniers jours)."""
    since = datetime.utcnow() - timedelta(days=30)
    rows = await db.relay_reviews.aggregate([
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$point_code", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        {"$sort": {"avg": -1, "count": -1}},
        {"$limit": 3},
    ]).to_list(3)
    podium = []
    for r in rows:
        p = await db.lolodrive_points.find_one({"code": r["_id"]}, {"_id": 0, "name": 1, "city": 1, "territory": 1})
        if p:
            podium.append({"code": r["_id"], "name": p["name"], "city": p.get("city"),
                           "territory": p.get("territory"), "avg": round(r["avg"], 1), "count": r["count"]})
    return {"podium": podium}


@relay_reviews_router.get("/relay-reviews/stats")
async def review_stats():
    """Note moyenne + nombre d'avis par relais (public)."""
    rows = await db.relay_reviews.aggregate([
        {"$group": {"_id": "$point_code", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]).to_list(200)
    return {"stats": {r["_id"]: {"avg": round(r["avg"], 1), "count": r["count"]} for r in rows if r["_id"]}}
