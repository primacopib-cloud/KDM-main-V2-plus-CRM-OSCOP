"""LOLODRIVE by O'SCOP — Shared helpers (split from routes_lolodrive_oscoop.py)."""
from fastapi import Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
import os
import uuid
import logging
import stripe

from auth import get_current_user_id
from lolodrive_models import DEFAULT_LOGISTICS_CONFIG, QuoteLine, CatalogType

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")

db = None

def set_lolodrive_helpers_database(database):
    global db
    db = database

async def emit_crm_event(event_type: str, payload: dict):
    """Best-effort CRM bridge; never blocks transactional flow."""
    try:
        from routes_crm_oscoop import crm_record_event
        await crm_record_event(db, event_type, payload)
    except Exception as e:
        logger.warning(f"CRM sync skipped for {event_type}: {e}")

# =======================
# Helpers
# =======================

async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    role = user.get("role") or user.get("user_role") or user.get("role_v2")
    is_admin = user.get("is_admin", False) or role in ["oscop_super_admin", "kdm_b2b_admin", "admin", "SUPER_ADMIN", "ADMIN"]
    if not is_admin:
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user

async def get_or_create_wallet(user_id: str) -> dict:
    wallet = await db.lolodrive_wallets.find_one({"user_id": user_id})
    if wallet:
        return wallet
    wallet = {"id": str(uuid.uuid4()), "user_id": user_id, "balance_uc": 0, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    await db.lolodrive_wallets.insert_one(wallet)
    return wallet

async def is_pass_active(user_id: str) -> bool:
    doc = await db.lolodrive_passes.find_one({"user_id": user_id})
    return bool(doc and doc.get("status") == "ACTIVE" and doc.get("ends_at") and doc["ends_at"] > datetime.utcnow())

def cents_to_uc(cents: int) -> int:
    # Règle interne : 10 centimes = 1 UC. Ne pas afficher comme taux public.
    return round(cents / 10)

async def logistics_config() -> dict:
    cfg = await db.lolodrive_logistics_config.find_one({"id": "default"}, {"_id": 0})
    if cfg:
        return cfg
    await db.lolodrive_logistics_config.insert_one({**DEFAULT_LOGISTICS_CONFIG, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    return DEFAULT_LOGISTICS_CONFIG

async def quote_cart(user_id: str, items: List[QuoteLine]) -> dict:
    pass_active = await is_pass_active(user_id)
    cfg = await logistics_config()
    allow_normal_uc = cfg.get("allow_uc_for_normal_if_pass_active", True)

    skus = [i.sku for i in items]
    products = await db.lolodrive_products.find({"sku": {"$in": skus}, "is_active": {"$ne": False}}).to_list(200)
    products_by_sku = {p["sku"]: p for p in products}

    subtotal_cents = 0
    subtotal_uc = 0
    lines = []

    for item in items:
        p = products_by_sku.get(item.sku)
        if not p:
            continue
        is_essential = p.get("catalog_type") == CatalogType.ESSENTIAL.value
        unit_cents = p.get("price_public_cents", 0)
        if is_essential and pass_active and p.get("price_pass_cents") is not None:
            unit_cents = p["price_pass_cents"]

        unit_uc = None
        if pass_active:
            if is_essential:
                unit_uc = cents_to_uc(unit_cents)
            elif allow_normal_uc:
                # Hors25 payable en UC sans avantage : UC sur prix normal
                unit_uc = cents_to_uc(p.get("price_public_cents", unit_cents))

        subtotal_cents += unit_cents * item.qty
        subtotal_uc += (unit_uc or 0) * item.qty
        lines.append({
            "sku": p["sku"],
            "name": p["name"],
            "qty": item.qty,
            "catalog_type": p.get("catalog_type"),
            "unit_cents": unit_cents,
            "unit_uc": unit_uc,
        })

    return {"pass_active": pass_active, "subtotal_cents": subtotal_cents, "subtotal_uc": subtotal_uc, "lines": lines}

async def ensure_customer(user: dict) -> str:
    if user.get("stripe_customer_id"):
        return user["stripe_customer_id"]
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    customer = stripe.Customer.create(
        email=user.get("email"),
        phone=user.get("phone"),
        metadata={"user_id": user["id"]},
    )
    await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer.id}})
    return customer.id



# --- Frais de distance UC (achat hors relais de référence) ---
DISTANCE_FEE_NEAR_UC = 0.05   # autre relais <= 50 km
DISTANCE_FEE_FAR_UC = 0.08    # autre relais > 50 km (même territoire)
DISTANCE_FEE_OUT_UC = 0.13    # hors territoire


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_fee_rate(ref_point: dict | None, point: dict | None) -> float:
    """UC/produit facturés quand on achète sur un relais différent de son relais de référence."""
    if not ref_point or not point or ref_point.get("code") == point.get("code"):
        return 0.0
    if (ref_point.get("territory") or "").upper() != (point.get("territory") or "").upper():
        return DISTANCE_FEE_OUT_UC
    coords = (ref_point.get("lat"), ref_point.get("lng"), point.get("lat"), point.get("lng"))
    if any(c is None for c in coords):
        return DISTANCE_FEE_NEAR_UC
    return DISTANCE_FEE_NEAR_UC if haversine_km(*coords) <= 50 else DISTANCE_FEE_FAR_UC
