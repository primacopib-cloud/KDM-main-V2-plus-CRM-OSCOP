"""Gestion des territoires (zones acheteurs) par le Super Admin : ajouter, masquer, supprimer.
Agit sur zones_v2 (sélecteur catalogue/checkout) et synchronise kdm_zones (logistique)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

territories_router = APIRouter(prefix="/api/admin/territories", tags=["territories"])

db = None


def set_territories_database(database):
    global db
    db = database


class TerritoryBody(BaseModel):
    code: str
    name: str


class TerritoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


@territories_router.get("")
async def list_territories(admin: dict = Depends(require_admin)):
    """Toutes les zones, actives et masquées, avec le nombre de commandes rattachées."""
    zones = await db.zones_v2.find({}, {"_id": 0}).sort("code", 1).to_list(100)
    for z in zones:
        z["orders_count"] = await db.orders.count_documents({"zone_code": z["code"]})
    return {"items": zones}


@territories_router.post("")
async def add_territory(body: TerritoryBody, admin: dict = Depends(require_admin)):
    code = body.code.strip().upper().replace(" ", "_")
    name = body.name.strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="Code et nom requis")
    if await db.zones_v2.find_one({"code": code}):
        raise HTTPException(status_code=409, detail=f"Le territoire {code} existe déjà")
    now = datetime.now(timezone.utc).isoformat()
    doc = {"id": str(uuid.uuid4()), "code": code, "name": name, "kind": "OM",
           "exw_only": True, "pickup_required": True, "is_active": True, "created_at": now}
    await db.zones_v2.insert_one({**doc})
    if not await db.kdm_zones.find_one({"code": code}):
        await db.kdm_zones.insert_one({"id": str(uuid.uuid4()), "code": code, "name": name,
                                       "kind": "OM", "exw_only": True, "pickup_required": True,
                                       "is_active": True, "created_at": now})
    logger.info("Territoire ajouté : %s (%s) par %s", code, name, admin.get("email"))
    return doc


@territories_router.patch("/{code}")
async def update_territory(code: str, body: TerritoryUpdate, admin: dict = Depends(require_admin)):
    """Renommer ou masquer/réafficher un territoire (masqué = invisible dans le sélecteur acheteur)."""
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="Rien à mettre à jour")
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.zones_v2.update_one({"code": code.upper()}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Territoire introuvable")
    await db.kdm_zones.update_one({"code": code.upper()}, {"$set": upd})
    logger.info("Territoire %s mis à jour (%s) par %s", code, upd, admin.get("email"))
    return {"ok": True}


@territories_router.delete("/{code}")
async def delete_territory(code: str, admin: dict = Depends(require_admin)):
    """Suppression définitive — refusée si des commandes existent sur la zone (masquer dans ce cas)."""
    code = code.upper()
    orders = await db.orders.count_documents({"zone_code": code})
    if orders:
        raise HTTPException(status_code=409,
                            detail=f"{orders} commande(s) rattachée(s) à ce territoire — masquez-le plutôt que de le supprimer")
    res = await db.zones_v2.delete_one({"code": code})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Territoire introuvable")
    await db.kdm_zones.delete_one({"code": code})
    logger.info("Territoire %s supprimé par %s", code, admin.get("email"))
    return {"ok": True}
