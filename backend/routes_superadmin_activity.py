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


superadmin_activity_router = APIRouter(prefix="/api/superadmin")

db = None

def set_superadmin_activity_database(database):
    global db
    db = database

@superadmin_activity_router.get("/alerts")
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


@superadmin_activity_router.get("/recent-activity")
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


