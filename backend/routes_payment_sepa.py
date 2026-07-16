"""KDMARCHE Payments — SEPA Direct Debit endpoints (split from routes_payment.py)."""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone
import os
import uuid
import logging
import stripe

from payment_models import (
    PaymentStatus, PaymentMethod, CreateSepaSetupRequest, SepaSetupResponse,
    get_current_user_from_request, get_stripe_checkout,
    BANK_DETAILS, KDMARCHE_BANK_DETAILS, CREDIT_PACKAGES,
)

logger = logging.getLogger(__name__)

payment_sepa_router = APIRouter(prefix="/api/payments")

db = None

def set_payment_sepa_database(database):
    global db
    db = database

# ============== SEPA DIRECT DEBIT ENDPOINTS ==============

@payment_sepa_router.post("/sepa/setup")
async def create_sepa_setup(
    request: Request,
    sepa_data: CreateSepaSetupRequest
):
    """Create SEPA Direct Debit setup intent"""
    
    user = await get_current_user_from_request(request)
    
    # Validate package
    package = CREDIT_PACKAGES.get(sepa_data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Package invalide")
    
    # Initialize Stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=sepa_data.email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(
                email=sepa_data.email,
                name=sepa_data.account_holder_name,
                metadata={
                    "user_id": user["id"],
                    "platform": "kdmarche_oscop"
                }
            )
        
        # Create SetupIntent for SEPA
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["sepa_debit"],
            usage="off_session",
            metadata={
                "user_id": user["id"],
                "package_id": package["id"],
                "credits": str(package["credits"]),
                "amount": str(package["price"])
            }
        )
        
        # Create transaction record
        transaction_id = f"sepa_{uuid.uuid4().hex[:12]}"
        transaction = {
            "id": transaction_id,
            "session_id": setup_intent.id,
            "stripe_customer_id": customer.id,
            "user_id": user["id"],
            "user_email": sepa_data.email,
            "account_holder": sepa_data.account_holder_name,
            "iban_last4": sepa_data.iban[-4:],
            "package_id": package["id"],
            "credits": package["credits"],
            "amount": package["price"],
            "currency": "EUR",
            "payment_method": PaymentMethod.SEPA_DEBIT.value,
            "status": PaymentStatus.INITIATED.value,
            "payment_status": "setup_pending",
            "credited": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.payment_transactions.insert_one(transaction)
        
        logger.info(f"SEPA setup created: {setup_intent.id} for user {user['id']}")
        
        return {
            "setup_id": setup_intent.id,
            "client_secret": setup_intent.client_secret,
            "customer_id": customer.id,
            "package": package,
            "status": "requires_payment_method"
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe SEPA error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@payment_sepa_router.post("/sepa/confirm/{setup_id}")
async def confirm_sepa_payment(
    request: Request,
    setup_id: str
):
    """Confirm SEPA setup and create payment"""
    
    user = await get_current_user_from_request(request)
    
    # Find transaction
    transaction = await db.payment_transactions.find_one({
        "session_id": setup_id,
        "user_id": user["id"],
        "payment_method": PaymentMethod.SEPA_DEBIT.value
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Setup SEPA non trouvé")
    
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        # Get setup intent status
        setup_intent = stripe.SetupIntent.retrieve(setup_id)
        
        if setup_intent.status != "succeeded":
            return {
                "status": setup_intent.status,
                "message": "Le mandat SEPA n'est pas encore confirmé"
            }
        
        # Create PaymentIntent with the payment method
        payment_intent = stripe.PaymentIntent.create(
            amount=int(transaction["amount"] * 100),  # cents
            currency="eur",
            customer=transaction["stripe_customer_id"],
            payment_method=setup_intent.payment_method,
            off_session=True,
            confirm=True,
            metadata={
                "user_id": user["id"],
                "package_id": transaction["package_id"],
                "transaction_id": transaction["id"]
            }
        )
        
        # Update transaction
        new_status = PaymentStatus.PENDING.value
        if payment_intent.status == "succeeded":
            new_status = PaymentStatus.PAID.value
            # Credit user
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"credits": transaction["credits"]}}
            )
            await db.payment_transactions.update_one(
                {"session_id": setup_id},
                {"$set": {"credited": True}}
            )
            logger.info(f"SEPA payment succeeded: {transaction['credits']} credits to user {user['id']}")
        
        await db.payment_transactions.update_one(
            {"session_id": setup_id},
            {
                "$set": {
                    "status": new_status,
                    "payment_status": payment_intent.status,
                    "payment_intent_id": payment_intent.id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "status": payment_intent.status,
            "credits": transaction["credits"] if payment_intent.status == "succeeded" else 0,
            "message": "Paiement SEPA en cours de traitement" if payment_intent.status == "processing" else "Paiement réussi"
        }
        
    except stripe.error.CardError as e:
        logger.error(f"SEPA payment failed: {e}")
        await db.payment_transactions.update_one(
            {"session_id": setup_id},
            {"$set": {"status": PaymentStatus.FAILED.value, "payment_status": "failed"}}
        )
        raise HTTPException(status_code=400, detail=str(e))


# ============== ADMIN ENDPOINTS ==============

@payment_sepa_router.post("/admin/validate-transfer/{transfer_id}")
async def admin_validate_bank_transfer(request: Request, transfer_id: str):
    """Admin: Validate a bank transfer and credit user"""
    
    admin = await get_current_user_from_request(request)
    
    if not admin.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    
    transaction = await db.payment_transactions.find_one({
        "session_id": transfer_id,
        "payment_method": PaymentMethod.BANK_TRANSFER.value
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Virement non trouvé")
    
    if transaction.get("credited"):
        raise HTTPException(status_code=400, detail="Virement déjà validé")
    
    # Credit user
    await db.users.update_one(
        {"id": transaction["user_id"]},
        {"$inc": {"credits": transaction["credits"]}}
    )
    
    # Update transaction
    await db.payment_transactions.update_one(
        {"session_id": transfer_id},
        {
            "$set": {
                "status": PaymentStatus.PAID.value,
                "payment_status": "paid",
                "credited": True,
                "validated_by": admin["id"],
                "validated_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    logger.info(f"Bank transfer {transfer_id} validated by admin {admin['id']}")
    
    return {
        "success": True,
        "transfer_id": transfer_id,
        "credits": transaction["credits"],
        "user_id": transaction["user_id"],
        "message": f"{transaction['credits']} crédits ajoutés à l'utilisateur"
    }


@payment_sepa_router.get("/admin/pending-transfers")
async def admin_list_pending_transfers(request: Request):
    """Admin: List all pending bank transfers"""
    
    admin = await get_current_user_from_request(request)
    
    if not admin.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    
    transfers = await db.payment_transactions.find(
        {
            "payment_method": PaymentMethod.BANK_TRANSFER.value,
            "status": PaymentStatus.PENDING_VALIDATION.value
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "transfers": transfers,
        "count": len(transfers)
    }

