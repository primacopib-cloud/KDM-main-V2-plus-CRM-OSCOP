"""
Native Google OAuth 2.0 (Authorization Code flow) for KDMARCHE × O'SCOP.

This uses our own Google Cloud project (project_id=kdmarche), independent from
the Emergent-managed OAuth gateway. Branding on Google's consent screen is
"KDMARCHE" (our own OAuth Client).

Flow:
  1. Frontend: anchor → GET /api/auth/google/login
  2. Backend redirects to https://accounts.google.com/o/oauth2/v2/auth?...
  3. Google → user consents → redirect to GOOGLE_REDIRECT_URI
     (= /api/auth/google/callback)
  4. Backend exchanges code → access_token → /oauth2/v3/userinfo
  5. Backend upserts MongoDB user by email, generates our JWT, redirects to
     FRONTEND_BASE_URL/auth/google/return?token=<JWT>
  6. Frontend reads token from query string, stores it (same as email/password
     login), redirects to /dashboard.

State / CSRF: A signed `state` parameter is sent to Google and verified on
callback (cryptographic random token, stored in HMAC-signed cookie).

Account linking:
  - If email exists in `users` → we attach `google_sub` & set
    `auth_provider="google"` and login that user.
  - If not → we create a new user (role=customer_org_buyer) with no password.
"""
from __future__ import annotations

import os
import json
import logging
import secrets
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/google", tags=["Google OAuth (native)"])

# ---------- Configuration ----------
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600  # 10 min

# Database injected by server.py
db = None


def set_google_auth_database(database):
    global db
    db = database


# ---------- Helpers ----------
def _cfg(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth non configuré : {key} manquant",
        )
    return value


def _sign_state(nonce: str) -> str:
    """HMAC-sign a nonce with JWT_SECRET_KEY so we can verify it on callback."""
    secret = os.environ.get("JWT_SECRET_KEY", "")
    mac = hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{nonce}.{mac}"


def _verify_state(signed: str) -> bool:
    try:
        nonce, mac = signed.rsplit(".", 1)
    except ValueError:
        return False
    expected = _sign_state(nonce).rsplit(".", 1)[1]
    return hmac.compare_digest(mac, expected)


def _frontend_base() -> str:
    base = os.environ.get("FRONTEND_BASE_URL") or os.environ.get("REACT_APP_BACKEND_URL")
    if not base:
        # Last-resort safety net: derive from GOOGLE_REDIRECT_URI host.
        redirect = os.environ.get("GOOGLE_REDIRECT_URI", "")
        if redirect:
            from urllib.parse import urlparse
            p = urlparse(redirect)
            base = f"{p.scheme}://{p.netloc}"
    return (base or "").rstrip("/")


# ---------- Routes ----------
@router.get("/login")
async def google_login(request: Request, redirect_after: Optional[str] = "/dashboard"):
    """Kick off the Google OAuth flow.

    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    """
    client_id = _cfg("GOOGLE_CLIENT_ID")
    redirect_uri = _cfg("GOOGLE_REDIRECT_URI")

    nonce = secrets.token_urlsafe(24)
    state = _sign_state(nonce)
    # Embed the post-login frontend path in the state (so we can return there)
    embedded = json.dumps({"s": state, "r": (redirect_after or "/dashboard")[:200]})

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
        "include_granted_scopes": "true",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key=STATE_COOKIE,
        value=embedded,
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback")
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Receive Google's authorization code, exchange it, upsert user, issue JWT, redirect to frontend.

    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    """
    front = _frontend_base()
    fail_url = f"{front}/connexion?google_error="

    if error:
        return RedirectResponse(url=fail_url + error, status_code=302)
    if not code or not state:
        return RedirectResponse(url=fail_url + "missing_code_or_state", status_code=302)

    # CSRF state verification
    cookie_raw = request.cookies.get(STATE_COOKIE)
    if not cookie_raw:
        return RedirectResponse(url=fail_url + "state_cookie_missing", status_code=302)
    try:
        cookie_data = json.loads(cookie_raw)
        if cookie_data.get("s") != state or not _verify_state(state):
            return RedirectResponse(url=fail_url + "state_mismatch", status_code=302)
        post_login_redirect = cookie_data.get("r") or "/dashboard"
    except (json.JSONDecodeError, ValueError):
        return RedirectResponse(url=fail_url + "state_invalid", status_code=302)

    client_id = _cfg("GOOGLE_CLIENT_ID")
    client_secret = _cfg("GOOGLE_CLIENT_SECRET")
    redirect_uri = _cfg("GOOGLE_REDIRECT_URI")

    # Exchange code → tokens
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if token_resp.status_code != 200:
            logger.warning("Google /token %s: %s", token_resp.status_code, token_resp.text[:200])
            return RedirectResponse(url=fail_url + "token_exchange_failed", status_code=302)
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(url=fail_url + "no_access_token", status_code=302)

        # Fetch userinfo
        async with httpx.AsyncClient(timeout=10.0) as client:
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if userinfo_resp.status_code != 200:
            logger.warning("Google /userinfo %s: %s", userinfo_resp.status_code, userinfo_resp.text[:200])
            return RedirectResponse(url=fail_url + "userinfo_failed", status_code=302)
        userinfo = userinfo_resp.json()
    except httpx.HTTPError as exc:
        logger.error("Google OAuth network error: %s", exc)
        return RedirectResponse(url=fail_url + "network_error", status_code=302)

    email = (userinfo.get("email") or "").lower().strip()
    email_verified = userinfo.get("email_verified", False)
    google_sub = userinfo.get("sub")
    name = userinfo.get("name") or ""
    picture = userinfo.get("picture")

    if not email or not email_verified or not google_sub:
        return RedirectResponse(url=fail_url + "email_not_verified", status_code=302)

    if db is None:
        return RedirectResponse(url=fail_url + "db_not_ready", status_code=302)

    # Upsert user — link by email
    import uuid
    now = datetime.now(timezone.utc)
    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if user:
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "google_sub": google_sub,
                "contact_name": user.get("contact_name") or name,
                "picture": picture,
                "auth_provider": "google",
                "updated_at": now,
            }},
        )
    else:
        new_user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "google_sub": google_sub,
            "contact_name": name,
            "picture": picture,
            "auth_provider": "google",
            "company_name": "",
            "siret": "",
            "phone": "",
            "subscription": "ess-acces-pro",
            "credits": 0,
            "is_admin": False,
            "role": "customer_org_buyer",
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(new_user)
        user = new_user

    # Issue our JWT (same one used for email/password login)
    from auth import create_access_token
    jwt_token = create_access_token(data={"sub": user["id"]})

    # Redirect to frontend with token in query string (frontend reads it & stores it)
    safe_path = post_login_redirect if post_login_redirect.startswith("/") else "/dashboard"
    return_url = f"{front}/auth/google/return?token={jwt_token}&next={safe_path}"
    response = RedirectResponse(url=return_url, status_code=302)
    response.delete_cookie(key=STATE_COOKIE, path="/")
    return response


async def setup_google_auth_indexes(database):
    await database.users.create_index("google_sub", sparse=True)
