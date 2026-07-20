"""Campagnes multi-lots : regroupement de consultations sous un calendrier commun."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

campaigns_router = APIRouter(prefix="/api/admin/campaigns", tags=["campaigns"])

db = None

PRE_PUBLICATION = ["BROUILLON", "EN_VALIDATION", "VALIDEE"]


def set_campaigns_database(database):
    global db
    db = database


class CampaignBody(BaseModel):
    name: str
    opens_at: str
    closes_at: str


class AttachBody(BaseModel):
    consultation_id: str


@campaigns_router.get("")
async def list_campaigns(admin: dict = Depends(require_admin)):
    campaigns = await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for camp in campaigns:
        camp["lots"] = await db.consultations.find(
            {"campaign_id": camp["id"]},
            {"_id": 0, "id": 1, "ref": 1, "title": 1, "status": 1, "opens_at": 1, "closes_at": 1}).to_list(100)
    return {"items": campaigns}


@campaigns_router.post("")
async def create_campaign(body: CampaignBody, admin: dict = Depends(require_admin)):
    if not body.name.strip() or body.closes_at <= body.opens_at:
        raise HTTPException(status_code=400, detail="Nom requis et clôture postérieure à l'ouverture")
    doc = {"id": str(uuid.uuid4()), "name": body.name.strip(),
           "opens_at": body.opens_at, "closes_at": body.closes_at,
           "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.campaigns.insert_one({**doc})
    await audit("CAMPAIGN_CREATED", admin.get("email"), None, {"campaign_id": doc["id"], "name": doc["name"]})
    return doc


@campaigns_router.put("/{camp_id}")
async def update_campaign(camp_id: str, body: CampaignBody, admin: dict = Depends(require_admin)):
    if body.closes_at <= body.opens_at:
        raise HTTPException(status_code=400, detail="Clôture postérieure à l'ouverture requise")
    res = await db.campaigns.update_one({"id": camp_id}, {"$set": {
        "name": body.name.strip(), "opens_at": body.opens_at, "closes_at": body.closes_at,
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return {"ok": True}


@campaigns_router.post("/{camp_id}/attach")
async def attach_lot(camp_id: str, body: AttachBody, admin: dict = Depends(require_admin)):
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    c = await db.consultations.find_one({"id": body.consultation_id}, {"_id": 0, "id": 1, "ref": 1, "status": 1})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    if c["status"] not in PRE_PUBLICATION:
        raise HTTPException(status_code=409, detail="Seuls les lots non publiés peuvent rejoindre une campagne")
    await db.consultations.update_one({"id": c["id"]}, {"$set": {
        "campaign_id": camp_id, "opens_at": camp["opens_at"], "closes_at": camp["closes_at"],
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit("CAMPAIGN_LOT_ATTACHED", admin.get("email"), c["id"],
                {"campaign_id": camp_id, "ref": c["ref"], "calendar_applied": True})
    return {"ok": True, "message": f"{c['ref']} rattaché — calendrier de campagne appliqué"}


@campaigns_router.post("/{camp_id}/detach")
async def detach_lot(camp_id: str, body: AttachBody, admin: dict = Depends(require_admin)):
    res = await db.consultations.update_one(
        {"id": body.consultation_id, "campaign_id": camp_id}, {"$unset": {"campaign_id": ""}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lot non rattaché à cette campagne")
    await audit("CAMPAIGN_LOT_DETACHED", admin.get("email"), body.consultation_id, {"campaign_id": camp_id})
    return {"ok": True}


@campaigns_router.post("/{camp_id}/apply-calendar")
async def apply_calendar(camp_id: str, admin: dict = Depends(require_admin)):
    """Ré-applique le calendrier de la campagne à tous ses lots non publiés."""
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    res = await db.consultations.update_many(
        {"campaign_id": camp_id, "status": {"$in": PRE_PUBLICATION}},
        {"$set": {"opens_at": camp["opens_at"], "closes_at": camp["closes_at"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit("CAMPAIGN_CALENDAR_APPLIED", admin.get("email"), None,
                {"campaign_id": camp_id, "lots_updated": res.modified_count})
    return {"ok": True, "lots_updated": res.modified_count}


@campaigns_router.get("/{camp_id}/dashboard")
async def campaign_dashboard(camp_id: str, admin: dict = Depends(require_admin)):
    """Avancement d'une campagne : inscriptions, offres valides et attributions par lot."""
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    from routes_bids import _latest_valid_bids
    lots, tot_entries, tot_bids, tot_awarded = [], 0, 0, 0
    async for c in db.consultations.find({"campaign_id": camp_id},
                                         {"_id": 0, "id": 1, "ref": 1, "title": 1, "status": 1, "closes_at": 1}):
        entries = await db.consultation_entries.count_documents(
            {"consultation_id": c["id"], "status": "INSCRIT"})
        valid_bids = len(await _latest_valid_bids(c["id"]))
        awarded = c["status"] == "ATTRIBUEE"
        lots.append({**c, "entries": entries, "valid_bids": valid_bids, "awarded": awarded})
        tot_entries += entries
        tot_bids += valid_bids
        tot_awarded += 1 if awarded else 0
    return {"campaign": camp, "lots": lots,
            "totals": {"lots": len(lots), "inscriptions": tot_entries,
                       "offres_valides": tot_bids, "attribues": tot_awarded}}


@campaigns_router.post("/{camp_id}/publish-all")
async def publish_all(camp_id: str, admin: dict = Depends(require_admin)):
    """Publie en un clic tous les lots VALIDEE de la campagne (contrôles de publication conservés)."""
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0, "id": 1, "name": 1})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    results = []
    from routes_consultations import publish_consultation
    async for c in db.consultations.find({"campaign_id": camp_id, "status": "VALIDEE"},
                                         {"_id": 0, "id": 1, "ref": 1}):
        try:
            await publish_consultation(c["id"], admin)
            results.append({"ref": c["ref"], "ok": True})
        except HTTPException as exc:
            results.append({"ref": c["ref"], "ok": False, "detail": exc.detail})
    published = sum(1 for r in results if r["ok"])
    await audit("CAMPAIGN_PUBLISH_ALL", admin.get("email"), None,
                {"campaign_id": camp_id, "published": published, "results": results})
    return {"ok": True, "published": published, "results": results}


@campaigns_router.post("/{camp_id}/remind-vendors")
async def remind_vendors(camp_id: str, admin: dict = Depends(require_admin)):
    """Relance en un clic les vendeurs des catégories des lots actifs sans offre (garde 24h)."""
    camp = await db.campaigns.find_one({"id": camp_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    last = camp.get("vendor_reminder_at")
    if last:
        try:
            since = datetime.now(timezone.utc) - datetime.fromisoformat(last)
            if since.total_seconds() < 24 * 3600:
                raise HTTPException(status_code=409, detail="Relance déjà envoyée il y a moins de 24h")
        except ValueError:
            pass
    from routes_bids import _latest_valid_bids
    lots = []
    async for c in db.consultations.find(
            {"campaign_id": camp_id, "status": {"$in": ["PUBLIEE", "INSCRIPTIONS_OUVERTES", "EN_COURS"]}},
            {"_id": 0, "id": 1, "ref": 1, "title": 1, "category": 1, "closes_at": 1, "cpc_cost": 1}):
        if not await _latest_valid_bids(c["id"]):
            lots.append(c)
    if not lots:
        raise HTTPException(status_code=400, detail="Tous les lots actifs de cette campagne ont déjà reçu des offres")
    categories = sorted({l["category"] for l in lots})
    vendor_ids = await db.vendor_products.distinct("vendor_id", {"category": {"$in": categories}})
    emails = set()
    if vendor_ids:
        async for v in db.vendors.find({"id": {"$in": vendor_ids}}, {"_id": 0, "email": 1}):
            if v.get("email"):
                emails.add(v["email"].lower())
    targeted = bool(emails)
    q = {"role": "vendor", "suspended": {"$ne": True}}
    if targeted:
        q["email"] = {"$in": list(emails)}
    from brevo_service import send_email
    base = os.environ.get("FRONTEND_PUBLIC_URL", "")
    lots_html = "".join(
        f"<li><strong>{l['ref']}</strong> — {l['title']} (catégorie {l['category']}, "
        f"clôture {str(l.get('closes_at', ''))[:16].replace('T', ' ')}, accès {l.get('cpc_cost')} CREDI'SCOP)</li>"
        for l in lots)
    sent = 0
    async for u in db.users.find(q, {"_id": 0, "email": 1, "full_name": 1, "name": 1}).limit(200):
        if not u.get("email"):
            continue
        try:
            await send_email(
                to_email=u["email"], to_name=u.get("full_name") or u.get("name"),
                subject=f"Derniers jours — {len(lots)} lot(s) encore sans offre ({camp['name']})",
                html_content=f"""<h2 style="color:#451F6B;">Campagne {camp['name']} — clôture imminente</h2>
                <p>Bonjour,</p>
                <p>Les lots suivants{' (correspondant à vos produits)' if targeted else ''} n'ont encore reçu
                <strong>aucune offre</strong> — c'est le moment idéal pour vous positionner :</p>
                <ul>{lots_html}</ul>
                <p style="margin:24px 0;"><a href="{base}/vendor?tab=consultations"
                style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Déposer mon offre</a></p>
                <p style="color:#777;font-size:12px;">Les offres sont exprimées en euros HT. Les CREDI'SCOP n'interviennent jamais dans le classement.</p>""",
                tags=["campaign-vendor-reminder"])
            sent += 1
        except Exception as exc:
            logger.warning("Relance campagne %s → %s : %s", camp_id, u["email"], exc)
    await db.campaigns.update_one({"id": camp_id}, {"$set": {
        "vendor_reminder_at": datetime.now(timezone.utc).isoformat()}})
    await audit("CAMPAIGN_VENDOR_REMINDER", admin.get("email"), None,
                {"campaign_id": camp_id, "sent": sent, "lots": [l["ref"] for l in lots],
                 "targeted_by_category": targeted, "categories": categories})
    return {"ok": True, "sent": sent, "lots": [l["ref"] for l in lots], "targeted_by_category": targeted}


@campaigns_router.delete("/{camp_id}")
async def delete_campaign(camp_id: str, admin: dict = Depends(require_admin)):
    await db.consultations.update_many({"campaign_id": camp_id}, {"$unset": {"campaign_id": ""}})
    res = await db.campaigns.delete_one({"id": camp_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    await audit("CAMPAIGN_DELETED", admin.get("email"), None, {"campaign_id": camp_id})
    return {"ok": True}
