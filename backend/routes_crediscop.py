"""CREDI'SCOP — solde unifié selon le profil connecté (badge barre de navigation)."""
import logging

from fastapi import APIRouter, Depends

from auth import get_current_user_id

logger = logging.getLogger(__name__)
crediscop_router = APIRouter(prefix="/api/me", tags=["CREDI'SCOP"])

db = None


def set_crediscop_database(database) -> None:
    global db
    db = database


@crediscop_router.get("/crediscop")
async def my_crediscop(user_id: str = Depends(get_current_user_id)):
    """Solde CREDI'SCOP du profil connecté : crédits IA vendeur, ou crédits du wallet org/perso."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return {"balance": None}

    if user.get("role") == "vendor" and user.get("vendor_id"):
        vendor = await db.vendors.find_one({"id": user["vendor_id"]}, {"_id": 0, "credits": 1})
        if vendor is not None:
            return {"balance": int(vendor.get("credits") or 0), "kind": "vendor",
                    "href": "/espace-vendeur", "label": "CREDI'SCOP"}

    membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0, "org_id": 1})
    if membership:
        wallet = await db.wallets.find_one({"org_id": membership["org_id"]}, {"_id": 0, "balance_credits": 1})
        if wallet is not None:
            return {"balance": int(wallet.get("balance_credits") or 0), "kind": "org",
                    "href": "/wallet", "label": "CREDI'SCOP"}

    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0, "balance_credits": 1})
    if wallet is not None:
        return {"balance": int(wallet.get("balance_credits") or 0), "kind": "user",
                "href": "/wallet", "label": "CREDI'SCOP"}
    return {"balance": 0, "kind": "user", "href": "/wallet", "label": "CREDI'SCOP"}
