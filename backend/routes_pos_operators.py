"""Opérateurs POS : comptes employés créés et gérés par le gérant du relais LOLODRIVE."""
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import get_current_user
from auth import get_password_hash

logger = logging.getLogger(__name__)
pos_operators_router = APIRouter(prefix="/api/lolodrive", tags=["POS Operators"])
db = None

OPERATOR_FIELDS = {"_id": 0, "id": 1, "contact_name": 1, "email": 1, "is_archived": 1,
                   "created_at": 1, "last_login_at": 1}


def set_pos_operators_database(database):
    global db
    db = database


class OperatorBody(BaseModel):
    name: str
    email: str
    password: Optional[str] = None


async def _owned_point(user_id: str) -> dict:
    """Relais dont l'utilisateur est LE gérant (pas un simple opérateur)."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user_id}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Réservé au gérant du relais")
    return point


def _validate(body: OperatorBody, require_password: bool):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nom de l'opérateur requis")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", body.email.strip().lower()):
        raise HTTPException(status_code=400, detail="Email invalide")
    if require_password and (not body.password or len(body.password) < 8):
        raise HTTPException(status_code=400, detail="Mot de passe requis (8 caractères minimum)")
    if body.password and len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (8 caractères minimum)")


@pos_operators_router.get("/manager/operators")
async def list_operators(user: dict = Depends(get_current_user)):
    point = await _owned_point(user["id"])
    ops = await db.users.find(
        {"role": "OPERATEUR_POS", "pos_point_id": point["id"]}, OPERATOR_FIELDS
    ).sort("created_at", 1).to_list(100)
    return {"point_code": point["code"], "operators": ops}


@pos_operators_router.post("/manager/operators")
async def create_operator(body: OperatorBody, user: dict = Depends(get_current_user)):
    point = await _owned_point(user["id"])
    _validate(body, require_password=True)
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec cet email")
    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()), "email": email, "password_hash": get_password_hash(body.password),
        "contact_name": body.name.strip(), "company_name": point["name"],
        "siret": "", "phone": "", "subscription": "pos-operator", "credits": 0,
        "is_admin": False, "role": "OPERATEUR_POS", "pos_point_id": point["id"],
        "created_by": user["id"], "is_archived": False,
        "created_at": now, "updated_at": now,
    }
    await db.users.insert_one(doc)
    return {"ok": True, "operator": {k: doc[k] for k in ("id", "email", "contact_name", "is_archived", "created_at")}}


@pos_operators_router.put("/manager/operators/{operator_id}")
async def update_operator(operator_id: str, body: OperatorBody, user: dict = Depends(get_current_user)):
    point = await _owned_point(user["id"])
    op = await db.users.find_one({"id": operator_id, "role": "OPERATEUR_POS", "pos_point_id": point["id"]})
    if not op:
        raise HTTPException(status_code=404, detail="Opérateur introuvable pour ce relais")
    _validate(body, require_password=False)
    email = body.email.strip().lower()
    if email != op["email"] and await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec cet email")
    updates = {"contact_name": body.name.strip(), "email": email, "updated_at": datetime.utcnow()}
    if body.password:
        updates["password_hash"] = get_password_hash(body.password)
    await db.users.update_one({"id": operator_id}, {"$set": updates})
    return {"ok": True, "operator_id": operator_id, "password_changed": bool(body.password)}


@pos_operators_router.post("/manager/operators/{operator_id}/archive")
async def archive_operator(operator_id: str, payload: dict, user: dict = Depends(get_current_user)):
    point = await _owned_point(user["id"])
    op = await db.users.find_one({"id": operator_id, "role": "OPERATEUR_POS", "pos_point_id": point["id"]})
    if not op:
        raise HTTPException(status_code=404, detail="Opérateur introuvable pour ce relais")
    archived = bool((payload or {}).get("archived", True))
    await db.users.update_one(
        {"id": operator_id}, {"$set": {"is_archived": archived, "updated_at": datetime.utcnow()}})
    return {"ok": True, "operator_id": operator_id, "is_archived": archived}


@pos_operators_router.get("/pos/session-info")
async def pos_session_info(user: dict = Depends(get_current_user)):
    """Nom + horodatage de connexion de la session en cours (affiché jusqu'à déconnexion)."""
    u = await db.users.find_one({"id": user["id"]},
                                {"_id": 0, "contact_name": 1, "email": 1, "role": 1,
                                 "last_login_at": 1, "pos_point_id": 1})
    point_code = None
    if u.get("pos_point_id"):
        pt = await db.lolodrive_points.find_one({"id": u["pos_point_id"]}, {"_id": 0, "code": 1})
        point_code = (pt or {}).get("code")
    else:
        pt = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0, "code": 1})
        point_code = (pt or {}).get("code")
    return {"name": u.get("contact_name") or u.get("email"), "email": u.get("email"),
            "role": u.get("role"), "last_login_at": u.get("last_login_at"), "point_code": point_code}
