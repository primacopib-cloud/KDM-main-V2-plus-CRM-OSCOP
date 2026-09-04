"""Espace LOGI'SCOP opérations achat-revente : expéditions, jalons, stockage et preuves de livraison."""
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2
from routes_purchase_resale import LOGISTICS_STATUSES, LOGISCOP_NOTICE

logger = logging.getLogger(__name__)
logiscop_ops_router = APIRouter(prefix="/api/admin/logiscop-ops", tags=["LOGI'SCOP Ops"])
db = None


def set_logiscop_ops_database(database):
    global db
    db = database


TRANSPORT_MODES = ["ROUTIER", "MARITIME", "AERIEN", "MULTIMODAL"]
MOVEMENTS = ["IN", "OUT"]


class ShipmentCreate(BaseModel):
    origin: str
    destination: str
    transport_mode: str = "MARITIME"
    carrier_name: Optional[str] = None
    internal_or_external: str = "INTERNAL"
    incoterm: Optional[str] = "EXW"


class MilestoneCreate(BaseModel):
    milestone: str
    comment: Optional[str] = None


class WarehouseCreate(BaseModel):
    location: str
    movement: str
    quantity: float = Field(gt=0)
    reference: Optional[str] = None


class PodCreate(BaseModel):
    received_by: str
    reference: Optional[str] = None
    comment: Optional[str] = None


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


async def _get_op(operation_id: str) -> dict:
    op = await db.purchase_resale_operations.find_one({"id": operation_id}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    return op


@logiscop_ops_router.get("/operations")
async def list_logistics_operations(admin: dict = Depends(_admin)):
    ops = await db.purchase_resale_operations.find(
        {"logistics_mode": {"$ne": "CUSTOMER_HANDLED"}}, {"_id": 0}).sort("created_at", -1).to_list(200)
    result = []
    for op in ops:
        shipments = await db.logiscop_shipments.count_documents({"operation_id": op["id"]})
        pods = await db.logiscop_pods.count_documents({"operation_id": op["id"]})
        result.append({
            "id": op["id"], "reference": op["reference"], "client_name": op.get("client_name"),
            "logistics_mode": op.get("logistics_mode"), "logistics_status": op.get("logistics_status"),
            "logistics_budget_ex_vat": op.get("logistics_budget_ex_vat"),
            "logistics_external_paid_amount": op.get("logistics_external_paid_amount", 0),
            "logiscop_internal_allocated_amount": op.get("logiscop_internal_allocated_amount", 0),
            "shipments_count": shipments, "pods_count": pods,
        })
    return {"operations": result, "logistics_statuses": LOGISTICS_STATUSES,
            "transport_modes": TRANSPORT_MODES, "notice": LOGISCOP_NOTICE}


@logiscop_ops_router.get("/operations/{operation_id}")
async def get_logistics_detail(operation_id: str, admin: dict = Depends(_admin)):
    op = await _get_op(operation_id)
    shipments = await db.logiscop_shipments.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    for s in shipments:
        s["milestones"] = await db.logiscop_milestones.find({"shipment_id": s["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    warehouse = await db.logiscop_warehouse.find({"operation_id": operation_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    pods = await db.logiscop_pods.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    return {"operation": op, "shipments": shipments, "warehouse": warehouse, "pods": pods}


@logiscop_ops_router.post("/operations/{operation_id}/shipments")
async def create_shipment(operation_id: str, payload: ShipmentCreate, admin: dict = Depends(_admin)):
    op = await _get_op(operation_id)
    if op.get("logistics_mode") == "CUSTOMER_HANDLED":
        raise HTTPException(status_code=409, detail="Logistique gérée par le client sur cette opération")
    if payload.transport_mode not in TRANSPORT_MODES:
        raise HTTPException(status_code=400, detail="Mode de transport invalide")
    shp = {"id": str(uuid.uuid4()), "operation_id": operation_id,
           "shipment_number": f"EXP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:5].upper()}",
           **payload.dict(), "status": "PICKUP_SCHEDULED",
           "created_by": admin.get("email"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_shipments.insert_one(dict(shp))
    await db.purchase_resale_operations.update_one(
        {"id": operation_id}, {"$set": {"logistics_status": "PICKUP_SCHEDULED"}})
    return shp


@logiscop_ops_router.post("/shipments/{shipment_id}/milestones")
async def add_milestone(shipment_id: str, payload: MilestoneCreate, admin: dict = Depends(_admin)):
    if payload.milestone not in LOGISTICS_STATUSES:
        raise HTTPException(status_code=400, detail="Jalon invalide")
    shp = await db.logiscop_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shp:
        raise HTTPException(status_code=404, detail="Expédition introuvable")
    ms = {"id": str(uuid.uuid4()), "shipment_id": shipment_id,
          "operation_id": shp["operation_id"], **payload.dict(),
          "created_by": admin.get("email"),
          "created_at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_milestones.insert_one(dict(ms))
    await db.logiscop_shipments.update_one({"id": shipment_id}, {"$set": {"status": payload.milestone}})
    await db.purchase_resale_operations.update_one(
        {"id": shp["operation_id"]}, {"$set": {"logistics_status": payload.milestone}})
    return ms


@logiscop_ops_router.post("/operations/{operation_id}/warehouse")
async def add_warehouse_record(operation_id: str, payload: WarehouseCreate, admin: dict = Depends(_admin)):
    await _get_op(operation_id)
    if payload.movement not in MOVEMENTS:
        raise HTTPException(status_code=400, detail="Mouvement invalide (IN/OUT)")
    rec = {"id": str(uuid.uuid4()), "operation_id": operation_id, **payload.dict(),
           "created_by": admin.get("email"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_warehouse.insert_one(dict(rec))
    return rec


@logiscop_ops_router.post("/shipments/{shipment_id}/pod")
async def validate_pod(shipment_id: str, payload: PodCreate, admin: dict = Depends(_admin)):
    shp = await db.logiscop_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shp:
        raise HTTPException(status_code=404, detail="Expédition introuvable")
    pod = {"id": str(uuid.uuid4()), "shipment_id": shipment_id,
           "operation_id": shp["operation_id"], **payload.dict(),
           "pod_number": f"POD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:5].upper()}",
           "validated_by": admin.get("email"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_pods.insert_one(dict(pod))
    await db.logiscop_shipments.update_one({"id": shipment_id}, {"$set": {"status": "POD_VALIDATED"}})
    await db.purchase_resale_operations.update_one(
        {"id": shp["operation_id"]}, {"$set": {"logistics_status": "POD_VALIDATED"}})
    return pod
