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
orders_router = APIRouter(prefix="/api/v2/orders")

# Database reference
db = None

def set_catalog_database(database):
    global db
    db = database


# ============== DEPENDENCIES ==============

async def get_current_user_catalog(request: Request):
    """Get current user from token"""
    from auth import decode_token
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = auth_header.split(" ")[1]
    user_id = decode_token(token)
    
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
    
    return [PickupLocationResponse(**l) for l in locations]


# ============== CART ==============

@catalog_router.get("/cart", response_model=CartResponse)
async def get_cart(current_user: dict = Depends(get_current_user_catalog)):
    """Get current user's cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    zone_code = await get_selected_zone(current_user)
    if not zone_code:
        raise HTTPException(status_code=400, detail="Sélectionnez une zone d'abord")
    
    # Get or create cart
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        cart = CartInDB(
            org_id=membership["org_id"],
            zone_code=zone_code,
        ).dict()
        await db.carts.insert_one(cart)
    
    return await _build_cart_response(cart)


@catalog_router.post("/cart/items", response_model=CartResponse)
async def add_to_cart(
    item: CartItemCreate,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Add item to cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    zone_code = await get_selected_zone(current_user)
    if not zone_code:
        raise HTTPException(status_code=400, detail="Sélectionnez une zone d'abord")
    
    # Check price access
    if not await check_price_access(current_user, zone_code):
        raise HTTPException(status_code=403, detail="Accès non autorisé à cette zone")
    
    # Get product
    product = await db.products.find_one({"id": item.product_id, "status": ProductStatus.ACTIVE.value})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Get price for zone
    zone_price = await db.zone_prices.find_one({
        "product_id": item.product_id,
        "zone_code": zone_code,
        "is_active": True,
    })
    if not zone_price:
        raise HTTPException(status_code=400, detail="Produit non disponible dans cette zone")
    
    # Check quantity
    if item.quantity < product["min_order_qty"]:
        raise HTTPException(
            status_code=400,
            detail=f"Quantité minimum: {product['min_order_qty']}"
        )
    
    if product.get("max_order_qty") and item.quantity > product["max_order_qty"]:
        raise HTTPException(
            status_code=400,
            detail=f"Quantité maximum: {product['max_order_qty']}"
        )
    
    # Get or create cart
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        cart = CartInDB(
            org_id=membership["org_id"],
            zone_code=zone_code,
        ).dict()
        await db.carts.insert_one(cart)
        cart = await db.carts.find_one({"id": cart["id"]})
    
    # Build cart item
    cart_item = {
        "id": str(uuid.uuid4()),
        "product_id": product["id"],
        "product_name": product["name"],
        "product_sku": product["sku"],
        "product_image": product.get("image_url"),
        "unit": product["unit"],
        "quantity": item.quantity,
        "price_ht_cents": zone_price["price_ht_cents"],
        "line_total_ht_cents": zone_price["price_ht_cents"] * item.quantity,
    }
    
    # Check if product already in cart
    items = cart.get("items", [])
    existing_idx = next((i for i, x in enumerate(items) if x["product_id"] == item.product_id), None)
    
    if existing_idx is not None:
        # Update quantity
        items[existing_idx]["quantity"] += item.quantity
        items[existing_idx]["line_total_ht_cents"] = (
            items[existing_idx]["price_ht_cents"] * items[existing_idx]["quantity"]
        )
    else:
        items.append(cart_item)
    
    # Recalculate totals
    subtotal = sum(i["line_total_ht_cents"] for i in items)
    tax = int(subtotal * 0.085)  # TVA réduite DOM
    total = subtotal + tax
    
    # Update cart
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {
            "items": items,
            "subtotal_ht_cents": subtotal,
            "tax_cents": tax,
            "total_ttc_cents": total,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_cart = await db.carts.find_one({"id": cart["id"]})
    return await _build_cart_response(updated_cart)


@catalog_router.delete("/cart/items/{item_id}", response_model=CartResponse)
async def remove_from_cart(
    item_id: str,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Remove item from cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    zone_code = await get_selected_zone(current_user)
    
    cart = await db.carts.find_one({
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": CartStatus.ACTIVE.value,
    })
    
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    
    # Remove item
    items = [i for i in cart.get("items", []) if i["id"] != item_id]
    
    # Recalculate
    subtotal = sum(i["line_total_ht_cents"] for i in items)
    tax = int(subtotal * 0.085)
    total = subtotal + tax
    
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {
            "items": items,
            "subtotal_ht_cents": subtotal,
            "tax_cents": tax,
            "total_ttc_cents": total,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_cart = await db.carts.find_one({"id": cart["id"]})
    return await _build_cart_response(updated_cart)


@catalog_router.delete("/cart", response_model=dict)
async def clear_cart(current_user: dict = Depends(get_current_user_catalog)):
    """Clear cart"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    zone_code = await get_selected_zone(current_user)
    
    await db.carts.update_one(
        {
            "org_id": membership["org_id"],
            "zone_code": zone_code,
            "status": CartStatus.ACTIVE.value,
        },
        {"$set": {
            "items": [],
            "subtotal_ht_cents": 0,
            "tax_cents": 0,
            "total_ttc_cents": 0,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    return {"message": "Panier vidé"}


async def _build_cart_response(cart: dict) -> CartResponse:
    """Build cart response"""
    items = []
    for item in cart.get("items", []):
        items.append(CartItemResponse(
            id=item["id"],
            product_id=item["product_id"],
            product_name=item["product_name"],
            product_sku=item["product_sku"],
            product_image=item.get("product_image"),
            unit=item["unit"],
            quantity=item["quantity"],
            price_ht_cents=item["price_ht_cents"],
            line_total_ht_cents=item["line_total_ht_cents"],
        ))
    
    return CartResponse(
        id=cart["id"],
        org_id=cart["org_id"],
        zone_code=cart["zone_code"],
        status=cart["status"],
        items=items,
        items_count=len(items),
        subtotal_ht_cents=cart.get("subtotal_ht_cents", 0),
        tax_cents=cart.get("tax_cents", 0),
        total_ttc_cents=cart.get("total_ttc_cents", 0),
        created_at=cart["created_at"],
        updated_at=cart["updated_at"],
    )


# ============== INSTALLMENT CALCULATION ==============

@catalog_router.get("/installment/calculate")
async def calculate_installment_plan(
    amount_ht_cents: int = Query(..., description="Montant HT en centimes"),
    current_user: dict = Depends(get_current_user_catalog),
):
    """
    Calculate installment plan for a given amount
    
    Formula:
    - Frais = Montant HT × 20%
    - TVA sur frais = Frais × 8.50%
    - Total frais = Frais + TVA
    - Réparti sur 4 échéances mensuelles
    """
    MIN_INSTALLMENT_HT_CENTS = 550000  # 5500€
    
    if amount_ht_cents < MIN_INSTALLMENT_HT_CENTS:
        return {
            "eligible": False,
            "min_amount_ht_cents": MIN_INSTALLMENT_HT_CENTS,
            "min_amount_ht_eur": MIN_INSTALLMENT_HT_CENTS / 100,
            "provided_amount_ht_cents": amount_ht_cents,
            "provided_amount_ht_eur": amount_ht_cents / 100,
            "message": f"Le paiement échelonné est disponible à partir de {MIN_INSTALLMENT_HT_CENTS/100:.0f}€ HT"
        }
    
    # Calculate fees
    fees_ht_cents = int(amount_ht_cents * 0.20)  # 20%
    fees_tva_cents = int(fees_ht_cents * 0.085)  # 8.50% TVA
    total_fees_cents = fees_ht_cents + fees_tva_cents
    
    # Total with original TVA (8.50%) + fees
    product_tva_cents = int(amount_ht_cents * 0.085)
    total_ttc_cents = amount_ht_cents + product_tva_cents
    total_with_fees_cents = total_ttc_cents + total_fees_cents
    
    # Calculate installments
    installment_amount = total_with_fees_cents // 4
    remainder = total_with_fees_cents % 4
    
    from dateutil.relativedelta import relativedelta
    base_date = datetime.utcnow()
    
    installments = []
    for i in range(4):
        due_date = base_date + relativedelta(months=i)
        amount = installment_amount + (1 if i < remainder else 0)
        installments.append({
            "number": i + 1,
            "amount_cents": amount,
            "amount_eur": amount / 100,
            "due_date": due_date.strftime("%Y-%m-%d"),
            "label": f"Échéance {i+1}/4 - {due_date.strftime('%B %Y')}"
        })
    
    return {
        "eligible": True,
        "subtotal_ht_cents": amount_ht_cents,
        "subtotal_ht_eur": amount_ht_cents / 100,
        "product_tva_cents": product_tva_cents,
        "product_tva_eur": product_tva_cents / 100,
        "total_ttc_cents": total_ttc_cents,
        "total_ttc_eur": total_ttc_cents / 100,
        "fee_rate": 0.20,
        "fee_rate_percent": "20%",
        "fee_tva_rate": 0.085,
        "fee_tva_rate_percent": "8.50%",
        "fees_ht_cents": fees_ht_cents,
        "fees_ht_eur": fees_ht_cents / 100,
        "fees_tva_cents": fees_tva_cents,
        "fees_tva_eur": fees_tva_cents / 100,
        "total_fees_cents": total_fees_cents,
        "total_fees_eur": total_fees_cents / 100,
        "total_with_fees_cents": total_with_fees_cents,
        "total_with_fees_eur": total_with_fees_cents / 100,
        "installment_count": 4,
        "installments": installments,
        "savings_vs_full_payment": 0,  # No savings, fees are additional
        "message": f"Paiement en 4× de {installment_amount/100:.2f}€/mois (frais inclus)"
    }


# ============== ORDERS ==============

@orders_router.post("", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user_catalog),
    request: Request = None,
):
    """Create order from cart (EXW only)"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    # Check role
    if membership["role"] not in [CustomerRole.CUSTOMER_ORG_OWNER.value, CustomerRole.CUSTOMER_ORG_BUYER.value]:
        raise HTTPException(status_code=403, detail="Rôle non autorisé à commander")
    
    # Get cart
    cart = await db.carts.find_one({"id": order_data.cart_id})
    if not cart or cart["org_id"] != membership["org_id"]:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    
    if not cart.get("items"):
        raise HTTPException(status_code=400, detail="Panier vide")
    
    zone_code = cart["zone_code"]
    
    # ABAC check
    org, subscription, partner, _, entitled_zones = await get_user_org_context(current_user)
    
    if not org or org.get("status") != OrgStatus.APPROVED.value:
        raise HTTPException(status_code=403, detail="Organisation non approuvée")
    
    if not subscription or subscription.get("status") != SubscriptionStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="Abonnement inactif")
    
    if not partner or partner.get("status") != PartnerProvisionStatus.ACCESS_ENABLED.value:
        raise HTTPException(status_code=403, detail="Accès KDMARCHE non activé")
    
    if zone_code not in entitled_zones:
        raise HTTPException(status_code=403, detail="Zone non autorisée")
    
    # Check pickup location
    pickup = await db.pickup_locations.find_one({
        "id": order_data.pickup_location_id,
        "zone_code": zone_code,
        "is_active": True,
    })
    if not pickup:
        raise HTTPException(status_code=400, detail="Point de retrait invalide pour cette zone")
    
    # Create order
    order_dict = {
        "id": str(uuid.uuid4()),
        "order_number": f"KDM-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        "org_id": membership["org_id"],
        "zone_code": zone_code,
        "status": OrderStatus.PENDING.value,
        "incoterm": "EXW",  # Always EXW
        "pickup_location_id": order_data.pickup_location_id,
        "items": cart["items"],
        "items_count": len(cart["items"]),
        "subtotal_ht_cents": cart["subtotal_ht_cents"],
        "tax_cents": cart["tax_cents"],
        "total_ttc_cents": cart["total_ttc_cents"],
        "notes": order_data.notes,
        "created_by_user_id": current_user["id"],
        "is_installment": False,
        "installment_plan": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Handle installment payment if requested
    MIN_INSTALLMENT_HT_CENTS = 550000  # 5500€ HT
    if order_data.use_installment:
        if cart["subtotal_ht_cents"] < MIN_INSTALLMENT_HT_CENTS:
            raise HTTPException(
                status_code=400, 
                detail=f"Le paiement échelonné est disponible à partir de 5 500€ HT. Votre commande: {cart['subtotal_ht_cents']/100:.2f}€"
            )
        
        # Calculate fees: HT × 20% + TVA 8.50% on fees
        subtotal_ht = cart["subtotal_ht_cents"]
        fees_ht = int(subtotal_ht * 0.20)  # 20% fees
        fees_tva = int(fees_ht * 0.085)  # 8.50% TVA on fees
        total_fees = fees_ht + fees_tva
        total_with_fees = cart["total_ttc_cents"] + total_fees
        
        # Create 4 installments
        installment_amount = total_with_fees // 4
        remainder = total_with_fees % 4
        
        installments = []
        from dateutil.relativedelta import relativedelta
        base_date = datetime.utcnow()
        
        for i in range(4):
            due_date = base_date + relativedelta(months=i)
            amount = installment_amount + (1 if i < remainder else 0)
            installments.append({
                "number": i + 1,
                "amount_cents": amount,
                "due_date": due_date.isoformat(),
                "status": "PENDING",
                "paid_at": None,
            })
        
        order_dict["is_installment"] = True
        order_dict["installment_plan"] = {
            "subtotal_ht_cents": subtotal_ht,
            "fees_ht_cents": fees_ht,
            "fees_tva_cents": fees_tva,
            "total_fees_cents": total_fees,
            "total_with_fees_cents": total_with_fees,
            "installments": installments,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"Installment order: {order_dict['order_number']} - Fees: {total_fees/100:.2f}€, Total: {total_with_fees/100:.2f}€")
    
    await db.orders.insert_one(order_dict)
    
    # Mark cart as converted
    await db.carts.update_one(
        {"id": cart["id"]},
        {"$set": {"status": CartStatus.CONVERTED.value, "updated_at": datetime.utcnow()}}
    )
    
    # Audit log
    audit = AuditLogEntry(
        org_id=membership["org_id"],
        actor_user_id=current_user["id"],
        actor_role=membership["role"],
        action="ORDER_CREATED",
        target_type="ORDER",
        target_id=order_dict["id"],
        meta={
            "order_number": order_dict["order_number"],
            "total_ttc": order_dict["total_ttc_cents"],
            "zone": zone_code,
            "is_installment": order_dict["is_installment"],
        },
        ip=request.client.host if request else None,
    )
    await db.audit_log.insert_one(audit.dict())
    
    logger.info(f"Order created: {order_dict['order_number']} for org {membership['org_id']}")
    
    return await _build_order_response(order_dict, pickup)


@orders_router.get("", response_model=List[OrderResponse])
async def list_orders(
    current_user: dict = Depends(get_current_user_catalog),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """List user's orders"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    query = {"org_id": membership["org_id"]}
    if status_filter:
        query["status"] = status_filter
    
    orders = await db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for o in orders:
        pickup = await db.pickup_locations.find_one({"id": o["pickup_location_id"]})
        result.append(await _build_order_response(o, pickup))
    
    return result


@orders_router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Get order details"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    order = await db.orders.find_one({"id": order_id})
    if not order or order["org_id"] != membership["org_id"]:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    pickup = await db.pickup_locations.find_one({"id": order["pickup_location_id"]})
    return await _build_order_response(order, pickup)


@orders_router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    reason: str = "Client request",
    current_user: dict = Depends(get_current_user_catalog),
):
    """Cancel order (if not yet processed)"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    order = await db.orders.find_one({"id": order_id})
    if not order or order["org_id"] != membership["org_id"]:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Can only cancel pending orders
    if order["status"] not in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]:
        raise HTTPException(status_code=400, detail="Commande ne peut plus être annulée")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": OrderStatus.CANCELED.value,
            "canceled_at": datetime.utcnow(),
            "cancel_reason": reason,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated = await db.orders.find_one({"id": order_id})
    pickup = await db.pickup_locations.find_one({"id": updated["pickup_location_id"]})
    return await _build_order_response(updated, pickup)


async def _build_order_response(order: dict, pickup: dict = None) -> OrderResponse:
    """Build order response"""
    items = [
        OrderItemResponse(
            product_id=i["product_id"],
            product_name=i["product_name"],
            product_sku=i["product_sku"],
            unit=i["unit"],
            quantity=i["quantity"],
            price_ht_cents=i["price_ht_cents"],
            line_total_ht_cents=i["line_total_ht_cents"],
        )
        for i in order.get("items", [])
    ]
    
    # Check installment eligibility (>= 5500€ HT)
    MIN_INSTALLMENT_HT_CENTS = 550000
    installment_eligible = order["subtotal_ht_cents"] >= MIN_INSTALLMENT_HT_CENTS
    
    return OrderResponse(
        id=order["id"],
        order_number=order["order_number"],
        org_id=order["org_id"],
        zone_code=order["zone_code"],
        status=order["status"],
        incoterm=order["incoterm"],
        pickup_location_id=order["pickup_location_id"],
        pickup_location_name=pickup["name"] if pickup else None,
        items=items,
        items_count=order["items_count"],
        subtotal_ht_cents=order["subtotal_ht_cents"],
        tax_cents=order["tax_cents"],
        total_ttc_cents=order["total_ttc_cents"],
        credits_used=order.get("credits_used", 0),
        notes=order.get("notes"),
        is_installment=order.get("is_installment", False),
        installment_plan=order.get("installment_plan"),
        installment_eligible=installment_eligible,
        confirmed_at=order.get("confirmed_at"),
        ready_at=order.get("ready_at"),
        picked_up_at=order.get("picked_up_at"),
        created_at=order["created_at"],
    )


# ============== ADMIN ROUTES ==============

@orders_router.get("/admin/all", response_model=List[OrderResponse])
async def admin_list_orders(
    current_user: dict = Depends(get_current_user_catalog),
    status_filter: Optional[str] = None,
    zone_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List all orders (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    if zone_filter:
        query["zone_code"] = zone_filter
    
    orders = await db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for o in orders:
        pickup = await db.pickup_locations.find_one({"id": o["pickup_location_id"]})
        result.append(await _build_order_response(o, pickup))
    
    return result


@orders_router.post("/admin/{order_id}/status", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: str,
    new_status: OrderStatus,
    current_user: dict = Depends(get_current_user_catalog),
):
    """Update order status (admin)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    update_data = {
        "status": new_status.value,
        "updated_at": datetime.utcnow(),
    }
    
    # Set timestamps based on status
    if new_status == OrderStatus.CONFIRMED:
        update_data["confirmed_at"] = datetime.utcnow()
    elif new_status == OrderStatus.READY_FOR_PICKUP:
        update_data["ready_at"] = datetime.utcnow()
    elif new_status == OrderStatus.PICKED_UP:
        update_data["picked_up_at"] = datetime.utcnow()
    elif new_status == OrderStatus.INVOICED:
        update_data["invoiced_at"] = datetime.utcnow()
    elif new_status == OrderStatus.PAID:
        update_data["paid_at"] = datetime.utcnow()
    
    await db.orders.update_one({"id": order_id}, {"$set": update_data})
    
    updated = await db.orders.find_one({"id": order_id})
    pickup = await db.pickup_locations.find_one({"id": updated["pickup_location_id"]})
    return await _build_order_response(updated, pickup)
