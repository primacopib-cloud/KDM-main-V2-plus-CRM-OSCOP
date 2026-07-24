"""Trésorerie consolidée : RCR détenue + transport LOGI'SCOP + adhésions, projection 30/60/90 jours."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from attestation_nominative import compute_rcr_ledger
from convention_settings import get_convention_settings
from core_deps import get_current_user, check_admin
from db import get_database

treasury_consolidated_router = APIRouter(prefix="/api/admin/treasury", tags=["treasury"])

BUCKETS = [("0-30 j", 0, 30), ("31-60 j", 31, 60), ("61-90 j", 61, 90)]


def _bucket_index(days: float) -> int | None:
    for i, (_, lo, hi) in enumerate(BUCKETS):
        if lo <= days <= hi:
            return i
    return None


@treasury_consolidated_router.get("/consolidated")
async def consolidated_treasury(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    now = datetime.now(timezone.utc)
    buckets = [{"label": b[0], "transport_in_cents": 0, "memberships_in_cents": 0,
                "rcr_out_cents": 0} for b in BUCKETS]

    # 1) Transport : encours impayé (net d'avoir), échéance = émission + 30 j
    transport = {"outstanding_cents": 0, "overdue_cents": 0, "overdue_count": 0,
                 "collected_cents": 0, "unpaid_count": 0}
    async for inv in db.logiscop_transport_invoices.find({}, {"_id": 0}):
        ttc = inv.get("total_ttc_cents") or 0
        if inv.get("status") == "PAID":
            transport["collected_cents"] += ttc
            continue
        credit = await db.logiscop_transport_credits.find_one(
            {"invoice_id": inv["id"]}, {"_id": 0, "total_ttc_cents": 1})
        net = max(0, ttc - ((credit or {}).get("total_ttc_cents") or 0))
        transport["outstanding_cents"] += net
        transport["unpaid_count"] += 1
        try:
            due = datetime.fromisoformat(inv["issued_at"]) + timedelta(days=30)
        except ValueError:
            continue
        days = (due - now).total_seconds() / 86400
        if days < 0:
            transport["overdue_cents"] += net
            transport["overdue_count"] += 1
            buckets[0]["transport_in_cents"] += net
        else:
            idx = _bucket_index(days)
            if idx is not None:
                buckets[idx]["transport_in_cents"] += net

    # 2) Adhésions : revenu mensuel récurrent des membres actifs (1 renouvellement / fenêtre 30 j)
    memberships = {"mrr_cents": 0, "active_count": 0}
    async for ob in db.vendor_onboarding.find(
            {"status": "ACTIVATED", "access_suspended": {"$ne": True}}, {"_id": 0, "amount_cents": 1}):
        memberships["mrr_cents"] += ob.get("amount_cents") or 0
        memberships["active_count"] += 1
    for b in buckets:
        b["memberships_in_cents"] = memberships["mrr_cents"]

    # 3) RCR : trésorerie détenue + décaissements prévus (expiration + délai réglementaire)
    settings = await get_convention_settings(db)
    reimb_days = int(settings.get("reimbursement_days", 45))
    rcr = {"held_cents": 0, "projected_out_cents": 0}
    async for e in db.rcr_fiscal_register.find({}, {"_id": 0, "kind": 1, "amount_cents": 1}):
        sign = -1 if e["kind"] == "REMBOURSEMENT" else 1
        rcr["held_cents"] += sign * e["amount_cents"]
    async for att in db.attestations_nominatives.find({"status": {"$ne": "closed"}}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        solde = ledger.get("solde_cents") or 0
        if solde <= 0:
            continue
        try:
            exp = datetime.fromisoformat(att["date_expiration"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days = (exp + timedelta(days=reimb_days) - now).total_seconds() / 86400
        idx = _bucket_index(max(0, days))
        if idx is not None:
            buckets[idx]["rcr_out_cents"] += solde
            rcr["projected_out_cents"] += solde

    cumulative = 0
    for b in buckets:
        b["net_cents"] = b["transport_in_cents"] + b["memberships_in_cents"] - b["rcr_out_cents"]
        cumulative += b["net_cents"]
        b["cumulative_cents"] = cumulative
    return {"as_of": now.isoformat(), "buckets": buckets, "transport": transport,
            "memberships": memberships, "rcr": rcr,
            "projected_net_90d_cents": cumulative}
