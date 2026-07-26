"""Suivi de conversion des CTA d'adhésion : clics publics + tableau admin."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lolodrive_helpers import require_admin

cta_stats_router = APIRouter(prefix="/api", tags=["cta-stats"])

db = None


def set_cta_stats_database(database):
    global db
    db = database


CTA_LABELS = {
    "hero_acces_pro": "Découvrir l'Accès Pro Mutualisé (hero accueil)",
    "devenir_relais": "Devenir relais LOLODRIVE (accueil)",
    "adherer_centrale": "Adhérer à la Centrale (vitrine zones)",
    "voir_catalogue": "Voir tout le catalogue (vitrine zones)",
    "tarifs_ess-acces-pro": "S'inscrire — ESS Accès Pro (/tarifs)",
    "tarifs_ess-volume-pro": "S'inscrire — ESS Volume Pro (/tarifs)",
    "tarifs_ess-impact-pro": "S'inscrire — ESS Impact Pro (/tarifs)",
    "rejoindre_parrainer": "Rejoindre et parrainer (bandeau défi parrainage)",
}


async def _collect_stats():
    now = datetime.now(timezone.utc)
    d7 = (now - timedelta(days=7)).isoformat()
    d30 = (now - timedelta(days=30)).isoformat()
    stats = []
    for cta_id, label in CTA_LABELS.items():
        total = await db.cta_clicks.count_documents({"cta_id": cta_id})
        last7 = await db.cta_clicks.count_documents({"cta_id": cta_id, "at": {"$gte": d7}})
        last30 = await db.cta_clicks.count_documents({"cta_id": cta_id, "at": {"$gte": d30}})
        conv_q = {"source_cta": cta_id, "status": {"$ne": "PAYMENT_PENDING"}}
        paid = await db.vendor_onboarding.count_documents(conv_q)
        paid30 = await db.vendor_onboarding.count_documents({**conv_q, "created_at": {"$gte": d30}})
        rate = round(paid / total * 100) if total else None
        stats.append({"cta_id": cta_id, "label": label, "total": total, "last7": last7,
                      "last30": last30, "paid": paid, "paid30": paid30, "rate": rate})
    stats.sort(key=lambda s: s["total"], reverse=True)
    return stats


class CtaClickBody(BaseModel):
    cta_id: str


@cta_stats_router.post("/public/cta-click")
async def record_cta_click(body: CtaClickBody):
    if body.cta_id not in CTA_LABELS:
        raise HTTPException(status_code=400, detail="CTA inconnu")
    await db.cta_clicks.insert_one({
        "cta_id": body.cta_id,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


@cta_stats_router.get("/admin/cta-stats")
async def cta_stats(admin: dict = Depends(require_admin)):
    stats = await _collect_stats()
    return {"stats": stats, "total_clicks": sum(s["total"] for s in stats),
            "total_paid": sum(s["paid"] for s in stats)}


@cta_stats_router.get("/admin/cta-stats/export")
async def cta_stats_export(admin: dict = Depends(require_admin)):
    stats = await _collect_stats()
    lines = ["CTA;Libellé;Clics 7j;Clics 30j;Clics total;Adhésions payées 30j;Adhésions payées total;Taux (%)"]
    for s in stats:
        label = (s["label"] or "").replace(";", ",")
        rate = "" if s["rate"] is None else s["rate"]
        lines.append(f'{s["cta_id"]};{label};{s["last7"]};{s["last30"]};{s["total"]};{s["paid30"]};{s["paid"]};{rate}')
    csv = "\ufeff" + "\n".join(lines)
    filename = f"conversion-cta-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
