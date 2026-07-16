"""KDMARCHE Payments — Bank details, credit packages, models & helpers (split from routes_payment.py)."""
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import os
import uuid
import logging

from emergentintegrations.payments.stripe.checkout import StripeCheckout

logger = logging.getLogger(__name__)

db = None

def set_payment_models_database(database):
    global db
    db = database

# ============== BANK TRANSFER DETAILS ==============
# OSCOP (Crédit Mutuel) — used for the public /bank-details endpoint (OSCOP credits)
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

# KDMARCHE (myPOS) — server-only constant, NOT exposed via public endpoints.
# Use this for internal payout / reconciliation routing logic for the KDMARCHE Stripe account.
# Owner request: keep these details only in server-side constants (no public route).
KDMARCHE_BANK_DETAILS = {
    "account_name": "KDMARCHE",
    "account_number": "40113620682",
    "beneficiary_name": "PIPEROL FELIXIA VANESSA",
    "beneficiary_address": "CHEMIN SYMPHART LAMPECINADO MORNE BOURG #",
    "iban": "IE72MPOS99039052096773",
    "bic": "MPOSIE2D",
    "bank_name": "myPOS Ltd",
    "bank_address": "12 St. Stephen's Green, Dublin 2 D02 WK11, Ireland",
    "currency": "EUR",
    "stripe_account_key_env": "STRIPE_KDMARCHE_LIVE_KEY",
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


