"""KDMARCHE Checkout V2 — Handlers webhook Stripe (split from routes_checkout.py)."""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import os
import uuid
import logging
import stripe

logger = logging.getLogger(__name__)

db = None

def set_checkout_handlers_database(database):
    global db
    db = database

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


