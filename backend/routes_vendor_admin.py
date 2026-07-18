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
    images = product.get("images") or []
    primary = next((i for i in images if i.get("is_primary")), images[0] if images else None)
    # Publish to catalog v2 (schema expected by routes_catalog: category_id, unit, zone_prices…)
    category_id = await _resolve_catalog_category(product.get("category"))
    product_for_catalog = {
        "id": product_id,
        "vendor_id": product.get("vendor_id"),
        "vendor_name": product.get("vendor_name", ""),
        "supplier_id": product.get("vendor_id"),
        "name": product["name"],
        "sku": product.get("sku", product_id),
        "description": product.get("description", ""),
        "category_id": category_id,
        "unit": product.get("unit_type", "unit"),
        "unit_quantity": 1,
        "min_order_qty": product.get("min_order_quantity", 1),
        "max_order_qty": None,
        "tva_rate": product.get("tva_rate", 8.5),
        "stock": product.get("stock_quantity") or product.get("stock_qty", 0),
        "country_of_origin": product.get("country_of_origin", ""),
        "country_flag": product.get("country_flag", ""),
        "images": product.get("images", []),
        "image_url": primary["url"] if primary else None,
        "tags": [product.get("vendor_name")] if product.get("vendor_name") else [],
        "status": "ACTIVE",
        "zones": product.get("available_zones") or product.get("zones", []),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.products.update_one(
        {"id": product_id},
        {"$set": product_for_catalog},
        upsert=True
    )

    # Zone prices so the product is purchasable in its available zones
    if product.get("price_ht") is not None:
        price_ht_cents = int(round(product["price_ht"] * 100))
    else:
        price_ht_cents = int(product.get("price_ht_cents") or 0)
    for zone_code in product.get("available_zones") or product.get("zones", []):
        await db.zone_prices.update_one(
            {"product_id": product_id, "zone_code": zone_code},
            {"$set": {"price_ht_cents": price_ht_cents, "price_type": "STANDARD",
                      "is_active": True, "updated_at": now.isoformat()},
             "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now.isoformat()}},
            upsert=True,
        )

    logger.info(f"Product approved: {product_id}")

    # Contrat automatisé d'engagement de volume (rétention 5% plafonnée 20 000 €)
    try:
        from routes_vendor_contracts import ensure_contract
        await ensure_contract(db, product["vendor_id"], product)
    except Exception as e:
        logger.error(f"Volume contract creation failed for {product_id}: {e}")
    
    return {"success": True, "message": "Produit approuvé et publié au catalogue"}


async def _resolve_catalog_category(vendor_category: str) -> str:
    """Mappe la catégorie vendeur (slug taxonomy) vers une catégorie du catalogue v2 (créée si absente)."""
    label = vendor_category or "Autre"
    tax = await db.product_categories.find_one({"value": vendor_category})
    if tax:
        label = tax["label"]
    existing = await db.categories.find_one({"name": {"$regex": f"^{label}$", "$options": "i"}})
    if existing:
        return existing["id"]
    doc = {"id": str(uuid.uuid4()), "name": label, "is_active": True, "sort_order": 99}
    await db.categories.insert_one({**doc})
    return doc["id"]


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
