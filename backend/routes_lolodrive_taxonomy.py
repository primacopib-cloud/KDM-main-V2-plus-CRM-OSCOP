"""Taxonomie LOLODRIVE (catégories → sous-catégories, gérées par le super admin) + frais de retrait/livraison par créneau."""
import uuid
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
taxonomy_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE Taxonomy & Fees"])
db = None


def set_taxonomy_database(database):
    global db
    db = database


DEFAULT_CATEGORIES = [
    {"name": "Épicerie", "subcategories": ["Riz & féculents", "Farines & sucres", "Huiles & condiments",
                                           "Petit-déjeuner & douceurs", "Conserves & bocaux",
                                           "Cafés, thés & laits", "Épices & vanille"]},
    {"name": "Boissons", "subcategories": ["Jus & boissons locales", "Rhums & spiritueux", "Eaux & sodas"]},
    {"name": "Frais", "subcategories": ["Fruits & légumes", "Viandes & volailles", "Œufs & produits laitiers"]},
    {"name": "Cuisine", "subcategories": ["Sauces & aides culinaires", "Épices locales"]},
]

SUBCAT_BACKFILL = {
    "RIZ-5KG": "Riz & féculents", "PATES-500G": "Riz & féculents", "MANIOC-500G": "Riz & féculents",
    "FARINE-1KG": "Farines & sucres", "SUCRE-1KG": "Farines & sucres", "SUCRE-CANNE-RE-1KG": "Farines & sucres",
    "HUILE-1L": "Huiles & condiments",
    "NUTELLA-400G": "Petit-déjeuner & douceurs",
    "CAFE-250G": "Cafés, thés & laits", "LAIT-1L": "Cafés, thés & laits",
    "VANILLE-BOURBON-3G": "Épices & vanille",
    "ACHARDS-LEGUMES-200G": "Conserves & bocaux",
    "JUS-MANGUE-1L": "Jus & boissons locales", "CACHIRI-1L": "Jus & boissons locales",
    "RHUM-AGRICOLE-70CL": "Rhums & spiritueux",
    "OEUFS-12": "Œufs & produits laitiers", "POULET-1KG": "Viandes & volailles", "BANANE-1KG": "Fruits & légumes",
    "TOMACOULI-500G": "Sauces & aides culinaires",
}


async def ensure_categories():
    """Seed idempotent des catégories + backfill des sous-catégories sur les produits démo."""
    if await db.lolodrive_categories.count_documents({}) == 0:
        for i, c in enumerate(DEFAULT_CATEGORIES):
            await db.lolodrive_categories.insert_one(
                {"id": str(uuid.uuid4()), "name": c["name"], "subcategories": c["subcategories"], "position": i})
    for sku, sub in SUBCAT_BACKFILL.items():
        await db.lolodrive_products.update_one(
            {"sku": sku, "$or": [{"subcategory": {"$exists": False}}, {"subcategory": None}]},
            {"$set": {"subcategory": sub}})
    await db.lolodrive_products.update_many(
        {"sku": "RHUM-AGRICOLE-70CL", "tva_rate": {"$exists": False}}, {"$set": {"tva_rate": 20.0}})
    await db.lolodrive_products.update_many(
        {"$or": [{"tva_rate": {"$exists": False}}, {"tva_rate": None}]}, {"$set": {"tva_rate": 8.5}})


@taxonomy_router.get("/categories")
async def list_categories():
    await ensure_categories()
    cats = await db.lolodrive_categories.find({}, {"_id": 0}).sort("position", 1).to_list(100)
    return {"categories": cats}


class CategoryBody(BaseModel):
    name: str
    subcategories: list = []


@taxonomy_router.post("/admin/categories")
async def create_category(body: CategoryBody, admin: dict = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom de catégorie requis")
    if await db.lolodrive_categories.find_one({"name": name}):
        raise HTTPException(status_code=400, detail="Cette catégorie existe déjà")
    count = await db.lolodrive_categories.count_documents({})
    doc = {"id": str(uuid.uuid4()), "name": name,
           "subcategories": [s.strip() for s in body.subcategories if s and s.strip()], "position": count}
    await db.lolodrive_categories.insert_one(doc)
    doc.pop("_id", None)
    return doc


@taxonomy_router.put("/admin/categories/{cid}")
async def update_category(cid: str, body: CategoryBody, admin: dict = Depends(require_admin)):
    cat = await db.lolodrive_categories.find_one({"id": cid}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    name = body.name.strip() or cat["name"]
    subs = [s.strip() for s in body.subcategories if s and s.strip()]
    await db.lolodrive_categories.update_one({"id": cid}, {"$set": {"name": name, "subcategories": subs}})
    if name != cat["name"]:
        await db.lolodrive_products.update_many({"category": cat["name"]}, {"$set": {"category": name}})
    return {"ok": True, "id": cid, "name": name, "subcategories": subs}


@taxonomy_router.delete("/admin/categories/{cid}")
async def delete_category(cid: str, admin: dict = Depends(require_admin)):
    cat = await db.lolodrive_categories.find_one({"id": cid}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    used = await db.lolodrive_products.count_documents({"category": cat["name"]})
    if used:
        raise HTTPException(status_code=400, detail=f"{used} produit(s) utilisent encore cette catégorie")
    await db.lolodrive_categories.delete_one({"id": cid})
    return {"ok": True}


# =======================
# Frais de retrait Drive / livraison par créneau (configurables super admin)
# =======================

DEFAULT_FEES = {
    "pickup_slots": [
        {"id": "AM", "label": "Matin — 8h00 à 12h00", "start": "08:00", "end": "12:00"},
        {"id": "PM", "label": "Après-midi — 12h01 à 20h00", "start": "12:01", "end": "20:00"},
    ],
    "delivery_slots": [
        {"id": "AM", "label": "Matin — 8h00 à 12h00", "start": "08:00", "end": "12:00"},
        {"id": "PM", "label": "Après-midi — 12h01 à 20h00", "start": "12:01", "end": "20:00"},
    ],
    # UC par article, par catégorie ("*" = tarif par défaut toutes catégories) et par créneau
    "pickup_rates": {"*": {"AM": 0.6, "PM": 19}},
    "delivery_rates": {"*": {"AM": 0.6, "PM": 19}},
    # Pénalité de non-retrait après le créneau : UC par article, par catégorie (1 UC = 0,10 €)
    "penalty_rates": {"*": 1},
    # Blocage temporaire de la commande Drive après trop de non-retraits (threshold 0 = désactivé)
    "no_pickup_block": {"threshold": 3, "window_days": 30, "block_days": 15},
    # Bonus fidélité 'Client fiable' : UC offerts si aucun non-retrait sur 6 mois (bonus_uc 0 = désactivé)
    "reliable_bonus": {"bonus_uc": 10, "min_orders": 5},
    # Alerte super admin : seuil de retours 'Défectueux' par produit sur le mois (0 = désactivé)
    "defective_alert_threshold": 3,
}


async def get_fees_config_doc() -> dict:
    doc = await db.lolodrive_settings.find_one({"key": "drive_fees"}, {"_id": 0})
    if not doc:
        await db.lolodrive_settings.update_one(
            {"key": "drive_fees"}, {"$setOnInsert": {"key": "drive_fees", "value": DEFAULT_FEES}}, upsert=True)
        return DEFAULT_FEES
    cfg = doc.get("value", DEFAULT_FEES)
    if "penalty_rates" not in cfg:
        cfg["penalty_rates"] = DEFAULT_FEES["penalty_rates"]
    if "no_pickup_block" not in cfg:
        cfg["no_pickup_block"] = DEFAULT_FEES["no_pickup_block"]
    if "reliable_bonus" not in cfg:
        cfg["reliable_bonus"] = DEFAULT_FEES["reliable_bonus"]
    if "defective_alert_threshold" not in cfg:
        cfg["defective_alert_threshold"] = DEFAULT_FEES["defective_alert_threshold"]
    return cfg


def compute_slot_fee_uc(cfg: dict, kind: str, slot_id: str, lines: list, cat_by_sku: dict) -> float:
    """Frais UC = Σ (qty × tarif[catégorie][créneau]), fallback tarif '*'."""
    rates = cfg.get(f"{kind}_rates", {}) or {}
    default = rates.get("*", {}) or {}
    fee = 0.0
    for l in lines:
        cat = cat_by_sku.get(l.get("sku")) or "*"
        rate = (rates.get(cat, {}) or {}).get(slot_id, default.get(slot_id, 0)) or 0
        fee += float(rate) * l.get("qty", 0)
    return round(fee, 2)


async def slot_fee_for_order(kind: str, slot_id: Optional[str], lines: list):
    """Retourne (fee_uc, slot_label) pour une commande, 0 si pas de créneau."""
    if not slot_id:
        return 0.0, None
    cfg = await get_fees_config_doc()
    slot = next((s for s in cfg.get(f"{kind}_slots", []) if s.get("id") == slot_id), None)
    if not slot:
        return 0.0, None
    skus = [l["sku"] for l in lines]
    prods = await db.lolodrive_products.find({"sku": {"$in": skus}}, {"_id": 0, "sku": 1, "category": 1}).to_list(300)
    cat_by_sku = {p["sku"]: p.get("category") for p in prods}
    return compute_slot_fee_uc(cfg, kind, slot_id, lines, cat_by_sku), slot.get("label")


async def compute_penalty_uc(lines: list) -> float:
    """Pénalité de non-retrait : Σ (qty × tarif_pénalité[catégorie]), fallback '*'."""
    cfg = await get_fees_config_doc()
    rates = cfg.get("penalty_rates", {}) or {}
    default = rates.get("*", 1)
    skus = [l["sku"] for l in lines]
    prods = await db.lolodrive_products.find({"sku": {"$in": skus}}, {"_id": 0, "sku": 1, "category": 1}).to_list(300)
    cat_by_sku = {p["sku"]: p.get("category") for p in prods}
    fee = 0.0
    for l in lines:
        rate = rates.get(cat_by_sku.get(l.get("sku")) or "*", default) or 0
        fee += float(rate) * l.get("qty", 0)
    return round(fee, 2)


async def check_no_pickup_block(user_id: str):
    """Retourne (blocked_until: datetime, count) si le client est suspendu de commande Drive, sinon None."""
    from datetime import datetime as dt, timedelta as td
    cfg = await get_fees_config_doc()
    block = cfg.get("no_pickup_block") or {}
    threshold = int(block.get("threshold") or 0)
    if threshold <= 0:
        return None
    now = dt.utcnow()
    window_start = now - td(days=int(block.get("window_days") or 30))
    offenders = await db.lolodrive_orders.find(
        {"user_id": user_id, "no_pickup_penalty_uc": {"$gt": 0},
         "no_pickup_penalty_refunded": {"$ne": True},
         "no_pickup_reminder_sent_at": {"$gte": window_start}},
        {"_id": 0, "no_pickup_reminder_sent_at": 1}).to_list(100)
    if len(offenders) < threshold:
        return None
    last = max(o["no_pickup_reminder_sent_at"] for o in offenders)
    blocked_until = last + td(days=int(block.get("block_days") or 15))
    if now >= blocked_until:
        return None
    return blocked_until, len(offenders)


@taxonomy_router.get("/admin/penalties")
async def admin_penalties(admin: dict = Depends(require_admin)):
    """Historique des commandes pénalisées (non retirées) + total UC par relais."""
    orders = await db.lolodrive_orders.find(
        {"no_pickup_penalty_uc": {"$gt": 0}},
        {"_id": 0, "id": 1, "order_number": 1, "user_id": 1, "lolo_point_id": 1, "status": 1,
         "no_pickup_penalty_uc": 1, "no_pickup_reminder_sent_at": 1, "items": 1,
         "auto_cancelled": 1, "cancelled_at": 1, "no_pickup_penalty_refunded": 1}
    ).sort("no_pickup_reminder_sent_at", -1).limit(200).to_list(200)
    user_ids = list({o["user_id"] for o in orders if o.get("user_id")})
    point_ids = list({o["lolo_point_id"] for o in orders if o.get("lolo_point_id")})
    users = {u["id"]: u async for u in db.users.find(
        {"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "contact_name": 1, "email": 1})}
    points = {p["id"]: p async for p in db.lolodrive_points.find(
        {"id": {"$in": point_ids}}, {"_id": 0, "id": 1, "name": 1, "code": 1})}
    rows, by_point = [], {}
    for o in orders:
        u, pt = users.get(o.get("user_id"), {}), points.get(o.get("lolo_point_id"), {})
        key = pt.get("code") or "—"
        agg = by_point.setdefault(key, {"code": key, "name": pt.get("name") or "Sans relais",
                                        "count": 0, "total_uc": 0.0})
        agg["count"] += 1
        agg["total_uc"] = round(agg["total_uc"] + o["no_pickup_penalty_uc"], 2)
        rows.append({
            "order_number": o.get("order_number"), "status": o.get("status"),
            "auto_cancelled": bool(o.get("auto_cancelled")),
            "refunded": bool(o.get("no_pickup_penalty_refunded")),
            "penalty_uc": o["no_pickup_penalty_uc"],
            "penalized_at": o.get("no_pickup_reminder_sent_at"),
            "customer": u.get("contact_name") or u.get("email") or "—",
            "point_name": pt.get("name"), "point_code": pt.get("code"),
            "items_count": sum(l.get("qty", 0) for l in o.get("items", []))})
    by_point_list = sorted(by_point.values(), key=lambda x: -x["total_uc"])
    return {"orders": rows, "by_point": by_point_list,
            "total_uc": round(sum(p["total_uc"] for p in by_point_list), 2)}


@taxonomy_router.get("/admin/penalties-export")
async def admin_penalties_export(month: str, admin: dict = Depends(require_admin)):
    """Export CSV comptable des pénalités de non-retrait du mois, par relais."""
    from datetime import datetime as dt
    try:
        y, m = map(int, month.split("-"))
        start = dt(y, m, 1)
        end = dt(y + 1, 1, 1) if m == 12 else dt(y, m + 1, 1)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Mois invalide (format attendu : YYYY-MM)")
    orders = await db.lolodrive_orders.find(
        {"no_pickup_penalty_uc": {"$gt": 0},
         "no_pickup_reminder_sent_at": {"$gte": start, "$lt": end}},
        {"_id": 0, "order_number": 1, "user_id": 1, "lolo_point_id": 1, "status": 1, "items": 1,
         "no_pickup_penalty_uc": 1, "no_pickup_reminder_sent_at": 1,
         "auto_cancelled": 1, "no_pickup_penalty_refunded": 1}
    ).sort("no_pickup_reminder_sent_at", 1).to_list(2000)
    users = {u["id"]: u async for u in db.users.find(
        {"id": {"$in": list({o["user_id"] for o in orders if o.get("user_id")})}},
        {"_id": 0, "id": 1, "contact_name": 1, "email": 1})}
    points = {p["id"]: p async for p in db.lolodrive_points.find(
        {"id": {"$in": list({o["lolo_point_id"] for o in orders if o.get("lolo_point_id")})}},
        {"_id": 0, "id": 1, "name": 1, "code": 1})}
    by_point = {}
    for o in orders:
        by_point.setdefault(o.get("lolo_point_id"), []).append(o)
    rows = ["relais;code;date;numero;client;articles;penalite_uc;penalite_eur;statut"]
    g_uc = g_ref = 0.0
    for pid, group in sorted(by_point.items(), key=lambda kv: (points.get(kv[0], {}).get("code") or "~")):
        pt = points.get(pid, {})
        pname, pcode = pt.get("name") or "Sans relais", pt.get("code") or "-"
        t_uc = t_ref = 0.0
        for o in group:
            u = users.get(o.get("user_id"), {})
            pen = o["no_pickup_penalty_uc"]
            statut = ("Remboursee (retrait tardif)" if o.get("no_pickup_penalty_refunded")
                      else "Annulee auto" if o.get("auto_cancelled")
                      else "Retiree" if o.get("status") == "FULFILLED" else "En attente")
            rows.append(f"{pname};{pcode};{o['no_pickup_reminder_sent_at'].strftime('%d/%m/%Y %H:%M')};"
                        f"{o.get('order_number')};{u.get('contact_name') or u.get('email') or '-'};"
                        f"{sum(l.get('qty', 0) for l in o.get('items', []))};"
                        f"{pen:g};{pen / 10:.2f};{statut}")
            t_uc += pen
            if o.get("no_pickup_penalty_refunded"):
                t_ref += pen
        rows.append(f"SOUS-TOTAL {pcode};;;;;{len(group)} cde(s);{t_uc:g};{t_uc / 10:.2f};"
                    f"dont remboursees {t_ref:g} UC")
        rows.append("")
        g_uc += t_uc
        g_ref += t_ref
    rows += [f"TOTAL GENERAL;;;;;{len(orders)} cde(s);{g_uc:g};{g_uc / 10:.2f};dont remboursees {g_ref:g} UC",
             f"NET FACTURE;;;;;;{g_uc - g_ref:g};{(g_uc - g_ref) / 10:.2f};"]
    return PlainTextResponse(
        "\ufeff" + "\n".join(rows), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=penalites-{month}.csv"})


@taxonomy_router.get("/admin/missing-photos")
async def admin_missing_photos(admin: dict = Depends(require_admin)):
    """Produits actifs du catalogue sans photo, pour complétion par le super admin."""
    products = await db.lolodrive_products.find(
        {"is_active": {"$ne": False}, "status": {"$nin": ["PENDING", "REJECTED"]},
         "$or": [{"image_url": {"$exists": False}}, {"image_url": None}, {"image_url": ""}]},
        {"_id": 0, "sku": 1, "name": 1, "brand": 1, "category": 1, "subcategory": 1, "point_code": 1}
    ).sort("category", 1).to_list(500)
    return {"products": products, "count": len(products)}


@taxonomy_router.post("/admin/products/{sku}/photo")
async def admin_set_product_photo(sku: str, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    """Upload direct d'une photo produit par le super admin (jpg/png/webp, 4 Mo max)."""
    prod = await db.lolodrive_products.find_one({"sku": sku}, {"_id": 0, "sku": 1})
    if not prod:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(status_code=400, detail="Format non supporté (jpg, png, webp)")
    data = await file.read()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 4 Mo)")
    up_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
    os.makedirs(up_dir, exist_ok=True)
    fname = f"product-admin-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(up_dir, fname), "wb") as f:
        f.write(data)
    image_url = f"/api/uploads/products/{fname}"
    await db.lolodrive_products.update_one({"sku": sku}, {"$set": {"image_url": image_url}})
    return {"ok": True, "sku": sku, "image_url": image_url}


@taxonomy_router.get("/admin/products-tva")
async def admin_products_tva(admin: dict = Depends(require_admin)):
    """Fiches produits du catalogue pour le super admin (TVA + photo)."""
    products = await db.lolodrive_products.find(
        {"is_active": {"$ne": False}, "status": {"$nin": ["PENDING", "REJECTED"]}},
        {"_id": 0, "sku": 1, "name": 1, "category": 1, "point_code": 1,
         "price_public_cents": 1, "tva_rate": 1, "image_url": 1, "image_ai_generated": 1}
    ).sort("category", 1).to_list(1000)
    return {"products": products, "count": len(products)}


@taxonomy_router.put("/admin/products/{sku}/tva")
async def admin_set_product_tva(sku: str, payload: dict, admin: dict = Depends(require_admin)):
    try:
        rate = float(payload.get("tva_rate"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="tva_rate : nombre attendu")
    if not (0 <= rate <= 30):
        raise HTTPException(status_code=400, detail="tva_rate : taux hors limites (0-30%)")
    res = await db.lolodrive_products.update_one({"sku": sku}, {"$set": {"tva_rate": rate}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "sku": sku, "tva_rate": rate}


@taxonomy_router.post("/admin/products/{sku}/generate-photo")
async def admin_generate_product_photo(sku: str, admin: dict = Depends(require_admin)):
    """Génère une photo d'illustration IA pour un produit sans image (super admin)."""
    prod = await db.lolodrive_products.find_one(
        {"sku": sku}, {"_id": 0, "sku": 1, "name": 1, "category": 1, "brand": 1})
    if not prod:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    from product_photo_ai import generate_product_photo
    try:
        image_url = await generate_product_photo(prod["name"], prod.get("category"), prod.get("brand"))
    except Exception as exc:
        logging.getLogger(__name__).warning("Génération photo IA %s : %s", sku, exc)
        raise HTTPException(status_code=502, detail="Génération IA indisponible — réessayez ou ajoutez une photo manuelle")
    await db.lolodrive_products.update_one({"sku": sku}, {"$set": {"image_url": image_url, "image_ai_generated": True}})
    return {"ok": True, "sku": sku, "image_url": image_url}


@taxonomy_router.get("/fees-config")
async def public_fees_config(user: dict = Depends(get_current_user)):
    return await get_fees_config_doc()


@taxonomy_router.put("/admin/fees-config")
async def update_fees_config(payload: dict, admin: dict = Depends(require_admin)):
    cfg = await get_fees_config_doc()
    for key in ("pickup_slots", "delivery_slots"):
        if key in payload:
            slots = [s for s in payload[key] if isinstance(s, dict) and s.get("id") and s.get("label")]
            if not slots:
                raise HTTPException(status_code=400, detail=f"{key} : au moins un créneau requis")
            cfg[key] = slots
    for key in ("pickup_rates", "delivery_rates"):
        if key in payload:
            clean = {}
            for cat, by_slot in (payload[key] or {}).items():
                if not isinstance(by_slot, dict):
                    continue
                entry = {}
                for sid, rate in by_slot.items():
                    try:
                        r = float(rate)
                    except (TypeError, ValueError):
                        continue
                    if 0 <= r <= 100000:
                        entry[sid] = r
                if entry:
                    clean[cat] = entry
            if "*" not in clean:
                raise HTTPException(status_code=400, detail=f"{key} : le tarif par défaut '*' est requis")
            cfg[key] = clean
    if "penalty_rates" in payload:
        clean = {}
        for cat, rate in (payload["penalty_rates"] or {}).items():
            try:
                r = float(rate)
            except (TypeError, ValueError):
                continue
            if 0 <= r <= 100000:
                clean[cat] = r
        if "*" not in clean:
            raise HTTPException(status_code=400, detail="penalty_rates : le tarif par défaut '*' est requis")
        cfg["penalty_rates"] = clean
    if "no_pickup_block" in payload:
        b = payload["no_pickup_block"] or {}
        clean = {}
        for key, default in (("threshold", 3), ("window_days", 30), ("block_days", 15)):
            try:
                v = int(b.get(key, default))
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"no_pickup_block.{key} : entier attendu")
            if not (0 <= v <= 3650):
                raise HTTPException(status_code=400, detail=f"no_pickup_block.{key} : valeur hors limites")
            clean[key] = v
        cfg["no_pickup_block"] = clean
    if "reliable_bonus" in payload:
        b = payload["reliable_bonus"] or {}
        try:
            bonus = float(b.get("bonus_uc", 10))
            min_orders = int(b.get("min_orders", 5))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="reliable_bonus : valeurs numériques attendues")
        if not (0 <= bonus <= 100000) or not (0 <= min_orders <= 1000):
            raise HTTPException(status_code=400, detail="reliable_bonus : valeurs hors limites")
        cfg["reliable_bonus"] = {"bonus_uc": bonus, "min_orders": min_orders}
    if "defective_alert_threshold" in payload:
        try:
            th = int(payload["defective_alert_threshold"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="defective_alert_threshold : entier attendu")
        if not (0 <= th <= 1000):
            raise HTTPException(status_code=400, detail="defective_alert_threshold : valeur hors limites")
        cfg["defective_alert_threshold"] = th
    await db.lolodrive_settings.update_one({"key": "drive_fees"}, {"$set": {"value": cfg}}, upsert=True)
    return {"ok": True, "config": cfg}
