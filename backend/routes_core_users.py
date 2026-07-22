"""Core user-facing routes: quotes, PDF offer, legal documents, subscriptions,
credits, user statistics (split from server.py)."""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse

from models import (
    QuoteRequestCreate, QuoteRequestResponse, QuoteRequestInDB,
    SubscriptionUpdate, CreditsAdd, CreditsResponse, OrderResponse,
)
from pdf_generator import generate_offer_pdf
from subscriptions import get_active_plans_from_db
from db import get_database
from core_deps import get_current_user

logger = logging.getLogger(__name__)

users_core_router = APIRouter(prefix="/api")


# ============== QUOTE REQUEST ROUTES ==============

@users_core_router.post("/quotes", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_quote_request(quote_data: QuoteRequestCreate):
    """Create a new quote request."""
    db = get_database()
    contact_name = (quote_data.contact_name or f"{quote_data.first_name or ''} {quote_data.last_name or ''}".strip()) or quote_data.email
    quote_in_db = QuoteRequestInDB(
        company=quote_data.company,
        contact_name=contact_name,
        first_name=quote_data.first_name,
        last_name=quote_data.last_name,
        legal_status=quote_data.legal_status,
        email=quote_data.email,
        phone=quote_data.phone,
        phone_country=quote_data.phone_country,
        lang=quote_data.lang or "fr",
        plan=quote_data.plan,
        message=quote_data.message
    )

    await db.quote_requests.insert_one(quote_in_db.dict())

    logger.info(f"New quote request from: {quote_data.email}")

    notification = {
        "id": str(uuid.uuid4()),
        "type": "new_quote",
        "title": "Nouvelle demande de devis",
        "message": f"{quote_data.company} - {contact_name} demande un devis",
        "data": {
            "quote_id": quote_in_db.id,
            "company": quote_data.company,
            "email": quote_data.email,
            "legal_status": quote_data.legal_status
        },
        "target_roles": ["oscop_super_admin", "oscop_compliance_admin", "kdm_b2b_admin"],
        "target_user_id": None,
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow()
    }
    await db.notifications.insert_one(notification)

    import asyncio
    from oscop_demandes_client import push_quote_to_oscop
    asyncio.create_task(push_quote_to_oscop(db, quote_in_db.id))

    from quote_notify import send_quote_notification_email, send_quote_ack_email
    asyncio.create_task(send_quote_notification_email(quote_in_db.dict()))
    asyncio.create_task(send_quote_ack_email(quote_in_db.dict()))

    return {
        "id": quote_in_db.id,
        "company": quote_in_db.company,
        "email": quote_in_db.email,
        "status": quote_in_db.status,
        "created_at": quote_in_db.created_at,
        "message": "Demande de devis envoyée avec succès"
    }


@users_core_router.get("/quotes", response_model=List[QuoteRequestResponse])
async def get_quote_requests(current_user: dict = Depends(get_current_user)):
    """Get all quote requests (admin only)."""
    db = get_database()
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )

    quotes = await db.quote_requests.find().sort("created_at", -1).to_list(100)
    return [QuoteRequestResponse(**quote) for quote in quotes]


# ============== PDF DOWNLOAD ROUTE ==============

@users_core_router.get("/download-offer")
async def download_offer():
    """Download the commercial offer as PDF."""
    try:
        pdf_buffer = generate_offer_pdf()

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=Offre_Commerciale_KDMARCHE_OSCOP.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du PDF"
        )


# ============== LEGAL DOCUMENTS ==============

LEGAL_DOCUMENTS = {
    "convention": {
        "id": "convention",
        "title": "Convention de partenariat KDMARCHE – O'SCOP",
        "filename": "convention-kdmarche-oscop.html",
        "description": "Communityplace B2B ESS — Partenariat (séparation stricte des rôles)",
        "type": "partnership"
    },
    "cg-oscop": {
        "id": "cg-oscop",
        "title": "CG O'SCOP — Accès, Abonnements, Wallet Crédits",
        "filename": "cg-oscop.html",
        "description": "Conditions générales applicables aux services O'SCOP (hors marchandises)",
        "type": "terms"
    },
    "cgv-kdmarche": {
        "id": "cgv-kdmarche",
        "title": "CGV KDMARCHE B2B — Marchandises (EXW)",
        "filename": "cgv-kdmarche-b2b.html",
        "description": "Conditions générales de vente B2B pour les marchandises (Incoterm EXW)",
        "type": "sales"
    },
    "note-preventive": {
        "id": "note-preventive",
        "title": "Note préventive ACPR / DGCCRF",
        "filename": "note-preventive-acpr-dgccrf.html",
        "description": "Qualification et prévention de requalification (assurance, paiement, tromperie)",
        "type": "compliance"
    }
}


@users_core_router.get("/documents")
async def list_legal_documents():
    """List available legal documents."""
    return {"documents": list(LEGAL_DOCUMENTS.values())}


@users_core_router.get("/documents/{doc_id}")
async def get_document_info(doc_id: str):
    """Get legal document info."""
    doc = LEGAL_DOCUMENTS.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return doc


# ============== SUBSCRIPTION ROUTES ==============

@users_core_router.get("/subscriptions")
async def get_subscriptions():
    """Get available subscription plans (loaded from DB, fallback to hardcoded)."""
    db = get_database()
    plans = await get_active_plans_from_db(db)
    return {"plans": plans}


@users_core_router.put("/users/subscription", response_model=dict)
async def update_subscription(
    update_data: SubscriptionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user subscription."""
    db = get_database()
    new_plan = update_data.plan.value

    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "subscription": new_plan,
                "updated_at": datetime.utcnow()
            }
        }
    )

    logger.info(f"User {current_user['email']} changed subscription to {new_plan}")

    return {
        "subscription": new_plan,
        "message": "Abonnement mis à jour avec succès"
    }


# ============== CREDITS ROUTES ==============

@users_core_router.post("/credits/add", response_model=CreditsResponse)
async def add_credits(
    credits_data: CreditsAdd,
    current_user: dict = Depends(get_current_user)
):
    """Ajout direct de crédits — réservé aux administrateurs. Les membres achètent leurs crédits."""
    admin_roles = ("SUPER_ADMIN", "ADMIN", "oscop_super_admin", "kdm_b2b_admin", "admin")
    if not (current_user.get("is_admin") or current_user.get("role") in admin_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les crédits CREDI'SCOP s'obtiennent uniquement par achat. Rendez-vous dans votre portefeuille pour acheter des crédits.",
        )
    db = get_database()
    new_credits = current_user["credits"] + credits_data.amount

    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "credits": new_credits,
                "updated_at": datetime.utcnow()
            }
        }
    )
    await db.credits_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "added",
        "amount": credits_data.amount,
        "description": f"Ajout direct par administrateur ({current_user['email']})",
        "created_at": datetime.utcnow()
    })

    logger.info(f"Admin {current_user['email']} added {credits_data.amount} credits to own account")

    return CreditsResponse(
        credits=new_credits,
        message=f"{credits_data.amount} crédits ajoutés avec succès"
    )


@users_core_router.get("/credits", response_model=dict)
async def get_credits(current_user: dict = Depends(get_current_user)):
    """Get user credits."""
    return {"credits": current_user["credits"]}


# ============== USER STATISTICS ROUTES ==============

@users_core_router.get("/users/stats", response_model=dict)
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics: orders, savings, credits history."""
    db = get_database()
    user_id = current_user["id"]

    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(100)

    total_orders = len(orders)
    total_spent = sum(o.get("total_amount", 0) for o in orders)
    total_savings = sum(o.get("savings", 0) for o in orders)
    total_credits_used = sum(o.get("credits_used", 0) for o in orders)

    credits_history = await db.credits_history.find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(50)

    # Monthly breakdown (last 6 months)
    monthly_stats = []
    for i in range(6):
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_start = month_start.replace(month=month_start.month - i if month_start.month > i else 12 + month_start.month - i)

        month_orders = [o for o in orders if o.get("created_at", datetime.min) >= month_start]
        monthly_stats.append({
            "month": month_start.strftime("%B %Y"),
            "orders": len(month_orders),
            "spent": sum(o.get("total_amount", 0) for o in month_orders),
            "savings": sum(o.get("savings", 0) for o in month_orders)
        })

    return {
        "overview": {
            "total_orders": total_orders,
            "total_spent": round(total_spent, 2),
            "total_savings": round(total_savings, 2),
            "total_credits_used": total_credits_used,
            "current_credits": current_user["credits"],
            "subscription": current_user["subscription"]
        },
        "recent_orders": [
            {
                "id": o["id"],
                "date": o["created_at"].isoformat() if isinstance(o.get("created_at"), datetime) else o.get("created_at"),
                "amount": o.get("total_amount", 0),
                "savings": o.get("savings", 0),
                "status": o.get("status", "pending"),
                "items_count": len(o.get("items", []))
            }
            for o in orders[:10]
        ],
        "credits_history": [
            {
                "id": c.get("id"),
                "type": c.get("type"),  # "added" or "used"
                "amount": c.get("amount"),
                "description": c.get("description"),
                "date": c["created_at"].isoformat() if isinstance(c.get("created_at"), datetime) else c.get("created_at")
            }
            for c in credits_history
        ],
        "monthly_stats": monthly_stats[:6]
    }


@users_core_router.get("/users/orders", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20
):
    """Get user's orders."""
    db = get_database()
    orders = await db.orders.find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return [OrderResponse(**o) for o in orders]
