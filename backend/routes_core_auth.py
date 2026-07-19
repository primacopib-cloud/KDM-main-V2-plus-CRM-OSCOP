"""Core public + authentication + password reset routes (split from server.py)."""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status, Response

from models import (
    UserCreate, UserLogin, UserResponse, UserInDB, Token,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetToken,
)
from pydantic import BaseModel
from auth import get_password_hash, verify_password, create_access_token, set_auth_cookie, clear_auth_cookie
from subscriptions import get_plan_default_credits
from email_service import send_password_reset_email
from db import get_database
from core_deps import get_user_by_email, get_current_user

logger = logging.getLogger(__name__)

auth_core_router = APIRouter(prefix="/api")


# ============== PUBLIC ROUTES ==============

@auth_core_router.get("/")
async def root():
    return {"message": "Communityplace B2B ESS - API", "status": "active"}


@auth_core_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============== AUTHENTICATION ROUTES ==============

@auth_core_router.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user/company."""
    db = get_database()
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cet email existe déjà"
        )

    plan = user_data.plan.value if user_data.plan else "ess-acces-pro"
    account_type = "vendor" if user_data.account_type == "vendor" else "buyer"
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

    user_doc = user_in_db.dict()
    user_doc["role"] = account_type
    if account_type == "vendor":
        import uuid as _uuid
        vendor_id = f"vendor-{_uuid.uuid4().hex[:12]}"
        await db.vendors.insert_one({
            "id": vendor_id,
            "company_name": user_data.company_name,
            "contact_name": user_data.contact_name,
            "email": user_data.email,
            "phone": user_data.phone,
            "siret": user_data.siret,
            "status": "pending",
            "credits": 0,
            "created_at": user_in_db.created_at.isoformat(),
        })
        user_doc["vendor_id"] = vendor_id
    await db.users.insert_one(user_doc)

    if user_data.siret:
        from company_extract import schedule_extract
        schedule_extract(db, user_data.siret, legal_name=user_data.company_name)

    logger.info(f"New user registered: {user_data.email}")

    return {
        "id": user_in_db.id,
        "email": user_in_db.email,
        "company_name": user_in_db.company_name,
        "message": "Compte créé avec succès"
    }


@auth_core_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, response: Response):
    """Login: sets an httpOnly auth cookie and returns the token (legacy)."""
    user = await get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    is_admin_account = bool(user.get("is_admin")) or str(user.get("role", "")).upper() in ("ADMIN", "SUPER_ADMIN")
    if is_admin_account and credentials.portal != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte administrateur : veuillez vous connecter via le bloc Administration."
        )
    if credentials.portal == "admin" and not is_admin_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l'équipe d'administration de la centrale."
        )

    access_token = create_access_token(data={"sub": user["id"]})
    set_auth_cookie(response, access_token)

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
            role=user.get("role"),
            must_change_password=user.get("must_change_password", False),
            created_at=user["created_at"]
        )
    )


@auth_core_router.post("/auth/logout", response_model=dict)
async def logout(response: Response):
    """Logout: clears the httpOnly auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Déconnexion réussie"}


@auth_core_router.get("/auth/me", response_model=UserResponse)
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
        must_change_password=current_user.get("must_change_password", False),
        created_at=current_user["created_at"]
    )


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@auth_core_router.post("/auth/change-password", response_model=dict)
async def change_password(payload: PasswordChange, current_user: dict = Depends(get_current_user)):
    """Change password (used for mandatory first-login change of temporary password)."""
    db = get_database()
    if not verify_password(payload.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nouveau mot de passe doit contenir au moins 8 caractères")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nouveau mot de passe doit être différent de l'actuel")

    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password_hash": get_password_hash(payload.new_password), "updated_at": datetime.utcnow()},
         "$unset": {"must_change_password": ""}},
    )
    logger.info(f"Password changed for user: {current_user['email']}")
    return {"message": "Mot de passe modifié avec succès"}


# ============== PASSWORD RESET ROUTES ==============

@auth_core_router.post("/auth/forgot-password", response_model=dict)
async def forgot_password(request: PasswordResetRequest):
    """Request password reset email."""
    db = get_database()
    user = await get_user_by_email(request.email)

    # Always return success to avoid email enumeration
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation."}

    reset_token = PasswordResetToken(
        user_id=user["id"],
        email=user["email"],
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    await db.password_resets.insert_one(reset_token.dict())

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


@auth_core_router.post("/auth/reset-password", response_model=dict)
async def reset_password(request: PasswordResetConfirm):
    """Reset password using token."""
    db = get_database()
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

    new_hash = get_password_hash(request.new_password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
    )

    await db.password_resets.update_one(
        {"id": token_doc["id"]},
        {"$set": {"used": True}}
    )

    logger.info(f"Password reset successful for user: {token_doc['email']}")

    return {"message": "Mot de passe réinitialisé avec succès"}
