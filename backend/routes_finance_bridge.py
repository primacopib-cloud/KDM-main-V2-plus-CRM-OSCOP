"""KDM → finance-api bridge routes — admin-only.

These routes live INSIDE the KDM backend (port 8001) but every business call
is delegated to the external `finance-api` microservice via
`FinanceExternalClient`. Each call is logged in the local Mongo collection
`finance_bridge_sync_events` for audit + retry.

Mounted by server.py with:
    from routes_finance_bridge import finance_bridge_router, set_finance_bridge_database
    set_finance_bridge_database(db)
    app.include_router(finance_bridge_router)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Reuse the KDM auth dependency from auth.py (avoid circular import via server.py)
from auth import get_current_user_id

from finance_external_client import FinanceExternalClient, FinanceExternalError

logger = logging.getLogger(__name__)

finance_bridge_router = APIRouter(prefix="/api/finance-bridge", tags=["finance-bridge"])

db = None  # set by set_finance_bridge_database(db)


def set_finance_bridge_database(database) -> None:
    global db
    db = database


def _new_id() -> str:
    return f"finsync-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


async def ensure_finance_bridge_indexes(database) -> None:
    """Called at startup by server.py."""
    await database.finance_bridge_sync_events.create_index("id", unique=True)
    await database.finance_bridge_sync_events.create_index(
        [("source", 1), ("source_id", 1), ("created_at", -1)]
    )
    await database.finance_bridge_sync_events.create_index([("status", 1), ("created_at", -1)])


async def _require_admin(user_id: str) -> Dict[str, Any]:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    if user.get("is_admin"):
        return user
    role = (user.get("role") or "").upper()
    if role in {"SUPER_ADMIN", "ADMIN", "COOP_BOARD", "OSCOP_SUPER_ADMIN", "KDM_B2B_ADMIN"}:
        return user
    raise HTTPException(status_code=403, detail="Réservé aux administrateurs")


async def _record(
    *,
    source: str,
    source_id: str,
    direction: str,
    status: str,
    payload: Optional[Dict[str, Any]],
    response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    doc = {
        "id": _new_id(),
        "source": source,
        "source_id": source_id,
        "direction": direction,
        "status": status,
        "payload": payload or {},
        "response": response or {},
        "created_at": datetime.utcnow(),
    }
    await db.finance_bridge_sync_events.insert_one(doc)
    doc.pop("_id", None)
    return doc


def _as_public_http_error(exc: FinanceExternalError) -> HTTPException:
    code = 502
    if exc.status_code and 400 <= exc.status_code < 500:
        code = exc.status_code
    return HTTPException(status_code=code, detail=str(exc))


# ============================================================
# Health
# ============================================================

@finance_bridge_router.get("/health")
async def finance_bridge_health(user_id: str = Depends(get_current_user_id)):
    """Returns a readable status: OK / DEGRADED / DISABLED. Always HTTP 200.

    DISABLED  : env vars manquantes
    DEGRADED  : microservice finance-api injoignable
    OK        : finance-api répond + flags config exposés
    """
    await _require_admin(user_id)
    client = FinanceExternalClient()
    cfg = client.config
    if not cfg.enabled:
        return {
            "bridge": "OK",
            "status": "DISABLED",
            "message": "FINANCE_API_URL / FINANCE_API_EMAIL / FINANCE_API_PASSWORD non configurés.",
            "config": {
                "url_configured": bool(cfg.base_url),
                "credentials_configured": bool(cfg.email and cfg.password),
                "timeout_seconds": cfg.timeout_seconds,
            },
        }
    try:
        external = client.health()
        return {
            "bridge": "OK",
            "status": "OK",
            "external_finance": external,
            "config": {
                "url_configured": True,
                "url": cfg.base_url,
                "credentials_configured": True,
                "timeout_seconds": cfg.timeout_seconds,
            },
        }
    except FinanceExternalError as exc:
        return {
            "bridge": "OK",
            "status": "DEGRADED",
            "error": str(exc),
            "message": "Microservice finance-api injoignable. Vérifier port 8030/8010 + credentials.",
            "config": {
                "url_configured": True,
                "url": cfg.base_url,
                "credentials_configured": True,
                "timeout_seconds": cfg.timeout_seconds,
            },
        }


# ============================================================
# Parties — from a KDM customer (user)
# ============================================================

class PushPartyResponse(BaseModel):
    party: Dict[str, Any]
    sync_event: Dict[str, Any]


@finance_bridge_router.post("/parties/from-customer/{customer_id}", response_model=PushPartyResponse)
async def push_party_from_customer(customer_id: str, user_id: str = Depends(get_current_user_id)):
    """Crée (ou récupère) un `Party` dans finance-api à partir d'un user KDM."""
    await _require_admin(user_id)
    customer = await db.users.find_one({"id": customer_id}, {"_id": 0, "password_hash": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Client KDM introuvable")

    payload = {
        "party_type": "company" if customer.get("company_name") else "individual",
        "display_name": customer.get("company_name") or customer.get("contact_name") or customer.get("email") or customer_id,
        "legal_name": customer.get("company_name") or "",
        "siret": customer.get("siret") or "",
        "email": customer.get("email") or "",
        "phone": customer.get("phone") or "",
        "city": customer.get("city") or "",
        "country": customer.get("country") or "FR",
        "external_customer_id": customer_id,
        "metadata_json": {
            "kdm_role": customer.get("role"),
            "kdm_subscription": customer.get("subscription"),
        },
    }

    client = FinanceExternalClient()
    try:
        existing = client.find_party_by_external_id(customer_id)
        if existing:
            event = await _record(source="kdm_customer", source_id=customer_id, direction="OUTBOUND",
                                  status="SUCCESS_IDEMPOTENT", payload=payload, response=existing)
            return {"party": existing, "sync_event": event}
        created = client.create_party(payload)
        event = await _record(source="kdm_customer", source_id=customer_id, direction="OUTBOUND",
                              status="SUCCESS", payload=payload, response=created)
        return {"party": created, "sync_event": event}
    except FinanceExternalError as exc:
        await _record(source="kdm_customer", source_id=customer_id, direction="OUTBOUND",
                      status="ERROR", payload=payload, response={"error": str(exc)})
        raise _as_public_http_error(exc)


# ============================================================
# Receivables — from a KDM LOLODRIVE order
# ============================================================

@finance_bridge_router.post("/receivables/from-order/{order_id}")
async def push_receivable_from_order(order_id: str, user_id: str = Depends(get_current_user_id)):
    """Crée un `Receivable` dans finance-api à partir d'une commande LOLODRIVE.

    Garantit qu'un `Party` existe d'abord (via le user_id de la commande).
    """
    await _require_admin(user_id)
    order = await db.lolodrive_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande LOLODRIVE introuvable")

    customer_id = order.get("user_id")
    customer = await db.users.find_one({"id": customer_id}, {"_id": 0, "password_hash": 0}) if customer_id else None

    client = FinanceExternalClient()
    party_id: Optional[str] = None
    try:
        # 1) Resolve/create party
        if customer:
            existing = client.find_party_by_external_id(customer_id)
            if existing:
                party_id = existing.get("id")
            else:
                created = client.create_party({
                    "party_type": "company" if customer.get("company_name") else "individual",
                    "display_name": customer.get("company_name") or customer.get("contact_name") or customer.get("email") or customer_id,
                    "legal_name": customer.get("company_name") or "",
                    "siret": customer.get("siret") or "",
                    "email": customer.get("email") or "",
                    "phone": customer.get("phone") or "",
                    "city": customer.get("city") or "",
                    "country": customer.get("country") or "FR",
                    "external_customer_id": customer_id,
                })
                party_id = created.get("id")
        if not party_id:
            raise HTTPException(status_code=400, detail="Commande sans utilisateur lié — impossible de créer une créance")

        # 2) Create receivable
        payload = {
            "party_id": party_id,
            "receivable_type": "ORDER",
            "reference": order.get("order_number") or order.get("id"),
            "title": f"Commande LOLODRIVE {order.get('order_number') or order.get('id')}",
            "description": f"{len(order.get('items') or [])} articles — {order.get('fulfillment_type') or ''}",
            "amount_cents": int(order.get("total_cents") or 0),
            "currency": "EUR",
            "external_source": "kdm_lolodrive_order",
            "external_id": order.get("id"),
            "metadata_json": {
                "items_count": len(order.get("items") or []),
                "fulfillment_type": order.get("fulfillment_type"),
                "stripe_payment_intent_id": order.get("stripe_payment_intent_id") or "",
                "stripe_account": order.get("stripe_account") or "",
            },
        }
        receivable = client.create_receivable(payload)
        event = await _record(source="kdm_lolodrive_order", source_id=order_id, direction="OUTBOUND",
                              status="SUCCESS", payload=payload, response=receivable)
        return {"receivable": receivable, "party_id": party_id, "sync_event": event}
    except FinanceExternalError as exc:
        await _record(source="kdm_lolodrive_order", source_id=order_id, direction="OUTBOUND",
                      status="ERROR", payload={"order_id": order_id}, response={"error": str(exc)})
        raise _as_public_http_error(exc)


# ============================================================
# Generic passthroughs (payments / installments / sepa)
# ============================================================

class GenericPayload(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


@finance_bridge_router.post("/payments/create")
async def create_payment(body: GenericPayload, user_id: str = Depends(get_current_user_id)):
    await _require_admin(user_id)
    client = FinanceExternalClient()
    try:
        resp = client.create_payment(body.payload)
        event = await _record(source="kdm_payment_request", source_id=resp.get("id", ""), direction="OUTBOUND",
                              status="SUCCESS", payload=body.payload, response=resp)
        return {"payment": resp, "sync_event": event}
    except FinanceExternalError as exc:
        await _record(source="kdm_payment_request", source_id="", direction="OUTBOUND",
                      status="ERROR", payload=body.payload, response={"error": str(exc)})
        raise _as_public_http_error(exc)


@finance_bridge_router.post("/installment-plans/create")
async def create_installment_plan(body: GenericPayload, user_id: str = Depends(get_current_user_id)):
    await _require_admin(user_id)
    client = FinanceExternalClient()
    try:
        resp = client.create_installment_plan(body.payload)
        event = await _record(source="kdm_installment_plan", source_id=resp.get("id", ""), direction="OUTBOUND",
                              status="SUCCESS", payload=body.payload, response=resp)
        return {"plan": resp, "sync_event": event}
    except FinanceExternalError as exc:
        await _record(source="kdm_installment_plan", source_id="", direction="OUTBOUND",
                      status="ERROR", payload=body.payload, response={"error": str(exc)})
        raise _as_public_http_error(exc)


@finance_bridge_router.post("/sepa/mandates/create")
async def create_sepa_mandate(body: GenericPayload, user_id: str = Depends(get_current_user_id)):
    await _require_admin(user_id)
    client = FinanceExternalClient()
    try:
        resp = client.create_sepa_mandate(body.payload)
        event = await _record(source="kdm_sepa_mandate", source_id=resp.get("id", ""), direction="OUTBOUND",
                              status="SUCCESS", payload=body.payload, response=resp)
        return {"mandate": resp, "sync_event": event}
    except FinanceExternalError as exc:
        await _record(source="kdm_sepa_mandate", source_id="", direction="OUTBOUND",
                      status="ERROR", payload=body.payload, response={"error": str(exc)})
        raise _as_public_http_error(exc)


# ============================================================
# Sync events journal
# ============================================================

@finance_bridge_router.get("/sync-events")
async def list_sync_events(
    user_id: str = Depends(get_current_user_id),
    source: Optional[str] = None,
    status: Optional[str] = Query(None, description="SUCCESS | SUCCESS_IDEMPOTENT | ERROR"),
    limit: int = Query(100, ge=1, le=500),
):
    await _require_admin(user_id)
    query: Dict[str, Any] = {}
    if source:
        query["source"] = source
    if status:
        query["status"] = status
    cursor = db.finance_bridge_sync_events.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    events = await cursor.to_list(limit)
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    agg = await db.finance_bridge_sync_events.aggregate(pipeline).to_list(10)
    counts = {row["_id"]: row["count"] for row in agg}
    return {
        "events": events,
        "counts": {
            "total": sum(counts.values()),
            "success": counts.get("SUCCESS", 0) + counts.get("SUCCESS_IDEMPOTENT", 0),
            "error": counts.get("ERROR", 0),
        },
    }
