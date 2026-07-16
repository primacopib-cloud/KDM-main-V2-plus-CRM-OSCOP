"""
KDMARCHE × O'SCOP - Super Admin API Routes
Dashboard de gestion avec KPIs complets
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import os
import logging

logger = logging.getLogger(__name__)


superadmin_stats_router = APIRouter(prefix="/api/superadmin")

db = None

def set_superadmin_stats_database(database):
    global db
    db = database

# ============== ADVANCED STATISTICS ==============

@superadmin_stats_router.get("/advanced-stats")
async def get_advanced_stats(period: str = "month"):
    """
    Get advanced statistics with trend data for charts
    Period: week, month, quarter, year
    """
    now = datetime.now(timezone.utc)
    
    # Calculate periods for trends
    if period == "week":
        days_back = 7
        group_by = "day"
    elif period == "month":
        days_back = 30
        group_by = "day"
    elif period == "quarter":
        days_back = 90
        group_by = "week"
    else:  # year
        days_back = 365
        group_by = "month"
    
    start_date = now - timedelta(days=days_back)
    
    # === SALES TRENDS ===
    try:
        # Daily/Weekly/Monthly sales aggregation
        if group_by == "day":
            _date_format = "%Y-%m-%d"
        elif group_by == "week":
            _date_format = "%Y-W%V"
        else:
            _date_format = "%Y-%m"
        # _date_format is reserved for future MongoDB $dateToString aggregation; not used by current Python-side grouping.
        
        # Get orders with dates
        orders_cursor = db.orders.find({
            "created_at": {"$gte": start_date.isoformat()},
            "status": {"$in": ["COMPLETED", "DELIVERED", "confirmed", "pending"]}
        })
        orders = await orders_cursor.to_list(10000)
        
        # Aggregate by period
        sales_by_period = {}
        for order in orders:
            try:
                created = order.get("created_at", "")
                if isinstance(created, str):
                    date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                else:
                    date_obj = created
                
                if group_by == "day":
                    period_key = date_obj.strftime("%Y-%m-%d")
                elif group_by == "week":
                    period_key = f"{date_obj.year}-W{date_obj.isocalendar()[1]:02d}"
                else:
                    period_key = date_obj.strftime("%Y-%m")
                
                if period_key not in sales_by_period:
                    sales_by_period[period_key] = {"revenue": 0, "orders": 0, "items": 0}
                
                sales_by_period[period_key]["revenue"] += order.get("total_ttc", 0)
                sales_by_period[period_key]["orders"] += 1
                sales_by_period[period_key]["items"] += len(order.get("items", []))
            except Exception as e:
                logger.debug(f"Error parsing order date: {e}")
        
        # Convert to sorted list for chart
        sales_trend = [
            {"period": k, **v}
            for k, v in sorted(sales_by_period.items())
        ]
        
        # Calculate growth
        if len(sales_trend) >= 2:
            current_revenue = sales_trend[-1]["revenue"] if sales_trend else 0
            previous_revenue = sales_trend[-2]["revenue"] if len(sales_trend) > 1 else 0
            growth_percent = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        else:
            growth_percent = 0
        
    except Exception as e:
        logger.error(f"Sales trend error: {e}")
        sales_trend = []
        growth_percent = 0
    
    # === TOP PRODUCTS ===
    try:
        top_products_pipeline = [
            {"$match": {"created_at": {"$gte": start_date.isoformat()}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.product_id",
                "product_name": {"$first": "$items.name"},
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}}
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 10}
        ]
        top_products = await db.orders.aggregate(top_products_pipeline).to_list(10)
        
        # Format for chart
        top_products_chart = [
            {
                "id": p["_id"],
                "name": p.get("product_name", "Produit inconnu")[:20],
                "quantity": p["total_quantity"],
                "revenue": round(p["total_revenue"], 2)
            }
            for p in top_products
        ]
    except Exception as e:
        logger.error(f"Top products error: {e}")
        top_products_chart = []
    
    # === SALES BY CATEGORY ===
    try:
        category_pipeline = [
            {"$match": {"created_at": {"$gte": start_date.isoformat()}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.category",
                "total_revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}},
                "total_orders": {"$sum": 1}
            }},
            {"$sort": {"total_revenue": -1}}
        ]
        categories = await db.orders.aggregate(category_pipeline).to_list(20)
        
        sales_by_category = [
            {
                "category": c["_id"] or "Non catégorisé",
                "revenue": round(c["total_revenue"], 2),
                "orders": c["total_orders"]
            }
            for c in categories
        ]
    except Exception as e:
        logger.error(f"Category sales error: {e}")
        sales_by_category = []
    
    # === USER REGISTRATION TREND ===
    try:
        users_cursor = db.users.find({
            "created_at": {"$gte": start_date.isoformat()}
        }, {"created_at": 1})
        users = await users_cursor.to_list(10000)
        
        users_by_period = {}
        for user in users:
            try:
                created = user.get("created_at", "")
                if isinstance(created, str):
                    date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                else:
                    date_obj = created
                
                if group_by == "day":
                    period_key = date_obj.strftime("%Y-%m-%d")
                elif group_by == "week":
                    period_key = f"{date_obj.year}-W{date_obj.isocalendar()[1]:02d}"
                else:
                    period_key = date_obj.strftime("%Y-%m")
                
                users_by_period[period_key] = users_by_period.get(period_key, 0) + 1
            except Exception:
                pass
        
        user_trend = [
            {"period": k, "new_users": v}
            for k, v in sorted(users_by_period.items())
        ]
    except Exception as e:
        logger.error(f"User trend error: {e}")
        user_trend = []
    
    # === ORDERS BY ZONE ===
    try:
        zone_pipeline = [
            {"$match": {"created_at": {"$gte": start_date.isoformat()}}},
            {"$group": {
                "_id": "$zone_code",
                "orders": {"$sum": 1},
                "revenue": {"$sum": "$total_ttc"}
            }},
            {"$sort": {"revenue": -1}}
        ]
        zones = await db.orders.aggregate(zone_pipeline).to_list(20)
        
        # Zone mapping for display names
        zone_names = {
            "971": "Guadeloupe",
            "972": "Martinique",
            "973": "Guyane",
            "974": "La Réunion",
            "976": "Mayotte",
            "75": "Île-de-France"
        }
        
        orders_by_zone = [
            {
                "zone_code": z["_id"] or "N/A",
                "zone_name": zone_names.get(z["_id"], z["_id"] or "Inconnu"),
                "orders": z["orders"],
                "revenue": round(z["revenue"], 2)
            }
            for z in zones
        ]
    except Exception as e:
        logger.error(f"Zone stats error: {e}")
        orders_by_zone = []
    
    # === WALLET ACTIVITY ===
    try:
        wallet_pipeline = [
            {"$match": {"created_at": {"$gte": start_date.isoformat()}}},
            {"$group": {
                "_id": "$type",
                "total": {"$sum": {"$abs": "$amount"}},
                "count": {"$sum": 1}
            }}
        ]
        wallet_activity = await db.wallet_transactions.aggregate(wallet_pipeline).to_list(10)
        
        wallet_summary = {
            item["_id"]: {"total": round(item["total"], 2), "count": item["count"]}
            for item in wallet_activity
        }
    except Exception as e:
        logger.error(f"Wallet stats error: {e}")
        wallet_summary = {}
    
    # === ORDER STATUS DISTRIBUTION ===
    try:
        status_pipeline = [
            {"$match": {"created_at": {"$gte": start_date.isoformat()}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_dist = await db.orders.aggregate(status_pipeline).to_list(20)
        
        order_status_chart = [
            {"status": s["_id"] or "unknown", "count": s["count"]}
            for s in status_dist
        ]
    except Exception as e:
        logger.error(f"Order status error: {e}")
        order_status_chart = []
    
    # === SUMMARY CALCULATIONS ===
    total_revenue = sum(p["revenue"] for p in sales_trend) if sales_trend else 0
    total_orders = sum(p["orders"] for p in sales_trend) if sales_trend else 0
    avg_basket = total_revenue / total_orders if total_orders > 0 else 0
    
    return {
        "period": period,
        "generated_at": now.isoformat(),
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "average_basket": round(avg_basket, 2),
            "growth_percent": round(growth_percent, 1),
            "total_new_users": sum(u.get("new_users", 0) for u in user_trend)
        },
        "charts": {
            "sales_trend": sales_trend,
            "user_trend": user_trend,
            "top_products": top_products_chart,
            "sales_by_category": sales_by_category,
            "orders_by_zone": orders_by_zone,
            "order_status": order_status_chart
        },
        "wallet": wallet_summary
    }
