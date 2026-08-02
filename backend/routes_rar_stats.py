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


@rar_stats_router.get("/alert-threshold")
async def get_alert_threshold(user: dict = Depends(get_current_user_checkout)):
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        return {"threshold_cents": 0, "alert_active": False}
    account = await db.rar_accounts.find_one(
        {"org_id": m["org_id"]}, {"alert_threshold_cents": 1, "alert_active": 1})
    return {"threshold_cents": (account or {}).get("alert_threshold_cents") or 0,
            "alert_active": bool((account or {}).get("alert_active"))}


@rar_stats_router.put("/alert-threshold")
async def set_alert_threshold(body: dict, user: dict = Depends(get_current_user_checkout)):
    """Seuil d'alerte email du plafond disponible (0 = désactivé)."""
    try:
        cents = int((body or {}).get("threshold_cents") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="threshold_cents : entier attendu")
    if cents < 0 or cents > 100_000_000:
        raise HTTPException(status_code=400, detail="Seuil hors limites")
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        raise HTTPException(status_code=404, detail="Aucune organisation associée")
    account = await db.rar_accounts.find_one({"org_id": m["org_id"]}, {"_id": 1})
    if not account:
        raise HTTPException(status_code=404, detail="Aucun compte Règlement à Réception Pro")
    await db.rar_accounts.update_one(
        {"org_id": m["org_id"]},
        {"$set": {"alert_threshold_cents": cents, "alert_active": False}})
    if cents:
        from rar_alerts import check_ceiling_alert
        await check_ceiling_alert(db, m["org_id"])
    return {"ok": True, "threshold_cents": cents}


@rar_stats_router.get("/carrier-scores")
async def carrier_scores(user: dict = Depends(get_current_user_checkout)):
    """Note de fiabilité par transporteur = part des livraisons sans réserve (transporteurs écartés exclus)."""
    blocked = set(await db.rar_blocked_carriers.distinct("carrier"))
    stats = {}
    async for p in db.delivery_proofs.find({}, {"_id": 0, "carrier_name": 1, "reserves": 1}):
        carrier = p.get("carrier_name") or "LOGI'SCOP"
        if carrier in blocked:
            continue
        s = stats.setdefault(carrier, {"carrier": carrier, "deliveries": 0, "clean": 0})
        s["deliveries"] += 1
        if not p.get("reserves"):
            s["clean"] += 1
    out = [{"carrier": s["carrier"], "deliveries": s["deliveries"],
            "score": round(100 * s["clean"] / s["deliveries"], 1)} for s in stats.values()]
    out.sort(key=lambda s: (-s["score"], -s["deliveries"]))
    return {"carriers": out}


@rar_stats_router.get("/alert-history")
async def alert_history(user: dict = Depends(get_current_user_checkout)):
    """Historique des alertes de plafond envoyées à l'organisation de l'acheteur."""
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        return {"alerts": []}
    alerts = await db.rar_alert_log.find(
        {"org_id": m["org_id"]}, {"_id": 0, "threshold_cents": 1, "available_cents": 1, "sent_at": 1}
    ).sort("sent_at", -1).to_list(20)
    return {"alerts": alerts}


@rar_stats_router.get("/ceiling-statement-annual-pdf")
async def ceiling_statement_annual_pdf(year: str, user: dict = Depends(get_current_user_checkout)):
    """Relevé annuel PDF des mouvements de plafond (year=YYYY) — pour le bilan comptable."""
    if not re.fullmatch(r"20\d{2}", year or ""):
        raise HTTPException(status_code=400, detail="Format d'année attendu : YYYY")
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        raise HTTPException(status_code=404, detail="Aucune organisation associée")
    from routes_rar_delivery import compute_ceiling_events
    events = [e for e in await compute_ceiling_events(m["org_id"]) if str(e["date"] or "")[:4] == year]
    org = await db.orgs.find_one({"id": m["org_id"]}, {"legal_name": 1, "name": 1}) or \
        await db.organizations.find_one({"id": m["org_id"]}, {"legal_name": 1, "name": 1})
    account = await db.rar_accounts.find_one({"org_id": m["org_id"]}, {"ceiling_cents": 1})
    from pdf_ceiling_statement import build_ceiling_annual_pdf
    pdf = build_ceiling_annual_pdf(
        (org or {}).get("legal_name") or (org or {}).get("name") or m["org_id"],
        year, events, (account or {}).get("ceiling_cents") or 0)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=releve-plafond-annuel-{year}.pdf"})


@rar_stats_router.post("/admin/blocked-carriers")
async def set_carrier_blocked(body: dict, admin: dict = Depends(require_admin)):
    """Écarte (blocked=true) ou réintègre (blocked=false) un transporteur des propositions."""
    from datetime import datetime
    carrier = ((body or {}).get("carrier") or "").strip()[:80]
    if not carrier:
        raise HTTPException(status_code=400, detail="Nom du transporteur requis")
    blocked = bool((body or {}).get("blocked", True))
    reason = ((body or {}).get("reason") or "").strip()[:300]
    if blocked:
        await db.rar_blocked_carriers.update_one(
            {"carrier": carrier},
            {"$set": {"carrier": carrier, "reason": reason, "blocked_by": admin.get("email"),
                      "blocked_at": datetime.utcnow()}}, upsert=True)
    else:
        await db.rar_blocked_carriers.delete_one({"carrier": carrier})
    await db.rar_carrier_block_log.insert_one({
        "carrier": carrier, "action": "BLOCK" if blocked else "UNBLOCK",
        "reason": reason if blocked else "", "by": admin.get("email"), "at": datetime.utcnow()})
    try:
        from consultation_audit import audit
        await audit("RAR_CARRIER_BLOCKED" if blocked else "RAR_CARRIER_UNBLOCKED",
                    admin.get("email"), None, {"carrier": carrier, "reason": reason})
    except Exception as exc:
        logger.warning("Audit écartement transporteur non journalisé : %s", exc)
    logger.info("Transporteur %s %s par %s", carrier, "écarté" if blocked else "réintégré", admin.get("email"))
    return {"ok": True, "carrier": carrier, "blocked": blocked}


@rar_stats_router.get("/admin/carrier-block-log")
async def carrier_block_log(admin: dict = Depends(require_admin)):
    """Journal d'audit des écartements et réintégrations de transporteurs."""
    entries = await db.rar_carrier_block_log.find({}, {"_id": 0}).sort("at", -1).to_list(50)
    for e in entries:
        e["at"] = str(e.get("at") or "")[:16]
    return {"entries": entries}


@rar_stats_router.get("/admin/carrier-block-log/export")
async def carrier_block_log_export(admin: dict = Depends(require_admin)):
    """Export CSV du journal des écartements pour les dossiers de conformité."""
    entries = await db.rar_carrier_block_log.find({}, {"_id": 0}).sort("at", -1).to_list(1000)
    lines = ["date;action;transporteur;motif;auteur"]
    for e in entries:
        lines.append(";".join([
            str(e.get("at") or "")[:16],
            "ECARTE" if e.get("action") == "BLOCK" else "REINTEGRE",
            (e.get("carrier") or "").replace(";", ","),
            (e.get("reason") or "").replace(";", ",").replace("\n", " "),
            e.get("by") or ""]))
    csv = "\ufeff" + "\n".join(lines)
    return Response(content=csv, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": "attachment; filename=journal-ecartements-transporteurs.csv"})


@rar_stats_router.get("/admin/unpaid")
async def unpaid_dashboard(admin: dict = Depends(require_admin)):
    """Tableau de bord des impayés RàR : ancienneté, relances envoyées, statut du plafond."""
    from datetime import datetime
    now = datetime.utcnow()
    orders = await db.orders.find(
        {"rar": True, "payment_status": "cod_pending", "cod_amount_due_cents": {"$gt": 0}},
        {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "cod_amount_due_cents": 1,
         "total_ttc_cents": 1, "rar_proof_at": 1, "confirmed_at": 1, "rar_reminder_count": 1,
         "rar_overdue_alert_sent": 1, "rar_suspension_done": 1, "rar_status": 1}
    ).sort("confirmed_at", 1).to_list(100)
    org_ids = list({o["org_id"] for o in orders if o.get("org_id")})
    orgs = {x["id"]: x.get("legal_name") or x.get("name") for x in
            await db.organizations.find({"id": {"$in": org_ids}}, {"id": 1, "legal_name": 1, "name": 1}).to_list(100)}
    accounts = {a["org_id"]: a.get("status") for a in
                await db.rar_accounts.find({"org_id": {"$in": org_ids}}, {"org_id": 1, "status": 1}).to_list(100)}
    items = []
    for o in orders:
        ref = o.get("rar_proof_at") or o.get("confirmed_at")
        items.append({
            "order_number": o.get("order_number"), "org_name": orgs.get(o.get("org_id"), o.get("org_id")),
            "due_cents": o.get("cod_amount_due_cents") or 0,
            "age_days": (now - ref).days if ref else None,
            "delivered": bool(o.get("rar_proof_at")),
            "reminders": o.get("rar_reminder_count") or 0,
            "final_notice": bool(o.get("rar_overdue_alert_sent")),
            "suspended": bool(o.get("rar_suspension_done")),
            "account_status": accounts.get(o.get("org_id"), "NONE"),
            "rar_status": o.get("rar_status"),
        })
    items.sort(key=lambda i: -(i["age_days"] or 0))
    return {"items": items, "count": len(items), "total_due_cents": sum(i["due_cents"] for i in items)}


@rar_stats_router.get("/admin/annual-archive/runs")
async def annual_archive_runs(admin: dict = Depends(require_admin)):
    """Historique des relevés annuels archivés dans la GEDESS (groupé par exercice)."""
    years = {}
    async for log in db.rar_statement_log.find({"month": {"$regex": "^ANNUEL-"}}, {"_id": 0}):
        year = log["month"].replace("ANNUEL-", "")
        y = years.setdefault(year, {"total": 0, "archived": 0})
        y["total"] += 1
        if log.get("ged_doc_id"):
            y["archived"] += 1
    runs = []
    for year in sorted(years, reverse=True):
        y = years[year]
        runs.append({
            "month": year, "rows": y["total"],
            "status": "SUCCESS" if y["archived"] == y["total"] else "ERROR",
            "error": None if y["archived"] == y["total"] else f"{y['archived']}/{y['total']} relevés archivés en GED",
            "ged_filename": f"releve-plafond-annuel-{year}-*.pdf" if y["archived"] else None,
        })
    return {"runs": runs, "total": len(runs)}


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
    blocked = {b["carrier"]: b async for b in db.rar_blocked_carriers.find(
        {}, {"_id": 0, "carrier": 1, "reason": 1, "blocked_by": 1, "blocked_at": 1})}
    for s in stats.values():
        s["reserve_rate"] = round(100 * s["with_reserves"] / s["deliveries"], 1) if s["deliveries"] else 0
        b = blocked.get(s["carrier"])
        s["blocked"] = b is not None
        s["blocked_reason"] = (b or {}).get("reason") or ""
        s["blocked_by"] = (b or {}).get("blocked_by")
        s["blocked_at"] = str((b or {}).get("blocked_at") or "")[:16]
        out.append(s)
    out.sort(key=lambda s: (-s["reserve_rate"], -s["deliveries"]))
    return {"carriers": out}
