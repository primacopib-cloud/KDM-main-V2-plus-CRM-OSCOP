from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "kdmarche-oscop-b2b-ess-secret-key-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
AUTH_COOKIE_NAME = "access_token"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token (optional: cookie fallback supported)
security = HTTPBearer(auto_error=False)


def set_auth_cookie(response: Response, token: str) -> None:
    """Set the JWT in a secure httpOnly cookie."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Remove the auth cookie."""
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")


def extract_user_id_from_request(request: Request) -> Optional[str]:
    """Resolve the user id from the Authorization header, falling back to the httpOnly cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        uid = decode_token(auth_header.split(" ", 1)[1])
        if uid:
            return uid
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return decode_token(cookie_token)
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[str]:
    """Decode and verify a JWT token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Get the current user ID from the JWT (Authorization header or httpOnly cookie)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = None
    if credentials and credentials.credentials:
        user_id = decode_token(credentials.credentials)
    if user_id is None:
        cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
        if cookie_token:
            user_id = decode_token(cookie_token)

    if user_id is None:
        raise credentials_exception

    return user_id
