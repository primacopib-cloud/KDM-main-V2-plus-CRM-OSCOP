"""
Export CSV logistique catalogue (incoterm, type de livraison, zones) — superadmin.
"""
import csv
import io
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

logistics_export_router = APIRouter(prefix="/api/catalog/admin")

db = None


def set_logistics_export_database(database):
    global db
    db = database


@logistics_export_router.get("/logistics-export")
async def logistics_export(admin: dict = Depends(require_admin)):
    """CSV de revue : incoterm, type de livraison et zones de chaque fiche produit ACTIVE."""
    products = await db.products.find(
        {"status": "ACTIVE"},
        {"_id": 0, "sku": 1, "name": 1, "category_id": 1, "logistics": 1, "incoterms": 1},
    ).sort("sku", 1).to_list(2000)

    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf, delimiter=";")
    w.writerow(["sku", "nom", "incoterm", "incoterms_par_zone", "type_livraison",
                "zones_disponibilite", "delai_standard_jours"])
    for p in products:
        lg = p.get("logistics") or {}
        legacy = p.get("incoterms") or {}
        legacy_txt = ", ".join(f"{z}: {'/'.join(codes)}" for z, codes in legacy.items() if codes)
        w.writerow([
            p.get("sku", ""),
            (p.get("name") or "").replace("\n", " "),
            lg.get("incoterm") or "",
            legacy_txt,
            lg.get("delivery_type") or "",
            ", ".join(lg.get("available_zones") or []),
            lg.get("lead_time_days") or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=catalogue-logistique.csv"},
    )
