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
orders_router = APIRouter(prefix="/api/v2/orders")

db = None

def set_orders_database(database):
    global db
    db = database

from routes_catalog import get_current_user_catalog, get_user_org_context, check_price_access, get_selected_zone, ensure_member_active
from role_guards import ensure_can_buy

# ============== ORDERS ==============

@orders_router.post("", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user_catalog),
    request: Request = None,
):
    """Create order from cart (EXW only)"""
    ensure_can_buy(current_user)
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    await ensure_member_active(membership["org_id"])
    
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
    
    # Bonus parrainage filleul acheteur — première commande (fire-and-forget)
    import asyncio as _asyncio
    from routes_referral import maybe_pay_referral_bonus
    _asyncio.create_task(maybe_pay_referral_bonus(current_user["id"], event_label="première commande"))
    
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
    import asyncio
    from erp_webhooks import dispatch_order_event
    asyncio.create_task(dispatch_order_event(order_id, "order.status_changed",
                                             {"previous_status": order["status"], "new_status": OrderStatus.CANCELED.value, "reason": reason}))
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
        logistics=order.get("logistics"),
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
        carrier=order.get("carrier"),
        carrier_pickup_confirmed_at=order.get("carrier_pickup_confirmed_at"),
        carrier_delivery_confirmed_at=order.get("carrier_delivery_confirmed_at"),
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
    """List all orders (admin ou COOPER)"""
    if not (current_user.get("is_admin") or (current_user.get("role") or "").upper() == "COOPER"):
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
    """Update order status (admin ou COOPER)"""
    if not (current_user.get("is_admin") or (current_user.get("role") or "").upper() == "COOPER"):
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

    import asyncio
    from erp_webhooks import dispatch_order_event
    asyncio.create_task(dispatch_order_event(order_id, "order.status_changed",
                                             {"previous_status": order["status"], "new_status": new_status.value}))
    from order_sms import send_order_status_sms
    asyncio.create_task(send_order_status_sms(db, order_id, new_status.value))

    # Rétention de garantie 5% sur facture (contrats d'engagement de volume)
    if new_status in (OrderStatus.INVOICED, OrderStatus.PAID):
        try:
            from routes_vendor_contracts import apply_invoice_retention
            await apply_invoice_retention(db, updated)
        except Exception as e:
            logger.error(f"Invoice retention failed for order {order_id}: {e}")

    pickup = await db.pickup_locations.find_one({"id": updated["pickup_location_id"]})
    return await _build_order_response(updated, pickup)
