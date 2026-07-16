"""
KDMARCHE × O'SCOP - Vendor (Seller) API Routes
Espace Vendeur Référencé - Soumission et gestion des produits
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum
import os
import logging
import uuid
import base64

logger = logging.getLogger(__name__)


vendor_admin_router = APIRouter(prefix="/api/vendor")

db = None

def set_vendor_admin_database(database):
    global db
    db = database

from vendor_models import VendorStatus, ProductStatus
from routes_vendor import get_vendor_by_id, get_vendor_by_email, generate_vendor_id

# ============== ADMIN ENDPOINTS FOR VENDOR MANAGEMENT ==============

@vendor_admin_router.get("/admin/list")
async def admin_list_vendors(status: Optional[str] = None, limit: int = 100):
    """Admin: List all vendors"""
    
    query = {}
    if status:
        query["status"] = status
    
    vendors = await db.vendors.find(
        query,
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "vendors": vendors,
        "count": len(vendors)
    }


@vendor_admin_router.post("/admin/invite")
async def admin_invite_vendor(email: EmailStr, company_name: str, message: Optional[str] = None):
    """Admin: Invite a vendor (pre-approved)"""
    
    # Check if already exists
    existing = await get_vendor_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    now = datetime.now(timezone.utc)
    vendor_id = generate_vendor_id()
    invite_code = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    invitation = {
        "id": vendor_id,
        "email": email.lower(),
        "company_name": company_name,
        "status": "invited",
        "invite_code": invite_code,
        "invite_message": message,
        "registration_method": "admin_invitation",
        "created_at": now.isoformat(),
        "invite_expires_at": (now + timedelta(days=7)).isoformat(),
    }
    
    await db.vendor_invitations.insert_one(invitation)
    
    # TODO: Send invitation email via SendGrid
    
    logger.info(f"Vendor invited: {email} - {company_name}")
    
    return {
        "success": True,
        "invitation_id": vendor_id,
        "invite_code": invite_code,
        "message": f"Invitation envoyée à {email}"
    }


@vendor_admin_router.post("/admin/{vendor_id}/approve")
async def admin_approve_vendor(vendor_id: str):
    """Admin: Approve a vendor"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    if vendor["status"] == VendorStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Vendeur déjà approuvé")
    
    await db.vendors.update_one(
        {"id": vendor_id},
        {
            "$set": {
                "status": VendorStatus.APPROVED.value,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # TODO: Send approval notification email
    
    logger.info(f"Vendor approved: {vendor_id}")
    
    return {"success": True, "message": "Vendeur approuvé"}


@vendor_admin_router.post("/admin/{vendor_id}/reject")
async def admin_reject_vendor(vendor_id: str, reason: str = ""):
    """Admin: Reject a vendor"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    await db.vendors.update_one(
        {"id": vendor_id},
        {
            "$set": {
                "status": VendorStatus.REJECTED.value,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "rejection_reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Vendor rejected: {vendor_id}")
    
    return {"success": True, "message": "Vendeur rejeté"}


@vendor_admin_router.post("/admin/products/{product_id}/approve")
async def admin_approve_product(product_id: str):
    """Admin: Approve a product"""
    
    product = await db.vendor_products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    now = datetime.now(timezone.utc)
    
    await db.vendor_products.update_one(
        {"id": product_id},
        {
            "$set": {
                "status": ProductStatus.APPROVED.value,
                "approved_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
        }
    )
    
    # Also create/update in main products collection for catalog
    product_for_catalog = {
        "id": product_id,
        "vendor_id": product["vendor_id"],
        "vendor_name": product["vendor_name"],
        "name": product["name"],
        "sku": product["sku"],
        "description": product["description"],
        "category": product["category"],
        "price_ht": product["price_ht"],
        "price_ttc": product["price_ttc"],
        "tva_rate": product["tva_rate"],
        "stock": product["stock_quantity"],
        "unit_type": product["unit_type"],
        "country_of_origin": product["country_of_origin"],
        "country_flag": product.get("country_flag", ""),
        "images": product.get("images", []),
        "status": "active",
        "zones": product.get("available_zones", []),
        "created_at": now.isoformat(),
    }
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": product_for_catalog},
        upsert=True
    )
    
    logger.info(f"Product approved: {product_id}")
    
    return {"success": True, "message": "Produit approuvé et publié au catalogue"}


@vendor_admin_router.post("/admin/products/{product_id}/reject")
async def admin_reject_product(product_id: str, reason: str = ""):
    """Admin: Reject a product"""
    
    product = await db.vendor_products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    await db.vendor_products.update_one(
        {"id": product_id},
        {
            "$set": {
                "status": ProductStatus.REJECTED.value,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "rejection_reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Product rejected: {product_id}")
    
    return {"success": True, "message": "Produit rejeté"}


@vendor_admin_router.get("/admin/products/pending")
async def admin_list_pending_products(status: str = "pending_approval", limit: int = 100):
    """Admin: List all products for validation"""
    
    # Get all products with requested status
    query = {"status": status} if status != "all" else {}
    
    products = await db.vendor_products.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich with vendor info
    enriched_products = []
    for p in products:
        vendor = await db.vendors.find_one({"id": p.get("vendor_id")}, {"_id": 0, "company_name": 1, "email": 1})
        p["vendor_name"] = vendor.get("company_name") if vendor else "N/A"
        p["vendor_email"] = vendor.get("email") if vendor else ""
        enriched_products.append(p)
    
    return {
        "products": enriched_products,
        "total": len(enriched_products)
    }


@vendor_admin_router.get("/admin/products/stats")
async def admin_products_stats():
    """Admin: Get products statistics"""
    
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    stats = await db.vendor_products.aggregate(pipeline).to_list(10)
    
    stats_dict = {s["_id"]: s["count"] for s in stats}
    
    return {
        "pending_approval": stats_dict.get("pending_approval", 0),
        "approved": stats_dict.get("approved", 0),
        "rejected": stats_dict.get("rejected", 0),
        "inactive": stats_dict.get("inactive", 0),
        "total": sum(stats_dict.values())
    }


# Import timedelta for invite expiration
from datetime import timedelta
