"""API publique v1 pour connecteurs ERP partenaires — authentification par clé API (header X-API-Key)."""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

public_api_router = APIRouter(prefix="/api/public/v1", tags=["public-api-v1"])

db = None


def set_public_api_database(database):
    global db
    db = database


async def _resolve_key(x_api_key: Optional[str], request: Optional[Request] = None) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Header X-API-Key manquant")
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    key = await db.api_keys.find_one({"key_hash": key_hash})
    if not key:
        raise HTTPException(status_code=401, detail="Clé API invalide")
    if not key.get("is_active", True):
        raise HTTPException(status_code=403, detail="Clé API désactivée")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    if key.get("usage_month") != month:
        await db.api_keys.update_one({"id": key["id"]}, {"$set": {"usage_month": month, "month_usage": 0}})
        key["month_usage"] = 0
    quota = key.get("monthly_quota") or 10000
    if (key.get("month_usage") or 0) >= quota:
        raise HTTPException(status_code=429, detail=f"Quota mensuel atteint ({quota} requêtes) — contactez l'administrateur")
    await db.api_keys.update_one({"id": key["id"]}, {
        "$set": {"last_used_at": datetime.now(timezone.utc).isoformat()},
        "$inc": {"requests_count": 1, "month_usage": 1},
    })
    if request is not None:
        await db.api_call_logs.insert_one({
            "key_id": key["id"], "method": request.method, "path": request.url.path,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    return key


def require_scope(scope: str):
    async def dep(request: Request, x_api_key: Optional[str] = Header(None)):
        key = await _resolve_key(x_api_key, request)
        if scope not in (key.get("scopes") or []):
            raise HTTPException(status_code=403, detail=f"Scope requis : {scope}")
        return key
    return dep


@public_api_router.get("/ping")
async def ping(request: Request, x_api_key: Optional[str] = Header(None)):
    """Vérifie la validité de la clé et renvoie ses scopes."""
    key = await _resolve_key(x_api_key, request)
    return {"ok": True, "name": key.get("name"), "scopes": key.get("scopes", []),
            "monthly_quota": key.get("monthly_quota") or 10000, "month_usage": (key.get("month_usage") or 0) + 1}


@public_api_router.get("/products")
async def list_products(
    key: dict = Depends(require_scope("catalog:read")),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    category_id: Optional[str] = None,
):
    q = {"status": {"$in": ["ACTIVE", "active", "APPROVED"]}}
    if category_id:
        q["category_id"] = category_id
    total = await db.products.count_documents(q)
    items = await db.products.find(q, {"_id": 0}).sort("name", 1).skip(offset).limit(limit).to_list(limit)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@public_api_router.get("/products/{product_id}")
async def get_product(product_id: str, key: dict = Depends(require_scope("catalog:read"))):
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p


class StockBody(BaseModel):
    stock_qty: int


@public_api_router.patch("/products/{product_id}/stock")
async def update_stock(product_id: str, body: StockBody, key: dict = Depends(require_scope("stock:write"))):
    """Synchronisation du stock depuis un ERP externe."""
    if body.stock_qty < 0:
        raise HTTPException(status_code=400, detail="stock_qty doit être positif")
    res = await db.products.update_one({"id": product_id}, {"$set": {
        "external_stock_qty": body.stock_qty,
        "external_stock_synced_at": datetime.now(timezone.utc).isoformat(),
        "external_stock_source": key.get("name"),
    }})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    from consultation_audit import audit
    await audit("ERP_STOCK_SYNC", f"api-key:{key.get('name')}", None,
                {"product_id": product_id, "stock_qty": body.stock_qty})
    return {"ok": True, "product_id": product_id, "stock_qty": body.stock_qty}


@public_api_router.get("/orders")
async def list_orders(
    key: dict = Depends(require_scope("orders:read")),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    status: Optional[str] = None, zone_code: Optional[str] = None,
):
    q = {}
    if status:
        q["status"] = status
    if zone_code:
        q["zone_code"] = zone_code.upper()
    total = await db.orders.count_documents(q)
    proj = {"_id": 0, "id": 1, "order_number": 1, "zone_code": 1, "status": 1, "incoterm": 1,
            "items": 1, "items_count": 1, "subtotal_ht_cents": 1, "tax_cents": 1,
            "total_ttc_cents": 1, "created_at": 1, "updated_at": 1, "logistics": 1}
    items = await db.orders.find(q, proj).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@public_api_router.get("/orders/{order_id}")
async def get_order(order_id: str, key: dict = Depends(require_scope("orders:read"))):
    proj = {"_id": 0, "id": 1, "order_number": 1, "zone_code": 1, "status": 1, "incoterm": 1,
            "items": 1, "items_count": 1, "subtotal_ht_cents": 1, "tax_cents": 1,
            "total_ttc_cents": 1, "created_at": 1, "updated_at": 1, "logistics": 1}
    o = await db.orders.find_one({"$or": [{"id": order_id}, {"order_number": order_id}]}, proj)
    if not o:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return o


@public_api_router.get("/territories")
async def list_territories(key: dict = Depends(require_scope("territories:read"))):
    items = await db.zones_v2.find({"is_active": {"$ne": False}}, {"_id": 0, "code": 1, "name": 1, "kind": 1}).sort("code", 1).to_list(100)
    return {"items": items}
