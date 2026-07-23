"""Trésorerie RCR détenue par le FOGEDOM-SCIC : encours par fournisseur + échéancier des remboursements."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from attestation_nominative import compute_rcr_ledger
from convention_settings import get_convention_settings
from core_deps import get_current_user, check_admin
from db import get_database
from rcr_fiscal import sync_rcr_fiscal_register

rcr_treasury_router = APIRouter(prefix="/api/convention", tags=["convention"])


@rcr_treasury_router.get("/admin/rcr-treasury")
async def rcr_treasury(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    await sync_rcr_fiscal_register(db)
    settings = await get_convention_settings(db)
    reimb_days = int(settings.get("reimbursement_days", 45))

    totals = {"CONSTITUTION": 0, "EXTOURNE": 0, "REMBOURSEMENT": 0}
    by_vendor = {}
    async for e in db.rcr_fiscal_register.find({}, {"_id": 0}):
        totals[e["kind"]] = totals.get(e["kind"], 0) + e["amount_cents"]
        v = by_vendor.setdefault(e["vendor_id"], {
            "vendor_id": e["vendor_id"], "vendor_name": e.get("vendor_name"),
            "constitue": 0, "extourne": 0, "rembourse": 0})
        if e["kind"] == "CONSTITUTION":
            v["constitue"] += e["amount_cents"]
        elif e["kind"] == "EXTOURNE":
            v["extourne"] += e["amount_cents"]
        else:
            v["rembourse"] += e["amount_cents"]
    vendors = []
    for v in by_vendor.values():
        v["solde_cents"] = v["constitue"] + v["extourne"] - v["rembourse"]
        vendors.append(v)
    vendors.sort(key=lambda x: -x["solde_cents"])

    # Échéancier : remboursement prévu à expiration + délai réglementaire, par attestation active
    schedule = {}
    async for att in db.attestations_nominatives.find(
            {"status": {"$ne": "closed"}}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        solde = ledger.get("solde_cents") or 0
        if solde <= 0:
            continue
        try:
            exp = datetime.fromisoformat(att["date_expiration"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        due = exp + timedelta(days=reimb_days)
        key = due.strftime("%Y-%m")
        month = schedule.setdefault(key, {"month": key, "amount_cents": 0, "items": []})
        month["amount_cents"] += solde
        month["items"].append({"attestation_ref": att["ref"], "vendor_name": att.get("vendor_name"),
                               "product_name": att.get("product_name"),
                               "due_date": due.strftime("%Y-%m-%d"), "amount_cents": solde})
    projections = [schedule[k] for k in sorted(schedule)]

    solde_total = totals["CONSTITUTION"] + totals["EXTOURNE"] - totals["REMBOURSEMENT"]
    return {
        "treasury_cents": solde_total,
        "constitue_cents": totals["CONSTITUTION"],
        "extourne_cents": totals["EXTOURNE"],
        "rembourse_cents": totals["REMBOURSEMENT"],
        "projected_total_cents": sum(m["amount_cents"] for m in projections),
        "reimbursement_days": reimb_days,
        "vendors": vendors,
        "projections": projections,
    }
