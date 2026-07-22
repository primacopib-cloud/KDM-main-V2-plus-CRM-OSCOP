"""
KDMARCHE × O'SCOP - API Catalogue Produits Admin
CRUD complet pour la gestion du catalogue depuis l'espace Super Admin
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

# Router
catalog_admin_router = APIRouter(prefix="/api/catalog/admin")

# Database reference
db = None

def set_catalog_admin_database(database):
    """Set database reference"""
    global db
    db = database


# ============== MODELS ==============

class ProductCreate(BaseModel):
    sku: str
    ean: Optional[str] = None
    manufacturer_ref: Optional[str] = None
    name: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    tags: List[str] = []
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    status: str = "draft"
    is_active: bool = True
    is_new: bool = False
    is_featured: bool = False
    unit_type: str = "piece"
    unit_label: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    dimensions: Optional[Dict[str, Any]] = None
    weight: Optional[Dict[str, Any]] = None
    origin: Optional[Dict[str, Any]] = None
    packaging: Optional[Dict[str, Any]] = None
    conservation: Optional[Dict[str, Any]] = None
    nutrition: Optional[Dict[str, Any]] = None
    allergens: Optional[Dict[str, Any]] = None
    ingredients: Optional[str] = None
    technical_specs: Optional[Dict[str, Any]] = None
    warranty: Optional[Dict[str, Any]] = None
    compliance: Optional[Dict[str, Any]] = None
    logistics: Optional[Dict[str, Any]] = None
    media: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None


class ProductUpdate(ProductCreate):
    pass


# ============== ENDPOINTS ==============

@catalog_admin_router.get("/products")
async def list_catalog_products(
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    GET /api/catalog/admin/products
    Liste tous les produits du catalogue avec filtres
    """
    try:
        query = {}
        
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"sku": {"$regex": search, "$options": "i"}},
                {"brand": {"$regex": search, "$options": "i"}}
            ]
        
        cursor = db.catalog_products.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
        products = await cursor.to_list(limit)
        
        total = await db.catalog_products.count_documents(query)
        
        return {
            "products": products,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.get("/products/{product_id}")
async def get_catalog_product(product_id: str):
    """
    GET /api/catalog/admin/products/{id}
    Récupère un produit par son ID
    """
    try:
        product = await db.catalog_products.find_one(
            {"id": product_id},
            {"_id": 0}
        )
        
        if not product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.post("/products")
async def create_catalog_product(product: ProductCreate):
    """
    POST /api/catalog/admin/products
    Crée un nouveau produit dans le catalogue
    """
    try:
        # Check if SKU already exists
        existing = await db.catalog_products.find_one({"sku": product.sku})
        if existing:
            raise HTTPException(status_code=400, detail="SKU déjà utilisé")
        
        # Build product document
        product_doc = {
            "id": f"prod_{uuid.uuid4().hex[:12]}",
            "sku": product.sku,
            "ean": product.ean,
            "manufacturer_ref": product.manufacturer_ref,
            "name": product.name,
            "short_description": product.short_description,
            "description": product.description,
            "category": product.category,
            "subcategory": product.subcategory,
            "tags": product.tags or [],
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "status": product.status,
            "is_active": product.is_active,
            "is_new": product.is_new,
            "is_featured": product.is_featured,
            "unit_type": product.unit_type,
            "unit_label": product.unit_label,
            "pricing": product.pricing or {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20},
            "dimensions": product.dimensions,
            "weight": product.weight,
            "origin": product.origin,
            "packaging": product.packaging,
            "conservation": product.conservation,
            "nutrition": product.nutrition,
            "allergens": product.allergens,
            "ingredients": product.ingredients,
            "technical_specs": product.technical_specs,
            "warranty": product.warranty,
            "compliance": product.compliance,
            "logistics": product.logistics,
            "media": product.media,
            "image_url": product.image_url,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.catalog_products.insert_one(product_doc)
        
        # Return without _id
        product_doc.pop("_id", None)
        
        logger.info(f"Created catalog product: {product_doc['id']} - {product.name}")
        
        return product_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.put("/products/{product_id}")
async def update_catalog_product(product_id: str, product: ProductUpdate):
    """
    PUT /api/catalog/admin/products/{id}
    Met à jour un produit existant
    """
    try:
        existing = await db.catalog_products.find_one({"id": product_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        # Check SKU uniqueness (if changed)
        if product.sku != existing.get("sku"):
            sku_exists = await db.catalog_products.find_one({"sku": product.sku, "id": {"$ne": product_id}})
            if sku_exists:
                raise HTTPException(status_code=400, detail="SKU déjà utilisé")
        
        # Update document
        update_doc = {
            "sku": product.sku,
            "ean": product.ean,
            "manufacturer_ref": product.manufacturer_ref,
            "name": product.name,
            "short_description": product.short_description,
            "description": product.description,
            "category": product.category,
            "subcategory": product.subcategory,
            "tags": product.tags or [],
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "status": product.status,
            "is_active": product.is_active,
            "is_new": product.is_new,
            "is_featured": product.is_featured,
            "unit_type": product.unit_type,
            "unit_label": product.unit_label,
            "pricing": product.pricing,
            "dimensions": product.dimensions,
            "weight": product.weight,
            "origin": product.origin,
            "packaging": product.packaging,
            "conservation": product.conservation,
            "nutrition": product.nutrition,
            "allergens": product.allergens,
            "ingredients": product.ingredients,
            "technical_specs": product.technical_specs,
            "warranty": product.warranty,
            "compliance": product.compliance,
            "logistics": product.logistics,
            "media": product.media,
            "image_url": product.image_url,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.catalog_products.update_one(
            {"id": product_id},
            {"$set": update_doc}
        )
        
        logger.info(f"Updated catalog product: {product_id}")
        
        return {**update_doc, "id": product_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.delete("/products/{product_id}")
async def delete_catalog_product(product_id: str):
    """
    DELETE /api/catalog/admin/products/{id}
    Supprime un produit du catalogue
    """
    try:
        result = await db.catalog_products.delete_one({"id": product_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        logger.info(f"Deleted catalog product: {product_id}")
        
        return {"success": True, "message": "Produit supprimé"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.post("/products/{product_id}/approve")
async def approve_product(product_id: str):
    """
    POST /api/catalog/admin/products/{id}/approve
    Approuve un produit (change le statut en 'approved')
    """
    try:
        result = await db.catalog_products.update_one(
            {"id": product_id},
            {
                "$set": {
                    "status": "approved",
                    "approved_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        return {"success": True, "message": "Produit approuvé"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.post("/products/bulk-import")
async def bulk_import_products(products: List[ProductCreate]):
    """
    POST /api/catalog/admin/products/bulk-import
    Import en masse de produits
    """
    try:
        created = 0
        errors = []
        
        for product in products:
            try:
                # Check SKU
                existing = await db.catalog_products.find_one({"sku": product.sku})
                if existing:
                    errors.append(f"SKU {product.sku} existe déjà")
                    continue
                
                product_doc = {
                    "id": f"prod_{uuid.uuid4().hex[:12]}",
                    "sku": product.sku,
                    "ean": product.ean,
                    "name": product.name,
                    "category": product.category,
                    "status": product.status or "draft",
                    "is_active": product.is_active,
                    "unit_type": product.unit_type,
                    "pricing": product.pricing or {"price_ht_cents": 0, "currency": "EUR", "tva_rate": 20},
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                
                await db.catalog_products.insert_one(product_doc)
                created += 1
                
            except Exception as e:
                errors.append(f"Erreur pour {product.sku}: {str(e)}")
        
        return {
            "success": True,
            "created": created,
            "errors": errors,
            "total": len(products)
        }
        
    except Exception as e:
        logger.error(f"Error bulk importing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@catalog_admin_router.get("/stats")
async def get_catalog_stats():
    """
    GET /api/catalog/admin/stats
    Statistiques du catalogue
    """
    try:
        total = await db.catalog_products.count_documents({})
        by_status = await db.catalog_products.aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]).to_list(10)
        by_category = await db.catalog_products.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]).to_list(20)
        
        return {
            "total": total,
            "by_status": {item["_id"]: item["count"] for item in by_status if item["_id"]},
            "by_category": {item["_id"]: item["count"] for item in by_category if item["_id"]}
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
