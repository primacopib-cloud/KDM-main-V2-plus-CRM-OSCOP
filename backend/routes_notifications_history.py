"""
Notifications History API
Extended notification management with filtering and history
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Database connection
client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]

def set_notifications_history_database(database):
    """Inject shared database reference from server.py/test_server.py."""
    global db
    db = database


notifications_history_router = APIRouter(prefix="/notifications", tags=["Notifications History"])


# ============== MODELS ==============

class NotificationType(str, Enum):
    """Types of notifications"""
    NEW_QUOTE = "new_quote"
    NEW_USER = "new_user"
    ORG_SUBMITTED = "org_submitted"
    ORG_APPROVED = "org_approved"
    ORG_REJECTED = "org_rejected"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_PAST_DUE = "subscription_past_due"
    ORDER_CREATED = "order_created"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    WALLET_CREDIT = "wallet_credit"
    WALLET_DEBIT = "wallet_debit"
    SYSTEM_ALERT = "system_alert"
    DOCUMENT_READY = "document_ready"
    POD_AVAILABLE = "pod_available"


class NotificationItem(BaseModel):
    """Notification item for list display"""
    id: str
    type: str
    title: str
    message: Optional[str] = None
    data: Optional[dict] = None
    is_read: bool = False
    created_at: str
    action_url: Optional[str] = None


class NotificationStats(BaseModel):
    """Statistics about notifications"""
    total: int
    unread: int
    by_type: dict


class NotificationHistoryResponse(BaseModel):
    """Paginated notification history response"""
    notifications: List[NotificationItem]
    total: int
    page: int
    page_size: int
    has_more: bool
    stats: Optional[NotificationStats] = None


class DateFilter(str, Enum):
    """Date filter options"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    ALL = "all"


# ============== HELPER: Get Current User ==============

async def get_current_user_from_token(authorization: str = None):
    """Extract user from token"""
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
            return user
    except Exception:
        pass
    return None

async def get_current_user_from_request(request):
    """Resolve user from Authorization header or httpOnly cookie."""
    from auth import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    if not user_id:
        return None
    return await db.users.find_one({"id": user_id})



def get_date_range(date_filter: DateFilter) -> tuple:
    """Get start and end dates for filter"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_filter == DateFilter.TODAY:
        return today_start, now
    elif date_filter == DateFilter.YESTERDAY:
        yesterday_start = today_start - timedelta(days=1)
        return yesterday_start, today_start
    elif date_filter == DateFilter.LAST_7_DAYS:
        week_ago = today_start - timedelta(days=7)
        return week_ago, now
    elif date_filter == DateFilter.LAST_30_DAYS:
        month_ago = today_start - timedelta(days=30)
        return month_ago, now
    else:  # ALL
        return None, None


# ============== HISTORY API ==============

from fastapi import Header, Request

@notifications_history_router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    date_filter: DateFilter = Query(DateFilter.ALL, description="Filter by date range"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    search: Optional[str] = Query(None, description="Search in title and message"),
    include_stats: bool = Query(False, description="Include notification statistics")
):
    """
    GET /api/notifications/history
    
    Get paginated notification history with advanced filtering.
    Supports filtering by type, date range, read status, and text search.
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    is_admin = user.get("role") == "admin" or "admin" in user.get("email", "")
    
    # Build query
    query = {}
    
    if is_admin:
        # Admins see role-targeted or all-admin notifications
        query["$or"] = [
            {"target_roles": {"$in": ["admin"]}},
            {"target_user_id": user_id}
        ]
    else:
        # Regular users only see their notifications
        query["target_user_id"] = user_id
    
    # Filter by type
    if notification_type:
        query["type"] = notification_type
    
    # Filter by date
    start_date, end_date = get_date_range(date_filter)
    if start_date:
        query["created_at"] = {"$gte": start_date.isoformat()}
    if end_date and "created_at" in query:
        query["created_at"]["$lte"] = end_date.isoformat()
    elif end_date:
        query["created_at"] = {"$lte": end_date.isoformat()}
    
    # Filter by read status
    if is_read is not None:
        if is_read:
            query["read_by"] = user_id
        else:
            query["read_by"] = {"$ne": user_id}
    
    # Search in title and message
    if search:
        query["$or"] = query.get("$or", [])
        query["$and"] = [
            {"$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"message": {"$regex": search, "$options": "i"}}
            ]}
        ]
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get total count
    total = await db.notifications.count_documents(query)
    
    # Get notifications
    cursor = db.notifications.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    notifications_raw = await cursor.to_list(page_size)
    
    # Format notifications
    notifications = []
    for n in notifications_raw:
        notifications.append(NotificationItem(
            id=n.get("id", str(n.get("_id", ""))),
            type=n.get("type", "system_alert"),
            title=n.get("title", "Notification"),
            message=n.get("message"),
            data=n.get("data"),
            is_read=user_id in n.get("read_by", []),
            created_at=n.get("created_at", datetime.now(timezone.utc).isoformat()),
            action_url=n.get("action_url")
        ))
    
    # Calculate stats if requested
    stats = None
    if include_stats:
        # Get stats for user
        base_query = {}
        if is_admin:
            base_query["$or"] = [
                {"target_roles": {"$in": ["admin"]}},
                {"target_user_id": user_id}
            ]
        else:
            base_query["target_user_id"] = user_id
        
        total_all = await db.notifications.count_documents(base_query)
        
        # Unread count
        unread_query = {**base_query, "read_by": {"$ne": user_id}}
        unread_count = await db.notifications.count_documents(unread_query)
        
        # Count by type
        pipeline = [
            {"$match": base_query},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        by_type_cursor = db.notifications.aggregate(pipeline)
        by_type_raw = await by_type_cursor.to_list(100)
        by_type = {item["_id"]: item["count"] for item in by_type_raw if item["_id"]}
        
        stats = NotificationStats(
            total=total_all,
            unread=unread_count,
            by_type=by_type
        )
    
    return NotificationHistoryResponse(
        notifications=notifications,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
        stats=stats
    )


@notifications_history_router.get("/types")
async def get_notification_types(request: Request):
    """
    GET /api/notifications/types
    
    Get available notification types with labels and icons.
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    types = [
        {"value": "new_quote", "label": "Demande de devis", "icon": "FileText", "color": "#D9B35A"},
        {"value": "new_user", "label": "Nouvel utilisateur", "icon": "User", "color": "#57D19A"},
        {"value": "org_submitted", "label": "Organisation soumise", "icon": "Building2", "color": "#3B82F6"},
        {"value": "org_approved", "label": "Organisation approuvée", "icon": "CheckCircle", "color": "#10B981"},
        {"value": "org_rejected", "label": "Organisation rejetée", "icon": "XCircle", "color": "#EF4444"},
        {"value": "subscription_activated", "label": "Abonnement activé", "icon": "CreditCard", "color": "#8B5CF6"},
        {"value": "subscription_past_due", "label": "Paiement en retard", "icon": "AlertTriangle", "color": "#F59E0B"},
        {"value": "order_created", "label": "Commande créée", "icon": "ShoppingCart", "color": "#06B6D4"},
        {"value": "order_shipped", "label": "Commande expédiée", "icon": "Truck", "color": "#14B8A6"},
        {"value": "order_delivered", "label": "Commande livrée", "icon": "Package", "color": "#22C55E"},
        {"value": "wallet_credit", "label": "Crédit wallet", "icon": "Plus", "color": "#10B981"},
        {"value": "wallet_debit", "label": "Débit wallet", "icon": "Minus", "color": "#EF4444"},
        {"value": "system_alert", "label": "Alerte système", "icon": "Bell", "color": "#6B7280"},
        {"value": "document_ready", "label": "Document prêt", "icon": "FileCheck", "color": "#8B5CF6"},
        {"value": "pod_available", "label": "POD disponible", "icon": "ClipboardCheck", "color": "#0EA5E9"},
    ]
    
    return {"types": types}


@notifications_history_router.delete("/history/clear-read")
async def clear_read_notifications(request: Request):
    """
    DELETE /api/notifications/history/clear-read
    
    Delete all read notifications (older than 30 days).
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    is_admin = user.get("role") == "admin" or "admin" in user.get("email", "")
    
    # Only clear notifications older than 30 days that are read
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    query = {
        "read_by": user_id,
        "created_at": {"$lt": thirty_days_ago}
    }
    
    if not is_admin:
        query["target_user_id"] = user_id
    
    result = await db.notifications.delete_many(query)
    
    return {
        "message": f"{result.deleted_count} notification(s) supprimée(s)",
        "deleted_count": result.deleted_count
    }


@notifications_history_router.get("/stats")
async def get_notification_stats(request: Request):
    """
    GET /api/notifications/stats
    
    Get notification statistics for the current user.
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    user_id = user.get("id")
    is_admin = user.get("role") == "admin" or "admin" in user.get("email", "")
    
    # Build base query
    base_query = {}
    if is_admin:
        base_query["$or"] = [
            {"target_roles": {"$in": ["admin"]}},
            {"target_user_id": user_id}
        ]
    else:
        base_query["target_user_id"] = user_id
    
    # Total count
    total = await db.notifications.count_documents(base_query)
    
    # Unread count
    unread_query = {**base_query, "read_by": {"$ne": user_id}}
    unread = await db.notifications.count_documents(unread_query)
    
    # Today's count
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = {**base_query, "created_at": {"$gte": today_start.isoformat()}}
    today_count = await db.notifications.count_documents(today_query)
    
    # This week's count
    week_start = today_start - timedelta(days=today_start.weekday())
    week_query = {**base_query, "created_at": {"$gte": week_start.isoformat()}}
    week_count = await db.notifications.count_documents(week_query)
    
    # By type aggregation
    pipeline = [
        {"$match": base_query},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_type_cursor = db.notifications.aggregate(pipeline)
    by_type_raw = await by_type_cursor.to_list(10)
    by_type = {item["_id"]: item["count"] for item in by_type_raw if item["_id"]}
    
    return {
        "total": total,
        "unread": unread,
        "today": today_count,
        "this_week": week_count,
        "by_type": by_type
    }
