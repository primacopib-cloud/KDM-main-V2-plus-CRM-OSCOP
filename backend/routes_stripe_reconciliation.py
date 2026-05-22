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

    # Build all-zero matrix so the frontend chart has every day in range
    days = []
    cursor = dt_from
    while cursor < dt_to:
        days.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)

    accounts = ["oscop", "kdmarche"]
    kinds = ["PASS", "RECHARGE", "ORDER"]

    by_day = {d: {a: {"amount_cents": 0, "count": 0} for a in accounts} for d in days}
    by_kind = {a: {k: {"amount_cents": 0, "count": 0} for k in kinds} for a in accounts}
    totals = {a: {"amount_cents": 0, "count": 0} for a in accounts}

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

    # Convert by_day dict into a list ordered chronologically (for charts)
    by_day_list = []
    for d in days:
        entry = {"day": d}
        for a in accounts:
            entry[f"{a}_cents"] = by_day[d][a]["amount_cents"]
            entry[f"{a}_count"] = by_day[d][a]["count"]
            entry[f"{a}_eur"] = round(by_day[d][a]["amount_cents"] / 100, 2)
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
            if (__import__("os").environ.get("STRIPE_MODE", "test").strip().lower() == "live")
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
        ])

    buf.seek(0)
    filename = f"stripe_reconciliation_{dt_from.strftime('%Y%m%d')}_{(dt_to - timedelta(days=1)).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
