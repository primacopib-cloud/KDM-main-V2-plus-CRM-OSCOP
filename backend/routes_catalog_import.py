"""Import catalogue fournisseur (annexe technique V1.0) : CSV « ; » UTF-8 ou .xlsx → vendor_products, avec rapport d'erreurs par email."""
import csv
import io
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

logger = logging.getLogger(__name__)

catalog_import_router = APIRouter(prefix="/api/vendors", tags=["Import catalogue"])

db = None

REQUIRED = ["sku_fournisseur", "code_ean", "designation_produit", "categorie",
            "prix_unitaire_ht", "taux_tva", "quantite_stock", "conditionnement"]
ALL_COLS = REQUIRED[:4] + ["description"] + REQUIRED[4:] + ["poids_kg", "url_image"]
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
        if line_err:
            errors.append(f"Ligne {n} : " + " ; ".join(line_err))
        else:
            valid.append({
                "sku": sku, "ean": ean, "name": g("designation_produit")[:150],
                "category": g("categorie"), "description": g("description"),
                "price_ht": price, "tva_rate": tva, "stock_quantity": stock,
                "conditionnement": g("conditionnement"),
                "weight_kg": float(g("poids_kg")) if g("poids_kg") else None,
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


@catalog_import_router.post("/{vendor_id}/catalog-import")
async def import_catalog(vendor_id: str, request: Request, file: UploadFile = File(...)):
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
        return {"ok": False, "rejected": True, "errors": errors[:50], "error_count": len(errors),
                "message": "Import rejeté — rapport d'anomalies envoyé par email au contact technique"}
    created = updated = 0
    now = datetime.now(timezone.utc).isoformat()
    for p in valid:
        base = {
            "name": p["name"], "description": p["description"], "category": p["category"],
            "price_ht": p["price_ht"], "tva_rate": p["tva_rate"],
            "price_ttc": round(p["price_ht"] * (1 + p["tva_rate"] / 100), 2),
            "stock_quantity": p["stock_quantity"], "unit": p["conditionnement"],
            "ean": p["ean"], "weight_kg": p["weight_kg"],
            "updated_at": now, "import_source": "catalog_file",
        }
        if p["image_url"]:
            base["image_url"] = p["image_url"]
        existing = await db.vendor_products.find_one({"vendor_id": vendor_id, "sku": p["sku"]}, {"_id": 0, "id": 1})
        if existing:
            await db.vendor_products.update_one({"vendor_id": vendor_id, "sku": p["sku"]}, {"$set": base})
            updated += 1
        else:
            base["status"] = "pending_approval"
            await db.vendor_products.insert_one({
                "id": str(uuid.uuid4()), "vendor_id": vendor_id, "sku": p["sku"],
                **base, "images": [], "documents": [], "created_at": now, "submitted_at": now,
            })
            created += 1
    return {"ok": True, "created": created, "updated": updated, "total": len(valid),
            "message": f"{created} produit(s) créé(s), {updated} mis à jour"}
