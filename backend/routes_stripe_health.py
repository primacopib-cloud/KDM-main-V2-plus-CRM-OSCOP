"""KDMARCHE Admin Stripe — Transactions détaillées & health-check LIVE (split from routes_stripe_reconciliation.py)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import os
import logging
import stripe

from auth import get_current_user_id
from stripe_accounts import AccountName, get_stripe_key

logger = logging.getLogger(__name__)

stripe_health_router = APIRouter(
    prefix="/api/admin/stripe", tags=["Admin · Stripe Reconciliation"]
)

db = None

def set_stripe_health_database(database):
    global db
    db = database

from routes_stripe_reconciliation import _require_admin, _parse_date

# ---------------- Transactions list (paginated, with refund status) ----------------

@stripe_health_router.get("/reconciliation/transactions")
async def stripe_reconciliation_transactions(
    user_id: str = Depends(get_current_user_id),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status_filter: str = Query("all", description="all | paid | refunded_full | refunded_partial"),
    account: Optional[str] = Query(None, description="oscop | kdmarche"),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
):
    """List flat transactions with refund status, for the admin reconciliation table."""
    await _require_admin(user_id)

    now_utc = datetime.now(timezone.utc)
    dt_to = _parse_date(date_to, now_utc) + timedelta(days=1)
    dt_from = _parse_date(date_from, now_utc - timedelta(days=30))
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="date_from doit être ≤ date_to")

    query: dict = {"applied": True, "applied_at": {"$gte": dt_from, "$lte": dt_to}}
    if status_filter == "paid":
        query["$or"] = [
            {"refund_status": {"$exists": False}},
            {"refund_status": None},
            {"refund_status": ""},
        ]
    elif status_filter == "refunded_full":
        query["refund_status"] = "full"
    elif status_filter == "refunded_partial":
        query["refund_status"] = "partial"
    elif status_filter == "refunded":
        query["refund_status"] = {"$in": ["full", "partial"]}

    if account in ("oscop", "kdmarche"):
        query["stripe_account"] = account

    total = await db.payment_transactions.count_documents(query)
    cursor = (
        db.payment_transactions.find(query, {"_id": 0})
        .sort("applied_at", -1)
        .skip(skip)
        .limit(limit)
    )

    # Resolve user emails in batch
    txs = await cursor.to_list(limit)
    user_ids = list({t.get("user_id") for t in txs if t.get("user_id")})
    users_map: dict = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1, "contact_name": 1}):
            users_map[u["id"]] = u

    items = []
    for t in txs:
        amt_cents = int(t.get("amount_cents") or 0)
        refund_cents = int(t.get("refund_amount_cents") or 0)
        u = users_map.get(t.get("user_id") or "", {})
        applied_at = t.get("applied_at")
        refunded_at = t.get("refunded_at")
        items.append({
            "id": t.get("id"),
            "session_id": t.get("session_id"),
            "stripe_account": t.get("stripe_account") or "oscop",
            "kind": t.get("kind"),
            "amount_cents": amt_cents,
            "amount_eur": round(amt_cents / 100, 2),
            "currency": t.get("currency", "eur"),
            "user_id": t.get("user_id"),
            "user_email": u.get("email", ""),
            "user_name": u.get("contact_name", ""),
            "pack_or_order": (t.get("metadata") or {}).get("pack") or (t.get("metadata") or {}).get("order_id") or "",
            "applied_at": applied_at.isoformat() if applied_at else None,
            "applied_by": t.get("applied_by", ""),
            "refund_status": t.get("refund_status") or None,
            "refund_amount_cents": refund_cents,
            "refund_amount_eur": round(refund_cents / 100, 2),
            "refunded_at": refunded_at.isoformat() if refunded_at else None,
            "refunded_by": t.get("refunded_by") or None,
            "net_amount_cents": amt_cents - refund_cents,
            "net_amount_eur": round((amt_cents - refund_cents) / 100, 2),
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


# ---------------- LIVE Health (go/no-go dashboard) ----------------

@stripe_health_router.get("/live-health")
async def stripe_live_health(user_id: str = Depends(get_current_user_id)):
    """Snapshot go/no-go pour le passage en LIVE Stripe.

    Renvoie en une seule requête :
      - `mode` : test | live (depuis STRIPE_MODE)
      - `accounts.{oscop,kdmarche}` : clé configurée, préfixe masqué, nombre de secrets webhook
      - `last_webhook_received` : dernier événement traité (via `applied_by=webhook:*`)
      - `last_successful_payment` : dernier paiement appliqué OK
      - `stats_24h.{oscop,kdmarche}` : paid_count / refund_count / stale_pending_count / paid_amount_cents
      - `verdict` : "go" | "warn" | "no-go" + `reasons[]` (liste courte de raisons humaines)

    Aucune écriture ; agrège uniquement `payment_transactions`.
    """
    await _require_admin(user_id)

    from stripe_accounts import get_stripe_key  # local import — module-scoped side effects  # noqa: WPS433

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=24)
    stale_threshold = now_utc - timedelta(minutes=15)

    mode = "live" if (os.environ.get("STRIPE_MODE", "test").strip().lower() == "live") else "test"
    accounts = ["oscop", "kdmarche"]

    def _mask_key(k: Optional[str]) -> Optional[str]:
        if not k:
            return None
        # Show first 14 chars only (sk_live_51ABCDE) so it's identifiable but not usable.
        return f"{k[:14]}…"

    def _webhook_secret_count(account: str) -> int:
        env_key = f"STRIPE_WEBHOOK_SECRETS_{account.upper()}"
        raw = os.environ.get(env_key, "").strip()
        if not raw:
            return 0
        return len([s for s in raw.split(",") if s.strip().startswith("whsec_")])

    accounts_info = {
        a: {
            "key_configured": bool(get_stripe_key(a)),
            "key_prefix": _mask_key(get_stripe_key(a)),
            "webhook_secrets_count": _webhook_secret_count(a),
        }
        for a in accounts
    }

    # Last webhook received (any account) — infer from applied_by starting with "webhook:"
    last_webhook = await db.payment_transactions.find_one(
        {"applied_by": {"$regex": "^webhook:"}},
        {"_id": 0, "applied_at": 1, "applied_by": 1, "stripe_account": 1, "kind": 1, "session_id": 1},
        sort=[("applied_at", -1)],
    )
    last_webhook_summary = None
    if last_webhook:
        applied_by = last_webhook.get("applied_by") or ""
        verified_account = applied_by.replace("webhook:", "", 1) if applied_by.startswith("webhook:") else None
        applied_at = last_webhook.get("applied_at")
        last_webhook_summary = {
            "at": applied_at.isoformat() if isinstance(applied_at, datetime) else applied_at,
            "account": last_webhook.get("stripe_account") or verified_account,
            "verified_account": verified_account,
            "kind": last_webhook.get("kind"),
            "session_id": last_webhook.get("session_id"),
            "unsigned_test_mode": verified_account == "unsigned-test",
        }

    # Last successful payment (any account)
    last_paid = await db.payment_transactions.find_one(
        {"applied": True, "payment_status": "paid"},
        {"_id": 0, "applied_at": 1, "stripe_account": 1, "kind": 1, "amount_cents": 1, "session_id": 1},
        sort=[("applied_at", -1)],
    )
    last_paid_summary = None
    if last_paid:
        applied_at = last_paid.get("applied_at")
        last_paid_summary = {
            "at": applied_at.isoformat() if isinstance(applied_at, datetime) else applied_at,
            "account": last_paid.get("stripe_account") or "oscop",
            "kind": last_paid.get("kind"),
            "amount_cents": int(last_paid.get("amount_cents") or 0),
            "amount_eur": round(int(last_paid.get("amount_cents") or 0) / 100, 2),
            "session_id": last_paid.get("session_id"),
        }

    # 24h aggregates per account
    stats_24h = {}
    for a in accounts:
        account_match = {"$or": [
            {"stripe_account": a},
            *([{"stripe_account": {"$exists": False}}] if a == "oscop" else []),  # legacy rows without stripe_account default to oscop
        ]}

        paid_pipeline = [
            {"$match": {"applied": True, "payment_status": "paid", "applied_at": {"$gte": window_start}, **account_match}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "amount_cents": {"$sum": {"$ifNull": ["$amount_cents", 0]}}}},
        ]
        paid_agg = await db.payment_transactions.aggregate(paid_pipeline).to_list(1)
        paid = paid_agg[0] if paid_agg else {"count": 0, "amount_cents": 0}

        refund_pipeline = [
            {"$match": {"refund_status": {"$in": ["full", "partial"]}, "refunded_at": {"$gte": window_start}, **account_match}},
            {"$group": {"_id": "$refund_status", "count": {"$sum": 1}, "amount_cents": {"$sum": {"$ifNull": ["$refund_amount_cents", 0]}}}},
        ]
        refund_agg = await db.payment_transactions.aggregate(refund_pipeline).to_list(10)
        refund_full = next((r for r in refund_agg if r["_id"] == "full"), {"count": 0, "amount_cents": 0})
        refund_partial = next((r for r in refund_agg if r["_id"] == "partial"), {"count": 0, "amount_cents": 0})

        # Stale-pending: transactions created > 15 min ago in last 24h, still not applied
        stale_pending = await db.payment_transactions.count_documents({
            "applied": {"$ne": True},
            "created_at": {"$gte": window_start, "$lte": stale_threshold},
            **account_match,
        })

        stats_24h[a] = {
            "paid_count": int(paid.get("count", 0)),
            "paid_amount_cents": int(paid.get("amount_cents", 0)),
            "paid_amount_eur": round(int(paid.get("amount_cents", 0)) / 100, 2),
            "refund_full_count": int(refund_full.get("count", 0)),
            "refund_full_amount_cents": int(refund_full.get("amount_cents", 0)),
            "refund_partial_count": int(refund_partial.get("count", 0)),
            "refund_partial_amount_cents": int(refund_partial.get("amount_cents", 0)),
            "stale_pending_count": stale_pending,
        }

    # Verdict
    reasons: list = []
    verdict = "go"

    if mode != "live":
        reasons.append(f"STRIPE_MODE = '{mode}' (attendu: 'live' pour go-live)")
        verdict = "warn"

    for a in accounts:
        info = accounts_info[a]
        if not info["key_configured"]:
            reasons.append(f"Compte {a}: clé Stripe non configurée")
            verdict = "no-go"
        if info["webhook_secrets_count"] == 0:
            reasons.append(f"Compte {a}: aucun webhook secret configuré")
            if verdict == "go":
                verdict = "warn"

    if last_webhook_summary and last_webhook_summary.get("unsigned_test_mode"):
        reasons.append("Dernier webhook reçu en mode NON signé (test only) — vérifier config prod")
        if verdict == "go":
            verdict = "warn"

    total_stale = sum(stats_24h[a]["stale_pending_count"] for a in accounts)
    if total_stale > 0:
        reasons.append(f"{total_stale} transaction(s) en attente > 15 min sur 24h (webhook potentiellement KO)")
        if verdict == "go":
            verdict = "warn"

    total_paid_24h = sum(stats_24h[a]["paid_count"] for a in accounts)
    # A LIVE-ready system needs at least one paid session on a `cs_live_...` id.
    live_payment_ever = False
    if last_paid_summary:
        sid = (last_paid_summary.get("session_id") or "").lower()
        live_payment_ever = sid.startswith("cs_live_") or sid.startswith("pi_live_") or sid.startswith("in_")
    if mode == "live" and total_paid_24h == 0 and not live_payment_ever:
        reasons.append("Aucun paiement LIVE encore observé — faire le test 1€ E2E pour valider (dernier paiement en TEST/legacy)")
        if verdict == "go":
            verdict = "warn"

    return {
        "checked_at": now_utc.isoformat(),
        "window_hours": 24,
        "mode": mode,
        "accounts": accounts_info,
        "last_webhook_received": last_webhook_summary,
        "last_successful_payment": last_paid_summary,
        "stats_24h": stats_24h,
        "verdict": verdict,
        "reasons": reasons,
    }
