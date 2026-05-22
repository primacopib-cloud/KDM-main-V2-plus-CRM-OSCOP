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

# Router
vendor_router = APIRouter(prefix="/api/vendor")

# Database reference
db = None

def set_vendor_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== ENUMS ==============

class VendorStatus(str, Enum):
    PENDING = "pending"           # Waiting for admin approval
    APPROVED = "approved"         # Can submit products
    SUSPENDED = "suspended"       # Temporarily suspended
    REJECTED = "rejected"         # Application rejected


class ProductStatus(str, Enum):
    DRAFT = "draft"               # Not yet submitted
    PENDING_APPROVAL = "pending_approval"  # Submitted, waiting for review
    APPROVED = "approved"         # Active and visible
    REJECTED = "rejected"         # Not approved
    INACTIVE = "inactive"         # Deactivated by vendor


class DocumentType(str, Enum):
    TECHNICAL = "technical"       # Technical datasheet
    REGULATORY = "regulatory"     # Regulatory compliance
    CERTIFICATE = "certificate"   # Quality certificate
    OTHER = "other"


# ============== MODELS ==============

class VendorRegistration(BaseModel):
    """Vendor registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=2)
    siret: str = Field(..., pattern=r'^[0-9]{14}$')
    tva_intra: Optional[str] = None
    address: str
    city: str
    postal_code: str
    country: str = "FR"
    phone: str
    contact_name: str
    contact_title: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class VendorProfile(BaseModel):
    """Vendor profile update"""
    company_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    bank_iban: Optional[str] = None
    bank_bic: Optional[str] = None


class ProductSubmission(BaseModel):
    """Product submission by vendor"""
    name: str = Field(..., min_length=2, max_length=200)
    sku: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=10)
    category: str
    subcategory: Optional[str] = None
    
    # Pricing
    price_ht: float = Field(..., gt=0)
    tva_rate: float = Field(default=20.0, ge=0, le=100)
    
    # Stock & Volume
    stock_quantity: int = Field(..., ge=0)
    min_order_quantity: int = Field(default=1, ge=1)
    unit_type: str = Field(default="unit")  # unit, kg, liter, box, pallet
    volume_per_unit: Optional[float] = None
    weight_per_unit: Optional[float] = None
    
    # Product Format
    format_type: str = Field(default="standard")  # standard, lot, palette, container
    units_per_lot: Optional[int] = None
    lots_per_palette: Optional[int] = None
    
    # Origin
    country_of_origin: str = Field(default="FR")
    region_of_origin: Optional[str] = None
    
    # Dates
    dlc_days: Optional[int] = None  # Days until expiration
    production_date: Optional[str] = None
    
    # Logistics
    ean13: Optional[str] = None
    dimensions: Optional[Dict] = None  # {length, width, height}
    storage_conditions: Optional[str] = None
    
    # Zones availability
    available_zones: List[str] = Field(default=["GUADELOUPE"])
    
    # Additional info
    brand: Optional[str] = None
    certifications: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    ingredients: Optional[str] = None


class ProductUpdate(BaseModel):
    """Product update by vendor"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_ht: Optional[float] = None
    stock_quantity: Optional[int] = None
    min_order_quantity: Optional[int] = None
    available_zones: Optional[List[str]] = None
    dlc_days: Optional[int] = None


class ProductDocument(BaseModel):
    """Document attached to product"""
    document_type: DocumentType
    name: str
    url: str
    description: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

def generate_vendor_id() -> str:
    """Generate unique vendor ID"""
    return f"vendor_{uuid.uuid4().hex[:12]}"


def generate_product_id() -> str:
    """Generate unique product ID"""
    return f"prod_{uuid.uuid4().hex[:12]}"


async def get_vendor_by_email(email: str):
    """Get vendor by email"""
    return await db.vendors.find_one({"email": email.lower()}, {"_id": 0})


async def get_vendor_by_id(vendor_id: str):
    """Get vendor by ID"""
    return await db.vendors.find_one({"id": vendor_id}, {"_id": 0})


# ============== COUNTRIES DATA ==============

COUNTRIES = {
    "FR": {"name": "France", "flag": "🇫🇷"},
    "GP": {"name": "Guadeloupe", "flag": "🇬🇵"},
    "MQ": {"name": "Martinique", "flag": "🇲🇶"},
    "GF": {"name": "Guyane", "flag": "🇬🇫"},
    "RE": {"name": "La Réunion", "flag": "🇷🇪"},
    "YT": {"name": "Mayotte", "flag": "🇾🇹"},
    "NC": {"name": "Nouvelle-Calédonie", "flag": "🇳🇨"},
    "PF": {"name": "Polynésie française", "flag": "🇵🇫"},
    "BE": {"name": "Belgique", "flag": "🇧🇪"},
    "DE": {"name": "Allemagne", "flag": "🇩🇪"},
    "ES": {"name": "Espagne", "flag": "🇪🇸"},
    "IT": {"name": "Italie", "flag": "🇮🇹"},
    "NL": {"name": "Pays-Bas", "flag": "🇳🇱"},
    "PT": {"name": "Portugal", "flag": "🇵🇹"},
    "MA": {"name": "Maroc", "flag": "🇲🇦"},
    "SN": {"name": "Sénégal", "flag": "🇸🇳"},
    "CI": {"name": "Côte d'Ivoire", "flag": "🇨🇮"},
    "CN": {"name": "Chine", "flag": "🇨🇳"},
    "TH": {"name": "Thaïlande", "flag": "🇹🇭"},
    "BR": {"name": "Brésil", "flag": "🇧🇷"},
    "US": {"name": "États-Unis", "flag": "🇺🇸"},
}


# ============== ENDPOINTS ==============

@vendor_router.get("/countries")
async def get_countries():
    """Get list of countries with flags for product origin"""
    return {
        "countries": [
            {"code": code, **data}
            for code, data in sorted(COUNTRIES.items(), key=lambda x: x[1]["name"])
        ]
    }


@vendor_router.post("/register")
async def register_vendor(data: VendorRegistration):
    """Register as a new vendor (pending approval)"""
    
    # Check if email already exists
    existing = await get_vendor_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Check SIRET
    existing_siret = await db.vendors.find_one({"siret": data.siret})
    if existing_siret:
        raise HTTPException(status_code=400, detail="SIRET déjà enregistré")
    
    now = datetime.now(timezone.utc)
    vendor_id = generate_vendor_id()
    
    # Hash password (simplified - use proper hashing in production)
    import hashlib
    password_hash = hashlib.sha256(data.password.encode()).hexdigest()
    
    vendor = {
        "id": vendor_id,
        "email": data.email.lower(),
        "password_hash": password_hash,
        "company_name": data.company_name,
        "siret": data.siret,
        "tva_intra": data.tva_intra,
        "address": data.address,
        "city": data.city,
        "postal_code": data.postal_code,
        "country": data.country,
        "phone": data.phone,
        "contact_name": data.contact_name,
        "contact_title": data.contact_title,
        "description": data.description,
        "website": data.website,
        "status": VendorStatus.PENDING.value,
        "registration_method": "self_registration",
        "product_count": 0,
        "total_sales": 0,
        "rating": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "approved_at": None,
        "rejected_at": None,
        "rejection_reason": None,
    }
    
    await db.vendors.insert_one(vendor)
    
    logger.info(f"New vendor registered: {vendor_id} - {data.company_name}")
    
    return {
        "success": True,
        "vendor_id": vendor_id,
        "status": VendorStatus.PENDING.value,
        "message": "Inscription enregistrée. En attente de validation par l'administrateur."
    }


@vendor_router.get("/profile/{vendor_id}")
async def get_vendor_profile(vendor_id: str):
    """Get vendor profile"""
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    # Remove sensitive data
    vendor.pop("password_hash", None)
    
    return vendor


@vendor_router.put("/profile/{vendor_id}")
async def update_vendor_profile(vendor_id: str, data: VendorProfile):
    """Update vendor profile"""
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.vendors.update_one({"id": vendor_id}, {"$set": update_data})
    
    return {"success": True, "message": "Profil mis à jour"}


@vendor_router.post("/products")
async def submit_product(vendor_id: str, data: ProductSubmission):
    """Submit a new product for approval"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    if vendor["status"] != VendorStatus.APPROVED.value:
        raise HTTPException(status_code=403, detail="Votre compte vendeur n'est pas encore approuvé")
    
    # Check SKU uniqueness for this vendor
    existing = await db.vendor_products.find_one({"vendor_id": vendor_id, "sku": data.sku})
    if existing:
        raise HTTPException(status_code=400, detail="Ce SKU existe déjà pour votre compte")
    
    now = datetime.now(timezone.utc)
    product_id = generate_product_id()
    
    # Calculate price TTC
    price_ttc = data.price_ht * (1 + data.tva_rate / 100)
    
    product = {
        "id": product_id,
        "vendor_id": vendor_id,
        "vendor_name": vendor["company_name"],
        
        # Basic info
        "name": data.name,
        "sku": data.sku,
        "description": data.description,
        "category": data.category,
        "subcategory": data.subcategory,
        
        # Pricing
        "price_ht": data.price_ht,
        "tva_rate": data.tva_rate,
        "price_ttc": round(price_ttc, 2),
        
        # Stock & Volume
        "stock_quantity": data.stock_quantity,
        "min_order_quantity": data.min_order_quantity,
        "unit_type": data.unit_type,
        "volume_per_unit": data.volume_per_unit,
        "weight_per_unit": data.weight_per_unit,
        
        # Format
        "format_type": data.format_type,
        "units_per_lot": data.units_per_lot,
        "lots_per_palette": data.lots_per_palette,
        
        # Origin
        "country_of_origin": data.country_of_origin,
        "country_flag": COUNTRIES.get(data.country_of_origin, {}).get("flag", ""),
        "country_name": COUNTRIES.get(data.country_of_origin, {}).get("name", data.country_of_origin),
        "region_of_origin": data.region_of_origin,
        
        # Dates
        "dlc_days": data.dlc_days,
        "production_date": data.production_date,
        
        # Logistics
        "ean13": data.ean13,
        "dimensions": data.dimensions,
        "storage_conditions": data.storage_conditions,
        
        # Zones
        "available_zones": data.available_zones,
        
        # Additional
        "brand": data.brand,
        "certifications": data.certifications or [],
        "allergens": data.allergens or [],
        "ingredients": data.ingredients,
        
        # Media
        "images": [],
        "documents": [],
        
        # Status
        "status": ProductStatus.PENDING_APPROVAL.value,
        
        # Stats
        "total_sold": 0,
        "view_count": 0,
        
        # Timestamps
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "submitted_at": now.isoformat(),
        "approved_at": None,
        "rejected_at": None,
        "rejection_reason": None,
    }
    
    await db.vendor_products.insert_one(product)
    
    # Update vendor product count
    await db.vendors.update_one(
        {"id": vendor_id},
        {"$inc": {"product_count": 1}}
    )
    
    logger.info(f"Product submitted: {product_id} by vendor {vendor_id}")
    
    return {
        "success": True,
        "product_id": product_id,
        "status": ProductStatus.PENDING_APPROVAL.value,
        "message": "Produit soumis pour validation"
    }


@vendor_router.get("/products/{vendor_id}")
async def get_vendor_products(vendor_id: str, status: Optional[str] = None):
    """Get all products for a vendor"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    query = {"vendor_id": vendor_id}
    if status:
        query["status"] = status
    
    products = await db.vendor_products.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    return {
        "products": products,
        "count": len(products),
        "vendor_id": vendor_id
    }


@vendor_router.get("/products/{vendor_id}/{product_id}")
async def get_product_detail(vendor_id: str, product_id: str):
    """Get single product detail"""
    
    product = await db.vendor_products.find_one(
        {"id": product_id, "vendor_id": vendor_id},
        {"_id": 0}
    )
    
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    return product


@vendor_router.put("/products/{vendor_id}/{product_id}")
async def update_product(vendor_id: str, product_id: str, data: ProductUpdate):
    """Update a product"""
    
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Cannot update if pending review
    if product["status"] == ProductStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Produit en cours de validation, modification impossible")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    # Recalculate TTC if price changes
    if "price_ht" in update_data:
        tva_rate = product.get("tva_rate", 20)
        update_data["price_ttc"] = round(update_data["price_ht"] * (1 + tva_rate / 100), 2)
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.vendor_products.update_one({"id": product_id}, {"$set": update_data})
    
    return {"success": True, "message": "Produit mis à jour"}


@vendor_router.post("/products/{vendor_id}/{product_id}/images")
async def add_product_image(vendor_id: str, product_id: str, image_url: str, is_primary: bool = False):
    """Add image URL to product"""
    
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    image = {
        "url": image_url,
        "is_primary": is_primary,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    # If primary, set others to non-primary
    if is_primary:
        await db.vendor_products.update_one(
            {"id": product_id},
            {"$set": {"images.$[].is_primary": False}}
        )
    
    await db.vendor_products.update_one(
        {"id": product_id},
        {"$push": {"images": image}}
    )
    
    return {"success": True, "message": "Image ajoutée"}


@vendor_router.post("/products/{vendor_id}/{product_id}/documents")
async def add_product_document(vendor_id: str, product_id: str, doc: ProductDocument):
    """Add document to product (technical, regulatory, certificate)"""
    
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    document = {
        "id": f"doc_{uuid.uuid4().hex[:8]}",
        "type": doc.document_type.value,
        "name": doc.name,
        "url": doc.url,
        "description": doc.description,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vendor_products.update_one(
        {"id": product_id},
        {"$push": {"documents": document}}
    )
    
    return {"success": True, "message": "Document ajouté", "document_id": document["id"]}


@vendor_router.delete("/products/{vendor_id}/{product_id}")
async def delete_product(vendor_id: str, product_id: str):
    """Delete/deactivate a product"""
    
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Soft delete - set to inactive
    await db.vendor_products.update_one(
        {"id": product_id},
        {"$set": {"status": ProductStatus.INACTIVE.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "message": "Produit désactivé"}


@vendor_router.get("/dashboard/{vendor_id}")
async def get_vendor_dashboard(vendor_id: str):
    """Get vendor dashboard data"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    # Count products by status
    status_pipeline = [
        {"$match": {"vendor_id": vendor_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = await db.vendor_products.aggregate(status_pipeline).to_list(10)
    products_by_status = {s["_id"]: s["count"] for s in status_counts}
    
    # Sales stats
    sales_pipeline = [
        {"$match": {"vendor_id": vendor_id, "status": {"$in": ["confirmed", "COMPLETED"]}}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$total_ht"},
            "order_count": {"$sum": 1}
        }}
    ]
    sales_result = await db.orders.aggregate(sales_pipeline).to_list(1)
    sales_data = sales_result[0] if sales_result else {"total_revenue": 0, "order_count": 0}
    
    # Recent orders
    recent_orders = await db.orders.find(
        {"vendor_id": vendor_id},
        {"_id": 0, "id": 1, "total_ht": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    return {
        "vendor_id": vendor_id,
        "company_name": vendor["company_name"],
        "status": vendor["status"],
        "products": {
            "total": sum(products_by_status.values()),
            "by_status": products_by_status,
            "approved": products_by_status.get("approved", 0),
            "pending": products_by_status.get("pending_approval", 0),
        },
        "sales": {
            "total_revenue": round(sales_data.get("total_revenue", 0), 2),
            "order_count": sales_data.get("order_count", 0),
        },
        "recent_orders": recent_orders,
        "created_at": vendor["created_at"]
    }


@vendor_router.get("/orders/{vendor_id}")
async def get_vendor_orders(vendor_id: str, status: Optional[str] = None, limit: int = 50):
    """Get orders for vendor's products"""
    
    vendor = await get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur non trouvé")
    
    query = {"vendor_id": vendor_id}
    if status:
        query["status"] = status
    
    orders = await db.orders.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "orders": orders,
        "count": len(orders)
    }


# ============== ADMIN ENDPOINTS FOR VENDOR MANAGEMENT ==============

@vendor_router.get("/admin/list")
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


@vendor_router.post("/admin/invite")
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


@vendor_router.post("/admin/{vendor_id}/approve")
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


@vendor_router.post("/admin/{vendor_id}/reject")
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


@vendor_router.post("/admin/products/{product_id}/approve")
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


@vendor_router.post("/admin/products/{product_id}/reject")
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


@vendor_router.get("/admin/products/pending")
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


@vendor_router.get("/admin/products/stats")
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
