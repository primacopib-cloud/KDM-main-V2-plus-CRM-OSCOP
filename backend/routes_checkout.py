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
    set_checkout_common_database(database)
    set_checkout_handlers_database(database)


from checkout_common import (
    CheckoutSessionRequest, CheckoutSessionResponse,
    PaymentIntentRequest, PaymentIntentResponse,
    InstallmentPaymentRequest, OrderPaymentStatus,
    get_current_user_checkout, get_order_with_access_check,
)
from checkout_common import set_checkout_common_database
from checkout_handlers import handle_checkout_completed, handle_payment_succeeded, handle_payment_failed, set_checkout_handlers_database

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
    endpoint_secret = (
        os.environ.get("STRIPE_WEBHOOK_SECRET")
        or os.environ.get("STRIPE_WEBHOOK_SECRET_KDMARCHE")
        or os.environ.get("STRIPE_WEBHOOK_SECRETS_KDMARCHE")
    )
    stripe_mode = (os.environ.get("STRIPE_MODE") or "live").lower()
    
    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        elif stripe_mode != "live":
            # Dev only: parse without signature verification
            import json
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        else:
            logger.error("Webhook rejeté: aucun secret configuré en mode LIVE")
            raise HTTPException(status_code=400, detail="Webhook signature required")
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    if not event_type:
        raise HTTPException(status_code=400, detail="Invalid payload: missing type")
    data = event["data"]["object"]
    
    logger.info(f"Webhook received: {event_type}")
    
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data)
    elif event_type == "payment_intent.succeeded":
        await handle_payment_succeeded(data)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failed(data)
    
    return {"status": "received"}


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
