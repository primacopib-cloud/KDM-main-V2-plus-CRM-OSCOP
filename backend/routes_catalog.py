"""
KDMARCHE × O'SCOP - Catalogue API Routes
Products, categories, pricing, cart, orders with ABAC gating
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from schema_catalog import (
    # Enums
    ProductStatus, PriceType, OrderStatus, CartStatus,
    # Categories
    CategoryCreate, CategoryResponse, CategoryInDB,
    # Products
    ProductCreate, ProductResponse, ProductInDB,
    # Pricing
    ZonePriceCreate, ZonePriceResponse, ZonePriceInDB,
    # Stock
    ZoneStockInDB,
    # Cart
    CartItemCreate, CartItemResponse, CartResponse, CartInDB,
    # Orders
    OrderCreate, OrderResponse, OrderInDB, OrderItemResponse,
    # Pickup
    PickupLocationResponse, PickupLocationInDB,
    # Defaults
    DEFAULT_CATEGORIES, DEFAULT_PICKUP_LOCATIONS, SAMPLE_PRODUCTS,
)
from schema_v2 import (
    OrgStatus, SubscriptionStatus, PartnerProvisionStatus,
    CustomerRole, LedgerDirection, LedgerStatus,
    AuditLogEntry, LedgerEntryInDB,
)
from abac_policy import ABACPolicyEngine, PolicyInput, PolicySubject, PolicyResource, PolicyData

logger = logging.getLogger(__name__)

# Router
catalog_router = APIRouter(prefix="/api/v2/catalog")

# Database reference
db = None

def set_catalog_database(database):
    global db
    db = database


# ============== DEPENDENCIES ==============

async def get_current_user_catalog(request: Request):
    """Get current user from token"""
    from auth import decode_token, extract_user_id_from_request
    
    user_id = extract_user_id_from_request(request)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


async def get_user_org_context(user: dict):
    """Get user's org, subscription, and access context for ABAC"""
    # Get membership
    membership = await db.org_memberships.find_one({"user_id": user["id"]})
    if not membership:
        return None, None, None, None, []
    
    org_id = membership["org_id"]
    
    # Get org
    org = await db.orgs.find_one({"id": org_id})
    if not org:
        return None, None, None, None, []
    
    # Get subscription
    subscription = await db.subscriptions.find_one({
        "org_id": org_id,
        "status": {"$in": [SubscriptionStatus.ACTIVE.value]}
    })
    
    # Get partner account
    partner = await db.partner_accounts.find_one({
        "org_id": org_id,
        "partner": "KDMARCHE"
    })
    
    # Get entitled zones
    entitlements = await db.org_zone_entitlements.find({
        "org_id": org_id,
        "status": "ACTIVE"
    }).to_list(100)
    
    # Get zone IDs
    zone_ids = [e["zone_id"] for e in entitlements]
    
    # Map to zone codes
    zones = await db.zones_v2.find({"id": {"$in": zone_ids}}).to_list(100)
    zone_codes = [z["code"] for z in zones]
    
    return org, subscription, partner, membership, zone_codes


async def check_price_access(user: dict, zone_code: str) -> bool:
    """Check if user can see prices for a zone"""
    org, subscription, partner, membership, entitled_zones = await get_user_org_context(user)
    
    if not org or not subscription or not partner:
        return False
    
    # ABAC check
    if org.get("status") != OrgStatus.APPROVED.value:
        return False
    
    if subscription.get("status") != SubscriptionStatus.ACTIVE.value:
        return False
    
    if partner.get("status") != PartnerProvisionStatus.ACCESS_ENABLED.value:
        return False
    
    if zone_code not in entitled_zones:
        return False
    
    return True


async def get_selected_zone(user: dict) -> Optional[str]:
    """Get user's currently selected zone"""
    membership = await db.org_memberships.find_one({"user_id": user["id"]})
    if not membership:
        return None
    
    prefs = await db.org_runtime_preferences.find_one({"org_id": membership["org_id"]})
    if not prefs or not prefs.get("selected_zone_id"):
        return None
    
    zone = await db.zones_v2.find_one({"id": prefs["selected_zone_id"]})
    return zone["code"] if zone else None


# ============== CATEGORIES ==============

@catalog_router.get("/categories", response_model=List[CategoryResponse])
async def list_categories():
    """List all active categories"""
    categories = await db.categories.find({"is_active": True}).sort("sort_order", 1).to_list(100)
    
    # Initialize if empty
    if not categories:
        for cat_data in DEFAULT_CATEGORIES:
            cat = CategoryInDB(**cat_data)
            await db.categories.insert_one(cat.dict())
        categories = await db.categories.find({"is_active": True}).sort("sort_order", 1).to_list(100)
    
    return [CategoryResponse(**c) for c in categories]


@catalog_router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    """Get category by ID"""
    category = await db.categories.find_one({"id": category_id, "is_active": True})
    if not category:
        raise HTTPException(status_code=404, detail="Catégorie non trouvée")
    return CategoryResponse(**category)


@catalog_router.post("/categories", response_model=CategoryResponse)
async def create_category(
    cat_data: CategoryCreate,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Create category (admin only)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    category = CategoryInDB(**cat_data.dict())
    await db.categories.insert_one(category.dict())
    
    return CategoryResponse(**category.dict())


# ============== PRODUCTS ==============

@catalog_router.get("/products", response_model=List[ProductResponse])
async def list_products(
    current_user: dict = Depends(get_current_user_catalog),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List products with ABAC-controlled pricing"""
    # Get user's selected zone
    zone_code = await get_selected_zone(current_user)
    
    # Check price access
    price_visible = False
    if zone_code:
        price_visible = await check_price_access(current_user, zone_code)
    
    # Build query
    query = {"status": ProductStatus.ACTIVE.value}
    
    if category_id:
        query["category_id"] = category_id
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"sku": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        query["tags"] = {"$in": tag_list}
    
    # Get products
    products = await db.products.find(query).skip(skip).limit(limit).to_list(limit)
    
    # Initialize sample products if empty
    if not products and not category_id and not search:
        await _init_sample_products()
        products = await db.products.find(query).skip(skip).limit(limit).to_list(limit)
    
    # Build response with pricing
    result = []
    for p in products:
        product_resp = await _build_product_response(p, zone_code, price_visible)
        result.append(product_resp)
    
    return result


@catalog_router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Get product details with ABAC-controlled pricing"""
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    zone_code = await get_selected_zone(current_user)
    price_visible = False
    if zone_code:
        price_visible = await check_price_access(current_user, zone_code)
    
    return await _build_product_response(product, zone_code, price_visible)


async def _build_product_response(product: dict, zone_code: str, price_visible: bool) -> ProductResponse:
    """Build product response with optional pricing"""
    # Get category name
    category = await db.categories.find_one({"id": product["category_id"]})
    category_name = category["name"] if category else None
    
    resp = ProductResponse(
        id=product["id"],
        sku=product["sku"],
        name=product["name"],
        description=product.get("description"),
        category_id=product["category_id"],
        category_name=category_name,
        unit=product["unit"],
        unit_quantity=product["unit_quantity"],
        min_order_qty=product["min_order_qty"],
        max_order_qty=product.get("max_order_qty"),
        image_url=product.get("image_url"),
        video_url=product.get("video_url"),
        video_urls=product.get("video_urls"),
        tags=product.get("tags", []),
        status=product["status"],
        price_visible=price_visible,
        in_stock=True,
    )
    
    # Add pricing if authorized
    if price_visible and zone_code:
        zone_price = await db.zone_prices.find_one({
            "product_id": product["id"],
            "zone_code": zone_code,
            "is_active": True,
        })
        
        if zone_price:
            resp.price_ht_cents = zone_price["price_ht_cents"]
            resp.price_type = zone_price["price_type"]
            resp.original_price_ht_cents = zone_price.get("original_price_ht_cents")
            
            if resp.original_price_ht_cents and resp.original_price_ht_cents > resp.price_ht_cents:
                resp.savings_percent = round(
                    (1 - resp.price_ht_cents / resp.original_price_ht_cents) * 100, 1
                )
        
        # Check stock
        stock = await db.zone_stocks.find_one({
            "product_id": product["id"],
            "zone_code": zone_code,
        })
        if stock:
            resp.in_stock = stock["quantity_available"] > stock["quantity_reserved"]
            resp.stock_quantity = stock["quantity_available"] - stock["quantity_reserved"]
    
    return resp


async def _init_sample_products():
    """Initialize sample products for demo"""
    # Get categories
    categories = await db.categories.find().to_list(100)
    cat_map = {c["code"]: c["id"] for c in categories}
    
    for p_data in SAMPLE_PRODUCTS:
        cat_id = cat_map.get(p_data["category_code"])
        if not cat_id:
            continue
        
        # Create product
        product = ProductInDB(
            sku=p_data["sku"],
            name=p_data["name"],
            category_id=cat_id,
            unit=p_data["unit"],
            unit_quantity=p_data["unit_quantity"],
            min_order_qty=p_data["min_order_qty"],
            tags=p_data["tags"],
        )
        await db.products.insert_one(product.dict())
        
        # Create zone prices
        for zone_code, price in p_data["prices"].items():
            zone_price = ZonePriceInDB(
                product_id=product.id,
                zone_code=zone_code,
                price_ht_cents=price,
                original_price_ht_cents=p_data.get("original_price"),
            )
            await db.zone_prices.insert_one(zone_price.dict())
        
        # Create zone stocks
        for zone_code in p_data["prices"].keys():
            stock = ZoneStockInDB(
                product_id=product.id,
                zone_code=zone_code,
                quantity_available=100,
            )
            await db.zone_stocks.insert_one(stock.dict())
    
    logger.info("Sample products initialized")


# ============== PICKUP LOCATIONS ==============

@catalog_router.get("/pickup-locations", response_model=List[PickupLocationResponse])
async def list_pickup_locations(
    zone_code: Optional[str] = None,
    current_user: dict = Depends(get_current_user_catalog),
):
    """List pickup locations"""
    query = {"is_active": True}
    if zone_code:
        query["zone_code"] = zone_code
    
    locations = await db.pickup_locations.find(query).to_list(100)
    
    # Initialize if empty
    if not locations:
        for loc_data in DEFAULT_PICKUP_LOCATIONS:
            loc = PickupLocationInDB(**loc_data)
            await db.pickup_locations.insert_one(loc.dict())
        locations = await db.pickup_locations.find(query).to_list(100)
    
    return [PickupLocationResponse(**loc) for loc in locations]


