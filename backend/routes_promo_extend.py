"""Prolongation de promo en un clic depuis l'email de relance vendeur."""
import logging
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
promo_extend_router = APIRouter(prefix="/api/promo", tags=["Promotions"])
db = None


def set_database(database):
    global db
    db = database


async def create_extend_token(product_id: str, promo_end: datetime) -> str:
    token = uuid.uuid4().hex
    await db.promo_extend_tokens.insert_one({
        "token": token, "product_id": product_id,
        "promo_end": promo_end, "used": False,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=10),
    })
    return token


def _page(title: str, message: str, ok: bool = True) -> HTMLResponse:
    color = "#2e7d32" if ok else "#c62828"
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;background:#1F0A33;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;">
<div style="max-width:480px;background:#2c1247;border:1px solid rgba(255,255,255,.15);border-radius:16px;padding:40px;text-align:center;">
<h1 style="color:{color};font-size:22px;">{title}</h1>
<p style="color:rgba(255,255,255,.8);line-height:1.6;">{message}</p>
<p style="margin-top:28px;"><a href="{os.environ.get('FRONTEND_PUBLIC_URL', '')}/vendor?tab=products"
style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Mon espace vendeur</a></p>
<p style="color:rgba(255,255,255,.4);font-size:12px;margin-top:24px;">CommunityPlace — O'SCOP × KDMARCHÉ</p>
</div></body></html>""")


@promo_extend_router.get("/admin/extension-log")
async def extension_log(admin: dict = Depends(require_admin)):
    """Journal des prolongations de promo (superadmin)."""
    items = await db.promo_extension_log.find({}, {"_id": 0}) \
        .sort("extended_at", -1).limit(50).to_list(50)
    return {"items": items}


@promo_extend_router.get("/extend/{token}")
async def extend_promo(token: str):
    doc = await db.promo_extend_tokens.find_one({"token": token})
    if not doc:
        return _page("Lien invalide", "Ce lien de prolongation est inconnu ou a été supprimé.", ok=False)
    if doc.get("used"):
        return _page("Déjà utilisé", "Cette promotion a déjà été prolongée via ce lien.", ok=False)
    if doc["expires_at"] < datetime.utcnow():
        return _page("Lien expiré", "Ce lien de prolongation n'est plus valide. Gérez votre promo depuis votre espace vendeur.", ok=False)
    new_end = doc["promo_end"] + timedelta(days=7)
    r = await db.zone_prices.update_many(
        {"product_id": doc["product_id"], "promo_end": doc["promo_end"]},
        {"$set": {"promo_end": new_end}})
    await db.products.update_one({"id": doc["product_id"]}, {"$unset": {"promo_renewal_reminded_at": ""}})
    await db.promo_extend_tokens.update_one({"token": token},
                                            {"$set": {"used": True, "used_at": datetime.utcnow()}})
    product = await db.products.find_one({"id": doc["product_id"]}, {"_id": 0, "name": 1, "sku": 1, "vendor_id": 1})
    await db.promo_extension_log.insert_one({
        "id": uuid.uuid4().hex, "product_id": doc["product_id"],
        "product_name": (product or {}).get("name"), "sku": (product or {}).get("sku"),
        "vendor_id": (product or {}).get("vendor_id"),
        "old_end": doc["promo_end"].isoformat(), "new_end": new_end.isoformat(),
        "zones_count": r.modified_count, "source": "email_one_click",
        "extended_at": datetime.utcnow().isoformat(),
    })
    logger.info("Promo prolongée +7j via email : %s (%d zone(s))", doc["product_id"], r.modified_count)
    return _page("Promotion prolongée ✓",
                 f"La promotion sur « {(product or {}).get('name', 'votre produit')} » a été prolongée de 7 jours "
                 f"sur {r.modified_count} zone(s), jusqu'au {new_end.strftime('%d/%m/%Y')}.")
