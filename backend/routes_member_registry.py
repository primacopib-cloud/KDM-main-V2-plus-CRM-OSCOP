"""Registres des membres Acheteurs pro / Vendeurs pro (Super Admin & Admin)."""
from typing import Optional

from fastapi import APIRouter, Depends

from auth import get_current_user_id
from admin_guard import require_admin

registry_router = APIRouter(prefix="/api/v2/admin", tags=["Registres membres"])

db = None


def set_registry_database(database) -> None:
    global db
    db = database


@registry_router.get("/member-registry")
async def list_member_registry(
    member_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    await require_admin(user_id)
    query = {}
    if member_type in ("BUYER_PRO", "VENDOR_PRO"):
        query["member_type"] = member_type
    members = await db.member_registry.find(query, {"_id": 0}).sort("registered_at", -1).to_list(500)
    counts = {
        "BUYER_PRO": await db.member_registry.count_documents({"member_type": "BUYER_PRO"}),
        "VENDOR_PRO": await db.member_registry.count_documents({"member_type": "VENDOR_PRO"}),
    }
    return {"members": members, "counts": counts}
