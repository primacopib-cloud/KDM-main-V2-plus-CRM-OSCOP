"""Espaces d'équipe (COOPER / EXPERT) + gestion des acheteurs par l'admin."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

team_space_router = APIRouter(prefix="/api/team", tags=["Team Space"])
admin_buyers_router = APIRouter(prefix="/api/admin/buyers", tags=["Admin Buyers"])

db = None

STAFF_ROLES = {"SUPER_ADMIN", "OSCOP_SUPER_ADMIN", "ADMIN", "COOPER", "EXPERT",
               "oscop_compliance_admin", "oscop_billing_admin", "oscop_support_agent",
               "kdm_b2b_admin", "kdm_b2b_sales", "kdm_warehouse", "kdm_finance"}


def set_team_space_database(database) -> None:
    global db
    db = database


async def require_staff(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    if user.get("is_admin") or (user.get("role") or "") in STAFF_ROLES:
        return user
    raise HTTPException(status_code=403, detail="Réservé aux membres de l'équipe")


@team_space_router.get("/overview")
async def team_overview(user: dict = Depends(require_staff)):
    """KPIs partagés pour les espaces COOPER (opérationnel) et EXPERT (consultation)."""
    products_total = await db.products.count_documents({})
    vendor_pending = await db.vendor_products.count_documents({"status": "pending_approval"})
    orders_total = await db.orders.count_documents({}) + await db.lolodrive_orders.count_documents({})
    users_total = await db.users.count_documents({})
    low_stock = await db.products.count_documents({"stock": {"$lt": 10, "$ne": None}})
    recent_orders = await db.lolodrive_orders.find({}, {"_id": 0, "id": 1, "status": 1, "total_ttc": 1, "created_at": 1}) \
        .sort("created_at", -1).limit(5).to_list(5)
    return {
        "role": user.get("role"),
        "contact_name": user.get("contact_name"),
        "kpis": {
            "products_total": products_total,
            "vendor_products_pending": vendor_pending,
            "orders_total": orders_total,
            "users_total": users_total,
            "low_stock": low_stock,
        },
        "recent_orders": recent_orders,
    }


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


BUYER_ROLES = ["buyer", "customer_org_buyer", "customer_org_owner", "customer_org_viewer"]
BUYER_FIELDS = {"_id": 0, "id": 1, "email": 1, "contact_name": 1, "company_name": 1,
                "siret": 1, "role": 1, "credits": 1, "subscription": 1, "created_at": 1, "suspended": 1}


@admin_buyers_router.get("")
async def list_buyers(q: str = Query(None), _: dict = Depends(_admin)):
    query: dict = {"role": {"$in": BUYER_ROLES}}
    if q:
        regex = {"$regex": q, "$options": "i"}
        query["$or"] = [{"email": regex}, {"contact_name": regex}, {"company_name": regex}]
    buyers = await db.users.find(query, BUYER_FIELDS).sort("created_at", -1).to_list(200)
    for b in buyers:
        b["orders_count"] = await db.orders.count_documents({"user_id": b["id"]}) \
            + await db.lolodrive_orders.count_documents({"user_id": b["id"]})
    return {"buyers": buyers, "total": len(buyers)}


class CreditsPayload(BaseModel):
    credits: int


class SuspendPayload(BaseModel):
    suspended: bool


@admin_buyers_router.patch("/{user_id}/credits")
async def update_buyer_credits(user_id: str, payload: CreditsPayload, admin: dict = Depends(_admin)):
    if payload.credits < 0:
        raise HTTPException(status_code=400, detail="Crédits invalides")
    result = await db.users.update_one(
        {"id": user_id, "role": {"$in": BUYER_ROLES}},
        {"$set": {"credits": payload.credits, "credits_updated_by": admin["email"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Acheteur introuvable")
    return {"status": "SUCCESS", "credits": payload.credits}


@admin_buyers_router.patch("/{user_id}/suspend")
async def suspend_buyer(user_id: str, payload: SuspendPayload, admin: dict = Depends(_admin)):
    result = await db.users.update_one(
        {"id": user_id, "role": {"$in": BUYER_ROLES}},
        {"$set": {"suspended": payload.suspended, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Acheteur introuvable")
    return {"status": "SUCCESS", "suspended": payload.suspended}
