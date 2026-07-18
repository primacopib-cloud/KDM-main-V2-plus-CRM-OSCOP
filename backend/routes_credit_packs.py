"""Packs de crédits achetables via Stripe + analytics crédits — /api/credit-packs, /api/admin/credit-analytics."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from admin_guard import require_admin
from auth import get_current_user_id

credit_packs_router = APIRouter(prefix="/api/credit-packs", tags=["Credit Packs"])
credit_analytics_router = APIRouter(prefix="/api/admin/credit-analytics", tags=["Credit Analytics"])

db = None


async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user

DEFAULT_PACKS = [
    ("starter", "Pack Starter", 50, 9.90),
    ("pro", "Pack Pro", 200, 29.90),
    ("studio", "Pack Studio", 500, 59.90),
]


def set_credit_packs_database(database) -> None:
    global db
    db = database


async def seed_credit_packs() -> None:
    if await db.credit_packs.count_documents({}) == 0:
        await db.credit_packs.insert_many([
            {"id": pid, "name": name, "credits": credits, "price_eur": price, "active": True}
            for pid, name, credits, price in DEFAULT_PACKS
        ])


@credit_packs_router.get("")
async def list_credit_packs():
    from credit_promotions import get_purchase_bonus_percent

    packs = await db.credit_packs.find({"active": True}, {"_id": 0}).sort("price_eur", 1).to_list(20)
    bonus = await get_purchase_bonus_percent("vendor")
    return {"packs": packs, "bonus_percent": bonus}


class PurchasePayload(BaseModel):
    pack_id: str
    vendor_id: str
    origin_url: str


@credit_packs_router.post("/purchase")
async def purchase_credit_pack(payload: PurchasePayload, user: dict = Depends(get_current_user)):
    from routes_lolodrive_checkout import _create_checkout_session
    from stripe_accounts import get_account_for_checkout_kind

    pack = await db.credit_packs.find_one({"id": payload.pack_id, "active": True}, {"_id": 0})
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    vendor = await db.vendors.find_one({"id": payload.vendor_id}, {"_id": 0, "id": 1})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")

    account = get_account_for_checkout_kind("RECHARGE")
    base = payload.origin_url.rstrip("/")
    metadata = {"kind": "CREDIT_PACK", "user_id": user["id"], "vendor_id": payload.vendor_id,
                "pack_id": pack["id"], "credits": str(pack["credits"]), "stripe_account": account}
    session = _create_checkout_session(
        account=account,
        amount_eur=pack["price_eur"],
        success_url=f"{base}/espace-vendeur?credit_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/espace-vendeur?credit_cancelled=1",
        metadata=metadata,
        product_name=f"KDMARCHÉ — {pack['name']} ({pack['credits']} crédits)",
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session["id"], "user_id": user["id"],
        "kind": "CREDIT_PACK", "vendor_id": payload.vendor_id, "pack_id": pack["id"],
        "stripe_account": account, "amount_cents": int(round(pack["price_eur"] * 100)),
        "currency": "eur", "payment_status": "initiated", "metadata": metadata,
        "applied": False, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    })
    return {"url": session["url"], "session_id": session["id"]}


@credit_packs_router.get("/status/{session_id}")
async def credit_pack_status(session_id: str, user: dict = Depends(get_current_user)):
    """Poll Stripe et crédite le vendeur (idempotent) avec bonus promo éventuel."""
    import stripe
    from stripe_accounts import get_stripe_key
    from credit_promotions import get_purchase_bonus_percent

    tx = await db.payment_transactions.find_one({"session_id": session_id, "kind": "CREDIT_PACK"})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if tx["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.retrieve(session_id, api_key=get_stripe_key(tx["stripe_account"]))
    status = session.payment_status
    await db.payment_transactions.update_one(
        {"session_id": session_id}, {"$set": {"payment_status": status, "updated_at": datetime.utcnow()}}
    )
    credited = 0
    if status == "paid":
        claim = await db.payment_transactions.update_one(
            {"session_id": session_id, "applied": {"$ne": True}},
            {"$set": {"applied": True, "applied_at": datetime.utcnow(), "applied_by": "polling"}},
        )
        if claim.modified_count == 1:
            pack_credits = int(tx["metadata"]["credits"])
            bonus_pct = await get_purchase_bonus_percent("vendor")
            bonus = int(round(pack_credits * bonus_pct / 100))
            credited = pack_credits + bonus
            await db.vendors.update_one({"id": tx["vendor_id"]}, {"$inc": {"credits": credited}})
            vendor = await db.vendors.find_one({"id": tx["vendor_id"]}, {"_id": 0, "credits": 1})
            await db.credit_transactions.insert_one({
                "id": str(uuid.uuid4()), "vendor_id": tx["vendor_id"], "owner_type": "vendor",
                "action": "pack_purchase", "cost": -credited,
                "detail": f"Achat {tx['pack_id']} ({pack_credits} crédits"
                          + (f" + {bonus} bonus {bonus_pct:.0f}%" if bonus else "") + ")",
                "balance_after": int((vendor or {}).get("credits") or 0),
                "at": datetime.utcnow().isoformat(),
            })
            try:
                await _send_invoice_email(tx, pack_credits, bonus, credited)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error("Invoice email failed: %s", exc)
    tx_after = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0, "payment_status": 1, "applied": 1})
    return {"payment_status": tx_after["payment_status"], "applied": tx_after.get("applied", False), "credited": credited}


async def _send_invoice_email(tx: dict, pack_credits: int, bonus: int, credited: int) -> None:
    """Facture PDF envoyée par email au vendeur après paiement d'un pack."""
    import base64
    from brevo_service import is_brevo_configured, send_email, _wrap_html
    from pdf_credit_invoice import generate_credit_invoice_pdf

    if not is_brevo_configured():
        return
    vendor = await db.vendors.find_one({"id": tx["vendor_id"]}, {"_id": 0}) or {}
    if not vendor.get("email"):
        return
    pack = await db.credit_packs.find_one({"id": tx["pack_id"]}, {"_id": 0}) or \
        {"name": tx["pack_id"], "credits": pack_credits}
    amount_eur = tx["amount_cents"] / 100
    pdf = generate_credit_invoice_pdf(vendor, pack, credited, bonus, amount_eur, tx["session_id"])
    body = (
        f"<p>Bonjour {vendor.get('contact_name', '')},</p>"
        f"<p>Merci pour votre achat ! <strong>{credited} crédits</strong> "
        + (f"(dont {bonus} offerts) " if bonus else "")
        + f"ont été ajoutés à votre solde pour <strong>{amount_eur:.2f} €</strong>.</p>"
        "<p>Vous trouverez votre facture en pièce jointe.</p>"
    )
    await send_email(
        to_email=vendor["email"], to_name=vendor.get("contact_name"),
        subject=f"Votre facture KDMARCHÉ — {pack['name']} ({credited} crédits)",
        html_content=_wrap_html("Facture — Pack de crédits", body),
        tags=["credit-invoice"],
        attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"facture-credits-{tx['session_id'][-8:]}.pdf"}],
    )


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


@credit_analytics_router.get("")
async def credit_analytics(_: dict = Depends(_admin)):
    """Crédits achetés / consommés / remboursés, ventilés par service, profil, vendeur, territoire, catégorie."""
    async def group_by(field: str, match: dict):
        pipeline = [
            {"$match": match},
            {"$group": {"_id": f"${field}", "credits": {"$sum": "$cost"}, "count": {"$sum": 1}}},
            {"$sort": {"credits": -1}}, {"$limit": 20},
        ]
        return [{"key": r["_id"] or "N/A", "credits": r["credits"], "count": r["count"]}
                async for r in db.credit_transactions.aggregate(pipeline)]

    consumed_match = {"cost": {"$gt": 0}}
    purchased_pipeline = [
        {"$match": {"action": "pack_purchase"}},
        {"$group": {"_id": None, "credits": {"$sum": {"$abs": "$cost"}}, "count": {"$sum": 1}}},
    ]
    purchased = [r async for r in db.credit_transactions.aggregate(purchased_pipeline)]
    refunded_pipeline = [
        {"$match": {"action": {"$regex": "^refund_"}}},
        {"$group": {"_id": None, "credits": {"$sum": {"$abs": "$cost"}}, "count": {"$sum": 1}}},
    ]
    refunded = [r async for r in db.credit_transactions.aggregate(refunded_pipeline)]
    consumed_total = [r async for r in db.credit_transactions.aggregate(
        [{"$match": consumed_match}, {"$group": {"_id": None, "credits": {"$sum": "$cost"}, "count": {"$sum": 1}}}]
    )]
    revenue = [r async for r in db.payment_transactions.aggregate(
        [{"$match": {"kind": "CREDIT_PACK", "payment_status": "paid"}},
         {"$group": {"_id": None, "cents": {"$sum": "$amount_cents"}, "count": {"$sum": 1}}}]
    )]
    return {
        "totals": {
            "purchased": (purchased[0]["credits"] if purchased else 0),
            "purchases_count": (purchased[0]["count"] if purchased else 0),
            "consumed": (consumed_total[0]["credits"] if consumed_total else 0),
            "refunded": (refunded[0]["credits"] if refunded else 0),
            "revenue_eur": round((revenue[0]["cents"] if revenue else 0) / 100, 2),
        },
        "by_service": await group_by("action", consumed_match),
        "by_vendor": await group_by("vendor_id", consumed_match),
        "by_territory": await group_by("territory", consumed_match),
        "by_category": await group_by("category", consumed_match),
        "by_profile": await group_by("owner_type", consumed_match),
    }
