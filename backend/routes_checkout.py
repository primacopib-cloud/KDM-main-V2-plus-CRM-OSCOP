"""
KDMARCHE × O'SCOP - Checkout & Payment API
Stripe integration for order finalization and payment processing
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import logging
import stripe
import os

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_API_KEY')

# Router
checkout_router = APIRouter(prefix="/api/v2/checkout")

# Database reference
db = None

def set_checkout_database(database):
    global db
    db = database


# ============== SCHEMAS ==============

class CheckoutSessionRequest(BaseModel):
    order_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    order_id: str
    order_number: str
    amount_cents: int
    currency: str = "eur"
    mode: str  # payment or subscription


class PaymentIntentRequest(BaseModel):
    order_id: str
    payment_method: str = "card"  # card, sepa_debit, bank_transfer


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    order_id: str
    amount_cents: int
    status: str


class OrderPaymentStatus(BaseModel):
    order_id: str
    order_number: str
    payment_status: str  # pending, processing, succeeded, failed
    payment_method: Optional[str]
    paid_at: Optional[datetime]
    stripe_payment_id: Optional[str]
    amount_paid_cents: int = 0


class InstallmentPaymentRequest(BaseModel):
    order_id: str
    installment_number: int  # 1-4


# ============== DEPENDENCIES ==============

async def get_current_user_checkout(request: Request):
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


async def get_order_with_access_check(order_id: str, user: dict):
    """Get order and verify user has access"""
    membership = await db.org_memberships.find_one({"user_id": user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    if order["org_id"] != membership["org_id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return order, membership


# ============== STRIPE CHECKOUT SESSION ==============

@checkout_router.post("/create-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request_data: CheckoutSessionRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_checkout),
):
    """
    Create a Stripe Checkout Session for order payment
    Supports both standard payment and installment plans
    """
    order, membership = await get_order_with_access_check(request_data.order_id, current_user)
    
    # Check order status
    if order["status"] not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(status_code=400, detail="Commande non éligible au paiement")
    
    # Get org for customer info
    org = await db.orgs.find_one({"id": order["org_id"]})
    org_name = org.get("legal_name", "Client") if org else "Client"
    
    # Calculate amount
    if order.get("is_installment") and order.get("installment_plan"):
        # For installment, charge total with fees
        amount_cents = order["installment_plan"]["total_with_fees_cents"]
    else:
        amount_cents = order["total_ttc_cents"]
    
    # Base URLs
    frontend_url = os.environ.get("FRONTEND_URL", "https://plan-builder-75.preview.emergentagent.com")
    success_url = request_data.success_url or f"{frontend_url}/espace-acheteur?payment=success&order={order['order_number']}"
    cancel_url = request_data.cancel_url or f"{frontend_url}/checkout?payment=cancelled&order={order['order_number']}"
    
    try:
        # Build line items
        line_items = []
        
        # Add products
        for item in order.get("items", []):
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "unit_amount": item["price_ht_cents"],
                    "product_data": {
                        "name": item["product_name"],
                        "description": f"SKU: {item['product_sku']} - {item['quantity']} {item.get('unit', 'unité')}(s)",
                    },
                },
                "quantity": item["quantity"],
            })
        
        # Add TVA as line item
        if order["tax_cents"] > 0:
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "unit_amount": order["tax_cents"],
                    "product_data": {
                        "name": "TVA (8,5%)",
                        "description": "Taxe sur la valeur ajoutée - DOM",
                    },
                },
                "quantity": 1,
            })
        
        # Add installment fees if applicable
        if order.get("is_installment") and order.get("installment_plan"):
            fees = order["installment_plan"]
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "unit_amount": fees["total_fees_cents"],
                    "product_data": {
                        "name": "Frais paiement échelonné 4×",
                        "description": f"Frais HT: {fees['fees_ht_cents']/100:.2f}€ + TVA: {fees['fees_tva_cents']/100:.2f}€",
                    },
                },
                "quantity": 1,
            })
        
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=["card", "sepa_debit"],
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=current_user.get("email"),
            client_reference_id=order["id"],
            metadata={
                "order_id": order["id"],
                "order_number": order["order_number"],
                "org_id": order["org_id"],
                "org_name": org_name,
                "zone_code": order["zone_code"],
                "is_installment": str(order.get("is_installment", False)),
            },
            payment_intent_data={
                "description": f"Commande {order['order_number']} - {org_name}",
                "metadata": {
                    "order_id": order["id"],
                    "order_number": order["order_number"],
                },
            },
        )
        
        # Store session ID on order
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {
                "stripe_session_id": session.id,
                "payment_status": "pending",
                "updated_at": datetime.utcnow(),
            }}
        )
        
        logger.info(f"Checkout session created: {session.id} for order {order['order_number']}")
        
        return CheckoutSessionResponse(
            session_id=session.id,
            checkout_url=session.url,
            order_id=order["id"],
            order_number=order["order_number"],
            amount_cents=amount_cents,
            currency="eur",
            mode="payment",
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")


# ============== PAYMENT INTENT (for embedded form) ==============

@checkout_router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    request_data: PaymentIntentRequest,
    current_user: dict = Depends(get_current_user_checkout),
):
    """
    Create a Stripe Payment Intent for embedded payment form
    """
    order, membership = await get_order_with_access_check(request_data.order_id, current_user)
    
    if order["status"] not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(status_code=400, detail="Commande non éligible au paiement")
    
    # Get org
    org = await db.orgs.find_one({"id": order["org_id"]})
    org_name = org.get("legal_name", "Client") if org else "Client"
    
    # Calculate amount
    if order.get("is_installment") and order.get("installment_plan"):
        amount_cents = order["installment_plan"]["total_with_fees_cents"]
    else:
        amount_cents = order["total_ttc_cents"]
    
    # Map payment method
    payment_method_types = ["card"]
    if request_data.payment_method == "sepa_debit":
        payment_method_types = ["sepa_debit"]
    elif request_data.payment_method == "bank_transfer":
        payment_method_types = ["customer_balance"]
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="eur",
            payment_method_types=payment_method_types,
            description=f"Commande {order['order_number']} - {org_name}",
            metadata={
                "order_id": order["id"],
                "order_number": order["order_number"],
                "org_id": order["org_id"],
            },
            receipt_email=current_user.get("email"),
        )
        
        # Store on order
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {
                "stripe_payment_intent_id": intent.id,
                "payment_status": "pending",
                "updated_at": datetime.utcnow(),
            }}
        )
        
        logger.info(f"Payment intent created: {intent.id} for order {order['order_number']}")
        
        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            order_id=order["id"],
            amount_cents=amount_cents,
            status=intent.status,
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")


# ============== INSTALLMENT PAYMENT ==============

@checkout_router.post("/pay-installment", response_model=dict)
async def pay_installment(
    request_data: InstallmentPaymentRequest,
    current_user: dict = Depends(get_current_user_checkout),
):
    """
    Process payment for a specific installment
    """
    order, membership = await get_order_with_access_check(request_data.order_id, current_user)
    
    if not order.get("is_installment") or not order.get("installment_plan"):
        raise HTTPException(status_code=400, detail="Commande non échelonnée")
    
    plan = order["installment_plan"]
    installments = plan.get("installments", [])
    
    # Find the installment
    installment_idx = request_data.installment_number - 1
    if installment_idx < 0 or installment_idx >= len(installments):
        raise HTTPException(status_code=400, detail="Numéro d'échéance invalide")
    
    installment = installments[installment_idx]
    
    if installment.get("status") == "PAID":
        raise HTTPException(status_code=400, detail="Échéance déjà payée")
    
    # Get org (currently unused — preserved for future receipt/metadata enrichment)
    await db.orgs.find_one({"id": order["org_id"]})
    
    try:
        # Create payment intent for this installment
        intent = stripe.PaymentIntent.create(
            amount=installment["amount_cents"],
            currency="eur",
            payment_method_types=["card", "sepa_debit"],
            description=f"Commande {order['order_number']} - Échéance {request_data.installment_number}/4",
            metadata={
                "order_id": order["id"],
                "order_number": order["order_number"],
                "installment_number": request_data.installment_number,
            },
            receipt_email=current_user.get("email"),
        )
        
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "installment_number": request_data.installment_number,
            "amount_cents": installment["amount_cents"],
            "due_date": installment["due_date"],
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")


# ============== PAYMENT STATUS ==============

@checkout_router.get("/payment-status/{order_id}", response_model=OrderPaymentStatus)
async def get_payment_status(
    order_id: str,
    current_user: dict = Depends(get_current_user_checkout),
):
    """Get payment status for an order"""
    order, _ = await get_order_with_access_check(order_id, current_user)
    
    return OrderPaymentStatus(
        order_id=order["id"],
        order_number=order["order_number"],
        payment_status=order.get("payment_status", "pending"),
        payment_method=order.get("payment_method"),
        paid_at=order.get("paid_at"),
        stripe_payment_id=order.get("stripe_payment_intent_id"),
        amount_paid_cents=order.get("amount_paid_cents", 0),
    )


# ============== STRIPE WEBHOOK ==============

@checkout_router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            # For development without webhook signature verification
            import json
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Webhook received: {event_type}")
    
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data)
    elif event_type == "payment_intent.succeeded":
        await handle_payment_succeeded(data)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failed(data)
    
    return {"status": "received"}


async def handle_checkout_completed(session: dict):
    """Handle successful checkout session"""
    order_id = session.get("metadata", {}).get("order_id")
    if not order_id:
        order_id = session.get("client_reference_id")
    
    if not order_id:
        logger.warning("No order_id in checkout session")
        return
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        logger.warning(f"Order not found: {order_id}")
        return
    
    # Update order
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "CONFIRMED",
            "payment_status": "succeeded",
            "payment_method": "stripe_checkout",
            "stripe_payment_intent_id": session.get("payment_intent"),
            "amount_paid_cents": session.get("amount_total", 0),
            "paid_at": datetime.utcnow(),
            "confirmed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }}
    )
    
    # Generate invoice
    from routes_invoices import generate_invoice_for_order
    try:
        await generate_invoice_for_order(order_id)
    except Exception as e:
        logger.error(f"Error generating invoice: {str(e)}")
    
    logger.info(f"Order {order['order_number']} payment completed")


async def handle_payment_succeeded(intent: dict):
    """Handle successful payment intent"""
    order_id = intent.get("metadata", {}).get("order_id")
    if not order_id:
        return
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        return
    
    installment_number = intent.get("metadata", {}).get("installment_number")
    
    if installment_number:
        # Update installment status
        installment_idx = int(installment_number) - 1
        installments = order.get("installment_plan", {}).get("installments", [])
        
        if 0 <= installment_idx < len(installments):
            installments[installment_idx]["status"] = "PAID"
            installments[installment_idx]["paid_at"] = datetime.utcnow().isoformat()
            installments[installment_idx]["stripe_payment_id"] = intent["id"]
            
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {
                    "installment_plan.installments": installments,
                    "updated_at": datetime.utcnow(),
                }}
            )
            
            # Check if all installments paid
            all_paid = all(i.get("status") == "PAID" for i in installments)
            if all_paid:
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "payment_status": "succeeded",
                        "status": "PAID",
                    }}
                )
            
            logger.info(f"Installment {installment_number}/4 paid for order {order['order_number']}")
    else:
        # Standard payment
        amount_paid = order.get("amount_paid_cents", 0) + intent.get("amount", 0)
        
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "payment_status": "succeeded",
                "amount_paid_cents": amount_paid,
                "paid_at": datetime.utcnow(),
                "status": "CONFIRMED",
                "confirmed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }}
        )
        
        logger.info(f"Payment succeeded for order {order['order_number']}")


async def handle_payment_failed(intent: dict):
    """Handle failed payment"""
    order_id = intent.get("metadata", {}).get("order_id")
    if not order_id:
        return
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "payment_status": "failed",
            "payment_error": intent.get("last_payment_error", {}).get("message"),
            "updated_at": datetime.utcnow(),
        }}
    )
    
    logger.info(f"Payment failed for order {order_id}")


# ============== QUICK PAYMENT CONFIRMATION ==============

@checkout_router.post("/confirm-payment", response_model=dict)
async def confirm_payment_manual(
    order_id: str = Query(...),
    payment_method: str = Query("card"),
    current_user: dict = Depends(get_current_user_checkout),
):
    """
    Manually confirm payment (for demo/testing without real Stripe flow)
    This simulates a successful payment
    """
    order, membership = await get_order_with_access_check(order_id, current_user)
    
    if order["status"] not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(status_code=400, detail="Commande non éligible")
    
    # Calculate total
    if order.get("is_installment") and order.get("installment_plan"):
        amount = order["installment_plan"]["total_with_fees_cents"]
    else:
        amount = order["total_ttc_cents"]
    
    # Update order as paid
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "CONFIRMED",
            "payment_status": "succeeded",
            "payment_method": payment_method,
            "amount_paid_cents": amount,
            "paid_at": datetime.utcnow(),
            "confirmed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }}
    )
    
    # Generate invoice
    from routes_invoices import generate_invoice_for_order
    try:
        invoice = await generate_invoice_for_order(order_id)
        invoice_number = invoice.get("invoice_number", "N/A")
    except Exception as e:
        logger.error(f"Error generating invoice: {str(e)}")
        invoice_number = None
    
    logger.info(f"Payment confirmed for order {order['order_number']}")
    
    return {
        "success": True,
        "order_id": order_id,
        "order_number": order["order_number"],
        "amount_paid_cents": amount,
        "payment_method": payment_method,
        "invoice_number": invoice_number,
        "message": "Paiement confirmé avec succès",
    }
