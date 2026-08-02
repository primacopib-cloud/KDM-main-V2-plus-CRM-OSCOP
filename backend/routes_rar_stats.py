"""Relevé mensuel de plafond (acheteur) + statistiques litiges par transporteur (admin)."""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from checkout_common import get_current_user_checkout
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
rar_stats_router = APIRouter(prefix="/api/rar/stats", tags=["rar-stats"])
db = None


def set_rar_stats_database(database):
    global db
    db = database


@rar_stats_router.get("/ceiling-statement-pdf")
async def ceiling_statement_pdf(month: str, user: dict = Depends(get_current_user_checkout)):
    """Relevé mensuel PDF des mouvements de plafond (month=YYYY-MM)."""
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month or ""):
        raise HTTPException(status_code=400, detail="Format de période attendu : YYYY-MM")
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        raise HTTPException(status_code=404, detail="Aucune organisation associée")
    from routes_rar_delivery import compute_ceiling_events
    events = [e for e in await compute_ceiling_events(m["org_id"]) if str(e["date"] or "")[:7] == month]
    org = await db.orgs.find_one({"id": m["org_id"]}, {"legal_name": 1, "name": 1}) or \
        await db.organizations.find_one({"id": m["org_id"]}, {"legal_name": 1, "name": 1})
    account = await db.rar_accounts.find_one({"org_id": m["org_id"]}, {"ceiling_cents": 1})
    from pdf_ceiling_statement import build_ceiling_statement_pdf
    pdf = build_ceiling_statement_pdf(
        (org or {}).get("legal_name") or (org or {}).get("name") or m["org_id"],
        month, events, (account or {}).get("ceiling_cents") or 0)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=releve-plafond-{month}.pdf"})


@rar_stats_router.get("/admin/carrier-stats")
async def carrier_stats(admin: dict = Depends(require_admin)):
    """Taux de réserves par transporteur pour repérer les livraisons à problème."""
    stats = {}
    async for p in db.delivery_proofs.find({}, {"_id": 0, "order_id": 1, "carrier_name": 1, "reserves": 1}):
        carrier = p.get("carrier_name") or "LOGI'SCOP"
        s = stats.setdefault(carrier, {"carrier": carrier, "deliveries": 0, "with_reserves": 0,
                                       "disputed_cents": 0, "credited_cents": 0})
        s["deliveries"] += 1
        if p.get("reserves"):
            s["with_reserves"] += 1
            order = await db.orders.find_one(
                {"id": p["order_id"]}, {"rar_disputed_cents": 1, "rar_reserve_resolution": 1})
            if order:
                res = order.get("rar_reserve_resolution") or {}
                s["disputed_cents"] += order.get("rar_disputed_cents") or res.get("amount_cents") or 0
                if res.get("action") == "CREDIT":
                    s["credited_cents"] += res.get("amount_cents") or 0
    out = []
    for s in stats.values():
        s["reserve_rate"] = round(100 * s["with_reserves"] / s["deliveries"], 1) if s["deliveries"] else 0
        out.append(s)
    out.sort(key=lambda s: (-s["reserve_rate"], -s["deliveries"]))
    return {"carriers": out}
