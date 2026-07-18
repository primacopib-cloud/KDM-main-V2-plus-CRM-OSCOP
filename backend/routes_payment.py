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
    get_current_user_from_request,
)
from payment_models import set_payment_models_database
from routes_payment_sepa import set_payment_sepa_database


def _wallet_stripe_key() -> str:
    """Clé Stripe du flux crédits wallet (compte O'SCOP, clé test fournie)."""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    return api_key


async def _send_wallet_receipt_email(user: dict, transaction: dict) -> None:
    """Reçu PDF envoyé par email Brevo à l'acheteur après achat de crédits wallet."""
    try:
        import base64
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        from pdf_credit_invoice import generate_credit_invoice_pdf

        if not is_brevo_configured() or not user.get("email"):
            return
        pack = await db.wallet_credit_packs.find_one({"id": transaction.get("package_id")}, {"_id": 0}) or \
            {"name": transaction.get("package_id", "Pack de crédits"), "credits": transaction["credits"]}
        client = {
            "company_name": user.get("company_name") or user.get("contact_name") or user["email"],
            "contact_name": user.get("contact_name") or "",
            "email": user["email"],
        }
        pdf = generate_credit_invoice_pdf(
            client, pack, transaction["credits"], 0,
            float(transaction["amount"]), transaction["session_id"],
        )
        body = (
            f"<p>Bonjour {client['contact_name']},</p>"
            f"<p>Merci pour votre achat ! <strong>{transaction['credits']} crédits</strong> "
            f"ont été ajoutés à votre solde CREDI&rsquo;SCOP pour <strong>{float(transaction['amount']):.2f} €</strong>.</p>"
            "<p>Vous trouverez votre reçu en pièce jointe.</p>"
        )
        await send_email(
            to_email=user["email"], to_name=client["contact_name"] or None,
            subject=f"Votre reçu KDMARCHÉ — {pack['name']} ({transaction['credits']} crédits)",
            html_content=_wrap_html("Reçu — Achat de crédits", body),
            tags=["wallet-credit-receipt"],
            attachments=[{
                "content": base64.b64encode(pdf).decode(),
                "name": f"recu-credits-{transaction['session_id'][-8:]}.pdf",
            }],
        )
        logger.info(f"Wallet receipt email sent to {user['email']} (session {transaction['session_id']})")
    except Exception as exc:
        logger.error(f"Wallet receipt email failed: {exc}")

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
    
    # Validate package (packs gérés par le Super Admin en base)
    from routes_wallet_packs_admin import get_wallet_pack
    package = await get_wallet_pack(checkout_data.package_id)
    if not package:
        raise HTTPException(
            status_code=400, 
            detail="Package invalide ou masqué"
        )
    
    # Build URLs from frontend origin
    origin = checkout_data.origin_url.rstrip("/")
    success_url = f"{origin}/wallet?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/wallet?payment=cancelled"
    
    # Create checkout session via the official Stripe SDK (real api.stripe.com)
    try:
        stripe.api_base = "https://api.stripe.com"
        session = stripe.checkout.Session.create(
            api_key=_wallet_stripe_key(),
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": int(round(package["price"] * 100)),
                    "product_data": {
                        "name": f"KDMARCHÉ — {package['name']} ({package['credits']} crédits)",
                    },
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user["id"],
                "user_email": user["email"],
                "package_id": package["id"],
                "credits": str(package["credits"]),
                "source": "wallet_topup"
            },
        )
        
        # Create payment transaction record
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        transaction = {
            "id": transaction_id,
            "session_id": session.id,
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
        
        logger.info(f"Checkout session created: {session.id} for user {user['id']}")
        
        return CheckoutSessionResponseModel(
            checkout_url=session.url,
            session_id=session.id,
            package=package,
            expires_at=datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
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
    try:
        stripe.api_base = "https://api.stripe.com"
        session = stripe.checkout.Session.retrieve(session_id, api_key=_wallet_stripe_key())
        stripe_payment_status = session.payment_status
        stripe_session_status = session.status
        
        # Update transaction status
        new_status = PaymentStatus.PENDING.value
        credited = transaction.get("credited", False)
        
        if stripe_payment_status == "paid":
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
                await _send_wallet_receipt_email(user, transaction)
                
        elif stripe_session_status == "expired":
            new_status = PaymentStatus.EXPIRED.value
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": new_status,
                    "payment_status": stripe_payment_status,
                    "credited": credited,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return PaymentStatusResponse(
            session_id=session_id,
            status=new_status,
            payment_status=stripe_payment_status,
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
    """Handle Stripe webhook events (signature vérifiée sur les secrets O'SCOP)"""
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature", "")
        
        secrets = [s.strip() for s in os.environ.get("STRIPE_WEBHOOK_SECRETS_OSCOP", "").split(",") if s.strip()]
        event = None
        for secret in secrets:
            try:
                event = stripe.Webhook.construct_event(body, signature, secret)
                break
            except Exception:
                continue
        if event is None:
            logger.warning("Wallet webhook: signature non vérifiée — ignoré (le polling créditera)")
            return {"received": True, "verified": False}
        
        session = event["data"]["object"]
        session_id = session.get("id")
        logger.info(f"Webhook received: {event['type']} for session {session_id}")
        
        # Handle payment success
        if event["type"] == "checkout.session.completed":
            transaction = await db.payment_transactions.find_one({
                "session_id": session_id
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
                    {"session_id": session_id},
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
                buyer = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
                if buyer:
                    await _send_wallet_receipt_email(buyer, transaction)
        
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


