"""Benchmark catégorie — statistiques anonymisées des consultations clôturées, débloquées en CPC."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from consultation_audit import audit

logger = logging.getLogger(__name__)

benchmark_router = APIRouter(prefix="/api/consultations-benchmark", tags=["consultation-benchmark"])

db = None

CLOSED_STATUSES = ["CLOTUREE", "EN_EVALUATION", "ATTRIBUEE", "SANS_SUITE", "ARCHIVEE"]


def set_benchmark_database(database):
    global db
    db = database


@benchmark_router.post("/{category}")
async def buy_benchmark(category: str, user_id: str = Depends(get_current_user_id)):
    """Débit unique par mois et par catégorie (idempotent). Données agrégées, jamais nominatives."""
    from routes_cpc import _require_vendor
    await _require_vendor(user_id)
    category = category.strip().lower()
    cons = await db.consultations.find(
        {"category": category, "status": {"$in": CLOSED_STATUSES}},
        {"_id": 0, "id": 1}).to_list(200)
    if not cons:
        raise HTTPException(status_code=404, detail="Aucune consultation clôturée dans cette catégorie pour l'instant")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"bench:{category}:{user_id}:{month}"
    already = await db.cpc_ledger.find_one({"idempotency_key": key}, {"_id": 0, "id": 1})
    if not already:
        from routes_cpc_admin import get_cpc_settings
        from cpc_ledger import add_cpc_movement
        cost = (await get_cpc_settings()).get("benchmark_cost", 15)
        await add_cpc_movement(user_id, "REPORT_PURCHASE", -cost, idempotency_key=key,
                               reason=f"Benchmark catégorie « {category} » ({month})")
        await audit("BENCHMARK_PURCHASED", user_id, None, {"category": category, "month": month, "cost": cost})
    from routes_bids import _latest_valid_bids
    prices, participants = [], []
    for c in cons:
        latest = await _latest_valid_bids(c["id"])
        priced = [b["amount_ht_cents"] for b in latest if b.get("amount_ht_cents")]
        prices += priced
        participants.append(len(latest))
    prices.sort()
    n = len(prices)
    return {
        "category": category, "period": month,
        "consultations": len(cons), "offers": n,
        "avg_participants": round(sum(participants) / len(participants), 1) if participants else 0,
        "avg_offer_ht_cents": round(sum(prices) / n) if n else None,
        "median_offer_ht_cents": prices[n // 2] if n else None,
        "min_offer_ht_cents": prices[0] if n else None,
        "max_offer_ht_cents": prices[-1] if n else None,
    }
