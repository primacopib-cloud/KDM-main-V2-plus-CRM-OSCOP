"""
KDMARCHE × O'SCOP - Invoice Management API
Generates and manages invoices for completed orders
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import logging

logger = logging.getLogger(__name__)

# Router
invoices_router = APIRouter(prefix="/api/v2/invoices")

# Database reference
db = None

def set_invoices_database(database):
    global db
    db = database


# ============== SCHEMAS ==============

class InvoiceItem(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    quantity: int
    unit: str
    unit_price_ht_cents: int
    line_total_ht_cents: int


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    order_id: str
    order_number: str
    org_id: str
    org_name: Optional[str] = None
    
    # Invoice details
    status: str  # DRAFT, ISSUED, PAID, CANCELED
    invoice_type: str  # ORDER, CREDIT_NOTE
    issue_date: datetime
    due_date: datetime
    
    # Line items
    items: List[InvoiceItem] = []
    items_count: int = 0
    
    # Amounts
    subtotal_ht_cents: int
    tax_rate: float
    tax_cents: int
    total_ttc_cents: int
    
    # Fees (for installment)
    fees_ht_cents: int = 0
    fees_tax_cents: int = 0
    total_fees_cents: int = 0
    
    # Payment
    payment_status: str  # PENDING, PARTIAL, PAID
    amount_paid_cents: int = 0
    balance_due_cents: int = 0
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    
    # Metadata
    zone_code: str
    incoterm: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceResponse]
    total: int
    has_more: bool


class InvoiceStats(BaseModel):
    total_invoices: int
    total_paid: int
    total_pending: int
    total_overdue: int
    total_amount_cents: int
    total_paid_cents: int
    total_pending_cents: int


# ============== DEPENDENCIES ==============

async def get_current_user_invoices(request: Request):
    """Get current user from token"""
    from auth import decode_token, extract_user_id_from_request
    
    user_id = extract_user_id_from_request(request)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


# ============== INVOICE GENERATION ==============

async def generate_invoice_for_order(order_id: str) -> dict:
    """Generate invoice from a completed order"""
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise ValueError(f"Order not found: {order_id}")
    
    # Check if invoice already exists
    existing = await db.invoices.find_one({"order_id": order_id})
    if existing:
        return existing
    
    # Get org details
    org = await db.orgs.find_one({"id": order["org_id"]})
    org_name = org.get("legal_name", "N/A") if org else "N/A"
    
    now = datetime.utcnow()
    
    # Build invoice items
    invoice_items = []
    for item in order.get("items", []):
        invoice_items.append({
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "product_sku": item["product_sku"],
            "quantity": item["quantity"],
            "unit": item.get("unit", "unité"),
            "unit_price_ht_cents": item["price_ht_cents"],
            "line_total_ht_cents": item["line_total_ht_cents"],
        })
    
    # Calculate fees if installment
    fees_ht_cents = 0
    fees_tax_cents = 0
    total_fees_cents = 0
    
    if order.get("is_installment") and order.get("installment_plan"):
        plan = order["installment_plan"]
        fees_ht_cents = plan.get("fees_ht_cents", 0)
        fees_tax_cents = plan.get("fees_tva_cents", 0)
        total_fees_cents = plan.get("total_fees_cents", 0)
    
    # Generate invoice number
    year = now.year
    month = now.month
    count = await db.invoices.count_documents({"invoice_number": {"$regex": f"^FA-{year}{month:02d}"}})
    invoice_number = f"FA-{year}{month:02d}-{count + 1:04d}"
    
    invoice = {
        "id": str(uuid.uuid4()),
        "invoice_number": invoice_number,
        "order_id": order["id"],
        "order_number": order["order_number"],
        "org_id": order["org_id"],
        "org_name": org_name,
        
        "status": "ISSUED",
        "invoice_type": "ORDER",
        "issue_date": now,
        "due_date": now,  # Due immediately for EXW
        
        "items": invoice_items,
        "items_count": len(invoice_items),
        
        "subtotal_ht_cents": order["subtotal_ht_cents"],
        "tax_rate": 0.085,  # 8.5% TVA DOM
        "tax_cents": order["tax_cents"],
        "total_ttc_cents": order["total_ttc_cents"] + total_fees_cents,
        
        "fees_ht_cents": fees_ht_cents,
        "fees_tax_cents": fees_tax_cents,
        "total_fees_cents": total_fees_cents,
        
        "payment_status": "PENDING",
        "amount_paid_cents": 0,
        "balance_due_cents": order["total_ttc_cents"] + total_fees_cents,
        "paid_at": None,
        "payment_method": None,
        
        "zone_code": order["zone_code"],
        "incoterm": order.get("incoterm", "EXW"),
        
        "created_at": now,
        "updated_at": now,
    }
    
    await db.invoices.insert_one(invoice)
    logger.info(f"Invoice generated: {invoice_number} for order {order['order_number']}")
    
    return invoice


# ============== ROUTES ==============

@invoices_router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    current_user: dict = Depends(get_current_user_invoices),
    status: Optional[str] = Query(None, description="Filter by status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List invoices for current user's organization"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        return InvoiceListResponse(invoices=[], total=0, has_more=False)
    
    # Build query
    query = {"org_id": membership["org_id"]}
    if status:
        query["status"] = status
    if payment_status:
        query["payment_status"] = payment_status
    
    # Get total count
    total = await db.invoices.count_documents(query)
    
    # Get invoices
    invoices = await db.invoices.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return InvoiceListResponse(
        invoices=[InvoiceResponse(**inv) for inv in invoices],
        total=total,
        has_more=(skip + limit) < total,
    )


@invoices_router.get("/stats", response_model=InvoiceStats)
async def get_invoice_stats(
    current_user: dict = Depends(get_current_user_invoices),
):
    """Get invoice statistics for current organization"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        return InvoiceStats(
            total_invoices=0,
            total_paid=0,
            total_pending=0,
            total_overdue=0,
            total_amount_cents=0,
            total_paid_cents=0,
            total_pending_cents=0,
        )
    
    org_id = membership["org_id"]
    
    # Aggregate stats
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$group": {
            "_id": None,
            "total_invoices": {"$sum": 1},
            "total_paid": {"$sum": {"$cond": [{"$eq": ["$payment_status", "PAID"]}, 1, 0]}},
            "total_pending": {"$sum": {"$cond": [{"$eq": ["$payment_status", "PENDING"]}, 1, 0]}},
            "total_amount_cents": {"$sum": "$total_ttc_cents"},
            "total_paid_cents": {"$sum": "$amount_paid_cents"},
        }}
    ]
    
    result = await db.invoices.aggregate(pipeline).to_list(1)
    
    if not result:
        return InvoiceStats(
            total_invoices=0,
            total_paid=0,
            total_pending=0,
            total_overdue=0,
            total_amount_cents=0,
            total_paid_cents=0,
            total_pending_cents=0,
        )
    
    stats = result[0]
    
    # Count overdue
    now = datetime.utcnow()
    overdue = await db.invoices.count_documents({
        "org_id": org_id,
        "payment_status": "PENDING",
        "due_date": {"$lt": now},
    })
    
    return InvoiceStats(
        total_invoices=stats["total_invoices"],
        total_paid=stats["total_paid"],
        total_pending=stats["total_pending"],
        total_overdue=overdue,
        total_amount_cents=stats["total_amount_cents"],
        total_paid_cents=stats["total_paid_cents"],
        total_pending_cents=stats["total_amount_cents"] - stats["total_paid_cents"],
    )


@invoices_router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user_invoices),
):
    """Get invoice details"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice or invoice["org_id"] != membership["org_id"]:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    return InvoiceResponse(**invoice)


@invoices_router.get("/by-order/{order_id}", response_model=InvoiceResponse)
async def get_invoice_by_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_invoices),
):
    """Get invoice for an order"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    invoice = await db.invoices.find_one({"order_id": order_id})
    if not invoice:
        # Try to generate invoice if order is completed
        order = await db.orders.find_one({"id": order_id})
        if order and order["org_id"] == membership["org_id"] and order["status"] == "COMPLETED":
            invoice = await generate_invoice_for_order(order_id)
        else:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice["org_id"] != membership["org_id"]:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    return InvoiceResponse(**invoice)


@invoices_router.post("/generate/{order_id}", response_model=InvoiceResponse)
async def generate_invoice(
    order_id: str,
    current_user: dict = Depends(get_current_user_invoices),
):
    """Manually generate invoice for an order (admin or completed orders)"""
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    is_admin = current_user.get("is_admin", False)
    
    if not membership and not is_admin:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Check access
    if not is_admin and (not membership or order["org_id"] != membership["org_id"]):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Generate invoice
    invoice = await generate_invoice_for_order(order_id)
    return InvoiceResponse(**invoice)


@invoices_router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    payment_method: str = Query("CARD", description="Payment method"),
    current_user: dict = Depends(get_current_user_invoices),
):
    """Mark invoice as paid (admin only)"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    now = datetime.utcnow()
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "payment_status": "PAID",
            "amount_paid_cents": invoice["total_ttc_cents"],
            "balance_due_cents": 0,
            "paid_at": now,
            "payment_method": payment_method,
            "updated_at": now,
        }}
    )
    
    updated = await db.invoices.find_one({"id": invoice_id})
    return InvoiceResponse(**updated)
