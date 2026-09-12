"""Import catalogue fournisseur (annexe technique V1.0) : CSV « ; » UTF-8 ou .xlsx → vendor_products, avec rapport d'erreurs par email."""
import csv
import io
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

catalog_import_router = APIRouter(prefix="/api/vendors", tags=["Import catalogue"])

db = None

REQUIRED = ["sku_fournisseur", "code_ean", "designation_produit", "categorie",
            "prix_unitaire_ht", "taux_tva", "quantite_stock", "conditionnement"]
ALL_COLS = REQUIRED[:4] + ["description"] + REQUIRED[4:] + ["poids_kg", "volume_m3", "url_image"]
VALID_TVA = {0.0, 2.1, 8.5}


def set_catalog_import_database(database):
    global db
    db = database


def _parse_rows(filename: str, content: bytes):
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows = [[("" if c is None else str(c).strip()) for c in r] for r in ws.iter_rows(values_only=True)]
    elif name.endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Encodage invalide : le CSV doit être en UTF-8")
        rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text), delimiter=";")]
    else:
        raise HTTPException(status_code=400, detail="Format non accepté : .csv (séparateur ;) ou .xlsx uniquement")
    rows = [r for r in rows if any(r)]
    if not rows:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return rows


def _validate(rows):
    """Retourne (produits_valides, erreurs[list de str])."""
    errors, valid = [], []
    headers = [h.strip().lower() for h in rows[0]]
    missing = [c for c in REQUIRED if c not in headers]
    if missing:
        return [], [f"En-têtes manquants ou renommés : {', '.join(missing)} (ligne 1)"]
    idx = {c: headers.index(c) for c in headers if c}
    for n, row in enumerate(rows[1:], start=2):
        def g(col):
            i = idx.get(col)
            return row[i] if i is not None and i < len(row) else ""
        line_err = []
        sku = g("sku_fournisseur")
        if not sku:
            line_err.append("sku_fournisseur manquant")
        elif " " in sku:
            line_err.append("sku_fournisseur contient un espace")
        ean = g("code_ean").split(".")[0]
        if not (ean.isdigit() and len(ean) == 13):
            line_err.append(f"code_ean invalide ({ean or 'vide'} — 13 chiffres requis)")
        if not g("designation_produit"):
            line_err.append("designation_produit manquante")
        if not g("categorie"):
            line_err.append("categorie manquante")
        price_raw = g("prix_unitaire_ht")
        if "," in price_raw:
            line_err.append("prix_unitaire_ht : utilisez un point comme séparateur décimal")
            price = None
        else:
            try:
                price = float(price_raw)
                if price <= 0:
                    line_err.append("prix_unitaire_ht doit être positif")
            except ValueError:
                price = None
                line_err.append(f"prix_unitaire_ht invalide ({price_raw or 'vide'})")
        try:
            tva = float(g("taux_tva"))
            if tva not in VALID_TVA:
                line_err.append(f"taux_tva {tva} non autorisé (0, 2.1 ou 8.5)")
        except ValueError:
            tva = None
            line_err.append(f"taux_tva invalide ({g('taux_tva') or 'vide'})")
        stock_raw = g("quantite_stock").split(".")[0]
        if not stock_raw.lstrip("-").isdigit():
            line_err.append(f"quantite_stock doit être un nombre entier ({g('quantite_stock') or 'vide'})")
            stock = None
        else:
            stock = int(stock_raw)
            if stock < 0:
                line_err.append("quantite_stock négative")
        if not g("conditionnement"):
            line_err.append("conditionnement manquant")
        url = g("url_image")
        if url and not url.startswith("https://"):
            line_err.append("url_image doit commencer par https://")
        weight = volume = None
        for col, unit in (("poids_kg", "kg"), ("volume_m3", "m³")):
            raw = g(col)
            if raw:
                try:
                    val = float(raw.replace(",", "."))
                    if val < 0:
                        line_err.append(f"{col} négatif")
                    elif col == "poids_kg":
                        weight = val
                    else:
                        volume = val
                except ValueError:
                    line_err.append(f"{col} invalide ({raw})")
        if line_err:
            errors.append(f"Ligne {n} : " + " ; ".join(line_err))
        else:
            valid.append({
                "sku": sku, "ean": ean, "name": g("designation_produit")[:150],
                "category": g("categorie"), "description": g("description"),
                "price_ht": price, "tva_rate": tva, "stock_quantity": stock,
                "conditionnement": g("conditionnement"),
                "weight_kg": weight, "volume_m3": volume,
                "image_url": url or None,
            })
    return valid, errors


async def _send_error_report(vendor: dict, filename: str, errors: list):
    from brevo_service import send_email
    rows = "".join(f"<li>{e}</li>" for e in errors[:50])
    more = f"<p>… et {len(errors) - 50} autres anomalies.</p>" if len(errors) > 50 else ""
    await send_email(
        to_email=vendor.get("email"), to_name=vendor.get("company_name"),
        subject=f"❌ Import catalogue rejeté — {filename}",
        html_content=(f"<p>Bonjour,</p><p>Votre fichier catalogue <b>{filename}</b> a été <b>rejeté</b> par la plateforme "
                      f"CommunityPlace. Rapport d'anomalies :</p><ul>{rows}</ul>{more}"
                      "<p>Corrigez les lignes indiquées puis déposez de nouveau le fichier (voir la checklist de l'annexe technique).</p>"
                      "<p>Support : tech@objectifscopoutremer.com — data@kdmarche.com</p>"),
        tags=["catalog-import-error"])


async def _download_image(product_id: str, url: str) -> dict:
    """Télécharge l'image publique https et la stocke dans l'object storage."""
    import httpx
    async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}) as cl:
        r = await cl.get(url)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(ctype)
    if not ext:
        raise ValueError(f"type non supporté ({ctype or 'inconnu'})")
    if len(r.content) > 5 * 1024 * 1024:
        raise ValueError("image trop lourde (max 5 Mo)")
    from upload_storage import save_upload
    dest = await save_upload(f"products/{product_id}-import-{uuid.uuid4().hex[:8]}.{ext}", r.content, ctype)
    return {"url": dest, "is_primary": True,
            "added_at": datetime.now(timezone.utc).isoformat(), "source": "catalog_import"}


async def _log_import(vendor_id: str, filename: str, status: str, **extra):
    await db.catalog_imports.insert_one({
        "id": str(uuid.uuid4()), "vendor_id": vendor_id, "filename": filename, "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(), **extra})


@catalog_import_router.get("/catalog-template/{fmt}")
async def catalog_template(fmt: str):
    """Modèle officiel de catalogue fournisseur (annexe technique V1.0)."""
    import os
    from fastapi.responses import FileResponse
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(status_code=404, detail="Format inconnu : csv ou xlsx")
    path = os.path.join(os.path.dirname(__file__), "assets", "catalogue", f"modele_catalogue_fournisseur.{fmt}")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Modèle indisponible")
    media = "text/csv" if fmt == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path, media_type=media, filename=f"modele_catalogue_fournisseur.{fmt}")


@catalog_import_router.get("/{vendor_id}/catalog-imports")
async def import_history(vendor_id: str, request: Request):
    from role_guards import ensure_seller_request
    await ensure_seller_request(db, request, vendor_id)
    items = await db.catalog_imports.find({"vendor_id": vendor_id}, {"_id": 0}) \
        .sort("created_at", -1).limit(20).to_list(20)
    return {"items": items}


@catalog_import_router.post("/{vendor_id}/catalog-import")
async def import_catalog(vendor_id: str, request: Request, file: UploadFile = File(...), confirm: bool = False):
    from role_guards import ensure_seller_request
    await ensure_seller_request(db, request, vendor_id)
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendeur introuvable")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo)")
    rows = _parse_rows(file.filename, content)
    valid, errors = _validate(rows)
    if errors:
        try:
            await _send_error_report(vendor, file.filename, errors)
        except Exception as exc:
            logger.warning("Email rapport import %s : %s", vendor_id, exc)
        await _log_import(vendor_id, file.filename, "rejected", error_count=len(errors), errors=errors[:20])
        return {"ok": False, "rejected": True, "errors": errors[:50], "error_count": len(errors),
                "message": "Import rejeté — rapport d'anomalies envoyé par email au contact technique"}
    if not confirm:
        return {"ok": True, "preview": True, "total": len(valid),
                "products": [{k: p[k] for k in ("sku", "name", "category", "price_ht", "tva_rate",
                                                "stock_quantity", "conditionnement", "image_url")} for p in valid]}
    from auth import extract_user_id_from_request
    from click_billing import charge_click
    click_user = extract_user_id_from_request(request)
    if click_user:
        await charge_click(db, click_user, f"Import catalogue — {file.filename} ({len(valid)} produits)")
    return await _apply_products(vendor_id, file.filename, valid)


async def _apply_products(vendor_id: str, filename: str, valid: list) -> dict:
    """Crée / met à jour les produits validés et télécharge les images ; trace l'historique."""
    created = updated = images_downloaded = 0
    now = datetime.now(timezone.utc).isoformat()
    for p in valid:
        base = {
            "name": p["name"], "description": p["description"], "category": p["category"],
            "price_ht": p["price_ht"], "tva_rate": p["tva_rate"],
            "price_ttc": round(p["price_ht"] * (1 + p["tva_rate"] / 100), 2),
            "stock_quantity": p["stock_quantity"], "unit": p["conditionnement"],
            "ean": p["ean"], "weight_kg": p["weight_kg"], "volume_m3": p["volume_m3"],
            "updated_at": now, "import_source": "catalog_file",
        }
        if p["image_url"]:
            base["image_url"] = p["image_url"]
        existing = await db.vendor_products.find_one({"vendor_id": vendor_id, "sku": p["sku"]},
                                                     {"_id": 0, "id": 1, "images": 1})
        if existing:
            await db.vendor_products.update_one({"vendor_id": vendor_id, "sku": p["sku"]}, {"$set": base})
            updated += 1
            pid, has_images = existing["id"], bool(existing.get("images"))
        else:
            base["status"] = "pending_approval"
            pid, has_images = str(uuid.uuid4()), False
            await db.vendor_products.insert_one({
                "id": pid, "vendor_id": vendor_id, "sku": p["sku"],
                **base, "images": [], "documents": [], "created_at": now, "submitted_at": now,
            })
            created += 1
        if p["image_url"] and not has_images:
            try:
                image = await _download_image(pid, p["image_url"])
                await db.vendor_products.update_one({"id": pid}, {"$push": {"images": image}})
                images_downloaded += 1
            except Exception as exc:
                logger.warning("Image import %s (%s) : %s", p["sku"], p["image_url"], exc)
    await _log_import(vendor_id, filename, "success", created=created, updated=updated,
                      total=len(valid), images_downloaded=images_downloaded)
    return {"ok": True, "created": created, "updated": updated, "total": len(valid),
            "images_downloaded": images_downloaded,
            "message": f"{created} produit(s) créé(s), {updated} mis à jour"
                       + (f", {images_downloaded} image(s) téléchargée(s)" if images_downloaded else "")}


# ---------- Synchronisation planifiée (import quotidien depuis une URL) ----------

class SyncConfig(BaseModel):
    url: str = ""
    enabled: bool = False


@catalog_import_router.get("/{vendor_id}/catalog-sync")
async def get_catalog_sync(vendor_id: str, request: Request):
    from role_guards import ensure_seller_request
    await ensure_seller_request(db, request, vendor_id)
    doc = await db.vendor_catalog_sync.find_one({"vendor_id": vendor_id}, {"_id": 0})
    return doc or {"vendor_id": vendor_id, "url": "", "enabled": False}


@catalog_import_router.put("/{vendor_id}/catalog-sync")
async def save_catalog_sync(vendor_id: str, body: SyncConfig, request: Request):
    from role_guards import ensure_seller_request
    await ensure_seller_request(db, request, vendor_id)
    url = body.url.strip()
    if body.enabled and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="L'URL du fichier doit commencer par https://")
    await db.vendor_catalog_sync.update_one(
        {"vendor_id": vendor_id},
        {"$set": {"url": url, "enabled": body.enabled,
                  "updated_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "vendor_id": vendor_id}},
        upsert=True)
    return {"ok": True, "url": url, "enabled": body.enabled}


@catalog_import_router.post("/{vendor_id}/catalog-sync/run")
async def run_catalog_sync_now(vendor_id: str, request: Request):
    from role_guards import ensure_seller_request
    await ensure_seller_request(db, request, vendor_id)
    sync = await db.vendor_catalog_sync.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not sync or not sync.get("url"):
        raise HTTPException(status_code=400, detail="Aucune URL de synchronisation enregistrée")
    return await _run_one_sync(sync)


async def _run_one_sync(sync: dict) -> dict:
    """Télécharge le fichier catalogue distant d'un vendeur et applique l'import."""
    vendor_id, url = sync["vendor_id"], sync["url"]
    now = datetime.now(timezone.utc).isoformat()
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0})

    async def _finish(status: str, message: str, result: dict | None = None):
        await db.vendor_catalog_sync.update_one(
            {"vendor_id": vendor_id},
            {"$set": {"last_run_at": now, "last_status": status, "last_message": message}})
        return {"ok": status == "success", "status": status, "message": message, **(result or {})}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}) as cl:
            r = await cl.get(url)
        r.raise_for_status()
        if len(r.content) > 5 * 1024 * 1024:
            return await _finish("error", "Fichier distant trop volumineux (max 5 Mo)")
    except Exception as exc:
        return await _finish("error", f"Téléchargement impossible : {exc}")
    fname = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1] or "catalogue-distant"
    if not fname.lower().endswith((".csv", ".xlsx")):
        ctype = (r.headers.get("content-type") or "").lower()
        fname += ".xlsx" if "spreadsheet" in ctype or "excel" in ctype else ".csv"
    try:
        rows = _parse_rows(fname, r.content)
        valid, errors = _validate(rows)
    except HTTPException as exc:
        return await _finish("error", f"Fichier illisible : {exc.detail}")
    if errors:
        try:
            await _send_error_report(vendor, fname, errors)
        except Exception as exc:
            logger.warning("Email rapport sync %s : %s", vendor_id, exc)
        await _log_import(vendor_id, f"{fname} (sync auto)", "rejected", error_count=len(errors), errors=errors[:20])
        return await _finish("rejected", f"{len(errors)} anomalie(s) — rapport envoyé par email")
    result = await _apply_products(vendor_id, f"{fname} (sync auto)", valid)
    return await _finish("success", result["message"], result)


async def run_catalog_syncs(database):
    """Cron quotidien : synchronise les catalogues distants activés (au plus une fois par 22 h)."""
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc)
    ran = 0
    async for sync in db.vendor_catalog_sync.find({"enabled": True, "url": {"$ne": ""}}):
        last = sync.get("last_run_at")
        if last:
            try:
                if (now - datetime.fromisoformat(last)).total_seconds() < 22 * 3600:
                    continue
            except ValueError:
                pass
        try:
            res = await _run_one_sync(sync)
            logger.info("Sync catalogue %s : %s", sync["vendor_id"], res.get("message"))
            ran += 1
        except Exception as exc:
            logger.exception("Sync catalogue %s : %s", sync["vendor_id"], exc)
    return ran
