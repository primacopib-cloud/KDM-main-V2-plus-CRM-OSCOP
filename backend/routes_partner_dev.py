"""Espace Développeur Partenaire — chaque partenaire consulte ses clés API, quotas et derniers appels."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from core_deps import get_current_user

logger = logging.getLogger(__name__)

partner_dev_router = APIRouter(prefix="/api/partner/dev", tags=["partner-dev"])

db = None


def set_partner_dev_database(database):
    global db
    db = database


@partner_dev_router.get("/keys")
async def my_keys(user: dict = Depends(get_current_user)):
    """Clés API rattachées à l'email du partenaire connecté (ou toutes si admin)."""
    email = (user.get("email") or "").lower()
    is_admin = user.get("is_admin", False)
    q = {} if is_admin else {"partner_email": {"$regex": f"^{email}$", "$options": "i"}}
    if not is_admin and not email:
        raise HTTPException(status_code=403, detail="Compte sans email")
    keys = await db.api_keys.find(q, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(50)
    for k in keys:
        k["last_calls"] = await db.api_call_logs.find(
            {"key_id": k["id"]}, {"_id": 0}
        ).sort("ts", -1).limit(30).to_list(30)
        k["last_deliveries"] = await db.webhook_deliveries.find(
            {"key_id": k["id"]}, {"_id": 0}
        ).sort("ts", -1).limit(20).to_list(20)
    return {"items": keys, "email": email}
