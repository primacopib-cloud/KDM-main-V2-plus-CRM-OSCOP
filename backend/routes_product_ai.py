"""Assistant IA fiche produit : scan photo/EAN → autoremplissage, image retrouvée (OpenFoodFacts) ou générée."""
import json
import logging
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin
from ai_usage import log_ai_usage

logger = logging.getLogger(__name__)
product_ai_router = APIRouter(prefix="/api/catalog/admin/products", tags=["product-ai"])
db = None

CATEGORY_VALUES = ["alimentaire", "boissons", "materiaux", "equipements", "matieres_premieres",
                   "hygiene", "chimie", "textile", "electronique", "autre"]
ALLOWED_KEYS = {"name", "brand", "manufacturer", "category", "subcategory", "short_description",
                "description", "tags", "ean", "unit_label", "country_code", "region",
                "ingredients", "nutri_score", "allergens_contains",
                "energy_kcal", "fat_g", "carbohydrates_g", "protein_g", "salt_g", "net_weight_kg"}


def set_product_ai_database(database):
    global db
    db = database


async def _off_lookup(ean: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(
                f"https://world.openfoodfacts.org/api/v2/product/{ean}",
                params={"fields": "product_name,brands,quantity,image_front_url,categories,"
                                  "ingredients_text_fr,ingredients_text,nutriscore_grade,"
                                  "nutriments,allergens_tags,countries"})
            data = r.json()
            if data.get("status") == 1:
                return data.get("product")
    except Exception as exc:
        logger.warning("OpenFoodFacts lookup %s : %s", ean, exc)
    return None


async def _llm_extract(off: dict | None, photo_b64: str | None, ean: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"product-scan-{uuid.uuid4()}",
        system_message=("Tu es un assistant de saisie de fiches produit e-commerce B2B. "
                        "Réponds UNIQUEMENT avec un objet JSON valide, sans markdown."),
    ).with_model("openai", "gpt-5.4")
    prompt = (
        "Remplis une fiche produit à partir des informations fournies"
        + (" et de la PHOTO du produit (lis aussi le code-barres EAN s'il est visible)" if photo_b64 else "") + ".\n"
        f"Catégories autorisées : {', '.join(CATEGORY_VALUES)}.\n"
        'JSON attendu (mets null si inconnu) : {"name", "brand", "manufacturer", "category" (une des catégories autorisées), '
        '"subcategory", "short_description" (accroche vendeuse max 180 caractères, en français), '
        '"description" (3-4 phrases en français), '
        '"tags" (6 à 8 mots-clés français en minuscules que taperait un acheteur dans une barre de recherche du catalogue), '
        '"ean", "unit_label" (ex: "bouteille 70cl"), "country_code" (ISO-2), "region", '
        '"ingredients", "nutri_score" (A-E), "allergens_contains" (liste), '
        '"energy_kcal", "fat_g", "carbohydrates_g", "protein_g", "salt_g" (pour 100g), "net_weight_kg"}.\n'
    )
    if ean:
        prompt += f"Code EAN scanné : {ean}\n"
    if off:
        prompt += f"Données OpenFoodFacts : {json.dumps(off, ensure_ascii=False)[:2500]}\n"
    msg = UserMessage(text=prompt, file_contents=[ImageContent(photo_b64)]) if photo_b64 else UserMessage(text=prompt)
    raw = str(await chat.send_message(msg)).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    data = json.loads(raw)
    return {k: v for k, v in data.items() if k in ALLOWED_KEYS and v not in (None, "", [])}


@product_ai_router.post("/ai-scan")
async def ai_scan_product(body: dict, admin: dict = Depends(require_admin)):
    ean = (body.get("ean") or "").strip()
    photo = body.get("photo") or ""
    photo_b64 = photo.split(",", 1)[1] if photo.startswith("data:image") else None
    if not ean and not photo_b64:
        raise HTTPException(status_code=400, detail="Fournissez une photo du produit ou un code EAN")
    off = await _off_lookup(ean) if ean else None
    try:
        fields = await _llm_extract(off, photo_b64, ean)
    except Exception as exc:
        logger.error("Scan IA produit échoué : %s", exc)
        raise HTTPException(status_code=502, detail="L'analyse IA a échoué — réessayez")
    if not off and fields.get("ean") and not ean:
        off = await _off_lookup(str(fields["ean"]))
    if off and off.get("image_front_url"):
        fields["off_image_url"] = off["image_front_url"]
    if ean and not fields.get("ean"):
        fields["ean"] = ean
    await log_ai_usage(db, "product_scan", fields.get("name") or ean)
    return {"fields": fields, "source": "openfoodfacts+ia" if off else ("photo+ia" if photo_b64 else "ia")}


@product_ai_router.post("/ai-image")
async def ai_product_image(body: dict, admin: dict = Depends(require_admin)):
    name = (body.get("name") or "").strip()
    brand = (body.get("brand") or "").strip()
    ean = (body.get("ean") or "").strip()
    off_url = (body.get("off_image_url") or "").strip()
    if not name and not ean and not off_url:
        raise HTTPException(status_code=400, detail="Renseignez au moins le nom ou la marque du produit")
    if not off_url and ean:
        off = await _off_lookup(ean)
        off_url = (off or {}).get("image_front_url") or ""
    if off_url:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(off_url)
                r.raise_for_status()
            up_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
            os.makedirs(up_dir, exist_ok=True)
            ext = "png" if off_url.lower().endswith(".png") else "jpg"
            fname = f"off-{uuid.uuid4().hex[:8]}.{ext}"
            with open(os.path.join(up_dir, fname), "wb") as f:
                f.write(r.content)
            return {"image_url": f"/api/uploads/products/{fname}", "source": "retrouvee"}
        except Exception as exc:
            logger.warning("Image OpenFoodFacts non téléchargée : %s", exc)
    from ai_media_service import generate_product_image
    try:
        url = await generate_product_image(
            f"Commercial product packshot of: {name}" + (f", brand '{brand}'" if brand else ""), "aiprod")
    except Exception as exc:
        logger.error("Génération image produit échouée : %s", exc)
        raise HTTPException(status_code=502, detail="Génération d'image impossible — réessayez")
    await log_ai_usage(db, "product_image", f"{brand} {name}".strip())
    return {"image_url": url, "source": "generee"}
