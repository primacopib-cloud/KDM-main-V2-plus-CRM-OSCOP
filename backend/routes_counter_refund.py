"""Retour / remboursement d'articles d'une vente au comptoir (scan du QR du ticket)."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import get_current_user
from routes_relay_products import _manager_point, log_stock_movement

counter_refund_router = APIRouter(prefix="/api/lolodrive", tags=["Retours comptoir"])
db = None


def set_counter_refund_database(database):
    global db
    db = database


async def _scoped_order(user_id: str, order_id: str):
    point = await _manager_point(user_id)
    order = await db.lolodrive_orders.find_one(
        {"id": order_id, "lolo_point_id": point["id"], "channel": "COUNTER"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Vente introuvable pour ce relais")
    return point, order


@counter_refund_router.get("/pos/counter-sale/{order_id}")
async def get_counter_sale(order_id: str, user: dict = Depends(get_current_user)):
    """Détail d'une vente au comptoir (pour le dialogue de retour, quantités déjà retournées incluses)."""
    _, order = await _scoped_order(user["id"], order_id)
    return {"order": order}


@counter_refund_router.post("/pos/counter-sale/{order_id}/refund")
async def refund_counter_sale(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Retour d'articles : remise en stock + remboursement (UC si payé en UC, sinon espèces)."""
    point, order = await _scoped_order(user["id"], order_id)
    wanted = {i.get("sku"): int(i.get("qty") or 0) for i in (payload or {}).get("items", []) if i.get("sku")}
    wanted = {k: v for k, v in wanted.items() if v > 0}
    if not wanted:
        raise HTTPException(status_code=400, detail="Aucun article à retourner")
    lines = {l["sku"]: l for l in order.get("items", [])}
    refund_cents = 0
    for sku, qty in wanted.items():
        line = lines.get(sku)
        if not line:
            raise HTTPException(status_code=400, detail=f"Article {sku} absent de la vente")
        available = line["qty"] - int(line.get("returned_qty") or 0)
        if qty > available:
            raise HTTPException(status_code=400, detail=f"{line['name']} : {available} retour(s) possible(s) au maximum")
        refund_cents += line["unit_cents"] * qty
    now = datetime.utcnow()
    method = "UC" if order.get("payment_method") == "UC" else "CASH"
    uc_refunded = None
    if method == "UC":
        if not order.get("user_id"):
            raise HTTPException(status_code=400, detail="Client inconnu : remboursement UC impossible")
        uc_refunded = round(refund_cents / 10, 1)
        wallet = await db.lolodrive_wallets.find_one({"user_id": order["user_id"]})
        if not wallet:
            raise HTTPException(status_code=400, detail="Wallet client introuvable")
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]}, {"$inc": {"balance_uc": uc_refunded}, "$set": {"updated_at": now}})
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
            "amount_uc": uc_refunded, "reason": "COUNTER_REFUND_UC",
            "order_number": order.get("order_number"), "created_at": now})
    # Remise en stock + quantités retournées sur la vente
    new_items = []
    for l in order.get("items", []):
        qty = wanted.get(l["sku"], 0)
        if qty:
            l = {**l, "returned_qty": int(l.get("returned_qty") or 0) + qty}
            from pymongo import ReturnDocument
            res = await db.lolodrive_products.find_one_and_update(
                {"sku": l["sku"], "stock_qty": {"$ne": None}},
                [{"$set": {"stock_qty": {"$add": [{"$ifNull": ["$stock_qty", 0]}, qty]}}}],
                return_document=ReturnDocument.AFTER, projection={"_id": 0, "stock_qty": 1})
            if res is not None:
                await log_stock_movement(l["sku"], l.get("name", l["sku"]), "RETURN", qty,
                                         res["stock_qty"], point.get("code"), order.get("order_number"))
        new_items.append(l)
    refund_doc = {"id": str(uuid.uuid4()), "order_id": order_id, "order_number": order.get("order_number"),
                  "point_id": point["id"], "items": [{"sku": s, "qty": q} for s, q in wanted.items()],
                  "amount_cents": refund_cents, "uc_refunded": uc_refunded, "method": method,
                  "operator_name": user.get("contact_name") or user.get("email"), "created_at": now}
    await db.counter_refunds.insert_one(dict(refund_doc))
    await db.lolodrive_orders.update_one(
        {"id": order_id}, {"$set": {"items": new_items, "updated_at": now},
                           "$inc": {"refunded_cents": refund_cents}})
    refund_doc.pop("_id", None)
    refund_doc["created_at"] = now.isoformat()
    return {"ok": True, "refunded_cents": refund_cents, "uc_refunded": uc_refunded, "method": method}
