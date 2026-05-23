"""Auth + bootstrap routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.all import BootstrapIn, TokenOut

router = APIRouter()


@router.post("/setup/bootstrap", response_model=TokenOut, tags=["auth"])
def bootstrap_admin(payload: BootstrapIn, db: Session = Depends(get_db)):
    """Create the very first admin account.

    Refuses once at least one user exists in the database (so this endpoint is
    safe to leave exposed in production: it is single-shot by design).
    """
    existing = int(db.execute(select(func.count(User.id))).scalar() or 0)
    if existing > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap déjà exécuté — utilisez /auth/token pour vous connecter.",
        )
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@router.post("/auth/token", response_model=TokenOut, tags=["auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow — also works with Swagger's Authorize button."""
    user: User | None = db.execute(
        select(User).where(User.email == form.username.lower())
    ).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")
    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
