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


async def compute_benchmark(category: str):
    """Stats anonymisées des consultations clôturées d'une catégorie (None si aucune)."""
    cons = await db.consultations.find(
        {"category": category, "status": {"$in": CLOSED_STATUSES}},
        {"_id": 0, "id": 1}).to_list(200)
    if not cons:
        return None
    from routes_bids import _latest_valid_bids
    prices, participants = [], []
    for c in cons:
        latest = await _latest_valid_bids(c["id"])
        prices += [b["amount_ht_cents"] for b in latest if b.get("amount_ht_cents")]
        participants.append(len(latest))
    prices.sort()
    n = len(prices)
    return {
        "consultations": len(cons), "offers": n,
        "avg_participants": round(sum(participants) / len(participants), 1) if participants else 0,
        "avg_offer_ht_cents": round(sum(prices) / n) if n else None,
        "median_offer_ht_cents": prices[n // 2] if n else None,
        "min_offer_ht_cents": prices[0] if n else None,
        "max_offer_ht_cents": prices[-1] if n else None,
    }


@benchmark_router.post("/{category}")
async def buy_benchmark(category: str, user_id: str = Depends(get_current_user_id)):
    """Débit unique par mois et par catégorie (idempotent). Données agrégées, jamais nominatives."""
    from routes_cpc import _require_vendor
    await _require_vendor(user_id)
    category = category.strip().lower()
    stats = await compute_benchmark(category)
    if stats is None:
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
    return {"category": category, "period": month, **stats}


async def _main_category(user: dict) -> str:
    vendor_id = user.get("vendor_id")
    if not vendor_id:
        v = await db.vendors.find_one({"email": user.get("email")}, {"_id": 0, "id": 1})
        vendor_id = (v or {}).get("id")
    if not vendor_id:
        return None
    pipeline = [{"$match": {"vendor_id": vendor_id, "category": {"$nin": [None, ""]}}},
                {"$group": {"_id": "$category", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$limit": 1}]
    rows = await db.vendor_products.aggregate(pipeline).to_list(1)
    return rows[0]["_id"] if rows else None


async def send_monthly_benchmarks(database) -> int:
    """Cron : benchmark de la catégorie principale offert chaque mois aux abonnés Expert et Réseau."""
    global db
    if db is None:
        db = database
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    sent = 0
    async for sub in db.cpc_subscriptions.find(
            {"status": {"$in": ["ACTIVE", "CANCELLING"]},
             "plan_id": {"$in": ["cpc-plan-expert", "cpc-plan-reseau"]},
             "benchmark_sent_month": {"$ne": month}}, {"_id": 0}):
        user = await db.users.find_one({"id": sub["user_id"]},
                                       {"_id": 0, "email": 1, "full_name": 1, "name": 1, "vendor_id": 1})
        if not user or not user.get("email"):
            continue
        category = await _main_category(user)
        stats = await compute_benchmark(category) if category else None
        await db.cpc_subscriptions.update_one(
            {"user_id": sub["user_id"], "plan_id": sub["plan_id"]},
            {"$set": {"benchmark_sent_month": month}})
        if not stats:
            continue
        eur = lambda c: f"{(c or 0) / 100:.2f} €".replace(".", ",")
        try:
            from brevo_service import send_email
            await send_email(
                to_email=user["email"], to_name=user.get("full_name") or user.get("name"),
                subject=f"Votre benchmark mensuel offert — catégorie « {category} » ({month})",
                html_content=f"""<h2 style="color:#451F6B;">Benchmark « {category} » — {month}</h2>
                <p>Bonjour,</p>
                <p>En tant qu'abonné <strong>{sub['plan_label']}</strong>, voici votre benchmark anonymisé
                mensuel offert (aucun crédit débité) :</p>
                <ul>
                  <li>Consultations clôturées analysées : <strong>{stats['consultations']}</strong></li>
                  <li>Offres analysées : <strong>{stats['offers']}</strong> · Participants moyens : <strong>{stats['avg_participants']}</strong></li>
                  <li>Prix moyen : <strong>{eur(stats['avg_offer_ht_cents'])}</strong> HT · Médiane : <strong>{eur(stats['median_offer_ht_cents'])}</strong> HT</li>
                  <li>Fourchette : {eur(stats['min_offer_ht_cents'])} — {eur(stats['max_offer_ht_cents'])} HT</li>
                </ul>
                <p style="color:#777;font-size:12px;">Données agrégées et anonymisées — aucun secret commercial individuel n'est divulgué.</p>""",
                tags=["monthly-benchmark"])
            sent += 1
        except Exception as exc:
            logger.warning("Benchmark mensuel %s : %s", user["email"], exc)
    return sent
