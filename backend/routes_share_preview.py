"""Testeur d'aperçu de partage (balises OG) pour les admins : racine du site + fiches produits."""
import html as html_mod
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from lolodrive_helpers import require_admin

share_preview_router = APIRouter(prefix="/api/admin/share-preview", tags=["share-preview"])

db = None


def set_share_preview_database(database):
    global db
    db = database


META_RE = re.compile(r"<meta\s+[^>]*>", re.I)
ATTR_RE = re.compile(r"([a-zA-Z:-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")


def _parse_og(html: str) -> dict:
    out = {}
    for m in META_RE.findall(html):
        attrs = {k: html_mod.unescape(v1 if v1 else v2) for k, v1, v2 in ATTR_RE.findall(m)}
        key = attrs.get("property") or attrs.get("name")
        if key and (key.startswith("og:") or key.startswith("twitter:")):
            out.setdefault(key, attrs.get("content", ""))
    t = re.search(r"<title[^>]*>([^<]*)</title>", html, re.I)
    if t:
        out.setdefault("page_title", html_mod.unescape(t.group(1).strip()))
    return out


@share_preview_router.get("/products")
async def preview_products(admin: dict = Depends(require_admin)):
    prods = await db.products.find(
        {"status": "ACTIVE"}, {"_id": 0, "id": 1, "name": 1}).sort("name", 1).to_list(100)
    return {"products": prods}


@share_preview_router.get("")
async def share_preview(request: Request, kind: str = "home", product_id: str = "",
                        admin: dict = Depends(require_admin)):
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto", "https")
    base = f"{proto}://{host}"
    if kind == "product":
        if not product_id:
            raise HTTPException(status_code=400, detail="Choisissez un produit")
        url = f"{base}/api/share/product/{product_id}"
        public_url = url
    else:
        url = f"{base}/"
        public_url = base
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "facebookexternalhit/1.1 (compatible; SharePreviewTester)"})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Impossible de récupérer la page : {exc}")
    tags = _parse_og(r.text)
    image = tags.get("og:image") or tags.get("twitter:image") or ""
    if image.startswith("/"):
        image = base + image
    return {
        "url": public_url, "domain": host, "status_code": r.status_code,
        "title": tags.get("og:title") or tags.get("page_title") or "",
        "description": tags.get("og:description") or tags.get("twitter:description") or "",
        "image": image,
        "site_name": tags.get("og:site_name") or "",
        "image_absolute": image.startswith("http"),
    }
