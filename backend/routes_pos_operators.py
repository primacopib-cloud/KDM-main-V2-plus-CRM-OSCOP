"""Opérateurs POS : comptes employés créés et gérés par le gérant du relais LOLODRIVE."""
import re
import uuid
import logging
from datetime import datetime, timedelta
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


@pos_operators_router.post("/pos/break/start")
async def start_break(user: dict = Depends(get_current_user)):
    """L'opérateur signale le début d'une pause (traçage des heures en caisse)."""
    from routes_relay_products import _manager_point
    point = await _manager_point(user["id"])
    if await db.pos_breaks.find_one({"user_id": user["id"], "ended_at": None}):
        raise HTTPException(status_code=400, detail="Une pause est déjà en cours")
    doc = {"id": str(uuid.uuid4()), "user_id": user["id"],
           "operator_name": user.get("contact_name") or user.get("email"),
           "point_id": point["id"], "point_code": point["code"],
           "started_at": datetime.utcnow(), "ended_at": None, "duration_min": None}
    await db.pos_breaks.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "break": doc}


@pos_operators_router.post("/pos/break/end")
async def end_break(user: dict = Depends(get_current_user)):
    """Fin de pause : reprise de la caisse, durée calculée."""
    br = await db.pos_breaks.find_one({"user_id": user["id"], "ended_at": None})
    if not br:
        raise HTTPException(status_code=400, detail="Aucune pause en cours")
    now = datetime.utcnow()
    duration = max(1, round((now - br["started_at"]).total_seconds() / 60))
    await db.pos_breaks.update_one({"id": br["id"]}, {"$set": {"ended_at": now, "duration_min": duration}})
    return {"ok": True, "duration_min": duration}


@pos_operators_router.get("/pos/break/status")
async def break_status(user: dict = Depends(get_current_user)):
    """Pause en cours + total des pauses du jour pour la session."""
    current = await db.pos_breaks.find_one({"user_id": user["id"], "ended_at": None}, {"_id": 0})
    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = await db.pos_breaks.find(
        {"user_id": user["id"], "started_at": {"$gte": day_start}, "ended_at": {"$ne": None}},
        {"_id": 0, "duration_min": 1}).to_list(50)
    return {"on_break": current is not None, "current": current,
            "today_count": len(today), "today_total_min": sum(t.get("duration_min", 0) for t in today)}


@pos_operators_router.get("/manager/operator-breaks")
async def operator_breaks(days: int = 7, user: dict = Depends(get_current_user)):
    """Historique des pauses des opérateurs du relais (gérant uniquement)."""
    point = await _owned_point(user["id"])
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)
    breaks = await db.pos_breaks.find(
        {"point_id": point["id"], "started_at": {"$gte": since}},
        {"_id": 0}).sort("started_at", -1).to_list(500)
    by_user = {}
    for b in breaks:
        e = by_user.setdefault(b["user_id"], {"operator_name": b["operator_name"], "count": 0,
                                              "total_min": 0, "on_break": False, "breaks": []})
        e["count"] += 1
        e["total_min"] += b.get("duration_min") or 0
        if b.get("ended_at") is None:
            e["on_break"] = True
        if len(e["breaks"]) < 10:
            e["breaks"].append(b)
    return {"days": days, "operators": list(by_user.values())}


@pos_operators_router.get("/manager/operator-hours")
async def operator_hours(days: int = 7, user: dict = Depends(get_current_user)):
    """Temps de présence estimé par opérateur : (première → dernière activité du jour) − pauses."""
    point = await _owned_point(user["id"])
    days = max(1, min(days, 31))
    since = datetime.utcnow() - timedelta(days=days)
    ops = await db.users.find({"role": "OPERATEUR_POS", "pos_point_id": point["id"]},
                              {"_id": 0, "id": 1, "contact_name": 1}).to_list(100)
    result = []
    for op in ops:
        events = {}
        async for l in db.pos_logins.find({"user_id": op["id"], "at": {"$gte": since}}, {"_id": 0, "at": 1}):
            events.setdefault(l["at"].strftime("%Y-%m-%d"), []).append(l["at"])
        async for o in db.lolodrive_orders.find(
                {"operator_id": op["id"], "created_at": {"$gte": since}}, {"_id": 0, "created_at": 1}):
            events.setdefault(o["created_at"].strftime("%Y-%m-%d"), []).append(o["created_at"])
        breaks_by_day = {}
        async for b in db.pos_breaks.find({"user_id": op["id"], "started_at": {"$gte": since}}, {"_id": 0}):
            d = b["started_at"].strftime("%Y-%m-%d")
            events.setdefault(d, []).append(b["started_at"])
            if b.get("ended_at"):
                events[d].append(b["ended_at"])
                breaks_by_day[d] = breaks_by_day.get(d, 0) + (b.get("duration_min") or 0)
        days_detail, total_min, total_break_min = [], 0, 0
        for d in sorted(events, reverse=True):
            span = max(0, round((max(events[d]) - min(events[d])).total_seconds() / 60))
            bmin = breaks_by_day.get(d, 0)
            presence = max(0, span - bmin)
            total_min += presence
            total_break_min += bmin
            days_detail.append({"date": d, "presence_min": presence, "break_min": bmin})
        result.append({"operator_id": op["id"], "operator_name": op.get("contact_name"),
                       "total_presence_min": total_min, "total_break_min": total_break_min,
                       "days": days_detail[:10]})
    return {"days": days, "operators": result}


@pos_operators_router.get("/pos/session-info")
async def pos_session_info(user: dict = Depends(get_current_user)):
    """Nom + horodatage de connexion de la session en cours (affiché jusqu'à déconnexion)."""
    u = await db.users.find_one({"id": user["id"]},
                                {"_id": 0, "contact_name": 1, "email": 1, "role": 1,
                                 "last_login_at": 1, "pos_point_id": 1})
    point_code = None
    point_details = None
    pt_fields = {"_id": 0, "code": 1, "name": 1, "address": 1, "city": 1, "zone_name": 1,
                 "territory": 1, "contact_phone": 1, "contact_email": 1, "opening_hours": 1}
    if u.get("pos_point_id"):
        pt = await db.lolodrive_points.find_one({"id": u["pos_point_id"]}, pt_fields)
        point_code = (pt or {}).get("code")
        point_details = pt
    else:
        pt = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, pt_fields)
        point_code = (pt or {}).get("code")
        point_details = pt
    return {"name": u.get("contact_name") or u.get("email"), "email": u.get("email"),
            "role": u.get("role"), "last_login_at": u.get("last_login_at"),
            "point_code": point_code, "point": point_details}
