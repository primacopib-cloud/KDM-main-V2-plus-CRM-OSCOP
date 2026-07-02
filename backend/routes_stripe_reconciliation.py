"""
Stripe Reconciliation — admin-only endpoints

Aggregates the `payment_transactions` collection by Stripe account
(KDMARCHE / O'SCOP OUTREMER) and by kind (PASS, RECHARGE, ORDER) for
accounting reconciliation purposes. Provides:

- GET /api/admin/stripe/reconciliation
    JSON aggregation by day + by kind + totals per account.

- GET /api/admin/stripe/reconciliation/export.csv
    Flat CSV of every applied transaction with stripe_account, kind, amount,
    user, session_id, applied_at. Designed to be opened in Excel / handed
    to an accountant.

Only `applied=true` transactions are counted (these are the ones for which
business logic has actually been executed — PASS activated / order paid).
"""
import csv
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from auth import get_current_user_id

logger = logging.getLogger(__name__)

reconciliation_router = APIRouter(
    prefix="/api/admin/stripe", tags=["Admin · Stripe Reconciliation"]
)

db = None


def set_reconciliation_database(database):
    global db
    db = database


async def _require_admin(user_id: str) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


def _parse_date(s: Optional[str], default: datetime) -> datetime:
    if not s:
        return default
    try:
        # Accept YYYY-MM-DD
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date invalide: {s} (format attendu YYYY-MM-DD)")


# ---------------- JSON Reconciliation ----------------

@reconciliation_router.get("/reconciliation")
async def stripe_reconciliation(
    user_id: str = Depends(get_current_user_id),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD (défaut J-30)"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD (défaut aujourd'hui)"),
):
    await _require_admin(user_id)

    now_utc = datetime.now(timezone.utc)
    dt_to = _parse_date(date_to, now_utc) + timedelta(days=1)  # end-of-day
    dt_from = _parse_date(date_from, now_utc - timedelta(days=30))
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="date_from doit être ≤ date_to")

    # Mongo aggregate: only applied transactions (paid + business logic run)
    # We do TWO passes: one for paid amounts, one for refunds (refund_status in {full, partial}).
    pipeline = [
        {"$match": {
            "applied": True,
            "applied_at": {"$gte": dt_from, "$lte": dt_to},
        }},
        {"$project": {
            "_id": 0,
            "stripe_account": {"$ifNull": ["$stripe_account", "oscop"]},
            "kind": "$kind",
            "amount_cents": "$amount_cents",
            "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$applied_at"}},
        }},
    ]
    rows = await db.payment_transactions.aggregate(pipeline).to_list(20000)

    # Refunds: refunded_at within range, regardless of when paid
    refund_pipeline = [
        {"$match": {
            "refund_status": {"$in": ["full", "partial"]},
            "refunded_at": {"$gte": dt_from, "$lte": dt_to},
        }},
        {"$project": {
            "_id": 0,
            "stripe_account": {"$ifNull": ["$stripe_account", "oscop"]},
            "kind": "$kind",
            "refund_amount_cents": "$refund_amount_cents",
            "refund_status": "$refund_status",
            "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$refunded_at"}},
        }},
    ]
    refund_rows = await db.payment_transactions.aggregate(refund_pipeline).to_list(20000)

    # Build all-zero matrix so the frontend chart has every day in range
    days = []
    cursor = dt_from
    while cursor < dt_to:
        days.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)

    accounts = ["oscop", "kdmarche"]
    kinds = ["PASS", "RECHARGE", "ORDER"]

    by_day = {d: {a: {"amount_cents": 0, "count": 0, "refund_cents": 0, "refund_count": 0} for a in accounts} for d in days}
    by_kind = {a: {k: {"amount_cents": 0, "count": 0} for k in kinds} for a in accounts}
    totals = {a: {"amount_cents": 0, "count": 0} for a in accounts}
    refund_totals = {a: {"full_cents": 0, "full_count": 0, "partial_cents": 0, "partial_count": 0} for a in accounts}

    for r in rows:
        a = r["stripe_account"] if r["stripe_account"] in accounts else "oscop"
        k = r["kind"] if r["kind"] in kinds else "ORDER"
        d = r["day"]
        amt = int(r.get("amount_cents") or 0)
        if d in by_day:
            by_day[d][a]["amount_cents"] += amt
            by_day[d][a]["count"] += 1
        by_kind[a][k]["amount_cents"] += amt
        by_kind[a][k]["count"] += 1
        totals[a]["amount_cents"] += amt
        totals[a]["count"] += 1

    for r in refund_rows:
        a = r["stripe_account"] if r["stripe_account"] in accounts else "oscop"
        d = r["day"]
        amt = int(r.get("refund_amount_cents") or 0)
        status = r.get("refund_status")
        if d in by_day:
            by_day[d][a]["refund_cents"] += amt
            by_day[d][a]["refund_count"] += 1
        if status == "full":
            refund_totals[a]["full_cents"] += amt
            refund_totals[a]["full_count"] += 1
        elif status == "partial":
            refund_totals[a]["partial_cents"] += amt
            refund_totals[a]["partial_count"] += 1

    # Convert by_day dict into a list ordered chronologically (for charts)
    by_day_list = []
    for d in days:
        entry = {"day": d}
        for a in accounts:
            entry[f"{a}_cents"] = by_day[d][a]["amount_cents"]
            entry[f"{a}_count"] = by_day[d][a]["count"]
            entry[f"{a}_eur"] = round(by_day[d][a]["amount_cents"] / 100, 2)
            entry[f"{a}_refund_cents"] = by_day[d][a]["refund_cents"]
            entry[f"{a}_refund_count"] = by_day[d][a]["refund_count"]
            entry[f"{a}_refund_eur"] = round(by_day[d][a]["refund_cents"] / 100, 2)
            # Net amount per account per day (paid - refunded), negative possible
            entry[f"{a}_net_eur"] = round((by_day[d][a]["amount_cents"] - by_day[d][a]["refund_cents"]) / 100, 2)
        by_day_list.append(entry)

    # Stripe dashboard URLs (deep-link to the right account dashboard, filtered)
    # Note: each Stripe account has its own dashboard URL; we link to the
    # generic search by metadata. The connected merchant just needs to be
    # logged in with the right Stripe account.
    dashboard_links = {
        "oscop": "https://dashboard.stripe.com/payments?status%5B%5D=successful",
        "kdmarche": "https://dashboard.stripe.com/payments?status%5B%5D=successful",
    }

    return {
        "range": {
            "date_from": dt_from.strftime("%Y-%m-%d"),
            "date_to": (dt_to - timedelta(days=1)).strftime("%Y-%m-%d"),
            "days": len(days),
        },
        "totals": {
            a: {
                "amount_cents": totals[a]["amount_cents"],
                "amount_eur": round(totals[a]["amount_cents"] / 100, 2),
                "count": totals[a]["count"],
                "refund_full_cents": refund_totals[a]["full_cents"],
                "refund_full_eur": round(refund_totals[a]["full_cents"] / 100, 2),
                "refund_full_count": refund_totals[a]["full_count"],
                "refund_partial_cents": refund_totals[a]["partial_cents"],
                "refund_partial_eur": round(refund_totals[a]["partial_cents"] / 100, 2),
                "refund_partial_count": refund_totals[a]["partial_count"],
                "net_cents": totals[a]["amount_cents"] - refund_totals[a]["full_cents"] - refund_totals[a]["partial_cents"],
                "net_eur": round(
                    (totals[a]["amount_cents"] - refund_totals[a]["full_cents"] - refund_totals[a]["partial_cents"]) / 100,
                    2,
                ),
            }
            for a in accounts
        },
        "by_kind": {
            a: {
                k: {
                    "amount_cents": by_kind[a][k]["amount_cents"],
                    "amount_eur": round(by_kind[a][k]["amount_cents"] / 100, 2),
                    "count": by_kind[a][k]["count"],
                }
                for k in kinds
            }
            for a in accounts
        },
        "by_day": by_day_list,
        "dashboard_links": dashboard_links,
        "stripe_mode": (
            "live"
            if (os.environ.get("STRIPE_MODE", "test").strip().lower() == "live")
            else "test"
        ),
    }


# ---------------- CSV Export ----------------

@reconciliation_router.get("/reconciliation/export.csv")
async def stripe_reconciliation_csv(
    user_id: str = Depends(get_current_user_id),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    await _require_admin(user_id)

    now_utc = datetime.now(timezone.utc)
    dt_to = _parse_date(date_to, now_utc) + timedelta(days=1)
    dt_from = _parse_date(date_from, now_utc - timedelta(days=30))
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="date_from doit être ≤ date_to")

    cursor = db.payment_transactions.find(
        {"applied": True, "applied_at": {"$gte": dt_from, "$lte": dt_to}},
        {"_id": 0},
    ).sort("applied_at", 1)

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "date_paiement",
        "session_id",
        "stripe_account",
        "kind",
        "amount_eur",
        "amount_cents",
        "currency",
        "user_id",
        "user_email",
        "pack_or_order_id",
        "applied_by",
        "refund_status",
        "refund_amount_eur",
        "refund_amount_cents",
        "refunded_at",
        "net_amount_eur",
    ])

    async for tx in cursor:
        amt_cents = int(tx.get("amount_cents") or 0)
        applied_at = tx.get("applied_at") or tx.get("updated_at")
        applied_at_str = applied_at.strftime("%Y-%m-%d %H:%M:%S") if applied_at else ""
        # Lookup user email (best-effort)
        user_email = ""
        if tx.get("user_id"):
            u = await db.users.find_one({"id": tx["user_id"]}, {"_id": 0, "email": 1})
            if u:
                user_email = u.get("email", "")
        meta = tx.get("metadata") or {}
        pack_or_order = meta.get("pack") or meta.get("order_id") or ""
        refund_status = tx.get("refund_status") or ""
        refund_cents = int(tx.get("refund_amount_cents") or 0)
        refunded_at = tx.get("refunded_at")
        refunded_at_str = refunded_at.strftime("%Y-%m-%d %H:%M:%S") if refunded_at else ""
        net_cents = amt_cents - refund_cents
        writer.writerow([
            applied_at_str,
            tx.get("session_id", ""),
            tx.get("stripe_account") or "oscop",
            tx.get("kind", ""),
            f"{amt_cents / 100:.2f}",
            amt_cents,
            tx.get("currency", "eur"),
            tx.get("user_id", ""),
            user_email,
            pack_or_order,
            tx.get("applied_by", ""),
            refund_status,
            f"{refund_cents / 100:.2f}" if refund_cents else "",
            refund_cents if refund_cents else "",
            refunded_at_str,
            f"{net_cents / 100:.2f}",
        ])

    buf.seek(0)
    filename = f"stripe_reconciliation_{dt_from.strftime('%Y%m%d')}_{(dt_to - timedelta(days=1)).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------- Transactions list (paginated, with refund status) ----------------

@reconciliation_router.get("/reconciliation/transactions")
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

@reconciliation_router.get("/live-health")
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
