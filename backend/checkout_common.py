"""KDMARCHE Checkout V2 — Schémas & dépendances communes (split from routes_checkout.py)."""
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

db = None

def set_checkout_common_database(database):
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


