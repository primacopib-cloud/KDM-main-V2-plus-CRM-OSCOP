"""Réglages légaux de la Convention cadre tripartite + registres admin."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
convention_settings_router = APIRouter(prefix="/api/convention", tags=["convention"])

DEFAULT_LEGAL = {
    "oscop": {"denomination": "SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP)", "capital": "[À COMPLÉTER]",
              "siege": "[À COMPLÉTER]", "rcs": "[À COMPLÉTER]", "siren": "[À COMPLÉTER]",
              "representant": "[NOM, PRÉNOM, QUALITÉ]"},
    "kdmarche": {"denomination": "KDMARCHÉ PRO", "forme": "[FORME SOCIALE]", "capital": "[À COMPLÉTER]",
                 "siege": "[À COMPLÉTER]", "rcs": "[À COMPLÉTER]", "siren": "[À COMPLÉTER]",
                 "representant": "[NOM, PRÉNOM, QUALITÉ]"},
    "rcr_default_rate": 5.0,
    "rcr_global_cap_eur": 50000,
    "tolerance_rate": 5.0,
    "reimbursement_days": 45,
    "liability_cap_eur": 150000,
    "insurance_min_eur": 500000,
    "tribunal": "[À COMPLÉTER]",
}


async def get_convention_settings(db) -> dict:
    doc = await db.system_flags.find_one({"key": "convention_legal_settings"}, {"_id": 0}) or {}
    merged = {**DEFAULT_LEGAL, **(doc.get("settings") or {})}
    merged["oscop"] = {**DEFAULT_LEGAL["oscop"], **(merged.get("oscop") or {})}
    merged["kdmarche"] = {**DEFAULT_LEGAL["kdmarche"], **(merged.get("kdmarche") or {})}
    return merged


@convention_settings_router.get("/admin/settings")
async def read_convention_settings(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    return await get_convention_settings(get_database())


@convention_settings_router.put("/admin/settings")
async def save_convention_settings(body: dict, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    current = await get_convention_settings(db)
    for key in ("oscop", "kdmarche"):
        if isinstance(body.get(key), dict):
            current[key] = {**current[key], **{k: str(v)[:200] for k, v in body[key].items()}}
    for key in ("rcr_default_rate", "rcr_global_cap_eur", "tolerance_rate",
                "reimbursement_days", "liability_cap_eur", "insurance_min_eur"):
        if body.get(key) is not None:
            try:
                current[key] = float(body[key])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"Valeur invalide : {key}")
    if body.get("tribunal") is not None:
        current["tribunal"] = str(body["tribunal"])[:200]
    await db.system_flags.update_one(
        {"key": "convention_legal_settings"},
        {"$set": {"settings": current, "updated_by": current_user.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True, "settings": current}


@convention_settings_router.get("/admin/registres")
async def registres_convention(current_user: dict = Depends(get_current_user)):
    """Registres : conventions cadres, attestations nominatives, registre analytique FOGEDOM-RCR."""
    await check_admin(current_user)
    db = get_database()
    settings = await get_convention_settings(db)
    conventions = await db.conventions_cadres.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    attestations = await db.attestations_nominatives.find(
        {}, {"_id": 0, "ai_text": 0}).sort("created_at", -1).to_list(300)
    # Registre analytique FOGEDOM-RCR : plafonds consolidés par fournisseur
    by_vendor = {}
    for a in attestations:
        v = by_vendor.setdefault(a["vendor_id"], {
            "vendor_id": a["vendor_id"], "vendor_name": a.get("vendor_name", ""),
            "attestations": 0, "montant_agrege_cents": 0, "plafond_cible_cents": 0})
        v["attestations"] += 1
        v["montant_agrege_cents"] += a.get("montant_agrege_cents", 0)
        v["plafond_cible_cents"] += a.get("plafond_cible_cents", 0)
    cap_cents = int(settings["rcr_global_cap_eur"] * 100)
    registre_rcr = []
    for v in by_vendor.values():
        v["plafond_global_cents"] = cap_cents
        v["plafond_applique_cents"] = min(v["plafond_cible_cents"], cap_cents)
        v["cap_reached"] = v["plafond_cible_cents"] >= cap_cents
        registre_rcr.append(v)
    # Retenues effectives (contrats de volume existants)
    retained_total = 0
    async for c in db.volume_contracts.find({}, {"retained_cents": 1}):
        retained_total += c.get("retained_cents", 0)
    return {"conventions": conventions, "attestations": attestations,
            "registre_rcr": sorted(registre_rcr, key=lambda x: -x["plafond_cible_cents"]),
            "totaux": {"conventions": len(conventions), "attestations": len(attestations),
                       "plafond_cible_total_cents": sum(v["plafond_cible_cents"] for v in registre_rcr),
                       "retenues_effectives_cents": retained_total,
                       "rcr_global_cap_eur": settings["rcr_global_cap_eur"]}}
