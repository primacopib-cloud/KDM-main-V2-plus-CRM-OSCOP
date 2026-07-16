"""
Emergent-managed Google OAuth — scaffolding for KDMARCHE × O'SCOP.

This integrates with Emergent's hosted OAuth gateway (no client_id/secret required
on our side — Emergent handles Google federation).

Frontend flow:
1. User clicks "Continuer avec Google"
   → redirect to https://auth.emergentagent.com/?redirect=<our_origin>/auth/callback
2. After Google auth, Emergent redirects back to <our_origin>/auth/callback#session_id=XYZ
3. Frontend extracts session_id, POSTs to /api/auth/emergent/session.
4. Backend calls Emergent /session-data to get user info + a 7-day session_token,
   stores it in MongoDB, sets httpOnly cookie, returns user.

Compatible with the existing JWT auth: a user signed in via Emergent gets:
  - a row in `users` (email, contact_name, picture, role="customer_org_buyer")
  - a row in `emergent_sessions` (session_token, expires_at)
  - a JWT access_token returned in the response so the existing frontend hooks keep working.
"""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/emergent", tags=["Emergent OAuth"])

EMERGENT_SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_TTL_DAYS = 7

# Database injected from server.py
db = None


def set_emergent_auth_database(database):
    global db
    db = database


class SessionExchange(BaseModel):
    session_id: str


@router.post("/session")
async def exchange_session(payload: SessionExchange, response: Response):
    """Exchange a one-time `session_id` (from URL fragment after Emergent OAuth) for a persistent session.

    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Auth Emergent non initialisé")

    headers = {"X-Session-ID": payload.session_id}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(EMERGENT_SESSION_DATA_URL, headers=headers)
        if r.status_code != 200:
            logger.warning("Emergent /session-data %s: %s", r.status_code, r.text[:200])
            raise HTTPException(status_code=401, detail="Session Emergent invalide")
        data = r.json()
    except httpx.HTTPError as exc:
        logger.error("Emergent /session-data network error: %s", exc)
        raise HTTPException(status_code=502, detail="Service Auth Emergent injoignable")

    email = (data.get("email") or "").lower().strip()
    name = data.get("name") or ""
    picture = data.get("picture")
    session_token = data.get("session_token")
    if not email or not session_token:
        raise HTTPException(status_code=502, detail="Réponse Emergent incomplète")

    # Upsert user (compatible with existing schema)
    now = datetime.now(timezone.utc)
    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if user:
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "contact_name": user.get("contact_name") or name,
                "picture": picture,
                "auth_provider": "emergent_google",
                "updated_at": now,
            }},
        )
    else:
        new_user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "contact_name": name,
            "picture": picture,
            "auth_provider": "emergent_google",
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

    # Persist Emergent session
    expires_at = now + timedelta(days=SESSION_TTL_DAYS)
    await db.emergent_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": user["id"],
            "email": email,
            "expires_at": expires_at,
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    # Set httpOnly cookie
    response.set_cookie(
        key="emergent_session",
        value=session_token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    # Also issue a JWT in an httpOnly cookie so the existing app hooks keep working
    from auth import create_access_token, set_auth_cookie  # local import to avoid circular
    access_token = create_access_token(data={"sub": user["id"]})
    set_auth_cookie(response, access_token)

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "contact_name": user.get("contact_name"),
            "picture": user.get("picture"),
            "is_admin": user.get("is_admin", False),
            "auth_provider": "emergent_google",
        },
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def emergent_logout(response: Response, emergent_session: Optional[str] = Cookie(None)):
    if db is not None and emergent_session:
        await db.emergent_sessions.delete_one({"session_token": emergent_session})
    response.delete_cookie(key="emergent_session", path="/", samesite="none", secure=True)
    return {"ok": True}


@router.get("/me")
async def emergent_me(emergent_session: Optional[str] = Cookie(None)):
    """Verify Emergent session via cookie. Returns user dict or 401."""
    if not emergent_session or db is None:
        raise HTTPException(status_code=401, detail="Non authentifié")
    sess = await db.emergent_sessions.find_one({"session_token": emergent_session}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Session inconnue")
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.emergent_sessions.delete_one({"session_token": emergent_session})
        raise HTTPException(status_code=401, detail="Session expirée")
    user = await db.users.find_one({"id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inexistant")
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "contact_name": user.get("contact_name"),
            "picture": user.get("picture"),
            "is_admin": user.get("is_admin", False),
            "auth_provider": user.get("auth_provider", "jwt"),
        }
    }


async def setup_emergent_indexes(database):
    await database.emergent_sessions.create_index("session_token", unique=True)
    await database.emergent_sessions.create_index("user_id")
    await database.emergent_sessions.create_index("expires_at")
