"""Calculateur de tarifs de fret maritime LOGI'SCOP (barème interne administrable)."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2

freight_router = APIRouter(prefix="/api", tags=["Fret maritime"])
db = None


def set_freight_database(database):
    global db
    db = database


CONTAINERS = {"20DV": "Conteneur 20' Dry", "40DV": "Conteneur 40' Dry", "40HC": "Conteneur 40' High Cube", "LCL": "Groupage (m³)"}

DEFAULT_RATES = [
    ("Le Havre", "Fort-de-France (Martinique)", {"20DV": 2450, "40DV": 3350, "40HC": 3550, "LCL": 95}, 18),
    ("Le Havre", "Pointe-à-Pitre (Guadeloupe)", {"20DV": 2400, "40DV": 3300, "40HC": 3500, "LCL": 92}, 17),
    ("Le Havre", "Dégrad-des-Cannes (Guyane)", {"20DV": 2900, "40DV": 3950, "40HC": 4150, "LCL": 110}, 21),
    ("Le Havre", "Port Réunion (La Réunion)", {"20DV": 2750, "40DV": 3800, "40HC": 4000, "LCL": 105}, 28),
    ("Marseille", "Longoni (Mayotte)", {"20DV": 3100, "40DV": 4250, "40HC": 4450, "LCL": 118}, 30),
    ("Le Havre", "Nouméa (Nouvelle-Calédonie)", {"20DV": 3900, "40DV": 5300, "40HC": 5600, "LCL": 145}, 42),
    ("Le Havre", "Papeete (Polynésie française)", {"20DV": 4100, "40DV": 5600, "40HC": 5900, "LCL": 152}, 45),
]
BAF_RATE = 12.0
THC = {"20DV": 180, "40DV": 260, "40HC": 260, "LCL": 22}


async def seed_freight_rates(database):
    for origin, destination, prices, transit in DEFAULT_RATES:
        await database.freight_rates.update_one(
            {"origin": origin, "destination": destination},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "origin": origin, "destination": destination,
                              "base_prices": prices, "transit_days": transit,
                              "baf_rate": BAF_RATE, "thc": THC, "active": True}},
            upsert=True)


class QuoteRequest(BaseModel):
    route_id: str
    container_type: str
    quantity: float = Field(default=1, gt=0, le=1000)
    insurance: bool = False
    goods_value_ex_vat: Optional[float] = Field(default=None, ge=0)


class RateUpdate(BaseModel):
    base_prices: Optional[dict] = None
    transit_days: Optional[int] = None
    baf_rate: Optional[float] = None
    active: Optional[bool] = None


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@freight_router.get("/public/freight/routes")
async def list_routes():
    routes = await db.freight_rates.find({"active": True}, {"_id": 0}).to_list(50)
    return {"routes": routes, "containers": CONTAINERS,
            "note": ("Barème indicatif LOGI'SCOP paramétré par O'SCOP — chiffrage interne pour sécuriser "
                     "le coût de revient. Devis contractuel confirmé avant tout engagement.")}


@freight_router.post("/public/freight/quote")
async def compute_quote(payload: QuoteRequest):
    route = await db.freight_rates.find_one({"id": payload.route_id, "active": True}, {"_id": 0})
    if not route:
        raise HTTPException(status_code=404, detail="Route introuvable")
    if payload.container_type not in CONTAINERS:
        raise HTTPException(status_code=400, detail=f"Type invalide : {list(CONTAINERS)}")
    base_unit = float(route["base_prices"].get(payload.container_type, 0))
    if base_unit <= 0:
        raise HTTPException(status_code=409, detail="Tarif non défini pour ce type sur cette route")
    base = base_unit * payload.quantity
    baf = round(base * float(route.get("baf_rate", BAF_RATE)) / 100, 2)
    thc = round(float(route.get("thc", THC).get(payload.container_type, 0)) * payload.quantity, 2)
    insurance = 0.0
    if payload.insurance:
        insurance = round(max((payload.goods_value_ex_vat or 0) * 0.006, 45.0), 2)
    total = round(base + baf + thc + insurance, 2)
    return {
        "route": f"{route['origin']} → {route['destination']}",
        "container": CONTAINERS[payload.container_type],
        "quantity": payload.quantity,
        "breakdown": {"base_freight": round(base, 2), "baf_surcharge": baf,
                      "thc_handling": thc, "transport_insurance": insurance},
        "total_ex_vat": total,
        "transit_days_estimate": route.get("transit_days"),
        "currency": "EUR",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Estimation LOGI'SCOP à intégrer au coût de revient (poste « Fret principal »).",
    }


@freight_router.put("/admin/freight/routes/{route_id}")
async def update_rate(route_id: str, payload: RateUpdate, admin: dict = Depends(_admin)):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    r = await db.freight_rates.update_one({"id": route_id}, {"$set": updates})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Route introuvable")
    return {"success": True}
