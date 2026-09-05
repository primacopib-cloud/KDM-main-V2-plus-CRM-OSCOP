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

# Ports de départ du monde entier — (port, (prix 20DV Antilles, transit j), (prix 20DV océan Indien, transit j))
WORLD_DEPARTURES = [
    ("Shanghai (Chine)", (5200, 40), (3300, 24)),
    ("Ningbo (Chine)", (5150, 41), (3280, 25)),
    ("Singapour", (4900, 36), (2900, 18)),
    ("Rotterdam (Pays-Bas)", (2600, 19), (2950, 29)),
    ("Anvers (Belgique)", (2580, 19), (2930, 29)),
    ("Hambourg (Allemagne)", (2650, 20), (3000, 30)),
    ("Barcelone (Espagne)", (2700, 17), (2850, 26)),
    ("Gênes (Italie)", (2750, 18), (2800, 25)),
    ("Algésiras (Espagne)", (2500, 14), (2750, 24)),
    ("Istanbul (Turquie)", (3100, 22), (3050, 27)),
    ("Jebel Ali (Dubaï, EAU)", (4300, 30), (2500, 14)),
    ("Nhava Sheva (Mumbai, Inde)", (4500, 32), (2350, 12)),
    ("New York (États-Unis)", (2900, 12), (4200, 35)),
    ("Houston (États-Unis)", (3000, 14), (4300, 37)),
    ("Miami (États-Unis)", (2450, 8), (4100, 34)),
    ("Santos (Brésil)", (2800, 12), (3900, 30)),
    ("Casablanca (Maroc)", (2400, 12), (3100, 26)),
    ("Dakar (Sénégal)", (2350, 10), (3200, 24)),
    ("Abidjan (Côte d'Ivoire)", (2600, 12), (3000, 21)),
    ("Durban (Afrique du Sud)", (3800, 24), (2200, 9)),
]


def _prices(p20: int) -> dict:
    return {"20DV": p20, "40DV": round(p20 * 1.37), "40HC": round(p20 * 1.45), "LCL": round(p20 / 26)}


def _world_rates():
    rates = []
    for port, (p_ant, t_ant), (p_reu, t_reu) in WORLD_DEPARTURES:
        rates.append((port, "Pointe-à-Pitre (Guadeloupe)", _prices(p_ant), t_ant))
        rates.append((port, "Fort-de-France (Martinique)", _prices(p_ant), t_ant + 1))
        rates.append((port, "Dégrad-des-Cannes (Guyane)", _prices(round(p_ant * 1.12)), t_ant + 3))
        rates.append((port, "Port Réunion (La Réunion)", _prices(p_reu), t_reu))
        rates.append((port, "Longoni (Mayotte)", _prices(round(p_reu * 1.08)), t_reu + 3))
    return rates


async def seed_freight_rates(database):
    for origin, destination, prices, transit in DEFAULT_RATES + _world_rates():
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


class AttachOrderRequest(BaseModel):
    order_id: str
    quote: dict


@freight_router.post("/freight/attach-to-order")
async def attach_quote_to_order(payload: AttachOrderRequest, current_user: dict = Depends(get_current_user_v2)):
    """L'acheteur (ou l'admin) intègre le devis fret à une commande précise."""
    order = await db.orders.find_one({"id": payload.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if not current_user.get("is_admin"):
        membership = await db.org_memberships.find_one({"user_id": current_user["id"]})
        if not membership or order.get("org_id") != membership.get("org_id"):
            raise HTTPException(status_code=403, detail="Cette commande ne vous appartient pas")
    quote = {
        "route": payload.quote.get("route"),
        "container": payload.quote.get("container"),
        "quantity": payload.quote.get("quantity"),
        "total_ex_vat": payload.quote.get("total_ex_vat"),
        "transit_days_estimate": payload.quote.get("transit_days_estimate"),
        "attached_by": current_user.get("email"),
        "attached_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orders.update_one({"id": payload.order_id}, {"$set": {"freight_quote": quote}})
    return {"success": True, "order_id": payload.order_id, "freight_quote": quote}


@freight_router.get("/public/freight/routes")
async def list_routes():
    routes = await db.freight_rates.find({"active": True}, {"_id": 0}).sort([("origin", 1), ("destination", 1)]).to_list(300)
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


@freight_router.post("/public/freight/quote-pdf")
async def quote_pdf(payload: QuoteRequest):
    """Devis fret PDF LOGI'SCOP numéroté (DF-YYYY-xxxx)."""
    from fastapi.responses import Response
    from operation_docs_pdf import build_operation_pdf, next_doc_number
    quote = await compute_quote(payload)
    number = await next_doc_number(db, "FREIGHT_QUOTE")
    eur = lambda v: f"{v:,.2f} EUR".replace(",", " ").replace(".", ",")
    b = quote["breakdown"]
    sections = [
        ("Route maritime", quote["route"]),
        ("Unité", f"{quote['container']} × {quote['quantity']}"),
        ("Fret de base", eur(b["base_freight"])),
        ("Surcharge BAF", eur(b["baf_surcharge"])),
        ("THC / manutention", eur(b["thc_handling"])),
        ("Assurance transport", eur(b["transport_insurance"])),
        ("Total HT", eur(quote["total_ex_vat"])),
        ("Transit estimé", f"{quote['transit_days_estimate']} jours"),
        ("Validité", "Estimation indicative — devis contractuel confirmé avant tout engagement"),
    ]
    doc = {"doc_type": "FREIGHT_QUOTE", "doc_number": number,
           "sections": sections, "created_at": quote["generated_at"]}
    await db.freight_quotes.insert_one({**doc, "id": number})
    pdf = build_operation_pdf(doc)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'})


@freight_router.post("/public/freight/compare")
async def compare_routes(payload: QuoteRequest):
    """Comparateur : devis sur toutes les routes actives pour un même chargement."""
    routes = await db.freight_rates.find({"active": True}, {"_id": 0}).sort([("origin", 1), ("destination", 1)]).to_list(300)
    results = []
    for route in routes:
        base_unit = float(route["base_prices"].get(payload.container_type, 0))
        if base_unit <= 0:
            continue
        base = base_unit * payload.quantity
        baf = round(base * float(route.get("baf_rate", BAF_RATE)) / 100, 2)
        thc = round(float(route.get("thc", THC).get(payload.container_type, 0)) * payload.quantity, 2)
        insurance = round(max((payload.goods_value_ex_vat or 0) * 0.006, 45.0), 2) if payload.insurance else 0.0
        results.append({
            "route_id": route["id"], "route": f"{route['origin']} → {route['destination']}",
            "total_ex_vat": round(base + baf + thc + insurance, 2),
            "transit_days": route.get("transit_days"),
            "breakdown": {"base_freight": round(base, 2), "baf_surcharge": baf,
                          "thc_handling": thc, "transport_insurance": insurance},
        })
    results.sort(key=lambda r: r["total_ex_vat"])
    return {"container": CONTAINERS.get(payload.container_type), "quantity": payload.quantity,
            "results": results, "cheapest": results[0]["route"] if results else None}


@freight_router.put("/admin/freight/routes/{route_id}")
async def update_rate(route_id: str, payload: RateUpdate, admin: dict = Depends(_admin)):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    r = await db.freight_rates.update_one({"id": route_id}, {"$set": updates})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Route introuvable")
    return {"success": True}


# ===== FRET AÉRIEN — marchandises urgentes =====
AIR_DEFAULT_RATES = [
    # (origine, destination, {palier €/kg}, min €, transit jours)
    ("Paris CDG", "Pointe-à-Pitre (Guadeloupe)", {"lt45": 6.9, "kg45": 5.4, "kg100": 4.6, "kg300": 3.8}, 95, 2),
    ("Paris CDG", "Fort-de-France (Martinique)", {"lt45": 6.9, "kg45": 5.4, "kg100": 4.6, "kg300": 3.8}, 95, 2),
    ("Paris CDG", "Cayenne (Guyane)", {"lt45": 7.6, "kg45": 6.0, "kg100": 5.1, "kg300": 4.2}, 110, 3),
    ("Paris CDG", "Saint-Denis (La Réunion)", {"lt45": 7.2, "kg45": 5.7, "kg100": 4.8, "kg300": 4.0}, 100, 2),
    ("Paris CDG", "Dzaoudzi (Mayotte)", {"lt45": 8.1, "kg45": 6.4, "kg100": 5.4, "kg300": 4.5}, 120, 3),
    ("Amsterdam (Pays-Bas)", "Pointe-à-Pitre (Guadeloupe)", {"lt45": 7.3, "kg45": 5.8, "kg100": 4.9, "kg300": 4.1}, 105, 3),
    ("Miami (États-Unis)", "Pointe-à-Pitre (Guadeloupe)", {"lt45": 5.8, "kg45": 4.5, "kg100": 3.8, "kg300": 3.1}, 85, 2),
    ("Miami (États-Unis)", "Fort-de-France (Martinique)", {"lt45": 5.8, "kg45": 4.5, "kg100": 3.8, "kg300": 3.1}, 85, 2),
    ("Dubaï (EAU)", "Saint-Denis (La Réunion)", {"lt45": 5.5, "kg45": 4.3, "kg100": 3.6, "kg300": 3.0}, 90, 2),
    ("Dubaï (EAU)", "Dzaoudzi (Mayotte)", {"lt45": 6.2, "kg45": 4.9, "kg100": 4.1, "kg300": 3.4}, 100, 3),
    ("Shanghai (Chine)", "Saint-Denis (La Réunion)", {"lt45": 6.6, "kg45": 5.2, "kg100": 4.4, "kg300": 3.6}, 110, 4),
    ("São Paulo (Brésil)", "Cayenne (Guyane)", {"lt45": 5.9, "kg45": 4.7, "kg100": 3.9, "kg300": 3.2}, 90, 2),
]
AIR_FUEL_RATE = 18.0
AIR_SECURITY_PER_KG = 0.15
VOLUMETRIC_KG_PER_M3 = 167


async def seed_air_rates(database):
    for origin, destination, per_kg, min_charge, transit in AIR_DEFAULT_RATES:
        await database.freight_air_rates.update_one(
            {"origin": origin, "destination": destination},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "origin": origin, "destination": destination,
                              "per_kg": per_kg, "min_charge": min_charge, "transit_days": transit,
                              "fuel_rate": AIR_FUEL_RATE, "security_per_kg": AIR_SECURITY_PER_KG,
                              "active": True}},
            upsert=True)


class AirQuoteRequest(BaseModel):
    route_id: str
    weight_kg: float = Field(gt=0, le=50000)
    volume_m3: float = Field(default=0, ge=0, le=500)


def _air_rate_for(per_kg: dict, taxable: float) -> float:
    if taxable < 45:
        return per_kg["lt45"]
    if taxable < 100:
        return per_kg["kg45"]
    if taxable < 300:
        return per_kg["kg100"]
    return per_kg["kg300"]


@freight_router.get("/public/freight/air/routes")
async def list_air_routes():
    routes = await db.freight_air_rates.find({"active": True}, {"_id": 0}).sort(
        [("origin", 1), ("destination", 1)]).to_list(100)
    return {"routes": routes,
            "note": "Barème aérien indicatif LOGI'SCOP pour marchandises urgentes — poids taxable = max(poids réel, volume × 167 kg/m³)."}


@freight_router.post("/public/freight/air/quote")
async def air_quote(payload: AirQuoteRequest):
    route = await db.freight_air_rates.find_one({"id": payload.route_id, "active": True}, {"_id": 0})
    if not route:
        raise HTTPException(status_code=404, detail="Route aérienne introuvable")
    taxable = max(payload.weight_kg, payload.volume_m3 * VOLUMETRIC_KG_PER_M3)
    rate = _air_rate_for(route["per_kg"], taxable)
    base = max(taxable * rate, route["min_charge"])
    fuel = round(base * route["fuel_rate"] / 100, 2)
    security = round(taxable * route["security_per_kg"], 2)
    total = round(base + fuel + security, 2)
    return {
        "mode": "AIR",
        "route": f"{route['origin']} ✈ {route['destination']}",
        "taxable_weight_kg": round(taxable, 1),
        "rate_per_kg": rate,
        "transit_days_estimate": route["transit_days"],
        "breakdown": {"base_freight": round(base, 2), "fuel_surcharge": fuel, "security_fee": security},
        "total_ex_vat": total,
    }
