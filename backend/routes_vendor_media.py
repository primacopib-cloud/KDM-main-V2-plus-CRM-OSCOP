"""Vendor product media endpoints (photos, PDF sheet, documents) — split from routes_vendor.py."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from datetime import datetime, timezone
import os
import uuid
import logging

from vendor_models import ProductStatus, ProductDocument

logger = logging.getLogger(__name__)

vendor_media_router = APIRouter(prefix="/api/vendor")

db = None


def set_vendor_media_database(database):
    global db
    db = database


@vendor_media_router.post("/products/{vendor_id}/{product_id}/upload-image")
async def upload_product_image(
    vendor_id: str,
    product_id: str,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
):
    """Téléverse une photo produit (PNG/JPEG, max 3 photos, 5 Mo max)."""
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    if len(product.get("images") or []) >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 photos par produit")
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Format accepté : PNG ou JPEG uniquement")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Photo trop lourde (max 5 Mo)")

    from vendor_credits import consume_credits
    _zones = product.get("available_zones") or product.get("zones") or []
    await consume_credits(vendor_id, "photo_upload", f"Photo produit {product.get('name', product_id)}",
                          category=product.get("category"), territory=(_zones[0] if _zones else None))

    ext = "png" if file.content_type == "image/png" else "jpg"
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{product_id}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(upload_dir, filename), "wb") as f:
        f.write(content)

    image = {
        "url": f"/api/uploads/products/{filename}",
        "is_primary": is_primary or not (product.get("images") or []),
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    if image["is_primary"] and (product.get("images") or []):
        await db.vendor_products.update_one({"id": product_id}, {"$set": {"images.$[].is_primary": False}})
    await db.vendor_products.update_one({"id": product_id}, {"$push": {"images": image}})
    # Sync la photo principale vers le catalogue B2B si le produit est déjà approuvé
    if image["is_primary"] and product.get("status") == ProductStatus.APPROVED.value:
        await db.products.update_one({"id": product_id}, {"$set": {"image_url": image["url"]}})
    return {"success": True, "image": image}


@vendor_media_router.get("/products/{vendor_id}/{product_id}/pdf")
async def download_product_sheet(vendor_id: str, product_id: str):
    """Télécharge la fiche produit au format PDF."""
    from fastapi.responses import Response
    from pdf_product_sheet import generate_product_sheet_pdf

    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    pdf = generate_product_sheet_pdf(product)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fiche-{product.get("sku", product_id)}.pdf"'},
    )


@vendor_media_router.post("/products/{vendor_id}/{product_id}/images")
async def add_product_image(vendor_id: str, product_id: str, image_url: str, is_primary: bool = False):
    """Add image URL to product"""

    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    image = {
        "url": image_url,
        "is_primary": is_primary,
        "added_at": datetime.now(timezone.utc).isoformat()
    }

    # If primary, set others to non-primary
    if is_primary:
        await db.vendor_products.update_one(
            {"id": product_id},
            {"$set": {"images.$[].is_primary": False}}
        )

    await db.vendor_products.update_one(
        {"id": product_id},
        {"$push": {"images": image}}
    )

    return {"success": True, "message": "Image ajoutée"}


@vendor_media_router.post("/products/{vendor_id}/{product_id}/documents")
async def add_product_document(vendor_id: str, product_id: str, doc: ProductDocument):
    """Add document to product (technical, regulatory, certificate)"""

    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    document = {
        "id": f"doc_{uuid.uuid4().hex[:8]}",
        "type": doc.document_type.value,
        "name": doc.name,
        "url": doc.url,
        "description": doc.description,
        "added_at": datetime.now(timezone.utc).isoformat()
    }

    await db.vendor_products.update_one(
        {"id": product_id},
        {"$push": {"documents": document}}
    )

    return {"success": True, "message": "Document ajouté", "document_id": document["id"]}
