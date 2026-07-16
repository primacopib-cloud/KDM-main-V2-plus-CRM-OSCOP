"""LOLODRIVE by O'SCOP — Logistics / POS / KPI dashboard routes (split from routes_lolodrive_oscoop.py)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import uuid
import logging

from brevo_service import notify_order_ready
from lolodrive_models import (
    PASS_PRICE_CENTS, PASS_UC, PASS_DAYS, RECHARGE_PACKS, DEFAULT_LOGISTICS_CONFIG,
    CatalogType, FulfillmentType, OrderStatus, EventType, StatusUpdate,
)
from lolodrive_helpers import (
    get_current_user, require_admin, get_or_create_wallet, is_pass_active,
    cents_to_uc, logistics_config, quote_cart, ensure_customer, emit_crm_event,
)

logger = logging.getLogger(__name__)

lolodrive_pos_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_pos_database(database):
    global db
    db = database

# =======================
# Logistics / POS
# =======================

@lolodrive_pos_router.get("/logistics/config")
async def get_logistics_config():
    return await logistics_config()

@lolodrive_pos_router.get("/logistics/zones")
async def get_delivery_zones():
    zones = await db.lolodrive_delivery_zones.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return {"zones": zones}

@lolodrive_pos_router.get("/pos/orders")
async def pos_orders(status_filter: Optional[OrderStatus] = Query(None, alias="status"), lolo_point_code: Optional[str] = None, territory: Optional[str] = None, user: dict = Depends(get_current_user)):
    query: Dict[str, Any] = {}
    if status_filter:
        query["status"] = status_filter.value
    if lolo_point_code:
        point = await db.lolodrive_points.find_one({"code": lolo_point_code})
        query["lolo_point_id"] = point.get("id") if point else "__missing__"
    if territory:
        terr_points = await db.lolodrive_points.find({"territory": territory.upper()}, {"_id": 0, "id": 1}).to_list(200)
        ids = [p["id"] for p in terr_points]
        query["lolo_point_id"] = {"$in": ids} if ids else "__missing__"
    orders = await db.lolodrive_orders.find(query, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"orders": orders}

@lolodrive_pos_router.post("/pos/orders/{order_id}/status")
async def pos_update_order_status(order_id: str, request: StatusUpdate, user: dict = Depends(get_current_user)):
    now = datetime.utcnow()
    extra = {"updated_at": now}
    if request.status == OrderStatus.PREPARING:
        extra["prepared_at"] = now
    if request.status == OrderStatus.READY:
        extra["ready_at"] = now
    if request.status == OrderStatus.FULFILLED:
        extra["fulfilled_at"] = now
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": request.status.value, **extra}})
    await _broadcast_pos_event("order.status_changed", {"order_id": order_id, "status": request.status.value})
    # Brevo email+SMS notification on READY (best-effort)
    if request.status == OrderStatus.READY:
        try:
            order = await db.lolodrive_orders.find_one({"id": order_id}, {"_id": 0})
            if order:
                user_doc = await db.users.find_one({"id": order.get("user_id")}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
                pickup = "Point de retrait LOLODRIVE"
                if order.get("lolo_point_id"):
                    pt = await db.lolodrive_points.find_one({"id": order["lolo_point_id"]}, {"_id": 0, "name": 1, "code": 1})
                    if pt:
                        pickup = pt.get("name") or pt.get("code") or pickup
                if user_doc and user_doc.get("email"):
                    await notify_order_ready(
                        to_email=user_doc["email"],
                        to_name=user_doc.get("contact_name"),
                        to_phone=user_doc.get("phone"),
                        order_number=str(order.get("order_number") or order.get("id", ""))[:32],
                        pickup_point=pickup,
                    )
        except Exception as exc:
            logger.warning(f"Brevo order-ready notification failed: {exc}")
    return {"ok": True, "order_id": order_id, "status": request.status.value}

@lolodrive_pos_router.post("/pos/orders/{order_id}/scan")
async def pos_scan(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.lolodrive_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] not in [OrderStatus.READY.value, OrderStatus.PAID.value]:
        raise HTTPException(status_code=400, detail="Commande non prête")
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": OrderStatus.FULFILLED.value, "fulfilled_at": datetime.utcnow(), "updated_at": datetime.utcnow()}})
    await _broadcast_pos_event("order.fulfilled", {"order_id": order_id})
    return {"ok": True, "order_id": order_id, "status": OrderStatus.FULFILLED.value}


@lolodrive_pos_router.post("/pos/orders/{order_id}/cancel")
async def pos_cancel_order(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Annulation / signalement d'un problème par l'opérateur POS.
    payload = {"reason": "...", "refund_uc": bool}. Si refund_uc=True et commande payée en UC, recrédite le wallet.
    """
    order = await db.lolodrive_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order["status"] in [OrderStatus.FULFILLED.value, OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value]:
        raise HTTPException(status_code=400, detail="Commande déjà finalisée")
    reason = (payload or {}).get("reason", "Annulation POS")
    refund_uc = (payload or {}).get("refund_uc", False)
    new_status = OrderStatus.CANCELLED.value
    extra = {"cancelled_at": datetime.utcnow(), "cancel_reason": reason}
    # Refund UC if requested and applicable
    if refund_uc and order.get("pay_with_uc") and order.get("total_uc"):
        wallet = await db.lolodrive_wallets.find_one({"user_id": order["user_id"]})
        if wallet:
            await db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": order["total_uc"]}, "$set": {"updated_at": datetime.utcnow()}})
            await db.lolodrive_wallet_ledger.insert_one({"id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT", "amount_uc": order["total_uc"], "reason": "ORDER_REFUND", "order_id": order_id, "created_at": datetime.utcnow()})
            new_status = OrderStatus.REFUNDED.value
            extra["refunded_at"] = datetime.utcnow()
    await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {"status": new_status, "updated_at": datetime.utcnow(), **extra}})
    await _broadcast_pos_event("order.cancelled", {"order_id": order_id, "status": new_status, "reason": reason})
    return {"ok": True, "order_id": order_id, "status": new_status, "reason": reason}


async def _broadcast_pos_event(event_type: str, payload: dict):
    """Broadcast LOLODRIVE POS events to all admin WebSocket clients."""
    try:
        from routes_websockets import manager
        await manager.broadcast_to_admins({
            "type": "lolodrive_pos_event",
            "payload": {"event": event_type, "data": payload, "timestamp": datetime.utcnow().isoformat()},
        })
    except Exception:
        pass


@lolodrive_pos_router.get("/admin/kpi/dashboard")
async def admin_kpi_dashboard(admin: dict = Depends(require_admin)):
    """Tableau de bord enrichi : UC en circulation, top produits, alertes, CA jour/mois."""
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    # UC en circulation
    pipeline = [{"$group": {"_id": None, "total_uc": {"$sum": "$balance_uc"}}}]
    uc_circ_doc = await db.lolodrive_wallets.aggregate(pipeline).to_list(1)
    uc_in_circulation = uc_circ_doc[0]["total_uc"] if uc_circ_doc else 0
    # UC consommées (DEBIT all-time)
    pipeline_consumed = [{"$match": {"type": "DEBIT"}}, {"$group": {"_id": None, "total": {"$sum": "$amount_uc"}}}]
    consumed_doc = await db.lolodrive_wallet_ledger.aggregate(pipeline_consumed).to_list(1)
    uc_consumed = consumed_doc[0]["total"] if consumed_doc else 0
    # CA jour & mois (statut PAID/PREPARING/READY/FULFILLED)
    paid_statuses = [OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.READY.value, OrderStatus.FULFILLED.value]
    ca_today = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": today}}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total_cents"}, "uc_orders": {"$sum": {"$cond": ["$pay_with_uc", 1, 0]}}}},
    ]).to_list(1)
    ca_today_data = ca_today[0] if ca_today else {"count": 0, "revenue": 0, "uc_orders": 0}
    ca_month = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total_cents"}}},
    ]).to_list(1)
    ca_month_data = ca_month[0] if ca_month else {"count": 0, "revenue": 0}
    # Top produits (30 derniers jours)
    from_30d = now - timedelta(days=30)
    top_products = await db.lolodrive_orders.aggregate([
        {"$match": {"status": {"$in": paid_statuses}, "created_at": {"$gte": from_30d}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.sku",
            "name": {"$first": "$items.name"},
            "qty": {"$sum": "$items.qty"},
            "revenue_cents": {"$sum": {"$multiply": ["$items.unit_cents", "$items.qty"]}},
            "catalog_type": {"$first": "$items.catalog_type"},
        }},
        {"$sort": {"qty": -1}},
        {"$limit": 5},
    ]).to_list(5)
    # Alertes
    alerts = []
    # PASS expirant J-3
    j3 = now + timedelta(days=3)
    pass_expiring = await db.lolodrive_passes.count_documents({"status": "ACTIVE", "ends_at": {"$lte": j3, "$gte": now}})
    if pass_expiring > 0:
        alerts.append({"severity": "warning", "icon": "alert-triangle", "message": f"{pass_expiring} PASS expirent dans moins de 3 jours"})
    # Commandes anciennes (PAID > 2h sans préparation)
    stale_paid = await db.lolodrive_orders.count_documents({"status": "PAID", "created_at": {"$lt": now - timedelta(hours=2)}})
    if stale_paid > 0:
        alerts.append({"severity": "critical", "icon": "clock", "message": f"{stale_paid} commande(s) payée(s) en attente >2h"})
    # Stock bas
    low_stock = await db.lolodrive_products.count_documents({"is_active": True, "stock_qty": {"$lt": 10}})
    if low_stock > 0:
        alerts.append({"severity": "warning", "icon": "package", "message": f"{low_stock} produit(s) avec stock < 10"})
    if not alerts:
        alerts.append({"severity": "ok", "icon": "check-circle", "message": "Aucune alerte. Tout est en ordre."})
    return {
        "uc_in_circulation": uc_in_circulation,
        "uc_consumed": uc_consumed,
        "ca_today": {"orders": ca_today_data["count"], "revenue_cents": ca_today_data["revenue"], "uc_orders": ca_today_data.get("uc_orders", 0)},
        "ca_month": {"orders": ca_month_data["count"], "revenue_cents": ca_month_data["revenue"]},
        "top_products": [{k: v for k, v in p.items() if k != "_id"} | {"sku": p["_id"]} for p in top_products],
        "alerts": alerts,
    }

