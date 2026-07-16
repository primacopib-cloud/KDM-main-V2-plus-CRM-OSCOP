"""Core admin routes: stats, users, quotes moderation, credits, organizations
listing, vendor alias (split from server.py)."""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from models import (
    UserResponse, QuoteRequestResponse, AdminStats, UserListResponse,
    OrganizationResponse,
)
from db import get_database
from core_deps import get_current_user, get_user_by_id, check_admin

logger = logging.getLogger(__name__)

admin_core_router = APIRouter(prefix="/api")


@admin_core_router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard statistics."""
    await check_admin(current_user)
    db = get_database()

    total_users = await db.users.count_documents({})
    total_quotes = await db.quote_requests.count_documents({})
    total_orders = await db.orders.count_documents({})

    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$credits"}}}]
    credits_result = await db.users.aggregate(pipeline).to_list(1)
    total_credits = credits_result[0]["total"] if credits_result else 0

    quotes_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    quotes_by_status_list = await db.quote_requests.aggregate(quotes_pipeline).to_list(10)
    quotes_by_status = {q["_id"]: q["count"] for q in quotes_by_status_list}

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = await db.users.count_documents({"created_at": {"$gte": month_start}})
    new_quotes_this_month = await db.quote_requests.count_documents({"created_at": {"$gte": month_start}})

    return AdminStats(
        total_users=total_users,
        total_quotes=total_quotes,
        total_orders=total_orders,
        total_credits_distributed=total_credits,
        quotes_by_status=quotes_by_status,
        new_users_this_month=new_users_this_month,
        new_quotes_this_month=new_quotes_this_month
    )


@admin_core_router.get("/admin/users", response_model=UserListResponse)
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    per_page: int = 20,
    search: str = None
):
    """Get all users (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if search:
        query = {
            "$or": [
                {"email": {"$regex": search, "$options": "i"}},
                {"company_name": {"$regex": search, "$options": "i"}},
                {"contact_name": {"$regex": search, "$options": "i"}}
            ]
        }

    total = await db.users.count_documents(query)
    skip = (page - 1) * per_page

    users = await db.users.find(query).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)

    return UserListResponse(
        users=[UserResponse(
            id=u["id"],
            email=u["email"],
            company_name=u["company_name"],
            siret=u["siret"],
            contact_name=u["contact_name"],
            phone=u["phone"],
            subscription=u["subscription"],
            credits=u["credits"],
            is_admin=u.get("is_admin", False),
            created_at=u["created_at"]
        ) for u in users],
        total=total,
        page=page,
        per_page=per_page
    )


@admin_core_router.get("/admin/quotes", response_model=List[QuoteRequestResponse])
async def get_all_quotes(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all quote requests (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if status_filter:
        query["status"] = status_filter

    quotes = await db.quote_requests.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [QuoteRequestResponse(**q) for q in quotes]


@admin_core_router.put("/admin/quotes/{quote_id}/status", response_model=dict)
async def update_quote_status(
    quote_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update quote request status (admin only)."""
    await check_admin(current_user)
    db = get_database()

    result = await db.quote_requests.update_one(
        {"id": quote_id},
        {"$set": {"status": new_status}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande non trouvée"
        )

    return {"message": "Statut mis à jour", "status": new_status}


@admin_core_router.put("/admin/users/{user_id}/credits", response_model=dict)
async def admin_update_credits(
    user_id: str,
    amount: int,
    current_user: dict = Depends(get_current_user)
):
    """Update user credits (admin only)."""
    await check_admin(current_user)
    db = get_database()

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    new_credits = user["credits"] + amount
    if new_credits < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les crédits ne peuvent pas être négatifs"
        )

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_credits, "updated_at": datetime.utcnow()}}
    )

    await db.credits_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "added" if amount > 0 else "used",
        "amount": abs(amount),
        "description": f"Ajusté par admin ({current_user['email']})",
        "created_at": datetime.utcnow()
    })

    logger.info(f"Admin {current_user['email']} updated credits for {user['email']}: {amount}")

    return {"credits": new_credits, "message": f"Crédits mis à jour: {'+' if amount > 0 else ''}{amount}"}


@admin_core_router.get("/admin/organizations", response_model=List[OrganizationResponse])
async def get_all_organizations(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all organizations (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if status_filter:
        query["status"] = status_filter

    orgs = await db.organizations.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [OrganizationResponse(**o) for o in orgs]


@admin_core_router.get("/admin/products/pending")
async def admin_products_pending_alias():
    """Alias for /api/vendor/admin/products/pending"""
    from routes_vendor_admin import admin_list_pending_products
    return await admin_list_pending_products()
