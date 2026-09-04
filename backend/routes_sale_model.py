"""SaleModel Phase 1 : deux circuits de vente juridiquement distincts."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routes_v2 import get_current_user_v2

logger = logging.getLogger(__name__)
sale_model_router = APIRouter(prefix="/api", tags=["Sale Model"])
db = None


def set_sale_model_database(database):
    global db
    db = database


class SaleModel(str, Enum):
    OSCOP_DIRECT_RESALE = "OSCOP_DIRECT_RESALE"
    PARTNER_DIRECT_SALE = "PARTNER_DIRECT_SALE"


DEFAULT_LEGAL = {
    "id": "legal_entities",
    "oscop": {
        "name": "O'SCOP",
        "legal_form": "Centrale coopérative",
        "address": "Adresse à compléter par l'administrateur",
        "siret": "",
        "rcs": "",
        "vat": "",
        "role": "Vendeur-facturier du circuit achat-revente O'SCOP et opérateur des services coopératifs",
    },
    "partner": {
        "name": "PRIMACOP INTERNATIONAL BUSINESS (KDMARCHÉ)",
        "legal_form": "Opérateur commercial B2B",
        "address": "Adresse à compléter par l'administrateur",
        "siret": "433 230 703 00020",
        "rcs": "",
        "vat": "",
        "role": "Vendeur-facturier du circuit vente partenaire directe",
    },
}

ROLES_MATRIX = {
    SaleModel.OSCOP_DIRECT_RESALE.value: {
        "label": "Achat-revente O'SCOP",
        "seller": "O'SCOP",
        "invoicer": "O'SCOP",
        "collector": "O'SCOP",
        "after_sales": "O'SCOP",
        "coop_services": "O'SCOP",
        "description": "O'SCOP achète, revend, facture et encaisse. O'SCOP assume la responsabilité de vendeur.",
    },
    SaleModel.PARTNER_DIRECT_SALE.value: {
        "label": "Vente partenaire directe",
        "seller": "Le partenaire vendeur",
        "invoicer": "Le partenaire vendeur",
        "collector": "Le partenaire vendeur",
        "after_sales": "Le partenaire vendeur",
        "coop_services": "O'SCOP",
        "description": "Le partenaire vend, facture et encaisse. O'SCOP assure uniquement les services coopératifs prévus.",
    },
}


async def migrate_sale_model(database):
    """Migration idempotente et non destructive : sale_model par défaut PARTNER_DIRECT_SALE."""
    results = {}
    for coll in ["products", "catalog_products"]:
        r = await database[coll].update_many(
            {"sale_model": {"$exists": False}},
            {"$set": {"sale_model": SaleModel.PARTNER_DIRECT_SALE.value}},
        )
        results[coll] = r.modified_count
    if any(results.values()):
        await database.migration_logs.insert_one({
            "id": str(uuid.uuid4()),
            "migration": "phase1_sale_model_default",
            "detail": results,
            "reversible": "unset sale_model field to rollback",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Migration sale_model appliquée: {results}")
    existing = await database.legal_settings.find_one({"id": "legal_entities"})
    if not existing:
        await database.legal_settings.insert_one(dict(DEFAULT_LEGAL))


async def build_roles_snapshot(database, items):
    """Snapshot immuable des rôles commerciaux à la création d'une commande."""
    snap_items = []
    for it in items or []:
        pid = it.get("product_id")
        prod = await database.products.find_one({"id": pid}) if pid else None
        sm = (prod or {}).get("sale_model", SaleModel.PARTNER_DIRECT_SALE.value)
        snap_items.append({
            "product_id": pid,
            "sale_model": sm,
            "roles": ROLES_MATRIX.get(sm, ROLES_MATRIX[SaleModel.PARTNER_DIRECT_SALE.value]),
        })
    legal = await database.legal_settings.find_one({"id": "legal_entities"}, {"_id": 0}) or {
        k: v for k, v in DEFAULT_LEGAL.items()
    }
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": snap_items,
        "legal_entities": legal,
        "immutable": True,
    }


class LegalEntity(BaseModel):
    name: str
    legal_form: Optional[str] = ""
    address: Optional[str] = ""
    siret: Optional[str] = ""
    rcs: Optional[str] = ""
    vat: Optional[str] = ""
    role: Optional[str] = ""


class LegalUpdate(BaseModel):
    oscop: LegalEntity
    partner: LegalEntity


class SaleModelUpdate(BaseModel):
    sale_model: SaleModel
    seller_name: Optional[str] = None


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@sale_model_router.get("/public/sale-model/config")
async def get_sale_model_config():
    legal = await db.legal_settings.find_one({"id": "legal_entities"}, {"_id": 0})
    if not legal:
        legal = {k: v for k, v in DEFAULT_LEGAL.items()}
    return {"legal": legal, "roles_matrix": ROLES_MATRIX}


@sale_model_router.put("/admin/sale-model/legal")
async def update_legal_entities(payload: LegalUpdate, admin: dict = Depends(_admin)):
    await db.legal_settings.update_one(
        {"id": "legal_entities"},
        {"$set": {
            "oscop": payload.oscop.dict(),
            "partner": payload.partner.dict(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": admin.get("email"),
        }},
        upsert=True,
    )
    return {"success": True}


@sale_model_router.patch("/admin/sale-model/products/{product_id}")
async def update_product_sale_model(product_id: str, payload: SaleModelUpdate, admin: dict = Depends(_admin)):
    update = {"sale_model": payload.sale_model.value}
    if payload.seller_name is not None:
        update["seller_name"] = payload.seller_name
    matched = 0
    for coll in ["products", "catalog_products"]:
        r = await db[coll].update_one({"id": product_id}, {"$set": update})
        matched += r.matched_count
    if not matched:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    await db.migration_logs.insert_one({
        "id": str(uuid.uuid4()),
        "migration": "sale_model_manual_change",
        "product_id": product_id,
        "new_value": update,
        "by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "product_id": product_id, **update}
