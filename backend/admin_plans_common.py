"""Super Admin Plans — Models & shared helpers (split from routes_admin_plans.py)."""
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_admin_plans_common_database(database):
    global db
    db = database

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
    visible: bool = True
    visible_from: Optional[str] = None
    visible_until: Optional[str] = None
    target_profiles: List[str] = ["all"]


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
    visible: Optional[bool] = None
    visible_from: Optional[str] = None
    visible_until: Optional[str] = None
    target_profiles: Optional[List[str]] = None


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
    visible: bool = True
    visible_from: Optional[str] = None
    visible_until: Optional[str] = None
    target_profiles: List[str] = ["all"]
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

async def get_current_admin_from_request(request):
    """Resolve admin from Authorization header or httpOnly cookie."""
    from auth import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    if not user_id:
        return None
    user = await db.users.find_one({"id": user_id})
    if user and (user.get("role") == "admin" or user.get("is_admin") is True):
        return user
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


