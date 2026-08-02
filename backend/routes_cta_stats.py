"""Suivi de conversion des CTA d'adhésion : clics publics + tableau admin."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

cta_stats_router = APIRouter(prefix="/api", tags=["cta-stats"])

db = None


def set_cta_stats_database(database):
    global db
    db = database


CTA_LABELS = {
    "hero_acces_pro": "Découvrir l'Accès Pro Mutualisé (hero accueil)",
    "devenir_relais": "Devenir relais LOLODRIVE (accueil)",
    "adherer_centrale": "Adhérer à la Centrale (vitrine zones)",
    "adherer_centrale_api": "Adhérer à la Centrale (section API accueil)",
    "voir_catalogue": "Voir tout le catalogue (vitrine zones)",
    "tarifs_ess-acces-pro": "S'inscrire — ESS Accès Pro (/tarifs)",
    "tarifs_ess-volume-pro": "S'inscrire — ESS Volume Pro (/tarifs)",
    "tarifs_ess-impact-pro": "S'inscrire — ESS Impact Pro (/tarifs)",
    "rejoindre_parrainer": "Rejoindre et parrainer (bandeau défi parrainage)",
    "territoire_guadeloupe": "Voir les offres — Guadeloupe (/kdmarche)",
    "territoire_martinique": "Voir les offres — Martinique (/kdmarche)",
    "territoire_guyane": "Voir les offres — Guyane (/kdmarche)",
    "territoire_reunion": "Voir les offres — La Réunion (/kdmarche)",
    "territoire_mayotte": "Voir les offres — Mayotte (/kdmarche)",
    "territoire_iles-du-nord": "Voir les offres — Îles du Nord (/kdmarche)",
}

TERRITORY_ZONES = {
    "territoire_guadeloupe": "GUADELOUPE",
    "territoire_martinique": "MARTINIQUE",
    "territoire_guyane": "GUYANE",
    "territoire_reunion": "REUNION",
    "territoire_mayotte": "MAYOTTE",
    "territoire_iles-du-nord": "CARIBBEAN",
}


async def _zone_has_recent_order(db_, cta_id, zone, cutoff):
    async for o in db_.orders.find({"source_cta": cta_id, "zone_code": zone}, {"_id": 0, "created_at": 1}):
        ca = o.get("created_at")
        if isinstance(ca, str):
            try:
                ca = datetime.fromisoformat(ca.replace("Z", "+00:00"))
            except ValueError:
                continue
        if not ca:
            continue
        if ca.tzinfo is None:
            ca = ca.replace(tzinfo=timezone.utc)
        if ca >= cutoff:
            return True
    return False


async def check_dormant_zones(db_):
    """Alerte les admins sur les territoires sans commande attribuée depuis 30 jours (max 1 alerte/zone/30 j)."""
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        to_alert = []
        for cta_id, zone in TERRITORY_ZONES.items():
            if await _zone_has_recent_order(db_, cta_id, zone, cutoff):
                continue
            flag = await db_.system_flags.find_one({"key": f"dormant_zone_alert_{zone}"}, {"_id": 0, "value": 1})
            if flag and flag.get("value") and datetime.fromisoformat(flag["value"]) > cutoff:
                continue
            to_alert.append((cta_id, zone))
        if not to_alert:
            return
        names = [CTA_LABELS[c].replace("Voir les offres — ", "").replace(" (/kdmarche)", "") for c, _ in to_alert]
        from core_deps import create_notification
        await create_notification(
            "dormant_zone", "💤 Territoire(s) dormant(s) à relancer",
            "Aucune commande attribuée depuis 30 jours pour : " + ", ".join(names) +
            ". Pensez à relancer ces zones (campagne, partage WhatsApp, promos locales) — suivi de conversion dans le Super Admin.",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"link": "/superadmin", "zones": [z for _, z in to_alert]})
        for _, zone in to_alert:
            await db_.system_flags.update_one(
                {"key": f"dormant_zone_alert_{zone}"}, {"$set": {"value": now.isoformat()}}, upsert=True)
        logger.info("Alerte zones dormantes envoyée : %s", names)
    except Exception as exc:
        logger.warning("Vérification zones dormantes : %s", exc)


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
        if cta_id in TERRITORY_ZONES:
            # Conversion territoire = commande passée dans la zone visitée après le clic
            conv_q = {"source_cta": cta_id, "zone_code": TERRITORY_ZONES[cta_id]}
            paid = await db.orders.count_documents(conv_q)
            paid30 = await db.orders.count_documents(
                {**conv_q, "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}})
            agg = await db.orders.aggregate([
                {"$match": conv_q},
                {"$group": {"_id": None, "avg": {"$avg": "$total_ttc_cents"},
                            "sum": {"$sum": "$total_ttc_cents"}}}]).to_list(1)
            avg_basket = round(agg[0]["avg"]) if agg and agg[0].get("avg") else None
            revenue = int(agg[0]["sum"]) if agg else 0
            dormant = not await _zone_has_recent_order(
                db, cta_id, TERRITORY_ZONES[cta_id], now - timedelta(days=30))
        else:
            paid = await db.vendor_onboarding.count_documents(conv_q)
            paid30 = await db.vendor_onboarding.count_documents({**conv_q, "created_at": {"$gte": d30}})
            avg_basket, revenue, dormant = None, 0, None
        rate = round(paid / total * 100) if total else None
        stats.append({"cta_id": cta_id, "label": label, "total": total, "last7": last7,
                      "last30": last30, "paid": paid, "paid30": paid30, "rate": rate,
                      "avg_basket_cents": avg_basket, "revenue_cents": revenue, "dormant": dormant})
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
    asyncio.create_task(_check_click_record())
    return {"ok": True}


async def _check_click_record():
    """Alerte les admins quand la semaine en cours bat le record hebdomadaire de clics."""
    try:
        weekly = {}
        async for d in db.cta_clicks.find({}, {"_id": 0, "at": 1}):
            key = datetime.fromisoformat(d["at"]).isocalendar()[:2]
            weekly[key] = weekly.get(key, 0) + 1
        cur_key = datetime.now(timezone.utc).isocalendar()[:2]
        current = weekly.pop(cur_key, 0)
        prev_record = max(weekly.values(), default=0)
        if prev_record == 0 or current <= prev_record:
            return
        week_tag = f"{cur_key[0]}-W{cur_key[1]:02d}"
        flag = await db.system_flags.find_one({"key": "cta_click_record_week"}, {"_id": 0, "value": 1})
        if flag and flag.get("value") == week_tag:
            return
        await db.system_flags.update_one(
            {"key": "cta_click_record_week"}, {"$set": {"value": week_tag}}, upsert=True)
        from core_deps import create_notification
        await create_notification(
            "cta_click_record", "📈 Record de clics d'adhésion battu !",
            f"La semaine en cours totalise {current} clics sur les boutons d'adhésion — le précédent record "
            f"hebdomadaire ({prev_record}) est dépassé. Une campagne fonctionne : consultez le suivi de conversion.",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"link": "/superadmin"})
        logger.info("Record clics CTA battu : %s clics (précédent %s)", current, prev_record)
    except Exception as exc:
        logger.warning("Vérification record clics CTA : %s", exc)


@cta_stats_router.get("/admin/cta-stats")
async def cta_stats(admin: dict = Depends(require_admin)):
    stats = await _collect_stats()
    return {"stats": stats, "total_clicks": sum(s["total"] for s in stats),
            "total_paid": sum(s["paid"] for s in stats)}


@cta_stats_router.get("/admin/cta-stats/trend")
async def cta_stats_trend(weeks: int = 12, admin: dict = Depends(require_admin)):
    """Clics et adhésions payées par semaine ISO (du lundi), semaines les plus anciennes d'abord."""
    weeks = min(max(weeks, 4), 26)
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    points = []
    for i in range(weeks - 1, -1, -1):
        start = monday - timedelta(weeks=i)
        end = start + timedelta(weeks=1)
        s_iso, e_iso = start.isoformat(), end.isoformat()
        clicks = await db.cta_clicks.count_documents({"at": {"$gte": s_iso, "$lt": e_iso}})
        paid = await db.vendor_onboarding.count_documents(
            {"status": {"$ne": "PAYMENT_PENDING"}, "created_at": {"$gte": s_iso, "$lt": e_iso}})
        points.append({"week": f"S{start.isocalendar()[1]}", "start": start.strftime("%d/%m"),
                       "clicks": clicks, "paid": paid})
    return {"weeks": weeks, "points": points}


@cta_stats_router.get("/admin/cta-stats/export")
async def cta_stats_export(admin: dict = Depends(require_admin)):
    stats = await _collect_stats()
    lines = ["CTA;Libellé;Clics 7j;Clics 30j;Clics total;Adhésions payées 30j;Adhésions payées total;Taux (%);Panier moyen (€);CA attribué (€)"]
    for s in stats:
        label = (s["label"] or "").replace(";", ",")
        rate = "" if s["rate"] is None else s["rate"]
        avg = "" if s["avg_basket_cents"] is None else f'{s["avg_basket_cents"] / 100:.2f}'.replace(".", ",")
        rev = "" if not s["revenue_cents"] else f'{s["revenue_cents"] / 100:.2f}'.replace(".", ",")
        lines.append(f'{s["cta_id"]};{label};{s["last7"]};{s["last30"]};{s["total"]};{s["paid30"]};{s["paid"]};{rate};{avg};{rev}')
    csv = "\ufeff" + "\n".join(lines)
    filename = f"conversion-cta-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
