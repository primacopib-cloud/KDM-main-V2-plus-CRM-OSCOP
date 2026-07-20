"""
Super Admin - Subscription Plans & Credits Management
Allows super admins to manage subscription plans, options, and credits

Découpé en modules : admin_plans_common, routes_admin_plans_credits.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from admin_plans_common import (
    get_current_admin_from_request,
    get_current_admin, slugify, PlanPeriod,
    SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanResponse,
    PlanOptionCreate, PlanOptionUpdate, PlanOptionResponse,
    set_admin_plans_common_database,
)
from routes_admin_plans_credits import set_admin_plans_credits_database

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_admin_plans_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database
    set_admin_plans_common_database(database)
    set_admin_plans_credits_database(database)


admin_plans_router = APIRouter(prefix="/admin/plans", tags=["Admin - Plans & Credits"])

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
    admin = await get_current_admin_from_request(request)
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
            visible=plan.get("visible", True),
            visible_from=plan.get("visible_from"),
            visible_until=plan.get("visible_until"),
            target_profiles=plan.get("target_profiles") or ["all"],
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
    admin = await get_current_admin_from_request(request)
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
        "visible": data.visible,
        "visible_from": data.visible_from,
        "visible_until": data.visible_until,
        "target_profiles": data.target_profiles or ["all"],
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
        visible=data.visible,
        visible_from=data.visible_from,
        visible_until=data.visible_until,
        target_profiles=data.target_profiles or ["all"],
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
    admin = await get_current_admin_from_request(request)
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
        visible=plan.get("visible", True),
        visible_from=plan.get("visible_from"),
        visible_until=plan.get("visible_until"),
        target_profiles=plan.get("target_profiles") or ["all"],
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
    admin = await get_current_admin_from_request(request)
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

    if "price_cents" in update_data and update_data["price_cents"] != plan.get("price_cents"):
        from consultation_audit import audit
        await audit("PLAN_PRICE_CHANGED", admin.get("email"), None, {
            "plan_id": plan_id, "plan_name": plan.get("name"),
            "old_price_cents": plan.get("price_cents"), "new_price_cents": update_data["price_cents"],
            "old_price_eur": round((plan.get("price_cents") or 0) / 100, 2),
            "new_price_eur": round(update_data["price_cents"] / 100, 2),
        })
    
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
        visible=updated.get("visible", True),
        visible_from=updated.get("visible_from"),
        visible_until=updated.get("visible_until"),
        target_profiles=updated.get("target_profiles") or ["all"],
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
    admin = await get_current_admin_from_request(request)
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
    admin = await get_current_admin_from_request(request)
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
    admin = await get_current_admin_from_request(request)
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
    admin = await get_current_admin_from_request(request)
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

    if "price_cents" in update_data and update_data["price_cents"] != option.get("price_cents"):
        from consultation_audit import audit
        await audit("OPTION_PRICE_CHANGED", admin.get("email"), None, {
            "option_id": option_id, "option_name": option.get("name"),
            "old_price_cents": option.get("price_cents"), "new_price_cents": update_data["price_cents"],
            "old_price_eur": round((option.get("price_cents") or 0) / 100, 2),
            "new_price_eur": round(update_data["price_cents"] / 100, 2),
        })
    
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
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    result = await db.plan_options.delete_one({"id": option_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    return {"message": "Option supprimée", "id": option_id}


