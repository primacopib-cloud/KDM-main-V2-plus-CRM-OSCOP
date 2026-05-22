"""
Super Admin - Subscription Plans & Credits Management
Allows super admins to manage subscription plans, options, and credits
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Database connection
client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_admin_plans_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database


admin_plans_router = APIRouter(prefix="/admin/plans", tags=["Admin - Plans & Credits"])


# ============== MODELS ==============

class PlanPeriod(str, Enum):
    MONTH = "mois"
    YEAR = "an"
    ONE_TIME = "unique"


class SubscriptionPlanCreate(BaseModel):
    """Create a new subscription plan"""
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None  # Auto-generated if not provided
    description: Optional[str] = None
    price_cents: int = Field(..., ge=0)
    period: PlanPeriod = PlanPeriod.MONTH
    default_credits: int = Field(default=100, ge=0)
    features: List[str] = []
    popular: bool = False
    active: bool = True
    sort_order: int = 0
    max_zones: int = 1
    max_users: int = 1
    color: Optional[str] = "#D9B35A"


class SubscriptionPlanUpdate(BaseModel):
    """Update an existing subscription plan"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(None, ge=0)
    period: Optional[PlanPeriod] = None
    default_credits: Optional[int] = Field(None, ge=0)
    features: Optional[List[str]] = None
    popular: Optional[bool] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None
    max_zones: Optional[int] = None
    max_users: Optional[int] = None
    color: Optional[str] = None


class SubscriptionPlanResponse(BaseModel):
    """Subscription plan response"""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    price_cents: int
    period: str
    default_credits: int
    features: List[str]
    popular: bool
    active: bool
    sort_order: int
    max_zones: int
    max_users: int
    color: str
    subscribers_count: int = 0
    created_at: str
    updated_at: str


class PlanOptionCreate(BaseModel):
    """Create a plan option/addon"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price_cents: int = Field(..., ge=0)
    period: PlanPeriod = PlanPeriod.MONTH
    credits_included: int = 0
    compatible_plans: List[str] = []  # Empty = all plans
    active: bool = True
    sort_order: int = 0


class PlanOptionUpdate(BaseModel):
    """Update a plan option"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(None, ge=0)
    period: Optional[PlanPeriod] = None
    credits_included: Optional[int] = None
    compatible_plans: Optional[List[str]] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanOptionResponse(BaseModel):
    """Plan option response"""
    id: str
    name: str
    description: Optional[str] = None
    price_cents: int
    period: str
    credits_included: int
    compatible_plans: List[str]
    active: bool
    sort_order: int
    created_at: str
    updated_at: str


class CreditAdjustment(BaseModel):
    """Credit adjustment for a user/org"""
    amount: int = Field(..., description="Positive to add, negative to deduct")
    reason: str = Field(..., min_length=1, max_length=500)
    reference: Optional[str] = None  # Invoice, order, etc.


class CreditHistoryItem(BaseModel):
    """Credit history entry"""
    id: str
    amount: int
    balance_after: int
    reason: str
    reference: Optional[str] = None
    admin_id: str
    admin_email: str
    created_at: str


# ============== HELPER: Auth ==============

async def get_current_admin(authorization: str = None):
    """Extract admin user from token. Admin = role=='admin' OR is_admin==True."""
    if not authorization:
        return None
    
    try:
        from jose import jwt
        token = authorization.replace("Bearer ", "")
        secret = os.environ.get("JWT_SECRET_KEY", "kdmarche-oscop-b2b-ess-secret-key-2025")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if user and (
                user.get("role") == "admin"
                or user.get("is_admin") is True
            ):
                return user
    except Exception as e:
        print(f"Auth error: {e}")
    return None


def slugify(text: str) -> str:
    """Generate a slug from text"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


# ============== SUBSCRIPTION PLANS API ==============

@admin_plans_router.get("/subscriptions", response_model=List[SubscriptionPlanResponse])
async def list_subscription_plans(
    request: Request,
    include_inactive: bool = False
):
    """
    GET /api/admin/plans/subscriptions
    List all subscription plans
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    query = {} if include_inactive else {"active": True}
    cursor = db.subscription_plans.find(query).sort("sort_order", 1)
    plans = await cursor.to_list(100)
    
    # Count subscribers for each plan
    result = []
    for plan in plans:
        count = await db.subscriptions.count_documents({"plan_id": plan.get("id")})
        result.append(SubscriptionPlanResponse(
            id=plan.get("id"),
            name=plan.get("name"),
            slug=plan.get("slug", ""),
            description=plan.get("description"),
            price_cents=plan.get("price_cents", 0),
            period=plan.get("period", "mois"),
            default_credits=plan.get("default_credits", 100),
            features=plan.get("features", []),
            popular=plan.get("popular", False),
            active=plan.get("active", True),
            sort_order=plan.get("sort_order", 0),
            max_zones=plan.get("max_zones", 1),
            max_users=plan.get("max_users", 1),
            color=plan.get("color", "#D9B35A"),
            subscribers_count=count,
            created_at=plan.get("created_at", ""),
            updated_at=plan.get("updated_at", "")
        ))
    
    return result


@admin_plans_router.post("/subscriptions", response_model=SubscriptionPlanResponse)
async def create_subscription_plan(data: SubscriptionPlanCreate, request: Request):
    """
    POST /api/admin/plans/subscriptions
    Create a new subscription plan
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Generate slug
    slug = data.slug or slugify(data.name)
    
    # Check for duplicate slug
    existing = await db.subscription_plans.find_one({"slug": slug})
    if existing:
        raise HTTPException(status_code=400, detail="Un plan avec ce nom existe déjà")
    
    now = datetime.now(timezone.utc).isoformat()
    plan_id = str(uuid.uuid4())
    
    new_plan = {
        "id": plan_id,
        "name": data.name,
        "slug": slug,
        "description": data.description,
        "price_cents": data.price_cents,
        "period": data.period.value,
        "default_credits": data.default_credits,
        "features": data.features,
        "popular": data.popular,
        "active": data.active,
        "sort_order": data.sort_order,
        "max_zones": data.max_zones,
        "max_users": data.max_users,
        "color": data.color or "#D9B35A",
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("id")
    }
    
    await db.subscription_plans.insert_one(new_plan)
    
    return SubscriptionPlanResponse(
        id=plan_id,
        name=data.name,
        slug=slug,
        description=data.description,
        price_cents=data.price_cents,
        period=data.period.value,
        default_credits=data.default_credits,
        features=data.features,
        popular=data.popular,
        active=data.active,
        sort_order=data.sort_order,
        max_zones=data.max_zones,
        max_users=data.max_users,
        color=data.color or "#D9B35A",
        subscribers_count=0,
        created_at=now,
        updated_at=now
    )


@admin_plans_router.get("/subscriptions/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(plan_id: str, request: Request):
    """
    GET /api/admin/plans/subscriptions/{plan_id}
    Get a specific subscription plan
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    plan = await db.subscription_plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    
    count = await db.subscriptions.count_documents({"plan_id": plan_id})
    
    return SubscriptionPlanResponse(
        id=plan.get("id"),
        name=plan.get("name"),
        slug=plan.get("slug", ""),
        description=plan.get("description"),
        price_cents=plan.get("price_cents", 0),
        period=plan.get("period", "mois"),
        default_credits=plan.get("default_credits", 100),
        features=plan.get("features", []),
        popular=plan.get("popular", False),
        active=plan.get("active", True),
        sort_order=plan.get("sort_order", 0),
        max_zones=plan.get("max_zones", 1),
        max_users=plan.get("max_users", 1),
        color=plan.get("color", "#D9B35A"),
        subscribers_count=count,
        created_at=plan.get("created_at", ""),
        updated_at=plan.get("updated_at", "")
    )


@admin_plans_router.patch("/subscriptions/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_subscription_plan(plan_id: str, data: SubscriptionPlanUpdate, request: Request):
    """
    PATCH /api/admin/plans/subscriptions/{plan_id}
    Update a subscription plan
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    plan = await db.subscription_plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    
    update_data = data.model_dump(exclude_unset=True)
    if "period" in update_data and update_data["period"]:
        update_data["period"] = update_data["period"].value if hasattr(update_data["period"], 'value') else update_data["period"]
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.subscription_plans.update_one(
        {"id": plan_id},
        {"$set": update_data}
    )
    
    updated = await db.subscription_plans.find_one({"id": plan_id})
    count = await db.subscriptions.count_documents({"plan_id": plan_id})
    
    return SubscriptionPlanResponse(
        id=updated.get("id"),
        name=updated.get("name"),
        slug=updated.get("slug", ""),
        description=updated.get("description"),
        price_cents=updated.get("price_cents", 0),
        period=updated.get("period", "mois"),
        default_credits=updated.get("default_credits", 100),
        features=updated.get("features", []),
        popular=updated.get("popular", False),
        active=updated.get("active", True),
        sort_order=updated.get("sort_order", 0),
        max_zones=updated.get("max_zones", 1),
        max_users=updated.get("max_users", 1),
        color=updated.get("color", "#D9B35A"),
        subscribers_count=count,
        created_at=updated.get("created_at", ""),
        updated_at=updated.get("updated_at", "")
    )


@admin_plans_router.delete("/subscriptions/{plan_id}")
async def delete_subscription_plan(plan_id: str, request: Request, force: bool = False):
    """
    DELETE /api/admin/plans/subscriptions/{plan_id}
    Delete a subscription plan (soft delete by default, force=true for hard delete)
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    plan = await db.subscription_plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    
    # Check for active subscriptions
    active_subs = await db.subscriptions.count_documents({"plan_id": plan_id, "status": "active"})
    if active_subs > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer: {active_subs} abonnement(s) actif(s). Utilisez force=true pour forcer."
        )
    
    if force:
        await db.subscription_plans.delete_one({"id": plan_id})
        return {"message": "Plan supprimé définitivement", "id": plan_id}
    else:
        await db.subscription_plans.update_one(
            {"id": plan_id},
            {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "Plan désactivé", "id": plan_id}


# ============== PLAN OPTIONS/ADDONS API ==============

@admin_plans_router.get("/options", response_model=List[PlanOptionResponse])
async def list_plan_options(request: Request, include_inactive: bool = False):
    """
    GET /api/admin/plans/options
    List all plan options/addons
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    query = {} if include_inactive else {"active": True}
    cursor = db.plan_options.find(query).sort("sort_order", 1)
    options = await cursor.to_list(100)
    
    return [PlanOptionResponse(
        id=opt.get("id"),
        name=opt.get("name"),
        description=opt.get("description"),
        price_cents=opt.get("price_cents", 0),
        period=opt.get("period", "mois"),
        credits_included=opt.get("credits_included", 0),
        compatible_plans=opt.get("compatible_plans", []),
        active=opt.get("active", True),
        sort_order=opt.get("sort_order", 0),
        created_at=opt.get("created_at", ""),
        updated_at=opt.get("updated_at", "")
    ) for opt in options]


@admin_plans_router.post("/options", response_model=PlanOptionResponse)
async def create_plan_option(data: PlanOptionCreate, request: Request):
    """
    POST /api/admin/plans/options
    Create a new plan option/addon
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    now = datetime.now(timezone.utc).isoformat()
    option_id = str(uuid.uuid4())
    
    new_option = {
        "id": option_id,
        "name": data.name,
        "description": data.description,
        "price_cents": data.price_cents,
        "period": data.period.value,
        "credits_included": data.credits_included,
        "compatible_plans": data.compatible_plans,
        "active": data.active,
        "sort_order": data.sort_order,
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("id")
    }
    
    await db.plan_options.insert_one(new_option)
    
    return PlanOptionResponse(
        id=option_id,
        name=data.name,
        description=data.description,
        price_cents=data.price_cents,
        period=data.period.value,
        credits_included=data.credits_included,
        compatible_plans=data.compatible_plans,
        active=data.active,
        sort_order=data.sort_order,
        created_at=now,
        updated_at=now
    )


@admin_plans_router.patch("/options/{option_id}", response_model=PlanOptionResponse)
async def update_plan_option(option_id: str, data: PlanOptionUpdate, request: Request):
    """
    PATCH /api/admin/plans/options/{option_id}
    Update a plan option
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    option = await db.plan_options.find_one({"id": option_id})
    if not option:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    update_data = data.model_dump(exclude_unset=True)
    if "period" in update_data and update_data["period"]:
        update_data["period"] = update_data["period"].value if hasattr(update_data["period"], 'value') else update_data["period"]
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.plan_options.update_one(
        {"id": option_id},
        {"$set": update_data}
    )
    
    updated = await db.plan_options.find_one({"id": option_id})
    
    return PlanOptionResponse(
        id=updated.get("id"),
        name=updated.get("name"),
        description=updated.get("description"),
        price_cents=updated.get("price_cents", 0),
        period=updated.get("period", "mois"),
        credits_included=updated.get("credits_included", 0),
        compatible_plans=updated.get("compatible_plans", []),
        active=updated.get("active", True),
        sort_order=updated.get("sort_order", 0),
        created_at=updated.get("created_at", ""),
        updated_at=updated.get("updated_at", "")
    )


@admin_plans_router.delete("/options/{option_id}")
async def delete_plan_option(option_id: str, request: Request):
    """
    DELETE /api/admin/plans/options/{option_id}
    Delete a plan option
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    admin = await get_current_admin(authorization)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    result = await db.plan_options.delete_one({"id": option_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    return {"message": "Option supprimée", "id": option_id}


# ============== CREDITS MANAGEMENT API ==============

@admin_plans_router.get("/credits/users")
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


@admin_plans_router.get("/credits/users/{user_id}")
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


@admin_plans_router.post("/credits/users/{user_id}/adjust")
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


@admin_plans_router.post("/credits/bulk-adjust")
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

@admin_plans_router.get("/stats")
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
