"""
KDMARCHE × O'SCOP - Payment Routes
Wallet credit purchases via Stripe Checkout, Bank Transfer, and SEPA Direct Debit
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum
import os
import logging
import uuid
import stripe

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, 
    CheckoutSessionResponse, 
    CheckoutStatusResponse, 
    CheckoutSessionRequest
)

logger = logging.getLogger(__name__)

# Router
payment_router = APIRouter(prefix="/api/payments")

# Database reference (set by server.py)
db = None

def set_payment_database(database):
    """Set database reference from main server"""
    global db
    db = database
    set_payment_models_database(database)
    set_payment_sepa_database(database)



from payment_models import (
    BANK_DETAILS, CREDIT_PACKAGES,
    PaymentMethod, PaymentStatus,
    CreateCheckoutRequest, CheckoutSessionResponseModel,
    CreateBankTransferRequest, BankTransferResponse, PaymentStatusResponse,
    get_current_user_from_request, get_stripe_checkout,
)
from payment_models import set_payment_models_database
from routes_payment_sepa import set_payment_sepa_database

# ============== ENDPOINTS ==============

@payment_router.get("/packages")
async def list_packages():
    """List all available credit packages"""
    return {
        "packages": list(CREDIT_PACKAGES.values()),
        "currency": "EUR"
    }


@payment_router.post("/checkout", response_model=CheckoutSessionResponseModel)
async def create_checkout_session(
    request: Request,
    checkout_data: CreateCheckoutRequest
):
    """Create a Stripe checkout session for purchasing credits"""
    
    # Get current user
    user = await get_current_user_from_request(request)
    
    # Validate package
    package = CREDIT_PACKAGES.get(checkout_data.package_id)
    if not package:
        raise HTTPException(
            status_code=400, 
            detail=f"Package invalide. Packages disponibles: {list(CREDIT_PACKAGES.keys())}"
        )
    
    # Build URLs from frontend origin
    origin = checkout_data.origin_url.rstrip("/")
    success_url = f"{origin}/wallet?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/wallet?payment=cancelled"
    
    # Initialize Stripe
    stripe_checkout = get_stripe_checkout(request)
    
    # Create checkout session
    try:
        checkout_request = CheckoutSessionRequest(
            amount=package["price"],
            currency="eur",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user["id"],
                "user_email": user["email"],
                "package_id": package["id"],
                "credits": str(package["credits"]),
                "source": "wallet_topup"
            }
        )
        
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        transaction = {
            "id": transaction_id,
            "session_id": session.session_id,
            "user_id": user["id"],
            "user_email": user["email"],
            "package_id": package["id"],
            "credits": package["credits"],
            "amount": package["price"],
            "currency": "EUR",
            "status": PaymentStatus.INITIATED.value,
            "payment_status": "pending",
            "credited": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.payment_transactions.insert_one(transaction)
        
        logger.info(f"Checkout session created: {session.session_id} for user {user['id']}")
        
        return CheckoutSessionResponseModel(
            checkout_url=session.url,
            session_id=session.session_id,
            package=package,
            expires_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur création session: {str(e)}")


@payment_router.get("/status/{session_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    request: Request,
    session_id: str
):
    """Check payment status and credit user if successful"""
    
    # Get current user
    user = await get_current_user_from_request(request)
    
    # Find transaction
    transaction = await db.payment_transactions.find_one({
        "session_id": session_id,
        "user_id": user["id"]
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction non trouvée")
    
    # Check with Stripe
    stripe_checkout = get_stripe_checkout(request)
    
    try:
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction status
        new_status = PaymentStatus.PENDING.value
        credited = transaction.get("credited", False)
        
        if status.payment_status == "paid":
            new_status = PaymentStatus.PAID.value
            
            # Credit user only once
            if not credited:
                # Add credits to user
                credits_to_add = transaction["credits"]
                await db.users.update_one(
                    {"id": user["id"]},
                    {"$inc": {"credits": credits_to_add}}
                )
                
                # Mark as credited
                credited = True
                
                logger.info(f"Credited {credits_to_add} to user {user['id']} for session {session_id}")
                
        elif status.status == "expired":
            new_status = PaymentStatus.EXPIRED.value
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": new_status,
                    "payment_status": status.payment_status,
                    "credited": credited,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return PaymentStatusResponse(
            session_id=session_id,
            status=new_status,
            payment_status=status.payment_status,
            package_id=transaction.get("package_id"),
            credits=transaction.get("credits"),
            amount=transaction.get("amount"),
            currency=transaction.get("currency", "eur").lower(),
            credited=credited
        )
        
    except Exception as e:
        logger.error(f"Failed to check payment status: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur vérification: {str(e)}")


@payment_router.post("/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    
    stripe_checkout = get_stripe_checkout(request)
    
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        logger.info(f"Webhook received: {webhook_response.event_type} for session {webhook_response.session_id}")
        
        # Handle payment success
        if webhook_response.event_type == "checkout.session.completed":
            transaction = await db.payment_transactions.find_one({
                "session_id": webhook_response.session_id
            })
            
            if transaction and not transaction.get("credited", False):
                # Credit user
                user_id = transaction["user_id"]
                credits_to_add = transaction["credits"]
                
                await db.users.update_one(
                    {"id": user_id},
                    {"$inc": {"credits": credits_to_add}}
                )
                
                # Update transaction
                await db.payment_transactions.update_one(
                    {"session_id": webhook_response.session_id},
                    {
                        "$set": {
                            "status": PaymentStatus.PAID.value,
                            "payment_status": "paid",
                            "credited": True,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                logger.info(f"Webhook: Credited {credits_to_add} to user {user_id}")
        
        return {"received": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True, "error": str(e)}


@payment_router.get("/history")
async def get_payment_history(request: Request, limit: int = 20):
    """Get user's payment history"""
    
    user = await get_current_user_from_request(request)
    
    transactions = await db.payment_transactions.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "transactions": transactions,
        "count": len(transactions)
    }


# ============== BANK TRANSFER ENDPOINTS ==============

@payment_router.get("/bank-details")
async def get_bank_details():
    """Get bank details for wire transfer"""
    return {
        "bank_details": BANK_DETAILS,
        "instructions": (
            "Pour effectuer un virement bancaire, utilisez les coordonnées ci-dessus. "
            "Indiquez votre référence de commande dans le libellé du virement. "
            "Les crédits seront ajoutés à votre compte après validation du paiement (1-3 jours ouvrés)."
        )
    }


@payment_router.post("/bank-transfer", response_model=BankTransferResponse)
async def create_bank_transfer(
    request: Request,
    transfer_data: CreateBankTransferRequest
):
    """Create a bank transfer payment request"""
    raise HTTPException(
        status_code=403,
        detail="Les crédits sont payables exclusivement par carte bancaire (Stripe).",
    )
    
    user = await get_current_user_from_request(request)
    
    # Validate package
    package = CREDIT_PACKAGES.get(transfer_data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Package invalide")
    
    # Generate unique reference
    transfer_id = f"vir_{uuid.uuid4().hex[:8].upper()}"
    reference = f"OSCOP-{transfer_id}-{transfer_data.company_name[:10].upper().replace(' ', '')}"
    
    # Create transaction record
    transaction = {
        "id": transfer_id,
        "session_id": transfer_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "company_name": transfer_data.company_name,
        "package_id": package["id"],
        "credits": package["credits"],
        "amount": package["price"],
        "currency": "EUR",
        "payment_method": PaymentMethod.BANK_TRANSFER.value,
        "reference": reference,
        "status": PaymentStatus.PENDING_VALIDATION.value,
        "payment_status": "awaiting_transfer",
        "credited": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.payment_transactions.insert_one(transaction)
    
    logger.info(f"Bank transfer created: {transfer_id} for user {user['id']}")
    
    return BankTransferResponse(
        transfer_id=transfer_id,
        reference=reference,
        package=package,
        amount=package["price"],
        currency="EUR",
        bank_details=BANK_DETAILS,
        instructions=(
            f"Effectuez un virement de {package['price']}€ vers le compte indiqué. "
            f"Utilisez la référence '{reference}' dans le libellé du virement. "
            "Vos crédits seront ajoutés après validation (1-3 jours ouvrés)."
        )
    )


@payment_router.get("/bank-transfer/{transfer_id}/status")
async def get_bank_transfer_status(request: Request, transfer_id: str):
    """Check bank transfer status"""
    
    user = await get_current_user_from_request(request)
    
    transaction = await db.payment_transactions.find_one({
        "session_id": transfer_id,
        "user_id": user["id"],
        "payment_method": PaymentMethod.BANK_TRANSFER.value
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Virement non trouvé")
    
    return {
        "transfer_id": transfer_id,
        "reference": transaction.get("reference"),
        "status": transaction.get("status"),
        "amount": transaction.get("amount"),
        "credits": transaction.get("credits"),
        "credited": transaction.get("credited", False),
        "created_at": transaction.get("created_at")
    }


