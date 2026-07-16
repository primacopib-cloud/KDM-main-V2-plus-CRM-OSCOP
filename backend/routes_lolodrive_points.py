"""LOLODRIVE by O'SCOP — LOLO POINTS & events routes (split from routes_lolodrive_oscoop.py)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import uuid
import logging

from lolodrive_models import (
    LoloPointCreate, CoopContributionCreate, PayoutPreviewRequest, EventCreate, PartnerCreate,
)
from lolodrive_helpers import (
    get_current_user, require_admin, is_pass_active, emit_crm_event,
)

logger = logging.getLogger(__name__)

lolodrive_points_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_points_database(database):
    global db
    db = database

# =======================
# LOLO POINTS cooperatifs
# =======================

TERRITORIES = [
    {"code": "GP", "name": "Guadeloupe", "center": {"lat": 16.2650, "lng": -61.5510}, "zoom": 9.5},
    {"code": "MQ", "name": "Martinique", "center": {"lat": 14.6415, "lng": -61.0242}, "zoom": 10},
    {"code": "GF", "name": "Guyane", "center": {"lat": 4.0000, "lng": -53.0000}, "zoom": 7},
    {"code": "RE", "name": "La Réunion", "center": {"lat": -21.1151, "lng": 55.5364}, "zoom": 10},
]


@lolodrive_points_router.get("/territories")
async def list_territories():
    """Liste des territoires d'exploitation (DOM)."""
    return {"territories": TERRITORIES}


@lolodrive_points_router.get("/lolo-points")
async def list_lolo_points(city: Optional[str] = None, territory: Optional[str] = None):
    query = {"status": "ACTIVE"}
    if city:
        query["city"] = city
    if territory:
        query["territory"] = territory.upper()
    points = await db.lolodrive_points.find(query, {"_id": 0}).sort("name", 1).to_list(200)
    return {"points": points}

@lolodrive_points_router.post("/admin/lolo-points")
async def create_lolo_point(request: LoloPointCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "status": "ACTIVE", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    await db.lolodrive_points.insert_one(doc)
    doc.pop("_id", None)
    await emit_crm_event("lolo_point.created", doc)
    return doc

@lolodrive_points_router.post("/admin/lolo-points/{point_id}/contributions")
async def create_contribution(point_id: str, request: CoopContributionCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": str(uuid.uuid4()), "lolo_point_id": point_id, "created_at": datetime.utcnow()})
    await db.lolodrive_contributions.insert_one(doc)
    doc.pop("_id", None)
    return doc

@lolodrive_points_router.post("/admin/lolo-points/{point_id}/payout-preview")
async def payout_preview(point_id: str, request: PayoutPreviewRequest, admin: dict = Depends(require_admin)):
    point = await db.lolodrive_points.find_one({"id": point_id})
    if not point:
        raise HTTPException(status_code=404, detail="Point introuvable")
    orders = await db.lolodrive_orders.find({
        "lolo_point_id": point_id,
        "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
        "created_at": {"$gte": request.from_date, "$lte": request.to_date},
    }).to_list(10000)

    volume = sum(o.get("subtotal_cents", 0) for o in orders)
    withdrawals = len(orders)
    pass_activations = await db.lolodrive_passes.count_documents({"source_lolo_point_id": point_id, "created_at": {"$gte": request.from_date, "$lte": request.to_date}})

    withdrawal_comm = withdrawals * point.get("withdrawal_commission_cents", 70)
    pass_comm = pass_activations * point.get("pass_activation_commission_cents", 400)
    volume_comm = round(volume * point.get("essential_volume_bps", 200) / 10000)
    calculated = withdrawal_comm + pass_comm + volume_comm
    percent_cap = round(volume * point.get("payout_cap_percent_bps", 600) / 10000)
    monthly_cap = point.get("payout_cap_cents_monthly", 120000)
    capped = min(calculated, percent_cap, monthly_cap)

    return {
        "point": {"id": point["id"], "name": point["name"], "code": point["code"]},
        "period": {"from": request.from_date, "to": request.to_date},
        "consumption_volume_cents": volume,
        "withdrawals": withdrawals,
        "pass_activations": pass_activations,
        "components": {"withdrawal_commission_cents": withdrawal_comm, "pass_commission_cents": pass_comm, "volume_commission_cents": volume_comm},
        "calculated_cents": calculated,
        "caps": {"percent_cap_cents": percent_cap, "monthly_cap_cents": monthly_cap},
        "capped_cents": capped,
    }

# =======================
# Events / partners / sponsors
# =======================

@lolodrive_points_router.get("/events/active")
async def active_events():
    now = datetime.utcnow()
    events = await db.lolodrive_events.find({"is_active": True, "ends_at": {"$gte": now}}, {"_id": 0}).sort("starts_at", 1).limit(100).to_list(100)
    # Add reservation count + remaining stock
    for ev in events:
        reservations = await db.lolodrive_reservations.count_documents({"event_id": ev["id"], "status": "CONFIRMED"})
        ev["reservations_count"] = reservations
        ev["remaining_stock"] = max(0, (ev.get("stock_limit") or 0) - reservations) if ev.get("stock_limit") else None
    return {"events": events}


@lolodrive_points_router.get("/events")
async def list_events(scope: str = "all"):
    """scope: all|upcoming|live|ended"""
    now = datetime.utcnow()
    q = {"is_active": True}
    if scope == "upcoming":
        q["starts_at"] = {"$gt": now}
    elif scope == "live":
        q["starts_at"] = {"$lte": now}
        q["ends_at"] = {"$gte": now}
    elif scope == "ended":
        q["ends_at"] = {"$lt": now}
    events = await db.lolodrive_events.find(q, {"_id": 0}).sort("starts_at", -1).limit(200).to_list(200)
    for ev in events:
        reservations = await db.lolodrive_reservations.count_documents({"event_id": ev["id"], "status": "CONFIRMED"})
        ev["reservations_count"] = reservations
        ev["remaining_stock"] = max(0, (ev.get("stock_limit") or 0) - reservations) if ev.get("stock_limit") else None
    return {"events": events}


@lolodrive_points_router.get("/events/{event_id}")
async def event_detail(event_id: str, user: dict = Depends(get_current_user)):
    ev = await db.lolodrive_events.find_one({"id": event_id}, {"_id": 0})
    if not ev:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    reservations = await db.lolodrive_reservations.count_documents({"event_id": event_id, "status": "CONFIRMED"})
    ev["reservations_count"] = reservations
    ev["remaining_stock"] = max(0, (ev.get("stock_limit") or 0) - reservations) if ev.get("stock_limit") else None
    # User reservation
    my_res = await db.lolodrive_reservations.find_one({"event_id": event_id, "user_id": user["id"], "status": "CONFIRMED"}, {"_id": 0})
    ev["my_reservation"] = my_res
    # Linked products with flash prices
    linked = ev.get("linked_products") or []
    skus = [lp["sku"] for lp in linked]
    products = await db.lolodrive_products.find({"sku": {"$in": skus}}, {"_id": 0}).to_list(100)
    by_sku = {p["sku"]: p for p in products}
    for lp in linked:
        p = by_sku.get(lp["sku"], {})
        lp["name"] = p.get("name", lp.get("name", lp["sku"]))
        lp["category"] = p.get("category")
        lp["image_url"] = p.get("image_url")
        lp["public_price_cents"] = p.get("price_public_cents")
    ev["linked_products"] = linked
    return ev


@lolodrive_points_router.post("/events/{event_id}/reserve")
async def reserve_event(event_id: str, user: dict = Depends(get_current_user)):
    ev = await db.lolodrive_events.find_one({"id": event_id})
    if not ev or not ev.get("is_active"):
        raise HTTPException(status_code=404, detail="Événement introuvable")
    now = datetime.utcnow()
    if ev.get("ends_at") and ev["ends_at"] < now:
        raise HTTPException(status_code=400, detail="Événement terminé")
    if ev.get("is_pass_only") and not await is_pass_active(user["id"]):
        raise HTTPException(status_code=403, detail="PASS Vie Chère requis pour réserver")
    # Per user limit
    per_user_limit = ev.get("per_user_limit") or 1
    user_res_count = await db.lolodrive_reservations.count_documents({"event_id": event_id, "user_id": user["id"], "status": "CONFIRMED"})
    if user_res_count >= per_user_limit:
        raise HTTPException(status_code=400, detail=f"Limite atteinte ({per_user_limit} par utilisateur)")
    # Global stock
    if ev.get("stock_limit"):
        global_count = await db.lolodrive_reservations.count_documents({"event_id": event_id, "status": "CONFIRMED"})
        if global_count >= ev["stock_limit"]:
            raise HTTPException(status_code=400, detail="Stock épuisé")
    res = {
        "id": str(uuid.uuid4()),
        "event_id": event_id,
        "user_id": user["id"],
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.lolodrive_reservations.insert_one(res)
    res.pop("_id", None)
    await emit_crm_event("event.reserved", {"event_id": event_id, "user_id": user["id"]})
    return res


@lolodrive_points_router.delete("/events/{event_id}/reserve")
async def cancel_reservation(event_id: str, user: dict = Depends(get_current_user)):
    r = await db.lolodrive_reservations.find_one({"event_id": event_id, "user_id": user["id"], "status": "CONFIRMED"})
    if not r:
        raise HTTPException(status_code=404, detail="Aucune réservation")
    await db.lolodrive_reservations.update_one({"id": r["id"]}, {"$set": {"status": "CANCELLED", "cancelled_at": datetime.utcnow()}})
    return {"ok": True, "reservation_id": r["id"]}


@lolodrive_points_router.get("/admin/events/{event_id}/reservations")
async def list_event_reservations(event_id: str, admin: dict = Depends(require_admin)):
    res = await db.lolodrive_reservations.find({"event_id": event_id}, {"_id": 0}).sort("created_at", -1).limit(500).to_list(500)
    user_ids = [r["user_id"] for r in res]
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)
    by_id = {u["id"]: u for u in users}
    for r in res:
        u = by_id.get(r["user_id"], {})
        r["user_name"] = u.get("contact_name") or u.get("company_name")
        r["user_email"] = u.get("email")
    return {"reservations": res}


@lolodrive_points_router.post("/admin/events/{event_id}/products")
async def link_products_to_event(event_id: str, payload: dict, admin: dict = Depends(require_admin)):
    """payload = {linked_products: [{sku, flash_price_cents, flash_price_uc, stock_per_product (optional)}]}"""
    items = payload.get("linked_products") or []
    await db.lolodrive_events.update_one({"id": event_id}, {"$set": {"linked_products": items, "updated_at": datetime.utcnow()}})
    return {"ok": True, "event_id": event_id, "count": len(items)}


