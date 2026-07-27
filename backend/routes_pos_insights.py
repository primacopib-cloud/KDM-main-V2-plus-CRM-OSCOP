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


def _week_ranges(now):
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return week_start, week_start - timedelta(days=7)


async def _seller_ranking(point_id, start, end):
    agg = {}
    async for o in db.lolodrive_orders.find(
            {"lolo_point_id": point_id, "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
            {"_id": 0, "operator_name": 1, "total_cents": 1}):
        name = o.get("operator_name") or "Gérant"
        e = agg.setdefault(name, {"name": name, "count": 0, "total_cents": 0})
        e["count"] += 1
        e["total_cents"] += o.get("total_cents", 0)
    return sorted(agg.values(), key=lambda x: (x["count"], x["total_cents"]), reverse=True)


@pos_insights_router.get("/pos/best-seller")
async def pos_best_seller(user: dict = Depends(get_current_user)):
    """Meilleur vendeur comptoir : gagnant de la semaine passée + course de la semaine en cours."""
    point = await _manager_point(user["id"])
    now = datetime.utcnow()
    week_start, prev_start = _week_ranges(now)
    current = await _seller_ranking(point["id"], week_start, now + timedelta(minutes=1))
    previous = await _seller_ranking(point["id"], prev_start, week_start)
    return {"current_week": current, "last_week_winner": previous[0] if previous else None}


@pos_insights_router.get("/pos/sales-goal")
async def pos_sales_goal(user: dict = Depends(get_current_user)):
    """Objectif mensuel de caisse du relais + progression en temps réel."""
    point = await _manager_point(user["id"])
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    totals = await _counter_totals(point["id"], month_start, now + timedelta(minutes=1))
    goal = point.get("monthly_goal_cents") or 0
    percent = round(totals["total_cents"] / goal * 100, 1) if goal > 0 else None
    return {"month": month_start.strftime("%Y-%m"), "goal_cents": goal,
            "month_total_cents": totals["total_cents"], "count": totals["count"], "percent": percent}


@pos_insights_router.put("/manager/sales-goal")
async def set_sales_goal(payload: dict, user: dict = Depends(get_current_user)):
    """Le gérant fixe son objectif mensuel de caisse (en centimes)."""
    from routes_pos_operators import _owned_point
    point = await _owned_point(user["id"])
    try:
        goal = int((payload or {}).get("goal_cents"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="goal_cents entier requis")
    if goal < 0 or goal > 100000000:
        raise HTTPException(status_code=400, detail="Objectif invalide")
    await db.lolodrive_points.update_one(
        {"id": point["id"]}, {"$set": {"monthly_goal_cents": goal, "updated_at": datetime.utcnow()}})
    return {"ok": True, "goal_cents": goal}


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
    wallet = await get_or_create_wallet(point.get("manager_user_id") or user["id"])
    return {"fee_uc": await get_relay_fee_uc(), "balance_uc": wallet.get("balance_uc", 0),
            "point_code": point["code"]}


@pos_insights_router.get("/pos/uc-debits")
async def pos_uc_debits(limit: int = 100, user: dict = Depends(get_current_user)):
    """Détail des débits UC produits relais du gérant (vente par vente)."""
    await _manager_point(user["id"])
    from lolodrive_helpers import get_or_create_wallet
    wallet = await get_or_create_wallet(user["id"])
    debits = await db.lolodrive_wallet_ledger.find(
        {"wallet_id": wallet["id"], "type": "DEBIT", "reason": "RELAY_PRODUCT_FEE"},
        {"_id": 0, "amount_uc": 1, "order_number": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(max(1, min(limit, 500)))
    return {"balance_uc": wallet.get("balance_uc", 0),
            "total_debited_uc": sum(d.get("amount_uc", 0) for d in debits), "debits": debits}


@pos_insights_router.post("/pos/credi-scop/recharge-session")
async def credi_scop_recharge(payload: dict, user: dict = Depends(get_current_user)):
    """Recharge CREDI'SCOP du gérant via Stripe (sans exigence de PASS actif)."""
    point = await _manager_point(user["id"])
    from lolodrive_checkout_apply import RECHARGE_PACKS
    from routes_lolodrive_checkout import _build_urls, _create_checkout_session
    from stripe_accounts import get_account_for_checkout_kind
    import uuid
    pack_key = (payload or {}).get("pack")
    origin_url = (payload or {}).get("origin_url") or ""
    pack = RECHARGE_PACKS.get(pack_key)
    if not pack or not origin_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Pack ou origin_url invalide")
    account = get_account_for_checkout_kind("RECHARGE")
    urls = _build_urls(origin_url, "RECHARGE", user["id"])
    metadata = {"kind": "RECHARGE", "user_id": user["id"], "pack": pack_key,
                "uc": str(pack["uc"]), "stripe_account": account, "context": "CREDI_SCOP_MANAGER"}
    session = _create_checkout_session(
        account=account, amount_eur=pack["amount_eur"],
        success_url=urls["success_url"], cancel_url=urls["cancel_url"],
        metadata=metadata, product_name=f"Recharge CREDI'SCOP — Pack {pack_key} ({point['code']})")
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session["id"], "user_id": user["id"],
        "kind": "RECHARGE", "stripe_account": account,
        "amount_cents": int(pack["amount_eur"] * 100), "currency": "eur",
        "payment_status": "initiated", "metadata": metadata, "applied": False,
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})
    return {"url": session["url"], "session_id": session["id"], "pack": pack_key,
            "uc": pack["uc"], "amount_eur": pack["amount_eur"]}


@pos_insights_router.post("/pos/inventory")
async def pos_inventory(payload: dict, user: dict = Depends(get_current_user)):
    """Mode inventaire : le gérant recompte et corrige tous ses stocks en une fois."""
    point = await _manager_point(user["id"])
    items = (payload or {}).get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="Aucun stock à mettre à jour")
    updated = []
    for it in items[:300]:
        sku = it.get("sku")
        try:
            qty = int(it.get("stock_qty"))
        except (TypeError, ValueError):
            continue
        if not sku or qty < 0 or qty > 100000:
            continue
        product = await db.lolodrive_products.find_one(
            {"sku": sku, "$or": [{"point_code": {"$exists": False}}, {"point_code": None},
                                 {"point_code": point["code"]}]},
            {"_id": 0, "sku": 1, "name": 1, "stock_qty": 1})
        if not product or (product.get("stock_qty") is not None and product["stock_qty"] == qty):
            continue
        old = product.get("stock_qty") or 0
        await db.lolodrive_products.update_one(
            {"sku": sku}, {"$set": {"stock_qty": qty, "updated_at": datetime.utcnow()}})
        await log_stock_movement(sku, product["name"], "INVENTORY", qty - old, qty, point["code"])
        updated.append({"sku": sku, "name": product["name"], "stock_qty": qty, "delta": qty - old})
    return {"ok": True, "updated_count": len(updated), "updated": updated}


@pos_insights_router.get("/admin/uc-fees-summary")
async def admin_uc_fees_summary(months: int = 6, admin: dict = Depends(require_admin)):
    """Revenus UC collectés via les frais produits relais, par mois et par relais."""
    months = max(1, min(months, 24))
    now = datetime.utcnow()
    y, m = now.year, now.month - (months - 1)
    while m <= 0:
        y, m = y - 1, m + 12
    since = datetime(y, m, 1)
    debits = await db.lolodrive_wallet_ledger.find(
        {"type": "DEBIT", "reason": "RELAY_PRODUCT_FEE", "created_at": {"$gte": since}},
        {"_id": 0, "amount_uc": 1, "order_number": 1, "created_at": 1}).to_list(5000)
    order_nums = [d["order_number"] for d in debits if d.get("order_number")]
    orders = {o["order_number"]: o.get("lolo_point_id") async for o in db.lolodrive_orders.find(
        {"order_number": {"$in": order_nums}}, {"_id": 0, "order_number": 1, "lolo_point_id": 1})}
    points = {p["id"]: p async for p in db.lolodrive_points.find(
        {}, {"_id": 0, "id": 1, "code": 1, "name": 1})}
    agg = {}
    total_uc = 0
    for d in debits:
        month = d["created_at"].strftime("%Y-%m")
        pid = orders.get(d.get("order_number"))
        pt = points.get(pid, {})
        key = (month, pt.get("code", "?"))
        e = agg.setdefault(key, {"month": month, "point_code": pt.get("code", "?"),
                                 "point_name": pt.get("name", "Relais inconnu"), "count": 0, "total_uc": 0})
        e["count"] += 1
        e["total_uc"] += d.get("amount_uc", 0)
        total_uc += d.get("amount_uc", 0)
    rows = sorted(agg.values(), key=lambda r: (r["month"], -r["total_uc"]), reverse=True)
    return {"months": months, "total_uc": total_uc, "rows": rows}


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
    rows = ["relais;date;heure;numero;operateur;paiement;articles;remise_promo_eur;total_eur"]
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
            rows.append(f"{label};{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};"
                        f"{o.get('operator_name') or 'Gerant'};{pay};"
                        f"\"{items}\";{(o.get('promo_discount_cents') or 0) / 100:.2f};{total / 100:.2f}")
        rows.append(f"SOUS-TOTAL {label};;;;;{len(plist)} vente(s);Especes {p_cash / 100:.2f};CB {p_card / 100:.2f};{(p_cash + p_card) / 100:.2f}")
        rows.append("")
        g_cash += p_cash
        g_card += p_card
    rows += [f"TOTAL RESEAU ESPECES;;;;;;;;{g_cash / 100:.2f}", f"TOTAL RESEAU CB;;;;;;;;{g_card / 100:.2f}",
             f"TOTAL RESEAU CAISSES;;;;;;;;{(g_cash + g_card) / 100:.2f}",
             f"NB RELAIS ACTIFS;;;;;;;;{len(by_point)}", f"NB VENTES;;;;;;;;{len(orders)}"]
    return PlainTextResponse(
        "\ufeff" + "\n".join(rows), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=caisses-reseau-{y}-{m:02d}.csv"})
