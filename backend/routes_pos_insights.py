"""Insights POS LOLODRIVE : comparatif mensuel gérant, alertes stock bas, export caisse consolidé admin."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from lolodrive_helpers import get_current_user, require_admin
from routes_relay_products import _manager_point, log_stock_movement, get_relay_fee_uc

logger = logging.getLogger(__name__)
pos_insights_router = APIRouter(prefix="/api/lolodrive", tags=["POS Insights"])
db = None


def set_pos_insights_database(database):
    global db
    db = database


async def _counter_totals(point_id: str, start: datetime, end: datetime) -> dict:
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point_id, "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0, "total_cents": 1}).to_list(3000)
    return {"count": len(orders), "total_cents": sum(o.get("total_cents", 0) for o in orders)}


@pos_insights_router.get("/pos/monthly-compare")
async def pos_monthly_compare(user: dict = Depends(get_current_user)):
    """Caisse du mois en cours vs même période du mois précédent (tendance)."""
    point = await _manager_point(user["id"])
    now = datetime.utcnow()
    cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (cur_start - timedelta(days=1)).replace(day=1)
    elapsed = now - cur_start
    prev_end = min(prev_start + elapsed, cur_start)
    current = await _counter_totals(point["id"], cur_start, now + timedelta(minutes=1))
    previous = await _counter_totals(point["id"], prev_start, prev_end)
    prev_full = await _counter_totals(point["id"], prev_start, cur_start)
    delta = None
    if previous["total_cents"] > 0:
        delta = round((current["total_cents"] - previous["total_cents"]) / previous["total_cents"] * 100, 1)
    trend = "flat"
    if delta is not None:
        trend = "up" if delta > 2 else ("down" if delta < -2 else "flat")
    elif current["total_cents"] > 0:
        trend, delta = "up", None
    return {"current_month": cur_start.strftime("%Y-%m"), "previous_month": prev_start.strftime("%Y-%m"),
            "day_of_month": now.day, "current": current, "previous_same_period": previous,
            "previous_full": prev_full, "delta_percent": delta, "trend": trend}


@pos_insights_router.get("/pos/stock-alerts")
async def pos_stock_alerts(days: int = 30, user: dict = Depends(get_current_user)):
    """Produits du top ventes comptoir dont le stock risque la rupture (< 14 jours de couverture)."""
    point = await _manager_point(user["id"])
    days = max(1, min(days, 365))
    since = datetime.utcnow() - timedelta(days=days)
    sold = {}
    async for o in db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": since}},
            {"_id": 0, "items": 1}):
        for l in o.get("items", []):
            sold[l["sku"]] = sold.get(l["sku"], 0) + l.get("qty", 0)
    if not sold:
        return {"days": days, "alerts": []}
    prods = await db.lolodrive_products.find(
        {"sku": {"$in": list(sold)}, "stock_qty": {"$ne": None}},
        {"_id": 0, "sku": 1, "name": 1, "stock_qty": 1}).to_list(100)
    alerts = []
    for p in prods:
        stock = p.get("stock_qty") or 0
        daily = sold[p["sku"]] / days
        days_left = round(stock / daily) if daily > 0 else None
        if stock <= 5 or (days_left is not None and days_left <= 14):
            alerts.append({"sku": p["sku"], "name": p["name"], "stock_qty": stock,
                           "sold_qty": sold[p["sku"]], "days_left": days_left,
                           "critical": stock <= 5 or (days_left is not None and days_left <= 5)})
    alerts.sort(key=lambda a: (a["days_left"] if a["days_left"] is not None else 999, a["stock_qty"]))
    return {"days": days, "alerts": alerts}


@pos_insights_router.get("/pos/relay-fee")
async def pos_relay_fee(user: dict = Depends(get_current_user)):
    """Règle réseau : frais UC appliqués aux ventes de produits relais + solde CREDI'SCOP du gérant."""
    point = await _manager_point(user["id"])
    from lolodrive_helpers import get_or_create_wallet
    wallet = await get_or_create_wallet(user["id"])
    return {"fee_uc": await get_relay_fee_uc(), "balance_uc": wallet.get("balance_uc", 0),
            "point_code": point["code"]}


@pos_insights_router.get("/admin/settings/relay-fee")
async def admin_get_relay_fee(admin: dict = Depends(require_admin)):
    return {"fee_uc": await get_relay_fee_uc()}


@pos_insights_router.put("/admin/settings/relay-fee")
async def admin_set_relay_fee(payload: dict, admin: dict = Depends(require_admin)):
    """Le super admin modifie la valeur UC débitée par produit relais vendu au comptoir."""
    try:
        fee = float((payload or {}).get("fee_uc"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="fee_uc numérique requis")
    if fee < 0 or fee > 1000:
        raise HTTPException(status_code=400, detail="fee_uc doit être entre 0 et 1000")
    if fee == int(fee):
        fee = int(fee)
    await db.lolodrive_settings.update_one(
        {"key": "relay_product_fee_uc"},
        {"$set": {"value_uc": fee, "updated_at": datetime.utcnow(), "updated_by": admin.get("email")}},
        upsert=True)
    return {"ok": True, "fee_uc": fee}


@pos_insights_router.patch("/pos/products/{sku}/stock")
async def pos_set_stock(sku: str, payload: dict, user: dict = Depends(get_current_user)):
    """Le gérant ajuste le stock d'un produit de son catalogue après un réassort."""
    point = await _manager_point(user["id"])
    try:
        qty = int((payload or {}).get("stock_qty"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="stock_qty entier requis")
    if qty < 0 or qty > 100000:
        raise HTTPException(status_code=400, detail="stock_qty doit être entre 0 et 100000")
    product = await db.lolodrive_products.find_one(
        {"sku": sku, "$or": [{"point_code": {"$exists": False}}, {"point_code": None},
                             {"point_code": point["code"]}]}, {"_id": 0, "sku": 1, "name": 1, "stock_qty": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable au catalogue du relais")
    old = product.get("stock_qty") or 0
    await db.lolodrive_products.update_one(
        {"sku": sku}, {"$set": {"stock_qty": qty, "updated_at": datetime.utcnow()}})
    await log_stock_movement(sku, product["name"], "RESTOCK", qty - old, qty, point["code"])
    return {"ok": True, "sku": sku, "name": product["name"], "stock_qty": qty}


@pos_insights_router.get("/pos/stock-history")
async def pos_stock_history(sku: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Historique des mouvements de stock d'un produit (réassorts, ventes, stock initial)."""
    await _manager_point(user["id"])
    movements = await db.stock_movements.find(
        {"sku": sku}, {"_id": 0}).sort("created_at", -1).to_list(max(1, min(limit, 200)))
    return {"sku": sku, "movements": movements}


@pos_insights_router.get("/admin/counter-ranking")
async def admin_counter_ranking(month: Optional[str] = None, admin: dict = Depends(require_admin)):
    """Classement des relais par chiffre d'affaires comptoir du mois (podium super admin)."""
    now = datetime.utcnow()
    try:
        y, m = map(int, (month or now.strftime("%Y-%m")).split("-"))
        start = datetime(y, m, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format mois invalide (attendu : YYYY-MM)")
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    agg = {}
    async for o in db.lolodrive_orders.find(
            {"channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
            {"_id": 0, "lolo_point_id": 1, "total_cents": 1}):
        e = agg.setdefault(o.get("lolo_point_id"), {"count": 0, "total_cents": 0})
        e["count"] += 1
        e["total_cents"] += o.get("total_cents", 0)
    points = {p["id"]: p async for p in db.lolodrive_points.find(
        {}, {"_id": 0, "id": 1, "code": 1, "name": 1, "city": 1})}
    ranking = [{"point_id": pid, "code": points.get(pid, {}).get("code", pid),
                "name": points.get(pid, {}).get("name", "Relais inconnu"),
                "city": points.get(pid, {}).get("city"), **vals}
               for pid, vals in agg.items()]
    ranking.sort(key=lambda r: r["total_cents"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1
    return {"month": start.strftime("%Y-%m"), "ranking": ranking}


@pos_insights_router.get("/admin/counter-journal/export")
async def admin_counter_journal_export(month: Optional[str] = None, admin: dict = Depends(require_admin)):
    """Export CSV consolidé des caisses comptoir de tous les relais du réseau (mois donné)."""
    now = datetime.utcnow()
    try:
        y, m = map(int, (month or now.strftime("%Y-%m")).split("-"))
        start = datetime(y, m, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format mois invalide (attendu : YYYY-MM)")
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    orders = await db.lolodrive_orders.find(
        {"channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0}).sort([("lolo_point_id", 1), ("created_at", 1)]).to_list(10000)
    points = {p["id"]: p async for p in db.lolodrive_points.find({}, {"_id": 0, "id": 1, "code": 1, "name": 1})}
    rows = ["relais;date;heure;numero;paiement;articles;remise_promo_eur;total_eur"]
    g_cash = g_card = 0
    by_point = {}
    for o in orders:
        by_point.setdefault(o.get("lolo_point_id"), []).append(o)
    for pid, plist in by_point.items():
        pt = points.get(pid, {})
        label = f"{pt.get('code', pid)} — {pt.get('name', '')}".strip(" —")
        p_cash = p_card = 0
        for o in plist:
            items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
            pay = "CB" if o.get("payment_method") == "CARD" else "Especes"
            total = o.get("total_cents", 0)
            if o.get("payment_method") == "CARD":
                p_card += total
            else:
                p_cash += total
            rows.append(f"{label};{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};{pay};"
                        f"\"{items}\";{(o.get('promo_discount_cents') or 0) / 100:.2f};{total / 100:.2f}")
        rows.append(f"SOUS-TOTAL {label};;;;{len(plist)} vente(s);Especes {p_cash / 100:.2f};CB {p_card / 100:.2f};{(p_cash + p_card) / 100:.2f}")
        rows.append("")
        g_cash += p_cash
        g_card += p_card
    rows += [f"TOTAL RESEAU ESPECES;;;;;;;{g_cash / 100:.2f}", f"TOTAL RESEAU CB;;;;;;;{g_card / 100:.2f}",
             f"TOTAL RESEAU CAISSES;;;;;;;{(g_cash + g_card) / 100:.2f}",
             f"NB RELAIS ACTIFS;;;;;;;{len(by_point)}", f"NB VENTES;;;;;;;{len(orders)}"]
    return PlainTextResponse(
        "\ufeff" + "\n".join(rows), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=caisses-reseau-{y}-{m:02d}.csv"})
