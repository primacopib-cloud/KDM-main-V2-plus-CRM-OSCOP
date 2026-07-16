"""LOLODRIVE by O'SCOP — Gérant LOLO POINT routes (split from routes_lolodrive_oscoop.py)."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from lolodrive_helpers import get_current_user, require_admin
from lolodrive_models import OrderStatus

logger = logging.getLogger(__name__)

lolodrive_manager_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_manager_database(database):
    global db
    db = database

# =======================
# Gérant LOLO POINT — vue dédiée
# =======================

@lolodrive_manager_router.get("/manager/my-point")
async def manager_my_point(user: dict = Depends(get_current_user)):
    """Retourne le LOLO POINT du gérant connecté (via manager_user_id)."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    return point


@lolodrive_manager_router.get("/manager/my-orders")
async def manager_my_orders(order_status: Optional[str] = None, user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    q = {"lolo_point_id": point["id"]}
    if order_status:
        q["status"] = order_status
    orders = await db.lolodrive_orders.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"point": point, "orders": orders}


@lolodrive_manager_router.get("/manager/my-payout-preview")
async def manager_my_payout_preview(user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=30)
    # Reuse existing payout calculation logic
    return await payout_preview_compute(point["id"], from_date, to_date)


@lolodrive_manager_router.get("/manager/my-timeseries")
async def manager_my_timeseries(days: int = 30, user: dict = Depends(get_current_user)):
    """Série temporelle quotidienne du Lolo Point du gérant : commandes + CA + retraits."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    days = max(7, min(days, 90))
    to_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
    from_date = (to_date - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "lolo_point_id": point["id"],
            "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
            "created_at": {"$gte": from_date, "$lte": to_date},
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "orders": {"$sum": 1},
            "revenue_cents": {"$sum": "$subtotal_cents"},
            "fulfilled": {"$sum": {"$cond": [{"$eq": ["$status", "FULFILLED"]}, 1, 0]}},
        }},
    ]
    rows = await db.lolodrive_orders.aggregate(pipeline).to_list(1000)
    by_day = {r["_id"]: r for r in rows}
    series = []
    cursor = from_date
    while cursor.date() <= to_date.date():
        key = cursor.strftime("%Y-%m-%d")
        r = by_day.get(key, {})
        series.append({
            "date": key,
            "orders": r.get("orders", 0),
            "revenue_cents": r.get("revenue_cents", 0),
            "fulfilled": r.get("fulfilled", 0),
        })
        cursor += timedelta(days=1)
    return {"point": {"id": point["id"], "name": point["name"], "code": point["code"]}, "days": days, "series": series}


@lolodrive_manager_router.get("/manager/network-ranking")
async def manager_network_ranking(days: int = 30, user: dict = Depends(get_current_user)):
    """Classement de tous les Lolo Points actifs par chiffre d'affaires sur N jours, et rang du gérant connecté."""
    days = max(7, min(days, 90))
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=days)
    points = await db.lolodrive_points.find({"status": "ACTIVE"}, {"_id": 0}).to_list(500)
    ids = [p["id"] for p in points]
    pipeline = [
        {"$match": {
            "lolo_point_id": {"$in": ids},
            "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
            "created_at": {"$gte": from_date, "$lte": to_date},
        }},
        {"$group": {
            "_id": "$lolo_point_id",
            "orders": {"$sum": 1},
            "revenue_cents": {"$sum": "$subtotal_cents"},
            "fulfilled": {"$sum": {"$cond": [{"$eq": ["$status", "FULFILLED"]}, 1, 0]}},
        }},
    ]
    by_id = {r["_id"]: r for r in await db.lolodrive_orders.aggregate(pipeline).to_list(1000)}
    enriched = []
    for p in points:
        s = by_id.get(p["id"], {})
        enriched.append({
            "point_id": p["id"],
            "code": p["code"],
            "name": p["name"],
            "territory": p.get("territory"),
            "city": p.get("city"),
            "orders": s.get("orders", 0),
            "revenue_cents": s.get("revenue_cents", 0),
            "fulfilled": s.get("fulfilled", 0),
        })
    enriched.sort(key=lambda x: (x["revenue_cents"], x["orders"]), reverse=True)
    for i, e in enumerate(enriched):
        e["rank"] = i + 1
    my_point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    my_rank = next((e for e in enriched if my_point and e["point_id"] == my_point.get("id")), None)
    return {
        "days": days,
        "ranking": enriched,
        "my_rank": my_rank,
        "total_points": len(enriched),
    }


async def payout_preview_compute(point_id: str, from_date: datetime, to_date: datetime) -> dict:
    """Re-usable payout preview computation."""
    point = await db.lolodrive_points.find_one({"id": point_id})
    if not point:
        raise HTTPException(status_code=404, detail="Point introuvable")
    orders = await db.lolodrive_orders.find({
        "lolo_point_id": point_id,
        "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
        "created_at": {"$gte": from_date, "$lte": to_date},
    }, {"_id": 0}).to_list(2000)
    consumption_volume_cents = sum(o.get("subtotal_cents", 0) for o in orders)
    withdrawals = sum(1 for o in orders if o.get("status") == "FULFILLED")
    pass_activations = await db.lolodrive_passes.count_documents({
        "source_lolo_point_id": point_id,
        "starts_at": {"$gte": from_date, "$lte": to_date},
    })
    withdrawal_commission = withdrawals * point.get("withdrawal_commission_cents", 70)
    pass_commission = pass_activations * point.get("pass_activation_commission_cents", 400)
    volume_commission = int(consumption_volume_cents * (point.get("essential_volume_bps", 200) / 10000))
    calculated = withdrawal_commission + pass_commission + volume_commission
    percent_cap = int(consumption_volume_cents * (point.get("payout_cap_percent_bps", 600) / 10000))
    monthly_cap = point.get("payout_cap_cents_monthly", 120000)
    capped = min(calculated, percent_cap, monthly_cap)
    return {
        "point_id": point_id,
        "from_date": from_date,
        "to_date": to_date,
        "consumption_volume_cents": consumption_volume_cents,
        "withdrawals": withdrawals,
        "pass_activations": pass_activations,
        "components": {
            "withdrawal_commission_cents": withdrawal_commission,
            "pass_commission_cents": pass_commission,
            "volume_commission_cents": volume_commission,
        },
        "calculated_cents": calculated,
        "caps": {"percent_cap_cents": percent_cap, "monthly_cap_cents": monthly_cap},
        "capped_cents": capped,
    }


# =======================
# Reporting timeseries
# =======================

@lolodrive_manager_router.get("/admin/kpi/timeseries")
async def admin_kpi_timeseries(metric: str = "revenue", days: int = 30, admin: dict = Depends(require_admin)):
    """Daily aggregation for charts. metric: revenue|orders|uc_consumed|pass_activations"""
    days = min(max(days, 7), 365)
    from_date = datetime.utcnow() - timedelta(days=days)
    paid_statuses = [OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.READY.value, OrderStatus.FULFILLED.value]
    points = []
    if metric == "revenue":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": paid_statuses}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": "$total_cents"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "orders":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": paid_statuses}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "uc_consumed":
        rows = await db.lolodrive_wallet_ledger.aggregate([
            {"$match": {"type": "DEBIT", "created_at": {"$gte": from_date}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": "$amount_uc"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "pass_activations":
        rows = await db.lolodrive_passes.aggregate([
            {"$match": {"starts_at": {"$gte": from_date}, "status": "ACTIVE"}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$starts_at"}}, "value": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    else:
        raise HTTPException(status_code=400, detail="metric invalide")
    return {"metric": metric, "days": days, "points": points}

