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
pricing_settings_router = APIRouter(prefix="/api/catalog/admin", tags=["product-ai"])
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


async def _create_draft_from_fields(ean: str, fields: dict, off: dict) -> dict:
    from datetime import datetime, timezone
    sku = f"EAN-{ean}"
    if await db.catalog_products.find_one({"$or": [{"sku": sku}, {"ean": ean}]}, {"id": 1}):
        return {"ean": ean, "status": "existant", "name": fields.get("name")}
    image_url = None
    off_img = (off or {}).get("image_front_url")
    if off_img:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(off_img)
                r.raise_for_status()
            up_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
            os.makedirs(up_dir, exist_ok=True)
            fname = f"off-{uuid.uuid4().hex[:8]}.jpg"
            with open(os.path.join(up_dir, fname), "wb") as f:
                f.write(r.content)
            image_url = f"/api/uploads/products/{fname}"
        except Exception:
            pass
    category = fields.get("category") if fields.get("category") in CATEGORY_VALUES else "alimentaire"
    now = datetime.now(timezone.utc)
    doc = {
        "id": f"prod_{uuid.uuid4().hex[:12]}", "sku": sku, "ean": ean,
        "name": fields.get("name") or f"Produit {ean}",
        "short_description": fields.get("short_description"), "description": fields.get("description"),
        "category": category, "subcategory": fields.get("subcategory"),
        "tags": fields.get("tags") or [], "brand": fields.get("brand"),
        "manufacturer": fields.get("manufacturer"), "status": "draft", "is_active": True,
        "is_new": True, "is_featured": False, "unit_type": "piece",
        "unit_label": fields.get("unit_label"),
        "pricing": {"price_ht_cents": 0, "currency": "EUR",
                    "tva_rate": 5.5 if category in ("alimentaire", "boissons") else 20},
        "origin": {"country_code": fields.get("country_code") or "FR", "region": fields.get("region")},
        "ingredients": fields.get("ingredients"), "image_url": image_url,
        "created_at": now, "updated_at": now,
    }
    await db.catalog_products.insert_one(doc)
    return {"ean": ean, "status": "cree", "name": doc["name"], "id": doc["id"], "image": bool(image_url)}


@product_ai_router.post("/bulk-ai")
async def bulk_ai_import(body: dict, admin: dict = Depends(require_admin)):
    """Import en masse : liste de codes EAN → fiches produit brouillon créées par l'IA."""
    raw = body.get("eans") or []
    eans = list(dict.fromkeys(e.strip() for e in raw if e and e.strip().isdigit()))[:10]
    if not eans:
        raise HTTPException(status_code=400, detail="Fournissez au moins un code EAN valide (max 10)")
    results = []
    for ean in eans:
        try:
            off = await _off_lookup(ean)
            if not off:
                results.append({"ean": ean, "status": "introuvable"})
                continue
            fields = await _llm_extract(off, None, ean)
            results.append(await _create_draft_from_fields(ean, fields, off))
            await log_ai_usage(db, "product_scan", f"bulk {ean}")
        except Exception as exc:
            logger.error("Import EAN %s échoué : %s", ean, exc)
            results.append({"ean": ean, "status": "erreur"})
    created = sum(1 for r in results if r["status"] == "cree")
    return {"results": results, "created": created, "total": len(eans)}


@product_ai_router.post("/ai-describe")
async def ai_describe(body: dict, admin: dict = Depends(require_admin)):
    """L'IA rédige les descriptions (accroche + description + tags) à partir des infos saisies."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Renseignez d'abord le nom du produit")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"ai-describe-{uuid.uuid4()}",
        system_message=("Tu es un rédacteur e-commerce B2B pour une centrale coopérative des Outre-mer. "
                        "Réponds UNIQUEMENT en JSON valide, sans markdown."),
    ).with_model("openai", "gpt-5.4")
    ctx = " | ".join(f"{k} : {body.get(k)}" for k in ("name", "brand", "manufacturer", "category", "subcategory", "unit_label", "ingredients") if body.get(k))
    prompt = (
        f"Rédige la fiche commerciale de ce produit : {ctx}.\n"
        'JSON attendu : {"short_description" (accroche vendeuse max 180 caractères, en français), '
        '"description" (3-5 phrases en français, ton professionnel et chaleureux, oriente vers l\'achat B2B), '
        '"tags" (6 à 8 mots-clés français en minuscules pour la barre de recherche du catalogue), '
        '"translations": {"en": {"short_description", "description"}, "es": {"short_description", "description"}} '
        '(traductions naturelles anglaise et espagnole des deux textes)}.')
    try:
        raw = str(await chat.send_message(UserMessage(text=prompt))).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
    except Exception as exc:
        logger.error("Description IA échouée : %s", exc)
        raise HTTPException(status_code=502, detail="Rédaction IA échouée — réessayez")
    await log_ai_usage(db, "product_scan", f"description {name}")
    return {k: v for k, v in data.items() if k in ("short_description", "description", "tags", "translations") and v}


@product_ai_router.post("/publish-bulk")
async def publish_bulk(body: dict, admin: dict = Depends(require_admin)):
    """Publie plusieurs fiches brouillon d'un coup."""
    ids = [i for i in (body.get("ids") or []) if isinstance(i, str)][:50]
    if not ids:
        raise HTTPException(status_code=400, detail="Sélectionnez au moins une fiche")
    res = await db.catalog_products.update_many(
        {"id": {"$in": ids}, "status": "draft"},
        {"$set": {"status": "approved", "is_active": True}})
    return {"published": res.modified_count, "requested": len(ids)}


@product_ai_router.post("/{product_id}/publish")
async def publish_product(product_id: str, admin: dict = Depends(require_admin)):
    """Publie une fiche brouillon (status draft → approved)."""
    res = await db.catalog_products.update_one(
        {"id": product_id}, {"$set": {"status": "approved", "is_active": True}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "status": "approved"}


@product_ai_router.post("/{product_id}/ai-price")
async def suggest_price(product_id: str, admin: dict = Depends(require_admin)):
    """L'IA suggère un prix de vente HT adapté au marché Outre-mer et l'applique à la fiche."""
    p = await db.catalog_products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    margins_doc = await db.pricing_margins.find_one({"id": "default"}, {"_id": 0}) or {}
    margin = margins_doc.get("margins", {}).get(p.get("category"), DEFAULT_MARGIN)
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"ai-price-{uuid.uuid4()}",
        system_message=("Tu es un expert pricing de la grande distribution dans les Outre-mer français "
                        "(Guadeloupe, Martinique, Guyane, Réunion) : octroi de mer, fret, coût de la vie +15-40% vs métropole. "
                        "Réponds UNIQUEMENT en JSON valide, sans markdown."),
    ).with_model("openai", "gpt-5.4")
    prompt = (
        "Suggère un prix de vente HT réaliste pour ce produit vendu en B2B via une centrale coopérative aux Outre-mer. "
        f"Produit : {p.get('name')} | Marque : {p.get('brand')} | Catégorie : {p.get('category')} | "
        f"Conditionnement : {p.get('unit_label') or 'unité'} | EAN : {p.get('ean') or 'n/a'}.\n"
        f"CONTRAINTE : estime d'abord le coût d'approvisionnement rendu Outre-mer (achat + fret + octroi de mer), "
        f"puis applique EXACTEMENT la marge cible de {margin}% fixée par l'admin pour cette catégorie.\n"
        'JSON attendu : {"cost_estimate_cents" (coût estimé en centimes), '
        '"price_ht_cents" (entier = coût × (1 + marge), arrondi commercialement), '
        '"reason" (1 phrase en français : coût estimé + marge appliquée)}.')
    try:
        raw = str(await chat.send_message(UserMessage(text=prompt))).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        price = max(1, int(data["price_ht_cents"]))
    except Exception as exc:
        logger.error("Prix IA échoué %s : %s", product_id, exc)
        raise HTTPException(status_code=502, detail="Suggestion de prix échouée — réessayez")
    await db.catalog_products.update_one(
        {"id": product_id}, {"$set": {"pricing.price_ht_cents": price}})
    await log_ai_usage(db, "product_scan", f"prix {p.get('name')}")
    return {"price_ht_cents": price, "reason": data.get("reason", ""),
            "cost_estimate_cents": data.get("cost_estimate_cents"), "margin_target": margin}


DEFAULT_MARGIN = 25


@pricing_settings_router.get("/pricing-margins")
async def get_pricing_margins(admin: dict = Depends(require_admin)):
    doc = await db.pricing_margins.find_one({"id": "default"}, {"_id": 0}) or {}
    margins = {c: DEFAULT_MARGIN for c in CATEGORY_VALUES}
    margins.update(doc.get("margins", {}))
    return {"margins": margins, "default": DEFAULT_MARGIN}


@pricing_settings_router.put("/pricing-margins")
async def set_pricing_margins(body: dict, admin: dict = Depends(require_admin)):
    margins = {k: max(0, min(int(v), 300)) for k, v in (body.get("margins") or {}).items()
               if k in CATEGORY_VALUES and isinstance(v, (int, float))}
    await db.pricing_margins.update_one({"id": "default"}, {"$set": {"margins": margins}}, upsert=True)
    return await get_pricing_margins(admin)
