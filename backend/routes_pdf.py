"""
KDMARCHE × O'SCOP - PDF Generation API
Generate signed purchase orders and invoices as PDF

Découpé : générateurs dans pdf_generators.py.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import logging
import io
import os

from pdf_generators import generate_order_pdf, generate_invoice_pdf

logger = logging.getLogger(__name__)

pdf_router = APIRouter(prefix="/api/v2/pdf")

db = None

def set_pdf_database(database):
    global db
    db = database

# ============== DEPENDENCIES ==============

async def get_current_user_pdf(request: Request):
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


# ============== ROUTES ==============

@pdf_router.get("/order/{order_id}")
async def download_order_pdf(
    order_id: str,
    current_user: dict = Depends(get_current_user_pdf),
):
    """Generate and download PDF for a purchase order"""
    # Get user's org
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    
    # Get order
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Check access
    if not current_user.get("is_admin"):
        if not membership or order["org_id"] != membership["org_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Get org info
    org = await db.orgs.find_one({"id": order["org_id"]})
    
    # Get signature data if available
    signature_data = None
    if order.get("signature_id"):
        signature = await db.signatures.find_one({"id": order["signature_id"]})
        if signature:
            signature_data = {
                "signature_id": signature["id"],
                "signer_name": signature.get("signer_name", current_user.get("contact_name", "N/A")),
                "signer_email": signature.get("signer_email", current_user.get("email", "N/A")),
                "signed_at": signature.get("signed_at", order.get("created_at")),
            }
    
    try:
        pdf_bytes = generate_order_pdf(order, org, signature_data)
        
        filename = f"bon_commande_{order['order_number']}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        logger.error(f"Error generating order PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de génération PDF: {str(e)}")


@pdf_router.get("/invoice/{invoice_id}")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: dict = Depends(get_current_user_pdf),
):
    """Generate and download PDF for an invoice"""
    # Get user's org
    membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
    
    # Get invoice
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    # Check access
    if not current_user.get("is_admin"):
        if not membership or invoice["org_id"] != membership["org_id"]:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Get related order
    order = await db.orders.find_one({"id": invoice["order_id"]}) if invoice.get("order_id") else None
    
    try:
        pdf_bytes = generate_invoice_pdf(invoice, order)
        
        filename = f"facture_{invoice['invoice_number']}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        logger.error(f"Error generating invoice PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de génération PDF: {str(e)}")
