"""Outils d'intelligence d'achat (espace acheteur) :
comparateur de lots, simulation de fret inter-îles, prévision de demande par catégorie."""
import logging
import statistics
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

buyer_tools_router = APIRouter(prefix="/api/buyer-tools", tags=["buyer-tools"])

db = None

CLOSED_STATUSES = ["CLOTUREE", "EN_EVALUATION", "ATTRIBUEE", "SANS_SUITE", "ARCHIVEE"]

TERRITORIES = ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "HEXAGONE"]

DEFAULT_FREIGHT_RATES = [
    {"pair": "GUADELOUPE|MARTINIQUE", "base_cents": 9000, "per_kg_cents": 28, "per_m3_cents": 5500, "delay_days": "2-3"},
    {"pair": "GUADELOUPE|GUYANE", "base_cents": 14000, "per_kg_cents": 45, "per_m3_cents": 8500, "delay_days": "4-6"},
    {"pair": "GUYANE|MARTINIQUE", "base_cents": 13000, "per_kg_cents": 42, "per_m3_cents": 8000, "delay_days": "4-6"},
    {"pair": "GUADELOUPE|HEXAGONE", "base_cents": 18000, "per_kg_cents": 55, "per_m3_cents": 11000, "delay_days": "12-18"},
    {"pair": "HEXAGONE|MARTINIQUE", "base_cents": 18000, "per_kg_cents": 55, "per_m3_cents": 11000, "delay_days": "12-18"},
    {"pair": "GUYANE|HEXAGONE", "base_cents": 20000, "per_kg_cents": 65, "per_m3_cents": 13000, "delay_days": "15-21"},
    {"pair": "HEXAGONE|REUNION", "base_cents": 19000, "per_kg_cents": 60, "per_m3_cents": 12000, "delay_days": "18-24"},
    {"pair": "GUADELOUPE|REUNION", "base_cents": 26000, "per_kg_cents": 85, "per_m3_cents": 17000, "delay_days": "25-35"},
    {"pair": "MARTINIQUE|REUNION", "base_cents": 26000, "per_kg_cents": 85, "per_m3_cents": 17000, "delay_days": "25-35"},
    {"pair": "GUYANE|REUNION", "base_cents": 26000, "per_kg_cents": 85, "per_m3_cents": 17000, "delay_days": "25-35"},
]
FUEL_SURCHARGE_PCT = 12  # BAF par défaut
EXPRESS_MULTIPLIER = 1.6


def set_buyer_tools_database(database):
    global db
    db = database


# ---------- Comparateur de lots ----------

async def _lot_stats(cid: str) -> dict:
    c = await db.consultations.find_one({"id": cid}, {"_id": 0, "published_snapshot": 0})
    if not c:
        raise HTTPException(status_code=404, detail=f"Consultation {cid} introuvable")
    from routes_bids import _latest_valid_bids
    entries = await db.consultation_entries.count_documents({"consultation_id": cid, "status": "INSCRIT"})
    closed = c["status"] in CLOSED_STATUSES
    bids = await _latest_valid_bids(cid)
    priced = [b["amount_ht_cents"] for b in bids if b.get("amount_ht_cents")] if closed else []
    award = await db.consultation_awards.find_one(
        {"consultation_id": cid, "awarded_entry_id": {"$ne": None}}, {"_id": 0, "ranking": 1, "awarded_entry_id": 1})
    winner = None
    if award:
        winner = next((r["company"] for r in award["ranking"] if r["entry_id"] == award["awarded_entry_id"]), None)
    return {
        "id": cid, "ref": c["ref"], "title": c["title"], "status": c["status"],
        "category": c["category"], "procedure": c["procedure"], "type": c["type"],
        "opens_at": c.get("opens_at"), "closes_at": c.get("closes_at"),
        "duplicated_from": c.get("duplicated_from"),
        "participants": entries, "valid_bids": len(bids),
        "best_offer_ht_cents": min(priced) if priced else None,
        "median_offer_ht_cents": int(statistics.median(priced)) if priced else None,
        "winner": winner, "closed": closed,
    }


@buyer_tools_router.get("/compare/candidates")
async def compare_candidates(user_id: str = Depends(get_current_user_id)):
    """Consultations clôturées comparables + paires liées par duplication."""
    items = await db.consultations.find(
        {"status": {"$in": CLOSED_STATUSES}},
        {"_id": 0, "id": 1, "ref": 1, "title": 1, "status": 1, "category": 1,
         "duplicated_from": 1, "closes_at": 1}).sort("closes_at", -1).limit(100).to_list(100)
    ids = {c["id"] for c in items}
    pairs = [{"a": c["duplicated_from"], "b": c["id"]}
             for c in items if c.get("duplicated_from") in ids]
    return {"items": items, "linked_pairs": pairs}


@buyer_tools_router.get("/compare")
async def compare_lots(a: str, b: str, user_id: str = Depends(get_current_user_id)):
    """Comparaison côte à côte de deux consultations (ex. un lot et sa version dupliquée)."""
    if a == b:
        raise HTTPException(status_code=400, detail="Sélectionnez deux consultations différentes")
    left, right = await _lot_stats(a), await _lot_stats(b)
    deltas = {}
    if left["best_offer_ht_cents"] and right["best_offer_ht_cents"]:
        diff = right["best_offer_ht_cents"] - left["best_offer_ht_cents"]
        deltas["best_offer_diff_cents"] = diff
        deltas["best_offer_diff_pct"] = round(diff / left["best_offer_ht_cents"] * 100, 1)
    deltas["participants_diff"] = right["participants"] - left["participants"]
    deltas["valid_bids_diff"] = right["valid_bids"] - left["valid_bids"]
    linked = right.get("duplicated_from") == a or left.get("duplicated_from") == b
    return {"a": left, "b": right, "deltas": deltas, "linked_by_duplication": linked}


@buyer_tools_router.get("/compare/pdf")
async def compare_pdf(a: str, b: str, user_id: str = Depends(get_current_user_id)):
    """Export PDF de la comparaison, à joindre au dossier d'achat."""
    from fastapi import Response
    data = await compare_lots(a, b, user_id)
    from buyer_tools_pdf import generate_compare_pdf
    pdf = generate_compare_pdf(data["a"], data["b"], data["deltas"], data["linked_by_duplication"])
    filename = f"comparaison-{data['a']['ref']}-{data['b']['ref']}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------- Simulation de fret ----------

async def _territory_codes() -> list:
    codes = [z["code"] async for z in db.zones_v2.find({"is_active": True}, {"_id": 0, "code": 1}).sort("code", 1)]
    return codes or TERRITORIES


GENERIC_RATE = {"base_cents": 20000, "per_kg_cents": 60, "per_m3_cents": 12000, "delay_days": "10-15"}


def _pair_key(o: str, d: str) -> str:
    return "|".join(sorted([o, d]))


async def _get_rates() -> list:
    if await db.freight_rates.count_documents({}) == 0:
        await db.freight_rates.insert_many([{**r} for r in DEFAULT_FREIGHT_RATES])
    return await db.freight_rates.find({}, {"_id": 0}).to_list(50)


@buyer_tools_router.get("/freight/rates")
async def freight_rates(user_id: str = Depends(get_current_user_id)):
    return {"territories": await _territory_codes(), "rates": await _get_rates(),
            "fuel_surcharge_pct": FUEL_SURCHARGE_PCT, "express_multiplier": EXPRESS_MULTIPLIER}


class FreightBody(BaseModel):
    origin: str
    destination: str
    weight_kg: float = 0
    volume_m3: float = 0
    express: bool = False


async def _simulate_one(origin: str, destination: str, weight_kg: float, volume_m3: float, express: bool) -> dict:
    codes = await _territory_codes()
    if origin not in codes or destination not in codes:
        raise HTTPException(status_code=400, detail="Territoire inconnu")
    if origin == destination:
        raise HTTPException(status_code=400, detail="Origine et destination identiques")
    if weight_kg <= 0 and volume_m3 <= 0:
        raise HTTPException(status_code=400, detail="Indiquez un poids ou un volume")
    await _get_rates()
    rate = await db.freight_rates.find_one({"pair": _pair_key(origin, destination)}, {"_id": 0})
    if not rate:
        rate = {"pair": _pair_key(origin, destination), **GENERIC_RATE}
        await db.freight_rates.insert_one({**rate, "auto_seeded": True})
    weight_cost = int(weight_kg * rate["per_kg_cents"])
    volume_cost = int(volume_m3 * rate["per_m3_cents"])
    variable = max(weight_cost, volume_cost)  # règle du payant (poids/volume)
    subtotal = rate["base_cents"] + variable
    fuel = int(subtotal * FUEL_SURCHARGE_PCT / 100)
    total = subtotal + fuel
    if express:
        total = int(total * EXPRESS_MULTIPLIER)
    return {
        "pair": rate["pair"], "destination": destination, "delay_days": rate["delay_days"],
        "base_cents": rate["base_cents"],
        "weight_cost_cents": weight_cost, "volume_cost_cents": volume_cost,
        "billed_on": "poids" if weight_cost >= volume_cost else "volume",
        "fuel_surcharge_cents": fuel, "fuel_surcharge_pct": FUEL_SURCHARGE_PCT,
        "express": express, "total_ht_cents": total,
        "disclaimer": "Estimation indicative hors taxes, octroi de mer et frais de douane — à confirmer avec le transporteur.",
    }


@buyer_tools_router.post("/freight/simulate")
async def freight_simulate(body: FreightBody, user_id: str = Depends(get_current_user_id)):
    return await _simulate_one(body.origin, body.destination, body.weight_kg, body.volume_m3, body.express)


class FreightMultiBody(BaseModel):
    origin: str
    destinations: list
    weight_kg: float = 0
    volume_m3: float = 0
    express: bool = False


@buyer_tools_router.post("/freight/simulate-multi")
async def freight_simulate_multi(body: FreightMultiBody, user_id: str = Depends(get_current_user_id)):
    """Fret vers plusieurs territoires à la fois (lots interterritoriaux à 3+ zones)."""
    dests = [d for d in dict.fromkeys(body.destinations) if d != body.origin]
    if not dests:
        raise HTTPException(status_code=400, detail="Indiquez au moins une destination différente de l'origine")
    if len(dests) > 10:
        raise HTTPException(status_code=400, detail="10 destinations maximum")
    items = [await _simulate_one(body.origin, d, body.weight_kg, body.volume_m3, body.express) for d in dests]
    return {"origin": body.origin, "items": items,
            "grand_total_ht_cents": sum(i["total_ht_cents"] for i in items),
            "disclaimer": items[0]["disclaimer"]}


class RateBody(BaseModel):
    base_cents: int
    per_kg_cents: int
    per_m3_cents: int
    delay_days: str


@buyer_tools_router.put("/freight/rates/{pair}")
async def update_freight_rate(pair: str, body: RateBody, admin: dict = Depends(require_admin)):
    res = await db.freight_rates.update_one({"pair": pair}, {"$set": body.dict()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Liaison inconnue")
    return {"ok": True}


# ---------- Prévision de demande ----------

def _last_months(n: int) -> list:
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


async def _category_month_series(months: list):
    since = f"{months[0]}-01"
    cats: dict = {}
    cons_ids = []
    async for c in db.consultations.find(
            {"created_at": {"$gte": since}}, {"_id": 0, "id": 1, "category": 1, "created_at": 1}):
        month = str(c["created_at"])[:7]
        if month not in months:
            continue
        cat = c["category"]
        cats.setdefault(cat, {m: 0 for m in months})
        cats[cat][month] += 1
        cons_ids.append((cat, c["id"]))
    part_by_cat: dict = {}
    if cons_ids:
        ids = [cid for _, cid in cons_ids]
        pipeline = [{"$match": {"consultation_id": {"$in": ids}, "status": "INSCRIT"}},
                    {"$group": {"_id": "$consultation_id", "n": {"$sum": 1}}}]
        counts = {r["_id"]: r["n"] async for r in db.consultation_entries.aggregate(pipeline)}
        for cat, cid in cons_ids:
            part_by_cat.setdefault(cat, []).append(counts.get(cid, 0))
    return cats, part_by_cat


def _trend_forecast(series: list):
    last3 = series[-3:]
    avg3 = sum(last3) / 3
    slope = (last3[-1] - last3[0]) / 2
    forecast = max(0, round(avg3 + slope))
    trend = "up" if slope > 0.3 else ("down" if slope < -0.3 else "stable")
    return forecast, trend


@buyer_tools_router.get("/demand-forecast")
async def demand_forecast(user_id: str = Depends(get_current_user_id)):
    """Prévision simple : lots lancés par catégorie et par mois (6 derniers), tendance + projection mois prochain."""
    months = _last_months(6)
    cats, part_by_cat = await _category_month_series(months)
    out = []
    for cat, series_map in sorted(cats.items()):
        series = [series_map[m] for m in months]
        forecast, trend = _trend_forecast(series)
        parts = part_by_cat.get(cat, [])
        out.append({
            "category": cat, "months": months, "series": series,
            "total_6m": sum(series), "forecast_next_month": forecast, "trend": trend,
            "avg_participants": round(sum(parts) / len(parts), 1) if parts else 0,
        })
    out.sort(key=lambda x: -x["total_6m"])
    return {"months": months, "categories": out,
            "method": "Moyenne mobile 3 mois + tendance — basée sur les consultations lancées."}


# ---------- Risque d'approvisionnement ----------

async def _eligible_vendors(category: str) -> int:
    vendor_ids = await db.vendor_products.distinct("vendor_id", {"category": category})
    emails = set()
    if vendor_ids:
        async for v in db.vendors.find({"id": {"$in": vendor_ids}}, {"_id": 0, "email": 1}):
            if v.get("email"):
                emails.add(v["email"].lower())
    return len(emails)


RISK_RECO = {
    "ELEVE": "Sécurisez en amont : négociation directe, sourcing de nouveaux fournisseurs ou report du lot.",
    "MODERE": "Anticipez : lancez la consultation tôt et prévoyez une relance ciblée des vendeurs.",
    "FAIBLE": "Concurrence suffisante — enchère ou offres scellées possibles sans précaution particulière.",
}


@buyer_tools_router.get("/supply-risk")
async def supply_risk(user_id: str = Depends(get_current_user_id)):
    """Score de risque par catégorie : liquidité fournisseurs × tendance de demande."""
    months = _last_months(6)
    cats, _ = await _category_month_series(months)
    categories = set(cats.keys()) | set(await db.vendor_products.distinct("category"))
    out = []
    for cat in sorted(c for c in categories if c):
        eligible = await _eligible_vendors(cat)
        series = [cats.get(cat, {}).get(m, 0) for m in months]
        _, trend = _trend_forecast(series)
        score = 90 if eligible == 0 else 70 if eligible == 1 else 50 if eligible == 2 else 30 if eligible <= 4 else 15
        if trend == "up":
            score += 15
        elif trend == "down":
            score -= 10
        score = max(5, min(100, score))
        level = "ELEVE" if score >= 70 else ("MODERE" if score >= 40 else "FAIBLE")
        out.append({"category": cat, "eligible_vendors": eligible, "demand_trend": trend,
                    "lots_6m": sum(series), "risk_score": score, "risk_level": level,
                    "recommendation": RISK_RECO[level]})
    out.sort(key=lambda x: -x["risk_score"])
    return {"categories": out,
            "method": "Score = rareté des fournisseurs éligibles, ajusté par la tendance de demande (6 mois)."}


@buyer_tools_router.get("/supply-risk/pdf")
async def supply_risk_pdf(user_id: str = Depends(get_current_user_id)):
    """Rapport PDF mensuel des risques d'approvisionnement (comités d'achat)."""
    from fastapi import Response
    data = await supply_risk(user_id)
    from buyer_tools_pdf import generate_risk_pdf
    pdf = generate_risk_pdf(data["categories"], data["method"])
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="risque-approvisionnement-{month}.pdf"'})


# ---------- Suggestion COOP'IA (procédure conseillée) ----------

def _rule_suggestion(eligible: int, trend: str, level: str) -> dict:
    if eligible >= 3 and level == "FAIBLE":
        return {"procedure": "ENCHERE_INVERSEE",
                "rationale": "Concurrence suffisante et risque faible : l'enchère inversée maximise la pression concurrentielle et fait baisser les prix."}
    if eligible >= 3 and level == "MODERE":
        return {"procedure": "ENCHERE_INVERSEE",
                "rationale": "Plusieurs fournisseurs éligibles malgré un risque modéré : l'enchère reste jouable, prévoyez une relance ciblée en cours de consultation."}
    return {"procedure": "SCELLEE",
            "rationale": "Fournisseurs rares ou risque élevé : les offres scellées évitent la désaffection des rares candidats et protègent la relation fournisseur."}


@buyer_tools_router.get("/procedure-suggestion")
async def procedure_suggestion(category: str, user_id: str = Depends(get_current_user_id)):
    """COOP'IA : recommande scellée ou enchère selon risque + liquidité, avec argumentaire IA."""
    data = await supply_risk(user_id)
    cat = next((c for c in data["categories"] if c["category"] == category), None)
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie sans données de risque")
    base = _rule_suggestion(cat["eligible_vendors"], cat["demand_trend"], cat["risk_level"])
    try:
        import os as _os
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=_os.environ.get("EMERGENT_LLM_KEY"),
                       session_id=f"coopia-proc-{user_id}",
                       system_message="Tu es COOP'IA, assistant achats de la coopérative KDMARCHÉ × O'SCOP. Réponds en français, 2 phrases maximum, ton professionnel.").with_model("openai", "gpt-5.4-mini")
        msg = (f"Catégorie « {category} » : {cat['eligible_vendors']} fournisseur(s) éligible(s), "
               f"tendance de demande {cat['demand_trend']}, score de risque {cat['risk_score']}/100 ({cat['risk_level']}), "
               f"{cat['lots_6m']} lots sur 6 mois. Procédure recommandée par nos règles : {base['procedure']}. "
               "Justifie cette recommandation en 2 phrases concrètes pour un comité d'achat.")
        resp = await chat.send_message(UserMessage(text=msg))
        if resp and len(str(resp).strip()) > 20:
            base["rationale"] = str(resp).strip()
            base["ai"] = True
    except Exception as exc:
        logger.warning("COOP'IA suggestion fallback (règles) : %s", exc)
        base["ai"] = False
    return {"category": category, "risk_score": cat["risk_score"], "risk_level": cat["risk_level"],
            "eligible_vendors": cat["eligible_vendors"], "demand_trend": cat["demand_trend"], **base}
