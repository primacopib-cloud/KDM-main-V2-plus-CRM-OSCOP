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


# ============== BANK TRANSFER DETAILS ==============
BANK_DETAILS = {
    "account_holder": "OBJECTIF SCOP OUTREMER",
    "iban": "FR76 1027 8053 4000 0212 5320 139",
    "bic": "CMCIFR2A",
    "bank_name": "Crédit Mutuel",
    "branch": "CCM LA JAILLE",
    "address": {
        "line1": "387 RUE DE L'INDUSTRIE",
        "line2": "PARC D'ACTIVITE DE LA JAILLE",
        "postal_code": "97122",
        "city": "BAIE MAHAULT",
        "country": "GUADELOUPE - FRANCE"
    }
}


# ============== CREDIT PACKAGES ==============
# Server-side defined packages - amounts are in EUR
CREDIT_PACKAGES = {
    "starter": {
        "id": "starter",
        "name": "Pack Starter",
        "credits": 100,
        "price": 50.00,  # EUR
        "description": "100 crédits O'SCOP",
        "popular": False
    },
    "pro": {
        "id": "pro",
        "name": "Pack Pro",
        "credits": 250,
        "price": 100.00,  # EUR
        "description": "250 crédits O'SCOP (+25% bonus)",
        "popular": True
    },
    "business": {
        "id": "business",
        "name": "Pack Business",
        "credits": 600,
        "price": 200.00,  # EUR
        "description": "600 crédits O'SCOP (+50% bonus)",
        "popular": False
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Pack Enterprise",
        "credits": 1500,
        "price": 400.00,  # EUR
        "description": "1500 crédits O'SCOP (+87% bonus)",
        "popular": False
    }
}


# ============== MODELS ==============

class PaymentStatus(str, Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    PENDING_VALIDATION = "PENDING_VALIDATION"  # For bank transfer awaiting admin validation
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    SEPA_DEBIT = "sepa_debit"


class CreateCheckoutRequest(BaseModel):
    """Request to create a checkout session"""
    package_id: str = Field(..., description="ID of the credit package to purchase")
    origin_url: str = Field(..., description="Frontend origin URL for redirects")


class CreateBankTransferRequest(BaseModel):
    """Request for bank transfer payment"""
    package_id: str = Field(..., description="ID of the credit package to purchase")
    company_name: str = Field(..., description="Company name for reference")


class CreateSepaSetupRequest(BaseModel):
    """Request to create SEPA Direct Debit setup"""
    package_id: str = Field(..., description="ID of the credit package to purchase")
    iban: str = Field(..., description="IBAN for SEPA debit")
    account_holder_name: str = Field(..., description="Account holder name")
    email: str = Field(..., description="Email for mandate notifications")


class CheckoutSessionResponseModel(BaseModel):
    """Response with checkout session details"""
    checkout_url: str
    session_id: str
    package: dict
    expires_at: datetime


class BankTransferResponse(BaseModel):
    """Response with bank transfer details"""
    transfer_id: str
    reference: str
    package: dict
    amount: float
    currency: str = "EUR"
    bank_details: dict
    instructions: str


class SepaSetupResponse(BaseModel):
    """Response for SEPA setup"""
    setup_id: str
    client_secret: str
    package: dict
    status: str


class PaymentStatusResponse(BaseModel):
    """Response for payment status check"""
    session_id: str
    status: str
    payment_status: str
    payment_method: Optional[str] = None
    package_id: Optional[str] = None
    credits: Optional[int] = None
    amount: Optional[float] = None
    currency: str = "eur"
    credited: bool = False


class CreditPackageResponse(BaseModel):
    """Credit package info"""
    id: str
    name: str
    credits: int
    price: float
    description: str
    popular: bool


# ============== HELPER FUNCTIONS ==============

async def get_current_user_from_request(request: Request):
    """Extract user from request authorization header"""
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
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return user


def get_stripe_checkout(request: Request) -> StripeCheckout:
    """Initialize Stripe checkout with webhook URL"""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/payments/webhook/stripe"
    
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


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


# ============== SEPA DIRECT DEBIT ENDPOINTS ==============

@payment_router.post("/sepa/setup")
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


@payment_router.post("/sepa/confirm/{setup_id}")
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

@payment_router.post("/admin/validate-transfer/{transfer_id}")
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


@payment_router.get("/admin/pending-transfers")
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

