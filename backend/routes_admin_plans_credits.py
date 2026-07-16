"""Super Admin — Credits management & stats (split from routes_admin_plans.py)."""
from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from admin_plans_common import (
    get_current_admin, slugify, CreditAdjustment, CreditHistoryItem,
)

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_admin_plans_credits_database(database):
    global db
    db = database

admin_plans_credits_router = APIRouter(prefix="/admin/plans", tags=["Admin - Plans & Credits"])

# ============== CREDITS MANAGEMENT API ==============

@admin_plans_credits_router.get("/credits/users")
async def list_users_with_credits(
    request: Request,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    GET /api/admin/plans/credits/users
    List users/orgs with their credit balances
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Build query
    query = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}},
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * page_size
    total = await db.users.count_documents(query)
    
    cursor = db.users.find(query).skip(skip).limit(page_size)
    users = await cursor.to_list(page_size)
    
    result = []
    for user in users:
        # Get credit balance from wallet
        wallet = await db.wallets.find_one({"user_id": user.get("id")})
        balance = wallet.get("balance_credits", 0) if wallet else 0
        
        result.append({
            "user_id": user.get("id"),
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "company_name": user.get("company_name"),
            "role": user.get("role"),
            "credits_balance": balance
        })
    
    return {
        "users": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (skip + page_size) < total
    }


@admin_plans_credits_router.get("/credits/users/{user_id}")
async def get_user_credits(user_id: str, request: Request):
    """
    GET /api/admin/plans/credits/users/{user_id}
    Get credit details for a specific user
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    wallet = await db.wallets.find_one({"user_id": user_id})
    balance = wallet.get("balance_credits", 0) if wallet else 0
    
    # Get credit history
    cursor = db.credit_history.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    history = await cursor.to_list(50)
    
    return {
        "user_id": user_id,
        "email": user.get("email"),
        "company_name": user.get("company_name"),
        "credits_balance": balance,
        "history": [{
            "id": h.get("id"),
            "amount": h.get("amount"),
            "balance_after": h.get("balance_after"),
            "reason": h.get("reason"),
            "reference": h.get("reference"),
            "admin_email": h.get("admin_email"),
            "created_at": h.get("created_at")
        } for h in history]
    }


@admin_plans_credits_router.post("/credits/users/{user_id}/adjust")
async def adjust_user_credits(user_id: str, data: CreditAdjustment, request: Request):
    """
    POST /api/admin/plans/credits/users/{user_id}/adjust
    Add or deduct credits from a user
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    # Get or create wallet
    wallet = await db.wallets.find_one({"user_id": user_id})
    current_balance = wallet.get("balance_credits", 0) if wallet else 0
    
    new_balance = current_balance + data.amount
    
    if new_balance < 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Solde insuffisant. Balance actuelle: {current_balance}, déduction demandée: {abs(data.amount)}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update wallet
    await db.wallets.update_one(
        {"user_id": user_id},
        {
            "$set": {"balance_credits": new_balance, "updated_at": now},
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    
    # Record history
    history_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": data.amount,
        "balance_after": new_balance,
        "reason": data.reason,
        "reference": data.reference,
        "admin_id": admin.get("id"),
        "admin_email": admin.get("email"),
        "created_at": now
    }
    
    await db.credit_history.insert_one(history_entry)
    
    action = "ajoutés" if data.amount > 0 else "déduits"
    
    return {
        "message": f"{abs(data.amount)} crédits {action}",
        "user_id": user_id,
        "previous_balance": current_balance,
        "adjustment": data.amount,
        "new_balance": new_balance,
        "reason": data.reason
    }


@admin_plans_credits_router.post("/credits/bulk-adjust")
async def bulk_adjust_credits(request: Request):
    """
    POST /api/admin/plans/credits/bulk-adjust
    Bulk adjust credits for multiple users
    Body: { "adjustments": [{ "user_id": "...", "amount": 100, "reason": "..." }] }
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    body = await request.json()
    adjustments = body.get("adjustments", [])
    
    if not adjustments:
        raise HTTPException(status_code=400, detail="Aucun ajustement fourni")
    
    results = []
    now = datetime.now(timezone.utc).isoformat()
    
    for adj in adjustments:
        user_id = adj.get("user_id")
        amount = adj.get("amount", 0)
        reason = adj.get("reason", "Ajustement en lot")
        
        user = await db.users.find_one({"id": user_id})
        if not user:
            results.append({"user_id": user_id, "status": "error", "message": "Utilisateur non trouvé"})
            continue
        
        wallet = await db.wallets.find_one({"user_id": user_id})
        current_balance = wallet.get("balance_credits", 0) if wallet else 0
        new_balance = current_balance + amount
        
        if new_balance < 0:
            results.append({
                "user_id": user_id, 
                "status": "error", 
                "message": f"Solde insuffisant ({current_balance})"
            })
            continue
        
        await db.wallets.update_one(
            {"user_id": user_id},
            {"$set": {"balance_credits": new_balance, "updated_at": now}},
            upsert=True
        )
        
        await db.credit_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "amount": amount,
            "balance_after": new_balance,
            "reason": reason,
            "admin_id": admin.get("id"),
            "admin_email": admin.get("email"),
            "created_at": now
        })
        
        results.append({
            "user_id": user_id,
            "status": "success",
            "previous_balance": current_balance,
            "new_balance": new_balance
        })
    
    success_count = len([r for r in results if r["status"] == "success"])
    
    return {
        "message": f"{success_count}/{len(adjustments)} ajustements effectués",
        "results": results
    }


# ============== STATS ==============

@admin_plans_credits_router.get("/stats")
async def get_plans_stats(request: Request):
    """
    GET /api/admin/plans/stats
    Get statistics about plans and credits
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Plans count
    total_plans = await db.subscription_plans.count_documents({})
    active_plans = await db.subscription_plans.count_documents({"active": True})
    
    # Options count
    total_options = await db.plan_options.count_documents({})
    active_options = await db.plan_options.count_documents({"active": True})
    
    # Subscriptions
    total_subscriptions = await db.subscriptions.count_documents({})
    active_subscriptions = await db.subscriptions.count_documents({"status": "active"})
    
    # Credits
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$balance_credits"}}}
    ]
    credits_result = await db.wallets.aggregate(pipeline).to_list(1)
    total_credits = credits_result[0]["total"] if credits_result else 0
    
    # Recent credit adjustments
    recent_adjustments = await db.credit_history.count_documents({})
    
    return {
        "plans": {
            "total": total_plans,
            "active": active_plans
        },
        "options": {
            "total": total_options,
            "active": active_options
        },
        "subscriptions": {
            "total": total_subscriptions,
            "active": active_subscriptions
        },
        "credits": {
            "total_distributed": total_credits,
            "total_adjustments": recent_adjustments
        }
    }
