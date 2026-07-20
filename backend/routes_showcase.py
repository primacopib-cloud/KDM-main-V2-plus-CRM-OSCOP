"""Carrousel Partenaires en vitrine (page d'accueil) — géré par le Super Admin."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

showcase_router = APIRouter(prefix="/api/showcase", tags=["showcase"])
showcase_admin_router = APIRouter(prefix="/api/admin/showcase", tags=["showcase-admin"])

db = None


def set_showcase_database(database):
    global db
    db = database


class PartnerBody(BaseModel):
    name: str
    logo_url: Optional[str] = None
    link: Optional[str] = None
    category: Optional[str] = "vendor"


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    link: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@showcase_router.get("/partners")
async def public_partners():
    """Logos visibles sur la page d'accueil : entrées manuelles + vendeurs approuvés ayant opté pour la vitrine."""
    items = await db.showcase_partners.find({"is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    manual_names = {i["name"].lower() for i in items}
    vendors = await db.vendors.find(
        {"status": "approved", "showcase_opt_in": True},
        {"_id": 0, "id": 1, "company_name": 1, "website": 1}
    ).to_list(100)
    for v in vendors:
        if v["company_name"].lower() in manual_names:
            continue
        product = await db.vendor_products.find_one(
            {"vendor_id": v["id"], "images.0": {"$exists": True}}, {"_id": 0, "images": 1})
        logo = ""
        if product:
            primary = next((im for im in product["images"] if im.get("is_primary")), product["images"][0])
            logo = primary.get("url", "")
        items.append({"id": f"vendor-{v['id']}", "name": v["company_name"], "logo_url": logo,
                      "link": v.get("website") or "", "category": "vendor", "auto": True})
    return {"items": items}


@showcase_router.get("/vendor-opt-in/{vendor_id}")
async def get_vendor_opt_in(vendor_id: str):
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0, "showcase_opt_in": 1, "status": 1})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")
    return {"opt_in": bool(vendor.get("showcase_opt_in")), "approved": vendor.get("status") == "approved"}


class OptInBody(BaseModel):
    opt_in: bool


@showcase_router.post("/vendor-opt-in/{vendor_id}")
async def set_vendor_opt_in(vendor_id: str, body: OptInBody):
    res = await db.vendors.update_one({"id": vendor_id}, {"$set": {"showcase_opt_in": body.opt_in}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")
    from consultation_audit import audit
    await audit("SHOWCASE_VENDOR_OPT_IN", vendor_id, None, {"opt_in": body.opt_in})
    return {"ok": True, "opt_in": body.opt_in}


@showcase_admin_router.get("/partners")
async def admin_list_partners(admin: dict = Depends(require_admin)):
    items = await db.showcase_partners.find({}, {"_id": 0}).sort("sort_order", 1).to_list(200)
    return {"items": items}


@showcase_admin_router.post("/partners")
async def add_partner(body: PartnerBody, admin: dict = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis")
    count = await db.showcase_partners.count_documents({})
    doc = {
        "id": str(uuid.uuid4()), "name": name, "logo_url": (body.logo_url or "").strip(),
        "link": (body.link or "").strip(), "category": body.category or "vendor",
        "is_active": True, "sort_order": count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.showcase_partners.insert_one({**doc})
    from consultation_audit import audit
    await audit("SHOWCASE_PARTNER_ADDED", admin.get("email"), None, {"name": name})
    return doc


@showcase_admin_router.post("/partners/{partner_id}/logo")
async def upload_partner_logo(partner_id: str, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    partner = await db.showcase_partners.find_one({"id": partner_id})
    if not partner:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/svg+xml"):
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPG, WEBP ou SVG")
    content = await file.read()
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo trop lourd (max 3 Mo)")
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}[file.content_type]
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "showcase")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{partner_id}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(upload_dir, filename), "wb") as f:
        f.write(content)
    logo_url = f"/api/uploads/showcase/{filename}"
    await db.showcase_partners.update_one({"id": partner_id}, {"$set": {"logo_url": logo_url}})
    return {"ok": True, "logo_url": logo_url}


@showcase_admin_router.patch("/partners/{partner_id}")
async def update_partner(partner_id: str, body: PartnerUpdate, admin: dict = Depends(require_admin)):
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="Rien à mettre à jour")
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.showcase_partners.update_one({"id": partner_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    from consultation_audit import audit
    await audit("SHOWCASE_PARTNER_UPDATED", admin.get("email"), None, {"id": partner_id, "changes": {k: v for k, v in upd.items() if k != "updated_at"}})
    return {"ok": True}


@showcase_admin_router.post("/partners/{partner_id}/move")
async def move_partner(partner_id: str, direction: str, admin: dict = Depends(require_admin)):
    """Déplace un logo vers le haut ou le bas dans l'ordre d'affichage."""
    items = await db.showcase_partners.find({}, {"_id": 0, "id": 1}).sort("sort_order", 1).to_list(200)
    ids = [i["id"] for i in items]
    if partner_id not in ids:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    idx = ids.index(partner_id)
    swap = idx - 1 if direction == "up" else idx + 1
    if swap < 0 or swap >= len(ids):
        return {"ok": True}
    ids[idx], ids[swap] = ids[swap], ids[idx]
    for pos, pid in enumerate(ids):
        await db.showcase_partners.update_one({"id": pid}, {"$set": {"sort_order": pos}})
    return {"ok": True}


@showcase_admin_router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str, admin: dict = Depends(require_admin)):
    partner = await db.showcase_partners.find_one({"id": partner_id})
    if not partner:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    await db.showcase_partners.delete_one({"id": partner_id})
    from consultation_audit import audit
    await audit("SHOWCASE_PARTNER_DELETED", admin.get("email"), None, {"id": partner_id, "name": partner.get("name")})
    return {"ok": True}
