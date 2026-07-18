"""Espace COOPER — adhésions en attente, transporteurs LOGI'SCOP et assignation."""
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth import get_current_user_id
from admin_guard import require_admin, require_cooper

logger = logging.getLogger(__name__)

cooper_router = APIRouter(prefix="/api/cooper", tags=["Espace COOPER"])

db = None


def set_cooper_database(database) -> None:
    global db
    db = database


@cooper_router.get("/adhesions")
async def list_pending_adhesions(user_id: str = Depends(get_current_user_id)):
    await require_cooper(user_id)
    apps = await db.b2b_applications.find(
        {"status": "PENDING_REVIEW"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for a in apps:
        org = await db.orgs.find_one({"id": a["org_id"]}, {"_id": 0})
        a["org"] = {
            "legal_name": (org or {}).get("legal_name"),
            "registration_id": (org or {}).get("registration_id"),
            "territory": (org or {}).get("territory"),
            "member_type": (org or {}).get("member_type", "BUYER_PRO"),
        }
    return {"applications": apps, "count": len(apps)}


# ============== TRANSPORTEURS LOGI'SCOP ==============

class CarrierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    territory: str = Field(..., min_length=2)


class CarrierUpdate(BaseModel):
    is_active: Optional[bool] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@cooper_router.get("/carriers")
async def list_carriers(user_id: str = Depends(get_current_user_id)):
    await require_cooper(user_id)
    carriers = await db.logiscop_carriers.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return {"carriers": carriers}


@cooper_router.post("/carriers")
async def create_carrier(carrier: CarrierCreate, user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    doc = carrier.dict()
    doc.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": datetime.utcnow()})
    await db.logiscop_carriers.insert_one(doc)
    doc.pop("_id", None)
    return doc


@cooper_router.patch("/carriers/{carrier_id}")
async def update_carrier(carrier_id: str, update: CarrierUpdate, user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    fields = {k: v for k, v in update.dict().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Aucune modification")
    res = await db.logiscop_carriers.update_one({"id": carrier_id}, {"$set": fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    return {"ok": True}


class CarrierAssign(BaseModel):
    carrier_id: str


@cooper_router.post("/orders/{order_id}/assign-carrier")
async def assign_carrier(order_id: str, payload: CarrierAssign, user_id: str = Depends(get_current_user_id)):
    user = await require_cooper(user_id)
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    carrier = await db.logiscop_carriers.find_one({"id": payload.carrier_id, "is_active": True}, {"_id": 0})
    if not carrier:
        raise HTTPException(status_code=404, detail="Transporteur introuvable ou inactif")
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "carrier": {"id": carrier["id"], "name": carrier["name"], "territory": carrier.get("territory")},
            "carrier_assigned_at": datetime.utcnow(),
            "carrier_assigned_by": user.get("email"),
            "updated_at": datetime.utcnow(),
        }}
    )
    logger.info("Carrier %s assigned to order %s by %s", carrier["name"], order_id, user.get("email"))
    return {"ok": True, "carrier": carrier["name"]}
