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

# Router
superadmin_router = APIRouter(prefix="/api/superadmin")

# Database reference
db = None

def set_superadmin_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== MODELS ==============

class KPIResponse(BaseModel):
    """Response model for KPIs"""
    period: str
    sales: dict
    users: dict
    products: dict
    wallet: dict
    orders: dict
    signatures: dict


class AdminStatsResponse(BaseModel):
    """Detailed admin statistics"""
    overview: dict
    trends: dict
    alerts: List[dict]


# ============== HELPER FUNCTIONS ==============

async def get_collection_count(collection_name: str, query: dict = None) -> int:
    """Get count from a collection"""
    try:
        return await db[collection_name].count_documents(query or {})
    except Exception:
        return 0


async def get_sum_field(collection_name: str, field: str, query: dict = None) -> float:
    """Get sum of a field from collection"""
    try:
        pipeline = [
            {"$match": query or {}},
            {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}
        ]
        result = await db[collection_name].aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0
    except Exception:
        return 0


# ============== ENDPOINTS ==============

@superadmin_router.get("/kpis")
async def get_kpis(period: str = "month"):
    """
    Get all KPIs for the Super Admin dashboard
    Period: day, week, month, year, all
    """
    now = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    
    date_query = {"created_at": {"$gte": start_date.isoformat()}}
    
    # === SALES KPIs ===
    try:
        # Total revenue from orders
        orders_pipeline = [
            {"$match": {"status": {"$in": ["COMPLETED", "DELIVERED", "confirmed"]}}},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_ttc"},
                "total_orders": {"$sum": 1},
                "avg_basket": {"$avg": "$total_ttc"}
            }}
        ]
        sales_result = await db.orders.aggregate(orders_pipeline).to_list(1)
        
        sales_data = sales_result[0] if sales_result else {"total_revenue": 0, "total_orders": 0, "avg_basket": 0}
        
        # Orders by status
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.orders.aggregate(status_pipeline).to_list(100)
        orders_by_status = {s["_id"]: s["count"] for s in status_result if s["_id"]}
    except Exception as e:
        logger.error(f"Sales KPI error: {e}")
        sales_data = {"total_revenue": 0, "total_orders": 0, "avg_basket": 0}
        orders_by_status = {}
    
    # === USERS KPIs ===
    try:
        total_users = await db.users.count_documents({})
        active_users = await db.users.count_documents({"is_active": True})
        new_users_period = await db.users.count_documents(date_query)
        
        # Users by role
        role_pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}}
        ]
        role_result = await db.users.aggregate(role_pipeline).to_list(100)
        users_by_role = {r["_id"]: r["count"] for r in role_result if r["_id"]}
        
        # Organizations
        total_orgs = await db.organizations.count_documents({})
        approved_orgs = await db.organizations.count_documents({"status": "APPROVED"})
        pending_orgs = await db.organizations.count_documents({"status": "PENDING_REVIEW"})
    except Exception as e:
        logger.error(f"Users KPI error: {e}")
        total_users = active_users = new_users_period = 0
        users_by_role = {}
        total_orgs = approved_orgs = pending_orgs = 0
    
    # === PRODUCTS KPIs ===
    try:
        total_products = await db.products.count_documents({})
        active_products = await db.products.count_documents({"status": "active"})
        
        # Products by category
        cat_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        cat_result = await db.products.aggregate(cat_pipeline).to_list(100)
        products_by_category = {c["_id"]: c["count"] for c in cat_result if c["_id"]}
        
        # Low stock products (stock < 10)
        low_stock = await db.products.count_documents({"stock": {"$lt": 10, "$gt": 0}})
        out_of_stock = await db.products.count_documents({"stock": 0})
        
        # Best sellers (simplified)
        best_sellers_pipeline = [
            {"$unwind": "$items"},
            {"$group": {"_id": "$items.product_id", "total_qty": {"$sum": "$items.quantity"}}},
            {"$sort": {"total_qty": -1}},
            {"$limit": 5}
        ]
        best_sellers = await db.orders.aggregate(best_sellers_pipeline).to_list(5)
    except Exception as e:
        logger.error(f"Products KPI error: {e}")
        total_products = active_products = low_stock = out_of_stock = 0
        products_by_category = {}
        best_sellers = []
    
    # === WALLET KPIs ===
    try:
        # Total credits sold
        credits_pipeline = [
            {"$match": {"type": "credit"}},
            {"$group": {"_id": None, "total_credits": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        credits_result = await db.wallet_transactions.aggregate(credits_pipeline).to_list(1)
        credits_data = credits_result[0] if credits_result else {"total_credits": 0, "count": 0}
        
        # Total credits consumed
        consumed_pipeline = [
            {"$match": {"type": "debit"}},
            {"$group": {"_id": None, "total_consumed": {"$sum": {"$abs": "$amount"}}, "count": {"$sum": 1}}}
        ]
        consumed_result = await db.wallet_transactions.aggregate(consumed_pipeline).to_list(1)
        consumed_data = consumed_result[0] if consumed_result else {"total_consumed": 0, "count": 0}
        
        # Current total balance across all wallets
        balance_pipeline = [
            {"$group": {"_id": None, "total_balance": {"$sum": "$balance"}}}
        ]
        balance_result = await db.wallets.aggregate(balance_pipeline).to_list(1)
        total_balance = balance_result[0]["total_balance"] if balance_result else 0
    except Exception as e:
        logger.error(f"Wallet KPI error: {e}")
        credits_data = {"total_credits": 0, "count": 0}
        consumed_data = {"total_consumed": 0, "count": 0}
        total_balance = 0
    
    # === SIGNATURES KPIs ===
    try:
        total_signatures = await db.signatures.count_documents({})
        signed_signatures = await db.signatures.count_documents({"status": "SIGNED"})
        pending_signatures = await db.signatures.count_documents({"status": {"$in": ["PENDING_OTP", "OTP_VERIFIED"]}})
        declined_signatures = await db.signatures.count_documents({"status": "DECLINED"})
    except Exception as e:
        logger.error(f"Signatures KPI error: {e}")
        total_signatures = signed_signatures = pending_signatures = declined_signatures = 0
    
    # === ORDERS KPIs (additional) ===
    try:
        # Orders by zone
        zone_pipeline = [
            {"$group": {"_id": "$zone_code", "count": {"$sum": 1}, "revenue": {"$sum": "$total_ttc"}}}
        ]
        zone_result = await db.orders.aggregate(zone_pipeline).to_list(100)
        orders_by_zone = {z["_id"]: {"count": z["count"], "revenue": z["revenue"]} for z in zone_result if z["_id"]}
        
        # Orders with installments
        installment_orders = await db.orders.count_documents({"installment_plan": {"$exists": True}})
    except Exception as e:
        logger.error(f"Orders additional KPI error: {e}")
        orders_by_zone = {}
        installment_orders = 0
    
    return {
        "period": period,
        "generated_at": now.isoformat(),
        "sales": {
            "total_revenue": round(sales_data.get("total_revenue", 0) or 0, 2),
            "total_orders": sales_data.get("total_orders", 0) or 0,
            "average_basket": round(sales_data.get("avg_basket", 0) or 0, 2),
            "orders_by_status": orders_by_status,
            "orders_by_zone": orders_by_zone,
            "installment_orders": installment_orders
        },
        "users": {
            "total": total_users,
            "active": active_users,
            "new_period": new_users_period,
            "by_role": users_by_role,
            "organizations": {
                "total": total_orgs,
                "approved": approved_orgs,
                "pending": pending_orgs
            }
        },
        "products": {
            "total": total_products,
            "active": active_products,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "by_category": products_by_category,
            "best_sellers": best_sellers
        },
        "wallet": {
            "total_credits_sold": round(credits_data.get("total_credits", 0), 2),
            "credits_transactions": credits_data.get("count", 0),
            "total_credits_consumed": round(consumed_data.get("total_consumed", 0), 2),
            "consumption_transactions": consumed_data.get("count", 0),
            "current_total_balance": round(total_balance, 2)
        },
        "signatures": {
            "total": total_signatures,
            "signed": signed_signatures,
            "pending": pending_signatures,
            "declined": declined_signatures,
            "success_rate": round((signed_signatures / total_signatures * 100) if total_signatures > 0 else 0, 1)
        }
    }


@superadmin_router.get("/alerts")
async def get_alerts():
    """Get system alerts for admin dashboard"""
    alerts = []
    now = datetime.now(timezone.utc)
    
    try:
        # Low stock alerts
        low_stock_count = await db.products.count_documents({"stock": {"$lt": 10, "$gt": 0}})
        if low_stock_count > 0:
            alerts.append({
                "type": "warning",
                "category": "stock",
                "title": "Stock faible",
                "message": f"{low_stock_count} produit(s) avec stock < 10 unités",
                "priority": "medium"
            })
        
        # Out of stock
        out_of_stock = await db.products.count_documents({"stock": 0})
        if out_of_stock > 0:
            alerts.append({
                "type": "error",
                "category": "stock",
                "title": "Rupture de stock",
                "message": f"{out_of_stock} produit(s) en rupture",
                "priority": "high"
            })
        
        # Pending organizations
        pending_orgs = await db.organizations.count_documents({"status": "PENDING_REVIEW"})
        if pending_orgs > 0:
            alerts.append({
                "type": "info",
                "category": "organizations",
                "title": "Validations en attente",
                "message": f"{pending_orgs} organisation(s) à valider",
                "priority": "medium"
            })
        
        # Failed payments (last 24h)
        yesterday = now - timedelta(days=1)
        failed_payments = await db.payments.count_documents({
            "status": "failed",
            "created_at": {"$gte": yesterday.isoformat()}
        })
        if failed_payments > 0:
            alerts.append({
                "type": "error",
                "category": "payments",
                "title": "Paiements échoués",
                "message": f"{failed_payments} paiement(s) échoué(s) (24h)",
                "priority": "high"
            })
        
        # Pending signatures
        pending_sigs = await db.signatures.count_documents({"status": "PENDING_OTP"})
        if pending_sigs > 5:
            alerts.append({
                "type": "warning",
                "category": "signatures",
                "title": "Signatures en attente",
                "message": f"{pending_sigs} signature(s) en attente de validation",
                "priority": "low"
            })
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "generated_at": now.isoformat()
    }


@superadmin_router.get("/recent-activity")
async def get_recent_activity(limit: int = 20):
    """Get recent activity feed"""
    activities = []
    
    try:
        # Recent orders
        recent_orders = await db.orders.find(
            {},
            {"_id": 0, "id": 1, "organization_id": 1, "total_ttc": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        for order in recent_orders:
            activities.append({
                "type": "order",
                "action": f"Commande {order.get('status', 'N/A')}",
                "details": f"Montant: {order.get('total_ttc', 0):.2f}€",
                "ref": order.get("id"),
                "timestamp": order.get("created_at")
            })
        
        # Recent signatures
        recent_sigs = await db.signatures.find(
            {},
            {"_id": 0, "id": 1, "status": 1, "document_type": 1, "created_at": 1, "signer.email": 1}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        for sig in recent_sigs:
            activities.append({
                "type": "signature",
                "action": f"Signature {sig.get('status', 'N/A')}",
                "details": sig.get("document_type", "Document"),
                "ref": sig.get("id"),
                "timestamp": sig.get("created_at")
            })
        
        # Recent organizations
        recent_orgs = await db.organizations.find(
            {},
            {"_id": 0, "id": 1, "legal_name": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        for org in recent_orgs:
            activities.append({
                "type": "organization",
                "action": f"Organisation {org.get('status', 'N/A')}",
                "details": org.get("legal_name", "N/A"),
                "ref": org.get("id"),
                "timestamp": org.get("created_at")
            })
        
        # Sort all by timestamp
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
    except Exception as e:
        logger.error(f"Error fetching activity: {e}")
    
    return {
        "activities": activities[:limit],
        "count": len(activities[:limit])
    }


@superadmin_router.get("/vendors")
async def get_vendors(status: str = None, limit: int = 50):
    """Get all vendors/sellers"""
    query = {"role": "vendor"}
    if status:
        query["status"] = status
    
    try:
        vendors = await db.users.find(
            query,
            {"_id": 0, "password": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Enrich with product counts
        for vendor in vendors:
            vendor_id = vendor.get("id")
            vendor["product_count"] = await db.products.count_documents({"vendor_id": vendor_id})
            vendor["order_count"] = await db.orders.count_documents({"vendor_id": vendor_id})
    except Exception as e:
        logger.error(f"Error fetching vendors: {e}")
        vendors = []
    
    return {
        "vendors": vendors,
        "count": len(vendors)
    }


@superadmin_router.post("/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str):
    """Approve a vendor"""
    result = await db.users.update_one(
        {"id": vendor_id, "role": "vendor"},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    return {"success": True, "message": "Vendeur approuvé"}


@superadmin_router.post("/vendors/{vendor_id}/reject")
async def reject_vendor(vendor_id: str, reason: str = ""):
    """Reject a vendor"""
    result = await db.users.update_one(
        {"id": vendor_id, "role": "vendor"},
        {"$set": {"status": "rejected", "rejection_reason": reason, "rejected_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    return {"success": True, "message": "Vendeur rejeté"}


@superadmin_router.get("/products/pending")
async def get_pending_products(limit: int = 50):
    """Get products pending approval"""
    try:
        products = await db.products.find(
            {"status": "pending_approval"},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
    except Exception:
        products = []
    
    return {
        "products": products,
        "count": len(products)
    }


@superadmin_router.post("/products/{product_id}/approve")
async def approve_product(product_id: str):
    """Approve a product"""
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": {"status": "active", "approved_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return {"success": True, "message": "Produit approuvé"}


@superadmin_router.post("/products/{product_id}/reject")
async def reject_product(product_id: str, reason: str = ""):
    """Reject a product"""
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": {"status": "rejected", "rejection_reason": reason}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return {"success": True, "message": "Produit rejeté"}


@superadmin_router.get("/export/summary")
async def export_summary():
    """Export summary data for reporting"""
    kpis = await get_kpis("all")
    alerts = await get_alerts()
    
    return {
        "report_type": "summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": kpis,
        "alerts": alerts["alerts"],
        "platform": "KDMARCHE × O'SCOP B2B ESS"
    }


# ============== ADVANCED STATISTICS ==============

@superadmin_router.get("/advanced-stats")
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
