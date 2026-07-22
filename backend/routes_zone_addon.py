"""Zone additionnelle payante : achat d'un accès zone par crédits CREDI'SCOP ou carte (Stripe)."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import stripe

from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
zone_addon_router = APIRouter(prefix="/api/zone-addon", tags=["zone-addon"])

DEFAULT_PRICING = {"credits": 250, "price_eur_cents": 12500}


async def get_zone_addon_pricing(db) -> dict:
    doc = await db.system_flags.find_one({"key": "zone_addon_pricing"}) or {}
    return {"credits": int(doc.get("credits", DEFAULT_PRICING["credits"])),
            "price_eur_cents": int(doc.get("price_eur_cents", DEFAULT_PRICING["price_eur_cents"]))}


@zone_addon_router.get("/pricing")
async def zone_addon_pricing(current_user: dict = Depends(get_current_user)):
    """Tarif public de la zone additionnelle."""
    return await get_zone_addon_pricing(get_database())


@zone_addon_router.put("/admin/pricing")
async def set_zone_addon_pricing(body: dict, current_user: dict = Depends(get_current_user)):
    """Réglage du tarif zone additionnelle (Super Admin)."""
    await check_admin(current_user)
    db = get_database()
    try:
        credits = max(0, int(body.get("credits")))
        cents = max(0, int(body.get("price_eur_cents")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Valeurs invalides")
    await db.system_flags.update_one(
        {"key": "zone_addon_pricing"},
        {"$set": {"credits": credits, "price_eur_cents": cents,
                  "updated_by": current_user.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True, "credits": credits, "price_eur_cents": cents}


async def _resolve_zone_context(db, user: dict, zone_code: str):
    membership = await db.org_memberships.find_one({"user_id": user["id"]})
    if not membership:
        raise HTTPException(status_code=400, detail="Aucune organisation associée à votre compte")
    org_id = membership["org_id"]
    zone = await db.zones_v2.find_one({"code": zone_code, "is_active": True})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    existing = await db.org_zone_entitlements.find_one(
        {"org_id": org_id, "zone_id": zone["id"], "status": "ACTIVE"})
    if existing:
        raise HTTPException(status_code=400, detail="Cette zone est déjà incluse dans votre abonnement")
    return org_id, zone


async def _activate_zone(db, org_id: str, zone: dict, payment_ref: str):
    now = datetime.utcnow()
    await db.org_zone_entitlements.update_one(
        {"org_id": org_id, "zone_id": zone["id"]},
        {"$set": {"org_id": org_id, "zone_id": zone["id"], "source": "OPTION",
                  "status": "ACTIVE", "starts_at": now, "payment_ref": payment_ref},
         "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}},
        upsert=True)
    logger.info("Zone add-on activée : org=%s zone=%s (%s)", org_id, zone["code"], payment_ref)


@zone_addon_router.post("/purchase-credits")
async def purchase_zone_with_credits(body: dict, current_user: dict = Depends(get_current_user)):
    """Achat d'une zone additionnelle en crédits CREDI'SCOP (débit immédiat)."""
    db = get_database()
    org_id, zone = await _resolve_zone_context(db, current_user, (body.get("zone_code") or "").strip())
    pricing = await get_zone_addon_pricing(db)
    cost = pricing["credits"]
    balance = current_user.get("credits", 0)
    if balance < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Solde insuffisant : {cost} crédits requis, vous en avez {balance}. Achetez des crédits depuis votre portefeuille.")
    res = await db.users.update_one(
        {"id": current_user["id"], "credits": {"$gte": cost}},
        {"$inc": {"credits": -cost}})
    if res.modified_count == 0:
        raise HTTPException(status_code=402, detail="Solde insuffisant")
    await _activate_zone(db, org_id, zone, f"credits:{current_user['id']}")
    await db.credits_history.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"], "type": "spent",
        "amount": cost, "description": f"Zone additionnelle — {zone['name']}",
        "created_at": datetime.utcnow()})
    new_balance = balance - cost
    return {"ok": True, "zone_code": zone["code"], "zone_name": zone["name"],
            "credits_spent": cost, "new_credits": new_balance}


@zone_addon_router.post("/checkout")
async def zone_addon_checkout(body: dict, current_user: dict = Depends(get_current_user)):
    """Crée une session Stripe pour l'achat d'une zone additionnelle par carte."""
    db = get_database()
    org_id, zone = await _resolve_zone_context(db, current_user, (body.get("zone_code") or "").strip())
    pricing = await get_zone_addon_pricing(db)
    origin = (body.get("origin_url") or "").rstrip("/")
    if not origin:
        raise HTTPException(status_code=400, detail="origin_url requis")
    from routes_payment import _wallet_stripe_key
    try:
        stripe.api_base = "https://api.stripe.com"
        session = stripe.checkout.Session.create(
            api_key=_wallet_stripe_key(),
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": pricing["price_eur_cents"],
                    "product_data": {"name": f"KDMARCHÉ — Zone additionnelle : {zone['name']}"},
                },
                "quantity": 1,
            }],
            success_url=f"{origin}/catalogue?zone_payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/catalogue?zone_payment=cancelled",
            metadata={"user_id": current_user["id"], "org_id": org_id,
                      "zone_id": zone["id"], "zone_code": zone["code"],
                      "source": "zone_addon"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Zone add-on checkout : %s", e)
        raise HTTPException(status_code=500, detail="Erreur création session de paiement")
    await db.zone_addon_transactions.insert_one({
        "id": f"zad_{uuid.uuid4().hex[:12]}", "session_id": session.id,
        "user_id": current_user["id"], "org_id": org_id,
        "zone_id": zone["id"], "zone_code": zone["code"], "zone_name": zone["name"],
        "amount_cents": pricing["price_eur_cents"], "currency": "EUR",
        "status": "INITIATED", "activated": False,
        "created_at": datetime.now(timezone.utc)})
    return {"checkout_url": session.url, "session_id": session.id}


@zone_addon_router.get("/status/{session_id}")
async def zone_addon_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Vérifie le paiement Stripe et active la zone (idempotent)."""
    db = get_database()
    txn = await db.zone_addon_transactions.find_one(
        {"session_id": session_id, "user_id": current_user["id"]})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction non trouvée")
    from routes_payment import _wallet_stripe_key
    try:
        stripe.api_base = "https://api.stripe.com"
        session = stripe.checkout.Session.retrieve(session_id, api_key=_wallet_stripe_key())
    except Exception as e:
        logger.error("Zone add-on status : %s", e)
        raise HTTPException(status_code=500, detail="Erreur vérification du paiement")
    activated = txn.get("activated", False)
    if session.payment_status == "paid" and not activated:
        zone = await db.zones_v2.find_one({"id": txn["zone_id"]})
        if zone:
            await _activate_zone(db, txn["org_id"], zone, f"stripe:{session_id}")
        activated = True
        await db.zone_addon_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "PAID", "activated": True,
                      "updated_at": datetime.now(timezone.utc)}})
    elif session.status == "expired":
        await db.zone_addon_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "EXPIRED", "updated_at": datetime.now(timezone.utc)}})
    return {"session_id": session_id, "payment_status": session.payment_status,
            "activated": activated, "zone_code": txn["zone_code"], "zone_name": txn.get("zone_name")}
