"""Registres & gestion des espaces (vendeur, investisseur, relais, PASS) pour le superadmin."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

admin_spaces_router = APIRouter(prefix="/api/admin/spaces", tags=["Admin Spaces"])

db = None


def set_admin_spaces_database(database):
    global db
    db = database


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


async def _vendors_registry():
    items = []
    async for v in db.vendors.find({}, {"_id": 0, "password_hash": 0}):
        items.append({
            "id": v.get("id"),
            "name": v.get("company_name") or v.get("contact_name"),
            "contact": v.get("contact_name"),
            "email": v.get("email"),
            "phone": v.get("phone"),
            "country": v.get("country") or v.get("city"),
            "status": (v.get("status") or "pending").upper(),
            "detail": f"{v.get('product_count', 0)} produit(s)",
            "created_at": _iso(v.get("created_at")),
            "account_connected": True,
        })
    return items


async def _investors_registry():
    items = []
    async for acc in db.investor_accounts.find({}, {"_id": 0}):
        user = await db.users.find_one({"id": acc.get("user_id")}, {"_id": 0, "password_hash": 0})
        items.append({
            "id": acc.get("id"),
            "name": (user or {}).get("contact_name") or (user or {}).get("company_name") or "—",
            "email": (user or {}).get("email"),
            "phone": (user or {}).get("phone"),
            "country": None,
            "status": (acc.get("status") or "ACTIVE").upper(),
            "detail": f"Plan {acc.get('plan_code', '—')} · {round((acc.get('monthly_invest_uc') or 0) / 100)} UC/mois",
            "created_at": _iso(acc.get("created_at")),
            "account_connected": bool(user),
        })
    return items


async def _relays_registry():
    gerants = {}
    async for u in db.users.find({"role": "GERANT_LOLO_POINT"}, {"_id": 0, "password_hash": 0}):
        if u.get("email"):
            gerants[u["email"].lower()] = u
    items = []
    async for p in db.lolodrive_points.find({}, {"_id": 0}):
        manager = gerants.get((p.get("contact_email") or "").lower())
        items.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "contact": (manager or {}).get("contact_name"),
            "email": p.get("contact_email"),
            "country": p.get("territory"),
            "status": (p.get("status") or "ACTIVE").upper(),
            "detail": f"{p.get('code', '')} · {p.get('city', '')}",
            "created_at": _iso(p.get("created_at")),
            "account_connected": bool(manager),
        })
    return items


async def _pass_registry():
    items = []
    async for u in db.users.find({"role": "TITULAIRE_PASS"}, {"_id": 0, "password_hash": 0}):
        p = await db.lolodrive_passes.find_one({"user_id": u.get("id")}, {"_id": 0}, sort=[("created_at", -1)])
        ends = _iso((p or {}).get("ends_at")) or ""
        items.append({
            "id": u.get("id"),
            "name": u.get("contact_name") or u.get("company_name") or "—",
            "email": u.get("email"),
            "phone": u.get("phone"),
            "country": None,
            "status": ((p or {}).get("status") or "SANS_PASS").upper(),
            "detail": f"PASS jusqu'au {str(ends)[:10]}" if p else "Aucun PASS actif",
            "created_at": _iso(u.get("created_at")),
            "account_connected": True,
        })
    return items


@admin_spaces_router.get("/registries")
async def get_registries(admin: dict = Depends(require_admin)):
    return {
        "vendors": await _vendors_registry(),
        "investors": await _investors_registry(),
        "relays": await _relays_registry(),
        "pass_members": await _pass_registry(),
    }


class StatusBody(BaseModel):
    status: str


_KINDS = {
    "vendors": ("vendors", "id"),
    "investors": ("investor_accounts", "id"),
    "relays": ("lolodrive_points", "id"),
}


@admin_spaces_router.patch("/{kind}/{item_id}/status")
async def update_space_status(kind: str, item_id: str, body: StatusBody, admin: dict = Depends(require_admin)):
    status = body.status.strip().upper()
    if not status:
        raise HTTPException(status_code=400, detail="Statut requis")
    now = datetime.now(timezone.utc).isoformat()
    if kind == "pass-members":
        res = await db.lolodrive_passes.update_one(
            {"user_id": item_id}, {"$set": {"status": status, "updated_at": now}}, upsert=False)
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Aucun PASS pour ce membre")
        return {"ok": True, "status": status}
    if kind not in _KINDS:
        raise HTTPException(status_code=404, detail="Type d'espace inconnu")
    coll, key = _KINDS[kind]
    if kind == "vendors":
        status = status.lower()
    res = await db[coll].update_one({key: item_id}, {"$set": {"status": status, "updated_at": now}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    return {"ok": True, "status": status}
