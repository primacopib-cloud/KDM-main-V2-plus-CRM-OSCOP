from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from db import set_database as set_shared_database
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import uuid

# Local imports
from models import (
    UserCreate, UserLogin, UserResponse, UserInDB, Token,
    QuoteRequestCreate, QuoteRequestResponse, QuoteRequestInDB,
    SubscriptionUpdate, CreditsAdd, CreditsResponse,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetToken,
    OrderResponse, OrderInDB, AdminStats, UserListResponse,
    # Phase 1 & 2: New models
    UserRole, OrgStatus, SubscriptionStatus, KdmAccessStatus,
    Zone, ZoneEntitlement, OrgZonesUpdate,
    OrganizationCreate, OrganizationResponse, OrganizationInDB, OrgDecision,
    NotificationType, Notification, NotificationResponse, NotificationsListResponse,
    UserWithRoleResponse
)
from auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user_id
)
from pdf_generator import generate_offer_pdf
from subscriptions import (
    SUBSCRIPTION_PLANS, DEFAULT_CREDITS,
    seed_subscription_plans, get_active_plans_from_db, get_plan_default_credits
)
from email_service import (
    send_password_reset_email, send_contact_notification, 
    send_welcome_email, is_email_configured
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]
set_shared_database(db)

# Create the main app
app = FastAPI(title="Centrale d'achats B2B ESS API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== HELPER FUNCTIONS ==============

async def get_user_by_email(email: str):
    """Get user by email from database."""
    user = await db.users.find_one({"email": email})
    return user


async def get_user_by_id(user_id: str):
    """Get user by ID from database."""
    user = await db.users.find_one({"id": user_id})
    return user


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Get the current user from database."""
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return user


# ============== PUBLIC ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "Centrale d'achats B2B ESS - API", "status": "active"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============== AUTHENTICATION ROUTES ==============

@api_router.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user/company."""
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cet email existe déjà"
        )
    
    # Create user
    plan = user_data.plan.value if user_data.plan else "ess-acces-pro"
    user_in_db = UserInDB(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        company_name=user_data.company_name,
        siret=user_data.siret,
        contact_name=user_data.contact_name,
        phone=user_data.phone,
        subscription=plan,
        credits=await get_plan_default_credits(db, plan)
    )
    
    # Insert into database
    await db.users.insert_one(user_in_db.dict())
    
    logger.info(f"New user registered: {user_data.email}")
    
    return {
        "id": user_in_db.id,
        "email": user_in_db.email,
        "company_name": user_in_db.company_name,
        "message": "Compte créé avec succès"
    }


@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login and get access token."""
    # Find user
    user = await get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user["id"]})
    
    logger.info(f"User logged in: {credentials.email}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            company_name=user["company_name"],
            siret=user["siret"],
            contact_name=user["contact_name"],
            phone=user["phone"],
            subscription=user["subscription"],
            credits=user["credits"],
            is_admin=user.get("is_admin", False),
            created_at=user["created_at"]
        )
    )


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current logged in user."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        company_name=current_user["company_name"],
        siret=current_user["siret"],
        contact_name=current_user["contact_name"],
        phone=current_user["phone"],
        subscription=current_user["subscription"],
        credits=current_user["credits"],
        is_admin=current_user.get("is_admin", False),
        created_at=current_user["created_at"]
    )


# ============== QUOTE REQUEST ROUTES ==============

@api_router.post("/quotes", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_quote_request(quote_data: QuoteRequestCreate):
    """Create a new quote request."""
    quote_in_db = QuoteRequestInDB(
        company=quote_data.company,
        contact_name=quote_data.contact_name,
        email=quote_data.email,
        phone=quote_data.phone,
        plan=quote_data.plan,
        message=quote_data.message
    )
    
    # Insert into database
    await db.quote_requests.insert_one(quote_in_db.dict())
    
    logger.info(f"New quote request from: {quote_data.email}")
    
    # Create notification for admins (Phase 1)
    notification = {
        "id": str(uuid.uuid4()),
        "type": "new_quote",
        "title": "Nouvelle demande de devis",
        "message": f"{quote_data.company} - {quote_data.contact_name} demande un devis",
        "data": {
            "quote_id": quote_in_db.id,
            "company": quote_data.company,
            "email": quote_data.email,
            "plan": quote_data.plan
        },
        "target_roles": ["oscop_super_admin", "oscop_compliance_admin", "kdm_b2b_admin"],
        "target_user_id": None,
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "id": quote_in_db.id,
        "company": quote_in_db.company,
        "email": quote_in_db.email,
        "status": quote_in_db.status,
        "created_at": quote_in_db.created_at,
        "message": "Demande de devis envoyée avec succès"
    }


@api_router.get("/quotes", response_model=List[QuoteRequestResponse])
async def get_quote_requests(current_user: dict = Depends(get_current_user)):
    """Get all quote requests (admin only)."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    quotes = await db.quote_requests.find().sort("created_at", -1).to_list(100)
    return [QuoteRequestResponse(**quote) for quote in quotes]


# ============== PDF DOWNLOAD ROUTE ==============

@api_router.get("/download-offer")
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
        "description": "Centrale d'achats B2B ESS — Partenariat (séparation stricte des rôles)",
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

@api_router.get("/documents")
async def list_legal_documents():
    """List available legal documents."""
    return {"documents": list(LEGAL_DOCUMENTS.values())}


@api_router.get("/documents/{doc_id}")
async def get_document_info(doc_id: str):
    """Get legal document info."""
    doc = LEGAL_DOCUMENTS.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return doc


# ============== SUBSCRIPTION ROUTES ==============

@api_router.get("/subscriptions")
async def get_subscriptions():
    """Get available subscription plans (loaded from DB, fallback to hardcoded)."""
    plans = await get_active_plans_from_db(db)
    return {"plans": plans}


@api_router.put("/users/subscription", response_model=dict)
async def update_subscription(
    update_data: SubscriptionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user subscription."""
    new_plan = update_data.plan.value
    
    # Update in database
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

@api_router.post("/credits/add", response_model=CreditsResponse)
async def add_credits(
    credits_data: CreditsAdd,
    current_user: dict = Depends(get_current_user)
):
    """Add credits to user wallet."""
    new_credits = current_user["credits"] + credits_data.amount
    
    # Update in database
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "credits": new_credits,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    logger.info(f"User {current_user['email']} added {credits_data.amount} credits")
    
    return CreditsResponse(
        credits=new_credits,
        message=f"{credits_data.amount} crédits ajoutés avec succès"
    )


@api_router.get("/credits", response_model=dict)
async def get_credits(current_user: dict = Depends(get_current_user)):
    """Get user credits."""
    return {"credits": current_user["credits"]}


# ============== PASSWORD RESET ROUTES ==============

@api_router.post("/auth/forgot-password", response_model=dict)
async def forgot_password(request: PasswordResetRequest):
    """Request password reset email."""
    user = await get_user_by_email(request.email)
    
    # Always return success to avoid email enumeration
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation."}
    
    # Create reset token (expires in 1 hour)
    reset_token = PasswordResetToken(
        user_id=user["id"],
        email=user["email"],
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    # Save to database
    await db.password_resets.insert_one(reset_token.dict())
    
    # Send email
    try:
        send_password_reset_email(
            to=user["email"],
            reset_token=reset_token.token,
            user_name=user["contact_name"]
        )
        logger.info(f"Password reset email sent to: {request.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
    
    return {"message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation."}


@api_router.post("/auth/reset-password", response_model=dict)
async def reset_password(request: PasswordResetConfirm):
    """Reset password using token."""
    # Find valid token
    token_doc = await db.password_resets.find_one({
        "token": request.token,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not token_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation invalide ou expiré"
        )
    
    # Update password
    new_hash = get_password_hash(request.new_password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
    )
    
    # Mark token as used
    await db.password_resets.update_one(
        {"id": token_doc["id"]},
        {"$set": {"used": True}}
    )
    
    logger.info(f"Password reset successful for user: {token_doc['email']}")
    
    return {"message": "Mot de passe réinitialisé avec succès"}


# ============== USER STATISTICS ROUTES ==============

@api_router.get("/users/stats", response_model=dict)
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics: orders, savings, credits history."""
    user_id = current_user["id"]
    
    # Get orders
    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    
    # Calculate stats
    total_orders = len(orders)
    total_spent = sum(o.get("total_amount", 0) for o in orders)
    total_savings = sum(o.get("savings", 0) for o in orders)
    total_credits_used = sum(o.get("credits_used", 0) for o in orders)
    
    # Get credits history
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


@api_router.get("/users/orders", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20
):
    """Get user's orders."""
    orders = await db.orders.find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return [OrderResponse(**o) for o in orders]


# ============== ADMIN ROUTES ==============

async def check_admin(current_user: dict):
    """Check if user is admin."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    return current_user


@api_router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard statistics."""
    await check_admin(current_user)
    
    # Count totals
    total_users = await db.users.count_documents({})
    total_quotes = await db.quote_requests.count_documents({})
    total_orders = await db.orders.count_documents({})
    
    # Sum credits
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$credits"}}}]
    credits_result = await db.users.aggregate(pipeline).to_list(1)
    total_credits = credits_result[0]["total"] if credits_result else 0
    
    # Quotes by status
    quotes_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    quotes_by_status_list = await db.quote_requests.aggregate(quotes_pipeline).to_list(10)
    quotes_by_status = {q["_id"]: q["count"] for q in quotes_by_status_list}
    
    # This month stats
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = await db.users.count_documents({"created_at": {"$gte": month_start}})
    new_quotes_this_month = await db.quote_requests.count_documents({"created_at": {"$gte": month_start}})
    
    return AdminStats(
        total_users=total_users,
        total_quotes=total_quotes,
        total_orders=total_orders,
        total_credits_distributed=total_credits,
        quotes_by_status=quotes_by_status,
        new_users_this_month=new_users_this_month,
        new_quotes_this_month=new_quotes_this_month
    )


@api_router.get("/admin/users", response_model=UserListResponse)
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    per_page: int = 20,
    search: str = None
):
    """Get all users (admin only)."""
    await check_admin(current_user)
    
    query = {}
    if search:
        query = {
            "$or": [
                {"email": {"$regex": search, "$options": "i"}},
                {"company_name": {"$regex": search, "$options": "i"}},
                {"contact_name": {"$regex": search, "$options": "i"}}
            ]
        }
    
    total = await db.users.count_documents(query)
    skip = (page - 1) * per_page
    
    users = await db.users.find(query).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)
    
    return UserListResponse(
        users=[UserResponse(
            id=u["id"],
            email=u["email"],
            company_name=u["company_name"],
            siret=u["siret"],
            contact_name=u["contact_name"],
            phone=u["phone"],
            subscription=u["subscription"],
            credits=u["credits"],
            is_admin=u.get("is_admin", False),
            created_at=u["created_at"]
        ) for u in users],
        total=total,
        page=page,
        per_page=per_page
    )


@api_router.get("/admin/quotes", response_model=List[QuoteRequestResponse])
async def get_all_quotes(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all quote requests (admin only)."""
    await check_admin(current_user)
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    quotes = await db.quote_requests.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [QuoteRequestResponse(**q) for q in quotes]


@api_router.put("/admin/quotes/{quote_id}/status", response_model=dict)
async def update_quote_status(
    quote_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update quote request status (admin only)."""
    await check_admin(current_user)
    
    result = await db.quote_requests.update_one(
        {"id": quote_id},
        {"$set": {"status": new_status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande non trouvée"
        )
    
    return {"message": "Statut mis à jour", "status": new_status}


@api_router.put("/admin/users/{user_id}/credits", response_model=dict)
async def admin_update_credits(
    user_id: str,
    amount: int,
    current_user: dict = Depends(get_current_user)
):
    """Update user credits (admin only)."""
    await check_admin(current_user)
    
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    new_credits = user["credits"] + amount
    if new_credits < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les crédits ne peuvent pas être négatifs"
        )
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_credits, "updated_at": datetime.utcnow()}}
    )
    
    # Log credits history
    await db.credits_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "added" if amount > 0 else "used",
        "amount": abs(amount),
        "description": f"Ajusté par admin ({current_user['email']})",
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"Admin {current_user['email']} updated credits for {user['email']}: {amount}")
    
    return {"credits": new_credits, "message": f"Crédits mis à jour: {'+' if amount > 0 else ''}{amount}"}


# ============== PHASE 1: NOTIFICATIONS ROUTES ==============

async def create_notification(
    notification_type: str,
    title: str,
    message: str,
    target_roles: List[str] = None,
    target_user_id: str = None,
    data: dict = None
):
    """Helper to create a notification."""
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "target_roles": target_roles or ["oscop_super_admin", "oscop_compliance_admin"],
        "target_user_id": target_user_id,
        "is_read": False,
        "read_by": [],
        "created_at": datetime.utcnow()
    }
    await db.notifications.insert_one(notification)
    logger.info(f"Notification created: {notification_type} - {title}")
    return notification


@api_router.get("/notifications", response_model=NotificationsListResponse)
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    unread_only: bool = False
):
    """Get notifications for current user (admin only or targeted)."""
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)
    
    # Build query - admins see role-targeted notifications, users see user-targeted
    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}
    
    if unread_only:
        query["read_by"] = {"$ne": user_id}
    
    notifications = await db.notifications.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Count unread
    unread_query = query.copy()
    unread_query["read_by"] = {"$ne": user_id}
    unread_count = await db.notifications.count_documents(unread_query)
    
    return NotificationsListResponse(
        notifications=[
            NotificationResponse(
                id=n["id"],
                type=n["type"],
                title=n["title"],
                message=n["message"],
                data=n.get("data", {}),
                is_read=user_id in n.get("read_by", []),
                created_at=n["created_at"]
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=len(notifications)
    )


@api_router.post("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    user_id = current_user["id"]
    
    result = await db.notifications.update_one(
        {"id": notification_id},
        {"$addToSet": {"read_by": user_id}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    return {"message": "Notification marquée comme lue"}


@api_router.post("/notifications/read-all", response_model=dict)
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read for current user."""
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)
    
    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}
    
    await db.notifications.update_many(query, {"$addToSet": {"read_by": user_id}})
    
    return {"message": "Toutes les notifications marquées comme lues"}


@api_router.get("/notifications/poll", response_model=dict)
async def poll_notifications(
    current_user: dict = Depends(get_current_user),
    since: str = None  # ISO timestamp
):
    """Poll for new notifications (for 30s polling)."""
    user_id = current_user["id"]
    user_role = current_user.get("role", "customer_org_buyer")
    is_admin = current_user.get("is_admin", False)
    
    # Build query
    if is_admin:
        query = {
            "$or": [
                {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
                {"target_user_id": user_id}
            ]
        }
    else:
        query = {"target_user_id": user_id}
    
    # Filter by timestamp if provided
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query["created_at"] = {"$gt": since_dt}
        except:
            pass
    
    # Get new notifications
    new_notifications = await db.notifications.find(query).sort("created_at", -1).limit(10).to_list(10)
    
    # Count total unread
    unread_query = {
        "$or": [
            {"target_roles": {"$in": [user_role, "oscop_super_admin"]}},
            {"target_user_id": user_id}
        ] if is_admin else {"target_user_id": user_id},
        "read_by": {"$ne": user_id}
    }
    unread_count = await db.notifications.count_documents(unread_query)
    
    return {
        "has_new": len(new_notifications) > 0,
        "unread_count": unread_count,
        "new_notifications": [
            {
                "id": n["id"],
                "type": n["type"],
                "title": n["title"],
                "message": n["message"],
                "created_at": n["created_at"].isoformat()
            }
            for n in new_notifications
        ],
        "server_time": datetime.utcnow().isoformat()
    }


# ============== PHASE 2: ZONES ROUTES ==============

# Default zones data
DEFAULT_ZONES = [
    {"code": "971", "name": "Guadeloupe", "country": "FR"},
    {"code": "972", "name": "Martinique", "country": "FR"},
    {"code": "973", "name": "Guyane", "country": "FR"},
    {"code": "974", "name": "La Réunion", "country": "FR"},
    {"code": "976", "name": "Mayotte", "country": "FR"},
    {"code": "75", "name": "Île-de-France", "country": "FR"},
]


@api_router.get("/zones", response_model=List[Zone])
async def get_zones():
    """Get all available zones."""
    zones = await db.zones.find({"is_active": True}).to_list(100)
    
    # Initialize zones if empty
    if not zones:
        for z in DEFAULT_ZONES:
            zone_doc = {
                "id": str(uuid.uuid4()),
                "code": z["code"],
                "name": z["name"],
                "country": z["country"],
                "is_active": True,
                "created_at": datetime.utcnow()
            }
            await db.zones.insert_one(zone_doc)
        zones = await db.zones.find({"is_active": True}).to_list(100)
    
    return [Zone(**z) for z in zones]


@api_router.post("/zones", response_model=Zone)
async def create_zone(
    zone: Zone,
    current_user: dict = Depends(get_current_user)
):
    """Create a new zone (admin only)."""
    await check_admin(current_user)
    
    zone_doc = zone.dict()
    zone_doc["id"] = str(uuid.uuid4())
    zone_doc["created_at"] = datetime.utcnow()
    
    await db.zones.insert_one(zone_doc)
    return Zone(**zone_doc)


# ============== PHASE 2: ORGANIZATIONS ROUTES ==============

@api_router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate, current_user: dict = Depends(get_current_user)):
    """Create a new organization (B2B application)."""
    
    # Check if org with same SIRET exists
    existing = await db.organizations.find_one({"siret": org.siret})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une organisation avec ce SIRET existe déjà"
        )
    
    # Create organization
    org_doc = OrganizationInDB(
        legal_name=org.legal_name,
        siret=org.siret,
        contact_email=org.contact_email,
        contact_name=org.contact_name,
        contact_phone=org.contact_phone,
        territory=org.territory,
        address=org.address,
        owner_user_id=current_user["id"],
        documents=org.documents or []
    ).dict()
    
    await db.organizations.insert_one(org_doc)
    
    # Update user with org_id
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"org_id": org_doc["id"], "role": UserRole.CUSTOMER_ORG_OWNER.value}}
    )
    
    logger.info(f"Organization created: {org.legal_name} (SIRET: {org.siret})")
    
    return OrganizationResponse(**org_doc)


@api_router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get organization details."""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    # Check access
    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return OrganizationResponse(**org)


@api_router.post("/organizations/{org_id}/submit", response_model=dict)
async def submit_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    """Submit organization for review."""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if org.get("owner_user_id") != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if org["status"] != OrgStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="L'organisation n'est pas en brouillon")
    
    # Transition: DRAFT → SUBMITTED → PENDING_REVIEW
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {"status": OrgStatus.PENDING_REVIEW.value, "updated_at": datetime.utcnow()}}
    )
    
    # Create notification for admins
    await create_notification(
        notification_type=NotificationType.ORG_SUBMITTED.value,
        title="Nouvelle demande d'adhésion",
        message=f"{org['legal_name']} a soumis une demande d'adhésion B2B",
        target_roles=["oscop_super_admin", "oscop_compliance_admin"],
        data={"org_id": org_id, "legal_name": org["legal_name"], "siret": org["siret"]}
    )
    
    logger.info(f"Organization submitted for review: {org['legal_name']}")
    
    return {"message": "Dossier soumis pour validation", "status": OrgStatus.PENDING_REVIEW.value}


@api_router.post("/organizations/{org_id}/decision", response_model=dict)
async def decide_organization(
    org_id: str,
    decision: OrgDecision,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject organization (compliance admin only)."""
    await check_admin(current_user)
    
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if org["status"] != OrgStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=400, detail="L'organisation n'est pas en attente de validation")
    
    if decision.decision == "approve":
        new_status = OrgStatus.APPROVED.value
        notification_type = NotificationType.ORG_APPROVED.value
        notification_title = "Demande approuvée"
        notification_message = f"Votre demande d'adhésion pour {org['legal_name']} a été approuvée !"
        
        # Enable KDM access and activate subscription
        await db.organizations.update_one(
            {"id": org_id},
            {"$set": {
                "status": new_status,
                "subscription_status": SubscriptionStatus.ACTIVE.value,
                "kdm_access_status": KdmAccessStatus.ACCESS_ENABLED.value,
                "credits": 100,  # Initial credits
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Add default zone entitlement
        zone = await db.zones.find_one({"code": org["territory"]})
        if zone:
            await db.organizations.update_one(
                {"id": org_id},
                {"$push": {"zone_entitlements": {
                    "zone_id": zone["id"],
                    "zone_code": zone["code"],
                    "zone_name": zone["name"],
                    "included_in_plan": True,
                    "is_addon": False,
                    "activated_at": datetime.utcnow().isoformat()
                }}}
            )
    else:
        new_status = OrgStatus.REJECTED.value
        notification_type = NotificationType.ORG_REJECTED.value
        notification_title = "Demande refusée"
        notification_message = f"Votre demande d'adhésion pour {org['legal_name']} a été refusée. Raison: {decision.comment or decision.reason_code}"
        
        await db.organizations.update_one(
            {"id": org_id},
            {"$set": {
                "status": new_status,
                "rejection_reason": decision.comment or decision.reason_code,
                "updated_at": datetime.utcnow()
            }}
        )
    
    # Notify organization owner
    await create_notification(
        notification_type=notification_type,
        title=notification_title,
        message=notification_message,
        target_user_id=org.get("owner_user_id"),
        data={"org_id": org_id, "decision": decision.decision}
    )
    
    logger.info(f"Organization {decision.decision}d: {org['legal_name']} by {current_user['email']}")
    
    return {
        "message": f"Organisation {'approuvée' if decision.decision == 'approve' else 'refusée'}",
        "status": new_status
    }


@api_router.post("/organizations/{org_id}/suspend", response_model=dict)
async def suspend_organization(
    org_id: str,
    reason: str = "compliance",
    current_user: dict = Depends(get_current_user)
):
    """Suspend an organization (admin only)."""
    await check_admin(current_user)
    
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if org["status"] not in [OrgStatus.APPROVED.value]:
        raise HTTPException(status_code=400, detail="Impossible de suspendre cette organisation")
    
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {
            "status": OrgStatus.SUSPENDED.value,
            "kdm_access_status": KdmAccessStatus.ACCESS_DISABLED.value,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Notify owner
    await create_notification(
        notification_type="org_suspended",
        title="Compte suspendu",
        message=f"Le compte {org['legal_name']} a été suspendu. Raison: {reason}",
        target_user_id=org.get("owner_user_id"),
        data={"org_id": org_id, "reason": reason}
    )
    
    return {"message": "Organisation suspendue", "status": OrgStatus.SUSPENDED.value}


@api_router.get("/organizations/{org_id}/zones", response_model=List[ZoneEntitlement])
async def get_org_zones(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get zones for organization."""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return [ZoneEntitlement(**z) for z in org.get("zone_entitlements", [])]


@api_router.post("/organizations/{org_id}/zones", response_model=dict)
async def add_org_zone(
    org_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Add a zone to organization (as addon)."""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone non trouvée")
    
    # Check if already entitled
    existing = [z for z in org.get("zone_entitlements", []) if z.get("zone_id") == zone_id]
    if existing:
        raise HTTPException(status_code=400, detail="Zone déjà ajoutée")
    
    entitlement = {
        "zone_id": zone["id"],
        "zone_code": zone["code"],
        "zone_name": zone["name"],
        "included_in_plan": False,
        "is_addon": True,
        "activated_at": datetime.utcnow().isoformat()
    }
    
    await db.organizations.update_one(
        {"id": org_id},
        {"$push": {"zone_entitlements": entitlement}}
    )
    
    return {"message": f"Zone {zone['name']} ajoutée", "zone": entitlement}


@api_router.post("/organizations/{org_id}/select-zone", response_model=dict)
async def select_zone(
    org_id: str,
    zone_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Select active zone for organization."""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    if not current_user.get("is_admin") and org.get("owner_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Check if zone is entitled
    entitled_zones = [z.get("zone_code") for z in org.get("zone_entitlements", [])]
    if zone_code not in entitled_zones:
        raise HTTPException(status_code=403, detail="Zone non autorisée pour cette organisation")
    
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {"selected_zone": zone_code, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": f"Zone {zone_code} sélectionnée", "selected_zone": zone_code}


@api_router.get("/admin/organizations", response_model=List[OrganizationResponse])
async def get_all_organizations(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all organizations (admin only)."""
    await check_admin(current_user)
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    orgs = await db.organizations.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [OrganizationResponse(**o) for o in orgs]


# Include the router in the main app
app.include_router(api_router)

# Import and include v2 routes
from routes_v2 import api_v2_router, set_database
set_database(db)
app.include_router(api_v2_router)

# Import and include catalog routes
from routes_catalog import catalog_router, orders_router, set_catalog_database
set_catalog_database(db)
app.include_router(catalog_router)
app.include_router(orders_router)

# Import and include GED (Document Management) routes
from routes_ged import ged_router, set_ged_database
set_ged_database(db)
app.include_router(ged_router)

# Import and include Export routes
from routes_export import export_router, set_export_database
set_export_database(db)
app.include_router(export_router)

# Import and include Payment routes
from routes_payment import payment_router, set_payment_database
set_payment_database(db)
app.include_router(payment_router)

# Import and include SMS Signature routes
from routes_signature import signature_router, set_signature_database
set_signature_database(db)
app.include_router(signature_router)

# Import and include Super Admin routes
from routes_superadmin import superadmin_router, set_superadmin_database
set_superadmin_database(db)
app.include_router(superadmin_router)

# Import and include Preparation routes (Zone-based preparation options)
from routes_preparation import preparation_router, set_preparation_database
set_preparation_database(db)
app.include_router(preparation_router)

# Import and include Admin Zones routes (CRUD zones + options)
from routes_admin_zones import admin_zones_router, set_admin_zones_database
set_admin_zones_database(db)
app.include_router(admin_zones_router)

# Import and include B2B routes (checkout + prep options)
from routes_b2b import b2b_router, set_b2b_database
set_b2b_database(db)
app.include_router(b2b_router)

# Import and include Vendor routes
from routes_vendor import vendor_router, set_vendor_database
set_vendor_database(db)
app.include_router(vendor_router)

# Alias routes for admin compatibility
@api_router.get("/admin/products/pending")
async def admin_products_pending_alias():
    """Alias for /api/vendor/admin/products/pending"""
    from routes_vendor import admin_list_pending_products
    return await admin_list_pending_products()

# Import and include OPA Bundle routes
from routes_opa_bundle import opa_bundle_router, set_opa_bundle_database
set_opa_bundle_database(db)
app.include_router(opa_bundle_router)

# Import and include Catalog Admin routes
from routes_catalog_admin import catalog_admin_router, set_catalog_admin_database
set_catalog_admin_database(db)
app.include_router(catalog_admin_router)

# Import and include Invoices routes
from routes_invoices import invoices_router, set_invoices_database
set_invoices_database(db)
app.include_router(invoices_router)

# Import and include Checkout routes
from routes_checkout import checkout_router, set_checkout_database
set_checkout_database(db)
app.include_router(checkout_router)

# Import and include PDF routes
from routes_pdf import pdf_router, set_pdf_database
set_pdf_database(db)
app.include_router(pdf_router)

# Import and include WebSocket routes
from routes_websockets import websocket_router, set_websocket_database
set_websocket_database(db)
app.include_router(websocket_router)

# Import and include LOGI'SCOP routes
from routes_logiscop import logiscop_router, set_logiscop_database
set_logiscop_database(db)
app.include_router(logiscop_router)

# Import and include V1 LOGI'SCOP routes (OpenAPI v1 endpoints)
from routes_v1_logiscop import v1_logiscop_router, set_v1_logiscop_database
set_v1_logiscop_database(db)
app.include_router(v1_logiscop_router)

# Import and include Contracts routes
from routes_contracts import contracts_router, set_contracts_database
set_contracts_database(db)
app.include_router(contracts_router)

# Import and include POD (Proof of Delivery) routes
from routes_pod import pod_router, set_pod_database
set_pod_database(db)
app.include_router(pod_router)

# Import and include ESS Route (Tournées Mutualisées) routes
from routes_ess import ess_router, set_ess_database
set_ess_database(db)
app.include_router(ess_router)

# Import and include Admin ESS Routes (CRUD policies, rules, capacity)
from routes_admin_ess import admin_ess_router, set_admin_ess_database
set_admin_ess_database(db)
app.include_router(admin_ess_router)

# Import and include User Preferences Routes (shortcuts)
from routes_user_prefs import user_prefs_router, set_user_prefs_database
set_user_prefs_database(db)
app.include_router(user_prefs_router, prefix="/api")

# Import and include Notifications History Routes
from routes_notifications_history import notifications_history_router, set_notifications_history_database
set_notifications_history_database(db)
app.include_router(notifications_history_router, prefix="/api")

# Import and include Shopping Lists Routes
from routes_shopping_lists import shopping_lists_router, set_shopping_lists_database
set_shopping_lists_database(db)
app.include_router(shopping_lists_router, prefix="/api")

# Import and include Super Admin Plans & Credits Routes
from routes_admin_plans import admin_plans_router, set_admin_plans_database
set_admin_plans_database(db)
app.include_router(admin_plans_router, prefix="/api")


# Import and include LOLODRIVE by O'SCOP routes (PASS Vie Chère, UC, Lolo Points, Events, POS)
from routes_lolodrive_oscoop import lolodrive_router, set_lolodrive_database, ensure_lolodrive_indexes
set_lolodrive_database(db)
app.include_router(lolodrive_router)

# Import and include LOLODRIVE Stripe Checkout (hosted page) for PASS/Recharge/Order
from routes_lolodrive_checkout import (
    checkout_router as lolodrive_checkout_router,
    webhook_router as lolodrive_webhook_router,
    set_checkout_database as set_lolo_checkout_db,
    setup_checkout_indexes,
)
set_lolo_checkout_db(db)
app.include_router(lolodrive_checkout_router)
app.include_router(lolodrive_webhook_router)

# Import and include CRM O'SCOP Bridge routes (contacts, organisations, opportunités, dossiers, impact)
from routes_crm_oscoop import crm_router, set_crm_database, ensure_crm_indexes
set_crm_database(db)
app.include_router(crm_router)

# Import and include Emergent OAuth (Google social login via Emergent platform)
from routes_emergent_auth import router as emergent_auth_router, set_emergent_auth_database, setup_emergent_indexes
set_emergent_auth_database(db)
app.include_router(emergent_auth_router)

# Native Google OAuth (KDMARCHE own Google Cloud project — branding KDMARCHE)
from routes_google_auth import router as google_auth_router, set_google_auth_database, setup_google_auth_indexes
set_google_auth_database(db)
app.include_router(google_auth_router)

# Brevo transactional webhooks (delivered/bounced metrics)
from routes_brevo_webhook import router as brevo_webhook_router, set_brevo_webhook_database, setup_brevo_webhook_indexes
set_brevo_webhook_database(db)
app.include_router(brevo_webhook_router)

# PASS lifecycle (auto-renew, referrals)
from routes_pass_lifecycle import router as pass_lifecycle_router, set_pass_lifecycle_database, setup_pass_lifecycle_indexes
set_pass_lifecycle_database(db)
app.include_router(pass_lifecycle_router)

# PASS Stripe Subscriptions (real recurring rebill)
from routes_pass_subscription import router as pass_subscription_router, set_pass_subscription_database, setup_pass_subscription_indexes
set_pass_subscription_database(db)
app.include_router(pass_subscription_router)

# Background scheduler (PASS J-3 reminders every 6h)
from scheduler import set_scheduler_database, start_scheduler, stop_scheduler
set_scheduler_database(db)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    """Create indexes on startup."""
    # Create unique index on email
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.quote_requests.create_index("id", unique=True)
    # Phase 1 & 2: Additional indexes
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("created_at")
    await db.organizations.create_index("id", unique=True)
    await db.organizations.create_index("siret", unique=True)
    await db.zones.create_index("id", unique=True)
    await db.zones.create_index("code", unique=True)
    
    # v2 Schema indexes
    await db.orgs.create_index("id", unique=True)
    await db.orgs.create_index([("registration_country", 1), ("registration_id", 1)], unique=True)
    await db.users_v2.create_index("id", unique=True)
    await db.users_v2.create_index("email", unique=True)
    await db.org_memberships.create_index("id", unique=True)
    await db.org_memberships.create_index([("org_id", 1), ("user_id", 1)], unique=True)
    await db.b2b_applications.create_index("id", unique=True)
    await db.b2b_applications.create_index("org_id")
    await db.application_documents.create_index("id", unique=True)
    await db.plans.create_index("id", unique=True)
    await db.plans.create_index("code", unique=True)
    await db.subscriptions.create_index("id", unique=True)
    await db.subscriptions.create_index("org_id")
    await db.billing_invoices.create_index("id", unique=True)
    await db.wallets.create_index("org_id", unique=True)
    await db.wallet_ledger.create_index("id", unique=True)
    await db.wallet_ledger.create_index([("org_id", 1), ("correlation_id", 1)], unique=True)
    await db.zones_v2.create_index("id", unique=True)
    await db.zones_v2.create_index("code", unique=True)
    await db.org_zone_entitlements.create_index("id", unique=True)
    await db.org_zone_entitlements.create_index([("org_id", 1), ("zone_id", 1)], unique=True)
    await db.partner_accounts.create_index("id", unique=True)
    await db.partner_accounts.create_index([("org_id", 1), ("partner", 1)], unique=True)
    await db.audit_log.create_index("id", unique=True)
    await db.audit_log.create_index([("org_id", 1), ("created_at", -1)])
    await db.outbox_events.create_index("id", unique=True)
    
    # Catalog indexes
    await db.categories.create_index("id", unique=True)
    await db.categories.create_index("code", unique=True)
    await db.products.create_index("id", unique=True)
    await db.products.create_index("sku", unique=True)
    await db.products.create_index("category_id")
    await db.products.create_index([("name", "text"), ("description", "text")])
    await db.zone_prices.create_index("id", unique=True)
    await db.zone_prices.create_index([("product_id", 1), ("zone_code", 1)], unique=True)
    await db.zone_stocks.create_index("id", unique=True)
    await db.zone_stocks.create_index([("product_id", 1), ("zone_code", 1)], unique=True)
    await db.pickup_locations.create_index("id", unique=True)
    await db.pickup_locations.create_index("zone_code")
    await db.carts.create_index("id", unique=True)
    await db.carts.create_index([("org_id", 1), ("zone_code", 1), ("status", 1)])
    await db.orders.create_index("id", unique=True)
    await db.orders.create_index("order_number", unique=True)
    await db.orders.create_index("org_id")
    
    # Preparation options indexes
    await db.zone_preparation_options.create_index("id", unique=True)
    await db.zone_preparation_options.create_index([("zone_code", 1), ("preparation_type", 1)])
    await db.zone_preparation_options.create_index([("zone_code", 1), ("code", 1)])
    
    # OPA cache index
    await db.kdm_opa_cache.create_index("cache_key", unique=True)
    
    # Vendor indexes
    await db.vendors.create_index("id", unique=True)
    await db.vendors.create_index("email", unique=True)
    await db.vendors.create_index("siret", unique=True)
    await db.vendor_products.create_index("id", unique=True)
    await db.vendor_products.create_index([("vendor_id", 1), ("sku", 1)], unique=True)
    
    # Super Admin: subscription plans, options, credits
    await db.subscription_plans.create_index("id", unique=True)
    await db.subscription_plans.create_index("slug", unique=True)
    await db.plan_options.create_index("id", unique=True)
    await db.credit_history.create_index("id", unique=True)
    await db.credit_history.create_index([("user_id", 1), ("created_at", -1)])

    # LOLODRIVE by O'SCOP indexes
    try:
        await ensure_lolodrive_indexes(db)
        logger.info("LOLODRIVE indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create LOLODRIVE indexes: {e}")

    # Stripe Checkout indexes (payment_transactions)
    try:
        await setup_checkout_indexes(db)
        logger.info("LOLODRIVE Checkout indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create LOLODRIVE Checkout indexes: {e}")

    # CRM O'SCOP Bridge indexes
    try:
        await ensure_crm_indexes(db)
        logger.info("CRM O'SCOP indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create CRM O'SCOP indexes: {e}")

    # Emergent OAuth indexes + start background scheduler
    try:
        await setup_emergent_indexes(db)
        logger.info("Emergent OAuth indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Emergent OAuth indexes: {e}")
    try:
        await setup_google_auth_indexes(db)
        logger.info("Native Google OAuth indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Google OAuth indexes: {e}")
    try:
        await setup_brevo_webhook_indexes(db)
        logger.info("Brevo webhook indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Brevo webhook indexes: {e}")
    try:
        await setup_pass_lifecycle_indexes(db)
        logger.info("PASS lifecycle indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create PASS lifecycle indexes: {e}")
    try:
        await setup_pass_subscription_indexes(db)
        logger.info("PASS subscription indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create PASS subscription indexes: {e}")
    try:
        start_scheduler()
    except Exception as e:
        logger.warning(f"Could not start scheduler: {e}")

    # Seed default subscription plans if missing
    try:
        seeded = await seed_subscription_plans(db)
        if seeded:
            logger.info(f"Seeded {seeded} default subscription plan(s)")
    except Exception as e:
        logger.warning(f"Could not seed default subscription plans: {e}")

    logger.info("Database indexes created (v1 + v2 + catalog + preparation + vendor + OPA + admin_plans)")


@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        stop_scheduler()
    except Exception:
        pass
    client.close()
