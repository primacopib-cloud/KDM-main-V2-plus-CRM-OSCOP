"""CREDI'SCOP-I : compteur d'unités de services internes, catalogue fermé, ledger. Aucune valeur monétaire."""
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2

logger = logging.getLogger(__name__)
sc_router = APIRouter(prefix="/api/admin/service-credits", tags=["CREDI'SCOP-I"])
db = None


def set_service_credits_database(database):
    global db
    db = database


ENTRY_TYPES = ["ALLOCATION", "RESERVATION", "DEBIT", "RELEASE", "EXPIRY", "CORRECTION"]
FORBIDDEN_KEYS = {"euro_value", "eur_value", "amount", "amount_cents", "currency", "price", "value_eur", "transfer_to"}

DEFAULT_CATALOG = [
    ("DATAROOM", "Accès à une data room complète", 10),
    ("SUPPLIER_QUALIF", "Qualification approfondie d'un fournisseur", 20),
    ("ECO_ANALYSIS", "Analyse économique et marge", 25),
    ("LOGISTICS_ANALYSIS", "Analyse logistique et documentaire", 15),
    ("LOGISTICS_SIMULATION", "Simulation du financement logistique", 10),
    ("LOGISCOP_TRACKING", "Activation du suivi opérationnel LOGI'SCOP", 10),
    ("PREVENTIVE_REPORT", "Accès au rapport préventif", 25),
    ("COMMITMENT_PREP", "Préparation du Bon d'Engagement", 20),
    ("PAYMENT_WORKFLOW", "Activation du workflow de paiement", 15),
    ("REPORTING_PLUS", "Reporting renforcé", 10),
    ("CLOSING_ARCHIVE", "Clôture et archivage", 5),
]

DISCLAIMER = ("Les CREDI'SCOP-I sont des unités internes de services : aucune valeur en euros, "
              "non convertibles, non transférables, non remboursables, jamais un moyen de paiement "
              "des produits, de la logistique ou des fournisseurs.")


async def seed_service_catalog(database):
    for code, label, units in DEFAULT_CATALOG:
        await database.service_catalog_items.update_one(
            {"code": code},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "code": code, "label": label,
                              "units": units, "active": True}},
            upsert=True)


class AccountCreate(BaseModel, extra="forbid"):
    investor_name: str
    investor_email: str


class CatalogUpdate(BaseModel, extra="forbid"):
    units: Optional[int] = Field(default=None, ge=1, le=10000)
    active: Optional[bool] = None


class LedgerEntryCreate(BaseModel, extra="forbid"):
    entry_type: str
    units: int = Field(gt=0, le=100000)
    service_catalog_item_id: Optional[str] = None
    operation_id: Optional[str] = None
    description: Optional[str] = None


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@sc_router.get("/catalog")
async def get_catalog(admin: dict = Depends(_admin)):
    items = await db.service_catalog_items.find({}, {"_id": 0}).to_list(100)
    return {"items": items, "disclaimer": DISCLAIMER}


@sc_router.put("/catalog/{item_id}")
async def update_catalog_item(item_id: str, payload: CatalogUpdate, admin: dict = Depends(_admin)):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    r = await db.service_catalog_items.update_one({"id": item_id}, {"$set": updates})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Service introuvable")
    return {"success": True}


@sc_router.post("/accounts")
async def create_account(payload: AccountCreate, admin: dict = Depends(_admin)):
    existing = await db.service_credit_accounts.find_one({"investor_email": payload.investor_email})
    if existing:
        raise HTTPException(status_code=409, detail="Un compteur existe déjà pour cet email")
    acc = {"id": str(uuid.uuid4()), **payload.dict(),
           "available_units": 0, "reserved_units": 0, "expired_units": 0,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.service_credit_accounts.insert_one(dict(acc))
    return acc


@sc_router.get("/accounts")
async def list_accounts(admin: dict = Depends(_admin)):
    accounts = await db.service_credit_accounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"accounts": accounts, "entry_types": ENTRY_TYPES, "disclaimer": DISCLAIMER}


@sc_router.get("/accounts/{account_id}/ledger")
async def get_ledger(account_id: str, admin: dict = Depends(_admin)):
    entries = await db.service_credit_ledger.find(
        {"account_id": account_id}, {"_id": 0}).sort("created_at", -1).to_list(300)
    return {"entries": entries}


@sc_router.post("/accounts/{account_id}/entries")
async def create_entry(account_id: str, payload: LedgerEntryCreate, admin: dict = Depends(_admin)):
    raw = payload.dict()
    if any(k in FORBIDDEN_KEYS for k in raw):
        raise HTTPException(status_code=409, detail="Aucune valeur monétaire ne peut être associée aux CREDI'SCOP-I")
    if payload.entry_type not in ENTRY_TYPES:
        raise HTTPException(status_code=400, detail=f"Type invalide. Autorisés : {ENTRY_TYPES} — aucun transfert entre utilisateurs")
    acc = await db.service_credit_accounts.find_one({"id": account_id}, {"_id": 0})
    if not acc:
        raise HTTPException(status_code=404, detail="Compteur introuvable")

    item = None
    if payload.entry_type in ("DEBIT", "RESERVATION"):
        if not payload.service_catalog_item_id:
            raise HTTPException(status_code=409, detail="Un débit CREDI'SCOP-I exige un service du catalogue fermé")
        item = await db.service_catalog_items.find_one({"id": payload.service_catalog_item_id, "active": True}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=409, detail="Service introuvable dans le catalogue fermé ou inactif")
        if payload.units != item["units"]:
            raise HTTPException(status_code=409, detail=f"Le service « {item['label']} » coûte exactement {item['units']} unités")

    deltas = {"ALLOCATION": {"available_units": payload.units},
              "RESERVATION": {"available_units": -payload.units, "reserved_units": payload.units},
              "DEBIT": {"available_units": -payload.units},
              "RELEASE": {"available_units": payload.units, "reserved_units": -payload.units},
              "EXPIRY": {"available_units": -payload.units, "expired_units": payload.units},
              "CORRECTION": {"available_units": payload.units}}[payload.entry_type]
    new_available = acc["available_units"] + deltas.get("available_units", 0)
    new_reserved = acc["reserved_units"] + deltas.get("reserved_units", 0)
    if payload.entry_type == "DEBIT":
        if acc["reserved_units"] >= payload.units:
            deltas = {"reserved_units": -payload.units}
            new_available = acc["available_units"]
            new_reserved = acc["reserved_units"] - payload.units
    if new_available < 0 or new_reserved < 0:
        raise HTTPException(status_code=409, detail="Solde d'unités insuffisant")

    entry = {"id": str(uuid.uuid4()), "account_id": account_id,
             "investor_email": acc["investor_email"],
             **payload.dict(),
             "service_label": item["label"] if item else None,
             "created_by": admin.get("email"),
             "created_at": datetime.now(timezone.utc).isoformat()}
    await db.service_credit_ledger.insert_one(dict(entry))
    await db.service_credit_accounts.update_one({"id": account_id}, {"$inc": deltas})
    return entry
