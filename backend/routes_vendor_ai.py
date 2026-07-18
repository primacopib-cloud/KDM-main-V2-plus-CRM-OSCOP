"""Routes Studio IA vendeur : génération/amélioration d'images + spot vidéo — /api/vendor/ai/*."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import ai_media_service
from vendor_credits import consume_credits, refund_credits

logger = logging.getLogger(__name__)

vendor_ai_router = APIRouter(prefix="/api/vendor/ai", tags=["Vendor AI Studio"])

db = None


def set_vendor_ai_database(database) -> None:
    global db
    db = database


class GenerateImagePayload(BaseModel):
    prompt: str


class EnhanceImagePayload(BaseModel):
    image_url: str
    instructions: str = ""


class GenerateVideoPayload(BaseModel):
    prompt: str
    image_url: str | None = None


async def _get_product(vendor_id: str, product_id: str) -> dict:
    product = await db.vendor_products.find_one({"id": product_id, "vendor_id": vendor_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product


async def _attach_image(product: dict, url: str) -> bool:
    """Ajoute l'image au produit si < 3 photos. Retourne True si attachée."""
    images = product.get("images") or []
    if len(images) >= 3:
        return False
    image = {"url": url, "is_primary": not images, "added_at": datetime.now(timezone.utc).isoformat(), "ai": True}
    await db.vendor_products.update_one({"id": product["id"]}, {"$push": {"images": image}})
    if image["is_primary"] and product.get("status") == "approved":
        await db.products.update_one({"id": product["id"]}, {"$set": {"image_url": url}})
    return True


@vendor_ai_router.get("/status")
async def ai_studio_status():
    return {"images": True, "video": ai_media_service.is_video_configured()}


@vendor_ai_router.post("/{vendor_id}/{product_id}/generate-image")
async def ai_generate_image(vendor_id: str, product_id: str, payload: GenerateImagePayload):
    product = await _get_product(vendor_id, product_id)
    await consume_credits(vendor_id, "ai_image_generation", f"Image IA pour {product['name']}")
    try:
        url = await ai_media_service.generate_product_image(payload.prompt, product_id)
    except Exception as exc:
        logger.error("AI image generation failed: %s", exc)
        await refund_credits(vendor_id, "ai_image_generation")
        raise HTTPException(status_code=502, detail="Échec de la génération IA — crédits remboursés, réessayez")
    attached = await _attach_image(product, url)
    return {"success": True, "image_url": url, "attached": attached}


@vendor_ai_router.post("/{vendor_id}/{product_id}/enhance-image")
async def ai_enhance_image(vendor_id: str, product_id: str, payload: EnhanceImagePayload):
    product = await _get_product(vendor_id, product_id)
    if not payload.image_url.startswith("/api/uploads/products/"):
        raise HTTPException(status_code=400, detail="URL d'image invalide")
    filename = os.path.basename(payload.image_url)
    path = os.path.join(os.path.dirname(__file__), "uploads", "products", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier image introuvable")
    await consume_credits(vendor_id, "ai_image_enhance", f"Amélioration photo pour {product['name']}")
    try:
        url = await ai_media_service.enhance_product_image(path, product_id, payload.instructions)
    except Exception as exc:
        logger.error("AI image enhance failed: %s", exc)
        await refund_credits(vendor_id, "ai_image_enhance")
        raise HTTPException(status_code=502, detail="Échec de l'amélioration IA — crédits remboursés, réessayez")
    attached = await _attach_image(product, url)
    return {"success": True, "image_url": url, "attached": attached}


@vendor_ai_router.post("/{vendor_id}/{product_id}/generate-video")
async def ai_generate_video(vendor_id: str, product_id: str, payload: GenerateVideoPayload):
    product = await _get_product(vendor_id, product_id)
    if not ai_media_service.is_video_configured():
        raise HTTPException(
            status_code=503,
            detail="Génération vidéo non configurée : une clé fal.ai (FAL_KEY) est requise. Obtenez-la sur fal.ai/dashboard/keys.",
        )
    await consume_credits(vendor_id, "ai_video_generation", f"Spot vidéo pour {product['name']}")
    job = {
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "product_id": product_id,
        "prompt": payload.prompt, "status": "RUNNING", "video_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ai_video_jobs.insert_one({**job})
    asyncio.get_event_loop().create_task(_run_video_job(job["id"], payload))
    return {"success": True, "job_id": job["id"], "status": "RUNNING"}


async def _run_video_job(job_id: str, payload: GenerateVideoPayload) -> None:
    try:
        image_abs = None
        if payload.image_url:
            base = os.environ.get("FRONTEND_URL", "")
            image_abs = payload.image_url if payload.image_url.startswith("http") else f"{base}{payload.image_url}"
        result = await ai_media_service.generate_product_video(payload.prompt, image_abs)
        await db.ai_video_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "DONE", "video_url": result.get("video_url"),
                      "finished_at": datetime.now(timezone.utc).isoformat()}},
        )
    except Exception as exc:
        logger.error("Video job %s failed: %s", job_id, exc)
        job_doc = await db.ai_video_jobs.find_one({"id": job_id}, {"_id": 0, "vendor_id": 1})
        if job_doc:
            await refund_credits(job_doc["vendor_id"], "ai_video_generation")
        await db.ai_video_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "ERROR", "error": str(exc)[:300]}}
        )


@vendor_ai_router.get("/video-jobs/{job_id}")
async def get_video_job(job_id: str):
    job = await db.ai_video_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job
