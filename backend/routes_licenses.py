"""Marque Blanche — licences territoriales : branding par territoire, page vitrine publique /t/{slug}."""
import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

licenses_admin_router = APIRouter(prefix="/api/admin/licenses", tags=["licenses-admin"])
licenses_public_router = APIRouter(prefix="/api/licenses", tags=["licenses-public"])

db = None


def set_licenses_database(database):
    global db
    db = database


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "licence"


class LicenseBody(BaseModel):
    name: str
    slug: Optional[str] = None
    territory_code: str
    tagline: Optional[str] = None
    contact_email: Optional[str] = None
    primary_color: Optional[str] = "#5B2E8C"
    accent_color: Optional[str] = "#D9B35A"
    logo_url: Optional[str] = None
    custom_domain: Optional[str] = None


class LicenseUpdate(BaseModel):
    name: Optional[str] = None
    territory_code: Optional[str] = None
    tagline: Optional[str] = None
    contact_email: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    custom_domain: Optional[str] = None
    is_active: Optional[bool] = None


@licenses_admin_router.get("")
async def list_licenses(admin: dict = Depends(require_admin)):
    items = await db.licenses.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": items}


@licenses_admin_router.post("")
async def create_license(body: LicenseBody, admin: dict = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis")
    territory = await db.zones_v2.find_one({"code": body.territory_code.upper()}, {"_id": 0})
    if not territory:
        raise HTTPException(status_code=404, detail="Territoire inconnu")
    slug = _slugify(body.slug or name)
    if await db.licenses.find_one({"slug": slug}):
        raise HTTPException(status_code=409, detail=f"Le slug « {slug} » existe déjà")
    doc = {
        "id": str(uuid.uuid4()), "slug": slug, "name": name,
        "territory_code": territory["code"], "territory_name": territory["name"],
        "tagline": (body.tagline or "").strip(), "contact_email": (body.contact_email or "").strip(),
        "primary_color": body.primary_color or "#5B2E8C", "accent_color": body.accent_color or "#D9B35A",
        "logo_url": (body.logo_url or "").strip(), "is_active": True,
        "custom_domain": (body.custom_domain or "").strip().lower(),
        "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.licenses.insert_one({**doc})
    from consultation_audit import audit
    await audit("LICENSE_CREATED", admin.get("email"), None, {"slug": slug, "name": name, "territory": territory["code"]})
    logger.info("Licence marque blanche créée : %s (/t/%s) par %s", name, slug, admin.get("email"))
    return doc


@licenses_admin_router.post("/{license_id}/logo")
async def upload_license_logo(license_id: str, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    lic = await db.licenses.find_one({"id": license_id})
    if not lic:
        raise HTTPException(status_code=404, detail="Licence introuvable")
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/svg+xml"):
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPG, WEBP ou SVG")
    content = await file.read()
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo trop lourd (max 3 Mo)")
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}[file.content_type]
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "licenses")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{license_id}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(upload_dir, filename), "wb") as f:
        f.write(content)
    logo_url = f"/api/uploads/licenses/{filename}"
    await db.licenses.update_one({"id": license_id}, {"$set": {"logo_url": logo_url}})
    return {"ok": True, "logo_url": logo_url}


@licenses_admin_router.patch("/{license_id}")
async def update_license(license_id: str, body: LicenseUpdate, admin: dict = Depends(require_admin)):
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="Rien à mettre à jour")
    if "territory_code" in upd:
        territory = await db.zones_v2.find_one({"code": upd["territory_code"].upper()}, {"_id": 0})
        if not territory:
            raise HTTPException(status_code=404, detail="Territoire inconnu")
        upd["territory_code"] = territory["code"]
        upd["territory_name"] = territory["name"]
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.licenses.update_one({"id": license_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Licence introuvable")
    from consultation_audit import audit
    await audit("LICENSE_UPDATED", admin.get("email"), None, {"id": license_id, "changes": {k: v for k, v in upd.items() if k != "updated_at"}})
    return {"ok": True}


@licenses_admin_router.delete("/{license_id}")
async def delete_license(license_id: str, admin: dict = Depends(require_admin)):
    lic = await db.licenses.find_one({"id": license_id})
    if not lic:
        raise HTTPException(status_code=404, detail="Licence introuvable")
    await db.licenses.delete_one({"id": license_id})
    from consultation_audit import audit
    await audit("LICENSE_DELETED", admin.get("email"), None, {"slug": lic.get("slug"), "name": lic.get("name")})
    return {"ok": True}


@licenses_public_router.get("/by-domain/resolve")
async def license_by_domain(host: str):
    """Résolution marque blanche par domaine personnalisé (ex : kdmarche-guadeloupe.fr)."""
    host = host.strip().lower().removeprefix("www.")
    lic = await db.licenses.find_one(
        {"is_active": True, "custom_domain": {"$in": [host, f"www.{host}"]}}, {"_id": 0})
    if not lic:
        raise HTTPException(status_code=404, detail="Aucune licence pour ce domaine")
    return await _license_with_stats(lic)


async def _license_with_stats(lic: dict) -> dict:
    code = lic.get("territory_code")
    products_in_zone = await db.zone_prices.distinct("product_id", {"zone_code": code, "is_active": True})
    vendors_in_zone = await db.vendor_products.distinct("vendor_id", {"zones": code, "status": "approved"})
    lic["stats"] = {
        "products": len(products_in_zone),
        "orders": await db.orders.count_documents({"zone_code": code}),
        "vendors": len(vendors_in_zone),
    }
    return lic


@licenses_public_router.get("/{slug}")
async def public_license(slug: str):
    """Page vitrine marque blanche : branding + statistiques publiques du territoire."""
    lic = await db.licenses.find_one({"slug": slug.lower(), "is_active": True}, {"_id": 0})
    if not lic:
        raise HTTPException(status_code=404, detail="Licence introuvable ou inactive")
    return await _license_with_stats(lic)
