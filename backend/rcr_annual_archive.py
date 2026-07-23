"""Archivage GEDESS annuel automatique des relevés fiscaux RCR (1er janvier, idempotent, relance quotidienne)."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core_deps import get_current_user, check_admin
from db import get_database
from gedess_client import gedess_upload_file, is_gedess_configured
from rcr_fiscal import build_annual_data, build_annual_statement_pdf, sync_rcr_fiscal_register

logger = logging.getLogger(__name__)
rcr_annual_archive_router = APIRouter(prefix="/api/convention", tags=["convention"])


async def archive_annual_statements_to_ged(db, year: str, force: bool = False) -> dict:
    """Archive dans la GEDESS le relevé annuel fiscal RCR de chaque fournisseur (idempotent par année+fournisseur)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await sync_rcr_fiscal_register(db)
    vendor_ids = await db.attestations_nominatives.distinct("vendor_id")
    results = {"year": year, "archived": 0, "already": 0, "errors": 0, "vendors": []}
    for vid in vendor_ids:
        run = await db.rcr_annual_archive_runs.find_one({"year": year, "vendor_id": vid}, {"_id": 0})
        if run and run.get("status") == "SUCCESS" and not force:
            results["already"] += 1
            continue
        vendor = await db.vendors.find_one({"id": vid}, {"_id": 0}) or {"id": vid, "company_name": vid}
        entry = {"id": (run or {}).get("id") or str(uuid.uuid4()), "year": year, "vendor_id": vid,
                 "vendor_name": vendor.get("company_name"), "attempted_at": now_iso}
        try:
            if not is_gedess_configured():
                raise RuntimeError("GEDESS non configurée (GEDESS_BASE_URL/EMAIL/PASSWORD)")
            data = await build_annual_data(db, vid, year)
            pdf = build_annual_statement_pdf(vendor, year, data)
            doc = await gedess_upload_file(
                f"releve-annuel-rcr-{year}-{vid[:8]}.pdf", pdf, categorie="rapport",
                description=f"Relevé annuel fiscal RCR {year} — {vendor.get('company_name')} (FOGEDOM-SCIC)",
                tags=f"rcr,releve-annuel,{year}", mime_type="application/pdf")
            entry.update({"status": "SUCCESS", "ged_doc_id": doc.get("id"), "error": None, "archived_at": now_iso})
            results["archived"] += 1
        except Exception as exc:
            entry.update({"status": "ERROR", "error": str(exc)[:300]})
            results["errors"] += 1
            logger.warning("Archivage annuel RCR %s/%s échoué : %s", year, vid, exc)
        await db.rcr_annual_archive_runs.update_one(
            {"year": year, "vendor_id": vid}, {"$set": entry}, upsert=True)
        results["vendors"].append({"vendor_id": vid, "vendor_name": vendor.get("company_name"),
                                   "status": entry["status"], "error": entry.get("error")})
    return results


async def run_annual_archive_watch(db) -> None:
    """Job scheduler : en janvier, archive l'exercice écoulé (relance quotidienne + alerte email en cas d'échec)."""
    now = datetime.now(timezone.utc)
    if now.month != 1:
        return
    year = str(now.year - 1)
    results = await archive_annual_statements_to_ged(db, year)
    if results["errors"] == 0:
        return
    today = now.strftime("%Y-%m-%d")
    flag = await db.system_flags.find_one({"key": f"rcr_annual_archive_alert_{year}"}, {"_id": 0})
    if flag and flag.get("sent_on") == today:
        return
    failed = [v for v in results["vendors"] if v["status"] == "ERROR"]
    from connectors.health_watch import _send_alert_email
    await _send_alert_email(
        f"Échec archivage GEDESS : relevés annuels RCR {year}",
        (f"L'archivage annuel automatique des relevés fiscaux RCR de l'exercice <strong>{year}</strong> a échoué "
         f"pour {len(failed)} fournisseur(s). Nouvelle tentative automatique demain jusqu'à réussite."),
        {"Exercice": year,
         "Fournisseurs en échec": ", ".join((f.get("vendor_name") or f["vendor_id"]) for f in failed)[:300],
         "Première erreur": (failed[0].get("error") or "Inconnue"),
         "Prochaine tentative": "Automatique (quotidienne)"},
        "critical")
    await db.system_flags.update_one(
        {"key": f"rcr_annual_archive_alert_{year}"}, {"$set": {"sent_on": today}}, upsert=True)


@rcr_annual_archive_router.post("/admin/rcr-annual-archive/{year}")
async def manual_annual_archive(year: str, force: bool = False,
                                current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    if not (year.isdigit() and len(year) == 4):
        raise HTTPException(status_code=400, detail="Année invalide")
    return await archive_annual_statements_to_ged(get_database(), year, force=force)


@rcr_annual_archive_router.get("/admin/rcr-annual-archive/runs")
async def list_annual_archive_runs(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    runs = await db.rcr_annual_archive_runs.find({}, {"_id": 0}).sort("attempted_at", -1).to_list(60)
    return {"count": len(runs), "runs": runs}
