"""Fidélité UC : jauge client + réglage du seuil/bonus par le super admin."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import get_current_user, require_admin
from loyalty_bonus import get_loyalty_config

logger = logging.getLogger(__name__)
loyalty_router = APIRouter(prefix="/api/lolodrive", tags=["Loyalty"])
db = None


def set_loyalty_database(database):
    global db
    db = database


@loyalty_router.get("/loyalty/me")
async def my_loyalty(user: dict = Depends(get_current_user)):
    """Jauge fidélité du client : progression vers le prochain bonus, par relais."""
    cfg = await get_loyalty_config(db)
    counts = {}
    async for row in db.lolodrive_orders.aggregate([
            {"$match": {"channel": "COUNTER", "user_id": user["id"], "lolo_point_id": {"$ne": None}}},
            {"$group": {"_id": "$lolo_point_id", "count": {"$sum": 1}}}]):
        counts[row["_id"]] = row["count"]
    relays = []
    if counts:
        async for pt in db.lolodrive_points.find({"id": {"$in": list(counts.keys())}},
                                                 {"_id": 0, "id": 1, "name": 1, "code": 1}):
            count = counts.get(pt["id"], 0)
            progress = count % cfg["threshold"]
            relays.append({
                "point_id": pt["id"], "point_name": pt.get("name"), "point_code": pt.get("code"),
                "count": count, "progress": progress,
                "remaining": cfg["threshold"] - progress,
                "bonuses_earned": count // cfg["threshold"],
            })
        relays.sort(key=lambda r: -r["progress"])
    return {"threshold": cfg["threshold"], "bonus_uc": cfg["bonus_uc"], "relays": relays}


@loyalty_router.get("/admin/loyalty-config")
async def admin_loyalty_config(admin: dict = Depends(require_admin)):
    return await get_loyalty_config(db)


@loyalty_router.put("/admin/loyalty-config")
async def admin_update_loyalty_config(payload: dict, admin: dict = Depends(require_admin)):
    try:
        threshold = int(payload.get("threshold"))
        bonus = float(payload.get("bonus_uc"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Seuil et bonus UC numériques requis")
    if not (2 <= threshold <= 100):
        raise HTTPException(status_code=400, detail="Seuil d'achats entre 2 et 100")
    if not (0 <= bonus <= 100000):
        raise HTTPException(status_code=400, detail="Bonus UC entre 0 et 100000")
    if bonus == int(bonus):
        bonus = int(bonus)
    await db.lolodrive_settings.update_one(
        {"key": "loyalty_config"},
        {"$set": {"value": {"threshold": threshold, "bonus_uc": bonus}}}, upsert=True)
    return {"ok": True, "threshold": threshold, "bonus_uc": bonus}
