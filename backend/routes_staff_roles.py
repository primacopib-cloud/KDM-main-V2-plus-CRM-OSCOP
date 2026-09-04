"""Rôles granulaires serveur (§18) : OSCOP_FINANCE, LOGISCOP_MANAGER, AUDITOR_READ_ONLY."""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from routes_v2 import get_current_user_v2

staff_roles_router = APIRouter(prefix="/api/admin/staff-roles", tags=["Rôles granulaires"])
db = None


def set_staff_roles_database(database):
    global db
    db = database


GRANULAR_ROLES = ["OSCOP_FINANCE", "LOGISCOP_MANAGER", "AUDITOR_READ_ONLY",
                  "OSCOP_PURCHASING", "OSCOP_SALES", "OSCOP_COMPLIANCE", "FOGEDOM_REVIEWER"]


async def get_staff_role(email: str):
    if not email:
        return None
    doc = await db.staff_roles.find_one({"email": email.lower()}, {"_id": 0})
    return doc["role"] if doc else None


async def require_reader(current_user: dict = Depends(get_current_user_v2)) -> dict:
    """Lecture : admin ou tout rôle granulaire (y compris AUDITOR_READ_ONLY)."""
    if current_user.get("is_admin"):
        return current_user
    role = await get_staff_role(current_user.get("email"))
    if role:
        current_user["staff_role"] = role
        return current_user
    raise HTTPException(status_code=403, detail="Accès réservé (rôle requis)")


async def require_finance(current_user: dict = Depends(get_current_user_v2)) -> dict:
    """Écritures financières : admin ou OSCOP_FINANCE."""
    if current_user.get("is_admin"):
        return current_user
    role = await get_staff_role(current_user.get("email"))
    if role == "OSCOP_FINANCE":
        current_user["staff_role"] = role
        return current_user
    raise HTTPException(status_code=403, detail="Rôle OSCOP_FINANCE requis (contrôle serveur)")


async def require_logiscop(current_user: dict = Depends(get_current_user_v2)) -> dict:
    """Écritures logistiques : admin ou LOGISCOP_MANAGER."""
    if current_user.get("is_admin"):
        return current_user
    role = await get_staff_role(current_user.get("email"))
    if role == "LOGISCOP_MANAGER":
        current_user["staff_role"] = role
        return current_user
    raise HTTPException(status_code=403, detail="Rôle LOGISCOP_MANAGER requis (contrôle serveur)")


class RoleAssign(BaseModel):
    email: EmailStr
    role: str


async def _superadmin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@staff_roles_router.get("")
async def list_roles(admin: dict = Depends(_superadmin)):
    roles = await db.staff_roles.find({}, {"_id": 0}).to_list(200)
    return {"assignments": roles, "available_roles": GRANULAR_ROLES}


@staff_roles_router.post("")
async def assign_role(payload: RoleAssign, admin: dict = Depends(_superadmin)):
    if payload.role not in GRANULAR_ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle invalide : {GRANULAR_ROLES}")
    await db.staff_roles.update_one(
        {"email": payload.email.lower()},
        {"$set": {"role": payload.role, "assigned_by": admin.get("email"),
                  "assigned_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True)
    return {"success": True, "email": payload.email.lower(), "role": payload.role}


@staff_roles_router.delete("/{email}")
async def revoke_role(email: str, admin: dict = Depends(_superadmin)):
    r = await db.staff_roles.delete_one({"email": email.lower()})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Aucun rôle pour cet email")
    return {"success": True}
