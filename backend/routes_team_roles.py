"""Gestion des droits d'équipe par le super admin — /api/admin/team/*.

Rôles attribuables : ADMIN, COOPER, EXPERT + rôles techniques existants.
"""
from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr

from admin_guard import require_admin
from auth import get_current_user_id, get_password_hash

team_router = APIRouter(prefix="/api/admin/team", tags=["Team Roles"])

db = None


def set_team_roles_database(database) -> None:
    global db
    db = database


ASSIGNABLE_ROLES = {
    "ADMIN": "Admin — gestion complète",
    "COOPER": "COOPER — coopérateur (accès opérationnel)",
    "EXPERT": "Expert — consultation & conseil",
    "oscop_compliance_admin": "O'SCOP Conformité",
    "oscop_billing_admin": "O'SCOP Facturation",
    "oscop_support_agent": "O'SCOP Support",
    "kdm_b2b_admin": "KDMARCHÉ Admin B2B",
    "kdm_b2b_sales": "KDMARCHÉ Commercial",
    "kdm_warehouse": "KDMARCHÉ Entrepôt",
    "kdm_finance": "KDMARCHÉ Finance",
}
SUPER_ROLES = {"SUPER_ADMIN", "OSCOP_SUPER_ADMIN"}
STAFF_ROLES = set(ASSIGNABLE_ROLES) | SUPER_ROLES

USER_FIELDS = {"_id": 0, "id": 1, "email": 1, "contact_name": 1, "company_name": 1,
               "role": 1, "is_admin": 1, "created_at": 1, "role_granted_at": 1,
               "role_granted_by": 1, "previous_role": 1}


async def _super_admin(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await require_admin(user_id)
    role = (user.get("role") or "").upper()
    if role in SUPER_ROLES or user.get("is_admin"):
        return user
    raise HTTPException(status_code=403, detail="Réservé au super administrateur")


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


class GrantPayload(BaseModel):
    user_id: str
    role: str


class RevokePayload(BaseModel):
    user_id: str


class CreatePayload(BaseModel):
    email: EmailStr
    contact_name: str
    role: str


def _check_role(role: str) -> None:
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {role}")


@team_router.get("/roles")
async def list_assignable_roles(_: dict = Depends(_admin)):
    return {"roles": [{"value": v, "label": lbl} for v, lbl in ASSIGNABLE_ROLES.items()]}


@team_router.get("")
async def list_team(_: dict = Depends(_admin)):
    query = {"$or": [{"role": {"$in": list(STAFF_ROLES)}}, {"is_admin": True}]}
    docs = await db.users.find(query, USER_FIELDS).sort("created_at", -1).to_list(200)
    return {"members": docs, "total": len(docs)}


@team_router.get("/search")
async def search_users(q: str = Query(..., min_length=2), _: dict = Depends(_admin)):
    regex = {"$regex": q, "$options": "i"}
    docs = await db.users.find(
        {"$or": [{"email": regex}, {"contact_name": regex}, {"company_name": regex}]},
        USER_FIELDS,
    ).limit(10).to_list(10)
    return {"users": docs}


@team_router.post("/grant")
async def grant_role(payload: GrantPayload, admin: dict = Depends(_super_admin)):
    _check_role(payload.role)
    target = await db.users.find_one({"id": payload.user_id}, USER_FIELDS)
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if (target.get("role") or "").upper() in SUPER_ROLES:
        raise HTTPException(status_code=403, detail="Impossible de modifier un super administrateur")
    now = datetime.now(timezone.utc).isoformat()
    update = {"role": payload.role, "role_granted_at": now, "role_granted_by": admin["email"], "updated_at": now}
    if target.get("role") not in STAFF_ROLES and "previous_role" not in target:
        update["previous_role"] = target.get("role") or "customer_org_buyer"
    await db.users.update_one({"id": payload.user_id}, {"$set": update})
    return {"status": "SUCCESS", "user_id": payload.user_id, "role": payload.role}


@team_router.post("/revoke")
async def revoke_role(payload: RevokePayload, admin: dict = Depends(_super_admin)):
    target = await db.users.find_one({"id": payload.user_id}, USER_FIELDS)
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if (target.get("role") or "").upper() in SUPER_ROLES or target.get("is_admin"):
        raise HTTPException(status_code=403, detail="Impossible de révoquer un super administrateur")
    now = datetime.now(timezone.utc).isoformat()
    restored_role = target.get("previous_role") or "customer_org_buyer"
    await db.users.update_one(
        {"id": payload.user_id},
        {"$set": {"role": restored_role, "updated_at": now},
         "$unset": {"previous_role": "", "role_granted_at": "", "role_granted_by": ""}},
    )
    return {"status": "SUCCESS", "user_id": payload.user_id, "restored_role": restored_role}


async def _send_welcome_email(email: str, name: str, role_label: str, temp_password: str) -> bool:
    from brevo_service import is_brevo_configured, send_email, _wrap_html

    if not is_brevo_configured():
        return False
    login_url = os.environ.get("FRONTEND_URL", "") + "/connexion"
    body = (
        f"<p>Bonjour {name},</p>"
        f"<p>Un accès <strong>{role_label}</strong> vient de vous être attribué sur la plateforme "
        "KDMARCHÉ × O'SCOP (Communityplace).</p>"
        f"<p><strong>Identifiant :</strong> {email}<br/>"
        f"<strong>Mot de passe temporaire :</strong> <code>{temp_password}</code></p>"
        "<p>Par sécurité, modifiez ce mot de passe dès votre première connexion.</p>"
        f"<p><a href='{login_url}'>Se connecter</a></p>"
    )
    result = await send_email(
        to_email=email, to_name=name,
        subject="Vos accès à la plateforme KDMARCHÉ × O'SCOP",
        html_content=_wrap_html("Bienvenue dans l'équipe", body),
        tags=["team-invite"],
    )
    return result is not None


@team_router.post("/create")
async def create_member(payload: CreatePayload, admin: dict = Depends(_super_admin)):
    _check_role(payload.role)
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    temp_password = secrets.token_urlsafe(9)
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "contact_name": payload.contact_name.strip(),
        "company_name": "KDMARCHÉ × O'SCOP",
        "siret": "",
        "phone": "",
        "subscription": "ess-acces-pro",
        "credits": 0,
        "role": payload.role,
        "password_hash": get_password_hash(temp_password),
        "must_change_password": True,
        "role_granted_at": now,
        "role_granted_by": admin["email"],
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one({**user})
    email_sent = await _send_welcome_email(email, payload.contact_name, ASSIGNABLE_ROLES[payload.role], temp_password)
    return {
        "status": "SUCCESS",
        "user": {k: user[k] for k in ("id", "email", "contact_name", "role")},
        "temp_password": temp_password,
        "email_sent": email_sent,
    }
