"""Alertes incoterm favori : préférences adhérent + notification à l'arrivée d'un produit correspondant."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
import logging

from vendor_models import ALLOWED_INCOTERMS

logger = logging.getLogger(__name__)

incoterm_alerts_router = APIRouter(prefix="/api/v2/catalog")

db = None


def set_incoterm_alerts_database(database):
    global db
    db = database


async def _require_user(request: Request):
    from auth import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    user = await db.users.find_one({"id": user_id}) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")
    return user


class AlertCodes(BaseModel):
    codes: List[str]


@incoterm_alerts_router.get("/incoterm-alerts")
async def get_incoterm_alerts(request: Request):
    """Incoterms suivis par l'adhérent connecté."""
    user = await _require_user(request)
    return {"codes": user.get("favorite_incoterms") or []}


@incoterm_alerts_router.put("/incoterm-alerts")
async def set_incoterm_alerts(body: AlertCodes, request: Request):
    """Met à jour la liste des incoterms suivis."""
    user = await _require_user(request)
    codes = [c.upper() for c in body.codes if c.upper() in ALLOWED_INCOTERMS]
    await db.users.update_one({"id": user["id"]}, {"$set": {"favorite_incoterms": codes}})
    return {"success": True, "codes": codes}


async def notify_incoterm_watchers(database, product: dict):
    """Notifie les adhérents dont un incoterm favori correspond au nouveau produit publié."""
    codes = sorted({c for lst in (product.get("incoterms") or {}).values() for c in (lst or [])})
    if not codes:
        return 0
    from core_deps import create_notification
    watchers = await database.users.find(
        {"favorite_incoterms": {"$in": codes}}, {"_id": 0, "id": 1, "favorite_incoterms": 1}
    ).to_list(500)
    sent = 0
    for w in watchers:
        matched = sorted(set(w.get("favorite_incoterms") or []) & set(codes))
        await create_notification(
            notification_type="product_incoterm_match",
            title=f"Nouveau produit livrable en {', '.join(matched)}",
            message=f"« {product.get('name')} » vient d'arriver au catalogue avec l'incoterm {', '.join(matched)} que vous suivez.",
            target_roles=[],
            target_user_id=w["id"],
            data={"link": f"/catalogue?produit={product.get('id')}", "product_id": product.get("id")},
        )
        sent += 1
    if sent:
        logger.info("Alertes incoterm : %d adhérent(s) notifié(s) pour %s (%s)", sent, product.get("id"), codes)
    return sent
