"""Indicateurs LOGI'SCOP admin : CA transport, ponctualité, réserves, retards + rémunération des opérateurs."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core_deps import get_current_user, check_admin
from db import get_database

logiscop_analytics_router = APIRouter(prefix="/api/logiscop-transport", tags=["logiscop-transport"])
CLOSED_STATUSES = ["LIVRE_CONFORME", "LIVRE_AVEC_RESERVES", "PARTIEL"]


async def get_operator_share_rate(db) -> float:
    doc = await db.logiscop_settings.find_one({"key": "operator_share_rate"}, {"_id": 0})
    return float(doc["value"]) if doc else 80.0


class ShareRateBody(BaseModel):
    rate_percent: float = Field(ge=0, le=100)


@logiscop_analytics_router.get("/admin/dashboard")
async def transport_dashboard(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    now = datetime.now(timezone.utc)

    ca = {"total_ht_cents": 0, "total_ttc_cents": 0, "paid_ttc_cents": 0,
          "outstanding_ttc_cents": 0, "overdue_count": 0, "overdue_ttc_cents": 0}
    async for inv in db.logiscop_transport_invoices.find({}, {"_id": 0}):
        ca["total_ht_cents"] += inv["amount_ht_cents"]
        ca["total_ttc_cents"] += inv["total_ttc_cents"]
        if inv["status"] == "PAID":
            ca["paid_ttc_cents"] += inv["total_ttc_cents"]
        else:
            ca["outstanding_ttc_cents"] += inv["total_ttc_cents"]
            try:
                if now - datetime.fromisoformat(inv["issued_at"]) > timedelta(days=30):
                    ca["overdue_count"] += 1
                    ca["overdue_ttc_cents"] += inv["total_ttc_cents"]
            except ValueError:
                pass

    total = delivered = with_reserves = on_time_base = on_time = pending = incidents = 0
    stars_sum = stars_count = 0
    async for ot in db.logiscop_transport_orders.find({}, {"_id": 0}):
        total += 1
        if ot["status"] == "PROPOSE":
            pending += 1
        if ot["status"] in CLOSED_STATUSES:
            delivered += 1
            if (ot.get("epod") or {}).get("reserves"):
                with_reserves += 1
            if (ot.get("epod") or {}).get("temperature_incident"):
                incidents += 1
            due = (ot.get("delivery") or {}).get("date")
            done = ((ot.get("execution") or {}).get("delivered_at") or (ot.get("epod") or {}).get("at") or "")[:10]
            if due and done:
                on_time_base += 1
                if done <= due:
                    on_time += 1
        if (ot.get("rating") or {}).get("stars"):
            stars_sum += ot["rating"]["stars"]
            stars_count += 1

    return {
        "ca": ca,
        "orders": {"total": total, "pending": pending, "delivered": delivered,
                   "reserves_rate": round(100 * with_reserves / delivered, 1) if delivered else None,
                   "on_time_rate": round(100 * on_time / on_time_base, 1) if on_time_base else None,
                   "temperature_incidents": incidents},
        "ratings": {"avg": round(stars_sum / stars_count, 2) if stars_count else None, "count": stars_count},
    }


@logiscop_analytics_router.get("/admin/operator-earnings")
async def operator_earnings(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    rate = await get_operator_share_rate(db)
    ops = {}
    async for ot in db.logiscop_transport_orders.find(
            {"execution.status": "LIVREE"}, {"_id": 0}):
        ex = ot["execution"]
        o = ops.setdefault(ex["operator_id"], {
            "operator_id": ex["operator_id"], "operator_name": ex.get("operator_name"),
            "delivered_count": 0, "total_ht_cents": 0, "stars_sum": 0, "stars_count": 0})
        o["delivered_count"] += 1
        o["total_ht_cents"] += ot.get("price_ht_cents") or 0
        if (ot.get("rating") or {}).get("stars"):
            o["stars_sum"] += ot["rating"]["stars"]
            o["stars_count"] += 1
    operators = []
    for o in ops.values():
        o["share_cents"] = round(o["total_ht_cents"] * rate / 100)
        o["avg_rating"] = round(o["stars_sum"] / o["stars_count"], 2) if o["stars_count"] else None
        del o["stars_sum"]
        operators.append(o)
    operators.sort(key=lambda x: -x["share_cents"])
    return {"rate_percent": rate, "operators": operators,
            "total_share_cents": sum(o["share_cents"] for o in operators)}


@logiscop_analytics_router.get("/admin/quality-history")
async def quality_history(current_user: dict = Depends(get_current_user)):
    """Évolution mensuelle : ponctualité, notes et réserves — global et par opérateur."""
    await check_admin(current_user)
    db = get_database()
    months = {}
    async for ot in db.logiscop_transport_orders.find({"status": {"$in": CLOSED_STATUSES}}, {"_id": 0}):
        month = ((ot.get("epod") or {}).get("at") or ot.get("created_at", ""))[:7]
        if not month:
            continue
        rec = months.setdefault(month, {"month": month, "delivered": 0, "on_time": 0, "on_time_base": 0,
                                        "with_reserves": 0, "stars_sum": 0, "stars_count": 0, "operators": {}})
        due = (ot.get("delivery") or {}).get("date")
        done = ((ot.get("execution") or {}).get("delivered_at") or (ot.get("epod") or {}).get("at") or "")[:10]
        stars = (ot.get("rating") or {}).get("stars")
        op_name = (ot.get("execution") or {}).get("operator_name") or "Sans opérateur"
        for target in (rec, rec["operators"].setdefault(
                op_name, {"delivered": 0, "on_time": 0, "on_time_base": 0,
                          "with_reserves": 0, "stars_sum": 0, "stars_count": 0})):
            target["delivered"] += 1
            if (ot.get("epod") or {}).get("reserves"):
                target["with_reserves"] += 1
            if due and done:
                target["on_time_base"] += 1
                if done <= due:
                    target["on_time"] += 1
            if stars:
                target["stars_sum"] += stars
                target["stars_count"] += 1

    def _fmt(t):
        return {"delivered": t["delivered"],
                "on_time_rate": round(100 * t["on_time"] / t["on_time_base"], 1) if t["on_time_base"] else None,
                "reserves_rate": round(100 * t["with_reserves"] / t["delivered"], 1) if t["delivered"] else None,
                "avg_rating": round(t["stars_sum"] / t["stars_count"], 2) if t["stars_count"] else None}

    return {"months": [{"month": m, **_fmt(rec),
                        "operators": [{"operator_name": k, **_fmt(v)} for k, v in sorted(rec["operators"].items())]}
                       for m, rec in sorted(months.items())]}


class CreditRatesBody(BaseModel):
    late_pct: float = Field(ge=0, le=100)
    reserves_pct: float = Field(ge=0, le=100)


@logiscop_analytics_router.get("/admin/service-credit-rates")
async def get_service_credit_rates(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    late = await db.logiscop_settings.find_one({"key": "service_credit_late_pct"}, {"_id": 0})
    res = await db.logiscop_settings.find_one({"key": "service_credit_reserves_pct"}, {"_id": 0})
    return {"late_pct": float(late["value"]) if late else 10.0,
            "reserves_pct": float(res["value"]) if res else 10.0}


@logiscop_analytics_router.post("/admin/service-credit-rates")
async def set_service_credit_rates(body: CreditRatesBody, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    await db.logiscop_settings.update_one(
        {"key": "service_credit_late_pct"}, {"$set": {"value": body.late_pct}}, upsert=True)
    await db.logiscop_settings.update_one(
        {"key": "service_credit_reserves_pct"}, {"$set": {"value": body.reserves_pct}}, upsert=True)
    return {"ok": True, "late_pct": body.late_pct, "reserves_pct": body.reserves_pct}


@logiscop_analytics_router.get("/admin/monthly-report/pdf")
async def monthly_report_pdf(month: str, current_user: dict = Depends(get_current_user)):
    """Synthèse mensuelle transport (CA, avoirs, litiges) — téléchargement PDF admin."""
    await check_admin(current_user)
    db = get_database()
    from logiscop_monthly_report import build_monthly_report_pdf, collect_monthly_stats
    stats = await collect_monthly_stats(db, month[:7])
    from fastapi.responses import Response
    return Response(content=build_monthly_report_pdf(stats), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=synthese-transport-{month[:7]}.pdf"})


@logiscop_analytics_router.post("/admin/operator-share-rate")
async def set_operator_share_rate(body: ShareRateBody, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    await db.logiscop_settings.update_one(
        {"key": "operator_share_rate"}, {"$set": {"value": body.rate_percent}}, upsert=True)
    return {"ok": True, "rate_percent": body.rate_percent}
