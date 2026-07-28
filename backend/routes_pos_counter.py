"""Caisse comptoir POS : encaissement (espèces / CB / UC / combiné), client PASS, journal, exports, primes."""
import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin, cents_to_uc
from routes_relay_products import (
    _manager_point, log_stock_movement, get_relay_fee_uc,
    _notify_negative_balance, _check_goal_reached,
)

logger = logging.getLogger(__name__)
pos_counter_router = APIRouter(prefix="/api/lolodrive", tags=["POS Counter"])
db = None


def set_pos_counter_database(database):
    global db
    db = database


def _pay_label(o: dict) -> str:
    m = o.get("payment_method")
    if m == "MIXED":
        return "UC+CB" if o.get("rest_method") == "CARD" else "UC+Especes"
    return {"CARD": "CB", "UC": "UC"}.get(m, "Especes")


def split_totals(orders: list):
    """Ventile les totaux d'une liste de ventes comptoir en (espèces, CB, UC) en centimes."""
    cash = card = uc = 0
    for o in orders:
        t = o.get("total_cents", 0)
        m = o.get("payment_method")
        if m == "UC":
            uc += t
        elif m == "MIXED":
            covered = o.get("uc_covered_cents") or 0
            uc += covered
            if o.get("rest_method") == "CARD":
                card += t - covered
            else:
                cash += t - covered
        elif m == "CARD":
            card += t
        else:
            cash += t
    return cash, card, uc


class CounterSaleItem(BaseModel):
    sku: str
    qty: int = 1


class CounterSaleBody(BaseModel):
    items: list
    payment_method: str = "CASH"
    customer_user_id: Optional[str] = None
    uc_amount: Optional[int] = None
    rest_method: Optional[str] = None


@pos_counter_router.get("/pos/customer-lookup")
async def pos_customer_lookup(q: str, user: dict = Depends(get_current_user)):
    """Recherche d'un client par code PASS LOLODRIVE, email ou nom → solde CREDI'SCOP, statut PASS et fidélité."""
    point = await _manager_point(user["id"])
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Saisissez au moins 2 caractères")
    proj = {"_id": 0, "id": 1, "contact_name": 1, "email": 1}
    target = None
    pass_doc = await db.lolodrive_passes.find_one(
        {"id": {"$regex": f"^{re.escape(q)}$", "$options": "i"}}, {"_id": 0})
    if pass_doc:
        target = await db.users.find_one({"id": pass_doc["user_id"]}, proj)
    if not target:
        target = await db.users.find_one({"email": q.lower()}, proj)
    if not target:
        target = await db.users.find_one(
            {"contact_name": {"$regex": re.escape(q), "$options": "i"}}, proj)
    if not target:
        raise HTTPException(status_code=404, detail="Aucun client trouvé (code PASS, email ou nom)")
    best_pass = await db.lolodrive_passes.find_one(
        {"user_id": target["id"]}, {"_id": 0, "id": 1, "status": 1, "ends_at": 1}, sort=[("ends_at", -1)])
    now = datetime.utcnow()
    pass_active = bool(best_pass and best_pass.get("status") == "ACTIVE"
                       and best_pass.get("ends_at") and best_pass["ends_at"] > now)
    from lolodrive_helpers import get_or_create_wallet
    wallet = await get_or_create_wallet(target["id"])
    from loyalty_bonus import get_loyalty_config
    loy_cfg = await get_loyalty_config(db)
    loy_count = await db.lolodrive_orders.count_documents(
        {"channel": "COUNTER", "user_id": target["id"], "lolo_point_id": point["id"]})
    loy_progress = loy_count % loy_cfg["threshold"]
    return {
        "user_id": target["id"], "name": target.get("contact_name"), "email": target.get("email"),
        "pass_id": (best_pass or {}).get("id"), "pass_active": pass_active,
        "pass_ends_at": (best_pass or {}).get("ends_at"),
        "balance_uc": wallet.get("balance_uc", 0),
        "loyalty": {"count": loy_count, "progress": loy_progress,
                    "threshold": loy_cfg["threshold"],
                    "remaining": loy_cfg["threshold"] - loy_progress,
                    "bonus_uc": loy_cfg["bonus_uc"]},
    }


@pos_counter_router.post("/pos/counter-sale")
async def pos_counter_sale(body: CounterSaleBody, user: dict = Depends(get_current_user)):
    """Vente au comptoir : encaissement en espèces, CB, UC (CREDI'SCOP client) ou paiement combiné."""
    point = await _manager_point(user["id"])
    items = [CounterSaleItem(**i) for i in (body.items or []) if i.get("sku") and int(i.get("qty", 0)) > 0]
    if not items:
        raise HTTPException(status_code=400, detail="Aucun article à encaisser")
    skus = [i.sku for i in items]
    prods = await db.lolodrive_products.find(
        {"sku": {"$in": skus}, "is_active": {"$ne": False},
         "$or": [{"point_code": {"$exists": False}}, {"point_code": None},
                 {"point_code": point["code"], "status": "APPROVED"}]},
        {"_id": 0}).to_list(100)
    by_sku = {p["sku"]: p for p in prods}
    from favorite_promo_alerts import _active_discount_promos, _matches_product
    promos = await _active_discount_promos(db)
    lines, total, discount = [], 0, 0
    for it in items:
        p = by_sku.get(it.sku)
        if not p:
            continue
        stock = p.get("stock_qty")
        if stock is not None and stock < it.qty:
            raise HTTPException(status_code=400, detail=(
                f"Rupture de stock : \"{p['name']}\" — {stock} restant(s), impossible d'encaisser {it.qty}. "
                "Réassortissez le stock avant la vente."))
        unit = p.get("price_public_cents", 0)
        pct = max((pr.get("value_percent") or 0 for pr in promos if _matches_product(pr, p)), default=0) if promos else 0
        if pct:
            disc_unit = round(unit * (1 - pct / 100))
            discount += (unit - disc_unit) * it.qty
            unit = disc_unit
        total += unit * it.qty
        lines.append({"sku": p["sku"], "name": p["name"], "qty": it.qty,
                      "unit_cents": unit, "promo_percent": pct or None,
                      "tva_rate": float(p.get("tva_rate") or 8.5)})
    if not lines:
        raise HTTPException(status_code=400, detail="Articles introuvables au catalogue du relais")
    tva_total_cents = round(sum(
        l["unit_cents"] * l["qty"] * l["tva_rate"] / (100 + l["tva_rate"]) for l in lines))
    now = datetime.utcnow()
    # ----- Résolution du mode de paiement (CASH / CARD / UC / MIXED) -----
    method = (body.payment_method or "CASH").upper()
    if method not in ("CASH", "CARD", "UC", "MIXED"):
        method = "CASH"
    from lolodrive_helpers import get_or_create_wallet
    customer = client_wallet = None
    uc_paid, rest_method = 0, None
    if body.customer_user_id:
        customer = await db.users.find_one({"id": body.customer_user_id},
                                           {"_id": 0, "id": 1, "contact_name": 1, "email": 1})
    if method in ("UC", "MIXED"):
        if not customer:
            raise HTTPException(status_code=400, detail="Client PASS requis pour un paiement en UC (recherchez son code PASS ou email)")
        client_wallet = await get_or_create_wallet(customer["id"])
        uc_total = cents_to_uc(total)
        if method == "UC":
            uc_paid = uc_total
        else:
            uc_paid = min(max(int(body.uc_amount or 0), 0), uc_total)
            if uc_paid <= 0:
                raise HTTPException(status_code=400, detail="Montant UC invalide pour un paiement combiné")
            rest_method = "CARD" if (body.rest_method or "").upper() == "CARD" else "CASH"
            if uc_paid >= uc_total:
                method, uc_paid, rest_method = "UC", uc_total, None
        balance = client_wallet.get("balance_uc", 0)
        if balance < uc_paid:
            raise HTTPException(status_code=400, detail=(
                f"Solde CREDI'SCOP insuffisant : {balance} UC disponibles, {uc_paid} UC requis"))
    relay_qty = sum(l["qty"] for l in lines if by_sku.get(l["sku"], {}).get("point_code"))
    fee_rate = await get_relay_fee_uc() if relay_qty else 0
    relay_fee_uc = round(fee_rate * relay_qty, 2)
    if relay_fee_uc == int(relay_fee_uc):
        relay_fee_uc = int(relay_fee_uc)
    order = {
        "id": str(uuid.uuid4()),
        "order_number": f"LC-{now:%Y%m%d}-{str(uuid.uuid4())[:6].upper()}",
        "channel": "COUNTER",
        "fulfillment_type": "COUNTER",
        "lolo_point_id": point["id"],
        "user_id": (customer or {}).get("id"),
        "customer_name": (customer or {}).get("contact_name"),
        "items": lines,
        "subtotal_cents": total,
        "promo_discount_cents": discount,
        "tva_total_cents": tva_total_cents,
        "fees_cents": 0,
        "total_cents": total,
        "payment_method": method,
        "pay_with_uc": uc_paid > 0,
        "uc_paid": uc_paid or None,
        "uc_covered_cents": uc_paid * 10 if uc_paid else None,
        "rest_method": rest_method,
        "relay_fee_uc": relay_fee_uc,
        "operator_id": user["id"],
        "operator_name": user.get("contact_name") or user.get("email"),
        "status": "FULFILLED",
        "created_at": now, "updated_at": now, "paid_at": now, "fulfilled_at": now,
    }
    await db.lolodrive_orders.insert_one(order)
    # ----- Débit UC du CREDI'SCOP client (mise à jour automatique) -----
    client_balance_uc = None
    if uc_paid > 0 and client_wallet:
        await db.lolodrive_wallets.update_one(
            {"id": client_wallet["id"]}, {"$inc": {"balance_uc": -uc_paid}, "$set": {"updated_at": now}})
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": client_wallet["id"], "type": "DEBIT",
            "amount_uc": uc_paid, "reason": "COUNTER_SALE_UC",
            "order_number": order["order_number"], "created_at": now})
        fresh = await db.lolodrive_wallets.find_one({"id": client_wallet["id"]}, {"_id": 0, "balance_uc": 1})
        client_balance_uc = (fresh or {}).get("balance_uc")
        from uc_receipt_email import send_uc_receipt
        await send_uc_receipt(db, customer["id"], uc_paid, client_balance_uc, kind="DEBIT",
                              order_number=order["order_number"], point_name=point.get("name"),
                              context="Achat au comptoir payé en UC")
    # Fidélité : bonus UC automatique tous les 10 achats au comptoir du relais
    loyalty_bonus_uc = 0
    if customer:
        try:
            from loyalty_bonus import check_loyalty_bonus
            loyalty_bonus_uc = await check_loyalty_bonus(db, customer, point, order["order_number"])
            if loyalty_bonus_uc and client_balance_uc is not None:
                client_balance_uc = round(client_balance_uc + loyalty_bonus_uc, 2)
        except Exception as exc:
            logger.warning("Bonus fidélité : %s", exc)
    from pymongo import ReturnDocument
    for l in lines:
        res = await db.lolodrive_products.find_one_and_update(
            {"sku": l["sku"], "stock_qty": {"$ne": None}},
            [{"$set": {"stock_qty": {"$max": [0, {"$subtract": [{"$ifNull": ["$stock_qty", 0]}, l["qty"]]}]}}}],
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "stock_qty": 1})
        if res is not None:
            await log_stock_movement(l["sku"], l["name"], "SALE", -l["qty"],
                                     res["stock_qty"], point["code"], order["order_number"])
    order.pop("_id", None)
    order["point_name"] = point.get("name")
    balance_uc = None
    if relay_fee_uc > 0:
        owner_id = point.get("manager_user_id") or user["id"]
        wallet = await get_or_create_wallet(owner_id)
        old_balance = wallet.get("balance_uc", 0)
        await db.lolodrive_wallets.update_one(
            {"id": wallet["id"]}, {"$inc": {"balance_uc": -relay_fee_uc}, "$set": {"updated_at": now}})
        await db.lolodrive_wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "DEBIT",
            "amount_uc": relay_fee_uc, "reason": "RELAY_PRODUCT_FEE",
            "order_number": order["order_number"], "created_at": now})
        fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
        balance_uc = (fresh or {}).get("balance_uc")
        if old_balance >= 0 and balance_uc is not None and balance_uc < 0:
            try:
                await _notify_negative_balance(owner_id, point, balance_uc, relay_fee_uc, order["order_number"])
            except Exception as exc:
                logger.warning("Alerte CREDI'SCOP négatif : %s", exc)
    try:
        await _check_goal_reached(point)
    except Exception as exc:
        logger.warning("Vérif objectif atteint : %s", exc)
    return {"ok": True, "order_number": order["order_number"],
            "total_cents": total, "promo_discount_cents": discount,
            "relay_fee_uc": relay_fee_uc, "credi_scop_balance_uc": balance_uc,
            "payment_method": method, "uc_paid": uc_paid or None,
            "client_balance_uc": client_balance_uc,
            "loyalty_bonus_uc": loyalty_bonus_uc or None,
            "customer_name": (customer or {}).get("contact_name"), "order": order}


@pos_counter_router.get("/pos/counter-journal")
async def pos_counter_journal(user: dict = Depends(get_current_user)):
    """Journal de caisse du jour : totaux espèces / CB / UC des ventes au comptoir."""
    point = await _manager_point(user["id"])
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start}},
        {"_id": 0, "order_number": 1, "total_cents": 1, "payment_method": 1, "created_at": 1,
         "operator_name": 1, "uc_covered_cents": 1, "rest_method": 1, "uc_paid": 1, "customer_name": 1}
    ).sort("created_at", -1).to_list(300)
    cash, card, uc = split_totals(orders)
    by_op = {}
    for o in orders:
        name = o.get("operator_name") or "Gérant"
        e = by_op.setdefault(name, {"name": name, "count": 0, "cash_cents": 0, "card_cents": 0, "uc_cents": 0})
        c, cd, u = split_totals([o])
        e["count"] += 1
        e["cash_cents"] += c
        e["card_cents"] += cd
        e["uc_cents"] += u
    for e in by_op.values():
        e["total_cents"] = e["cash_cents"] + e["card_cents"] + e["uc_cents"]
    recharges = await db.counter_recharges.find(
        {"point_id": point["id"], "created_at": {"$gte": start}}, {"_id": 0}).sort("created_at", -1).to_list(200)
    rech = {"count": len(recharges),
            "cash_cents": sum(r["amount_cents"] for r in recharges if r.get("payment_method") == "CASH"),
            "card_cents": sum(r["amount_cents"] for r in recharges if r.get("payment_method") == "CARD"),
            "total_uc": sum(r.get("amount_uc", 0) for r in recharges)}
    return {"date": start.strftime("%d/%m/%Y"), "count": len(orders),
            "cash_cents": cash, "card_cents": card, "uc_cents": uc,
            "total_cents": cash + card + uc, "sales": orders, "recharges": rech,
            "by_operator": sorted(by_op.values(), key=lambda x: x["total_cents"], reverse=True)}


@pos_counter_router.get("/pos/counter-journal/export")
async def export_counter_journal(month: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Export CSV du journal de caisse du mois (comptabilité)."""
    point = await _manager_point(user["id"])
    now = datetime.utcnow()
    try:
        y, m = map(int, (month or now.strftime("%Y-%m")).split("-"))
        start = datetime(y, m, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format mois invalide (attendu : YYYY-MM)")
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0}).sort("created_at", 1).to_list(3000)
    rows = ["date;heure;numero;operateur;paiement;articles;remise_promo_eur;total_eur"]
    for o in orders:
        items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
        operator = o.get("operator_name") or "Gerant"
        rows.append(f"{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};{operator};{_pay_label(o)};"
                    f"\"{items}\";{(o.get('promo_discount_cents') or 0) / 100:.2f};{o.get('total_cents', 0) / 100:.2f}")
    cash, card, uc = split_totals(orders)
    rows += ["", f"TOTAL ESPECES;;;;;;;{cash / 100:.2f}", f"TOTAL CB;;;;;;;{card / 100:.2f}",
             f"TOTAL UC;;;;;;;{uc / 100:.2f}",
             f"TOTAL CAISSE;;;;;;;{(cash + card + uc) / 100:.2f}"]
    return PlainTextResponse(
        "\ufeff" + "\n".join(rows), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=caisse-{point['code']}-{y}-{m:02d}.csv"})


@pos_counter_router.get("/pos/top-products")
async def pos_top_products(days: int = 30, user: dict = Depends(get_current_user)):
    """Top des produits les plus vendus au comptoir du relais."""
    point = await _manager_point(user["id"])
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    agg = {}
    async for o in db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": since}},
            {"_id": 0, "items": 1}):
        for l in o.get("items", []):
            e = agg.setdefault(l["sku"], {"sku": l["sku"], "name": l["name"], "qty": 0, "revenue_cents": 0})
            e["qty"] += l.get("qty", 0)
            e["revenue_cents"] += l.get("unit_cents", 0) * l.get("qty", 0)
    top = sorted(agg.values(), key=lambda x: (x["qty"], x["revenue_cents"]), reverse=True)[:5]
    return {"days": days, "top": top}


@pos_counter_router.post("/pos/counter-sale/{order_id}/email-ticket")
async def email_counter_ticket(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Envoie le ticket de caisse d'une vente au comptoir par email."""
    email = ((payload or {}).get("email") or "").strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide")
    point = await _manager_point(user["id"])
    order = await db.lolodrive_orders.find_one(
        {"id": order_id, "channel": "COUNTER", "lolo_point_id": point["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Vente introuvable pour ce relais")
    from brevo_service import send_email, _wrap_html

    def _eu(l):
        ttc = l["unit_cents"] * l["qty"]
        rate = float(l.get("tva_rate") or 8.5)
        ht = round(ttc / (1 + rate / 100))
        return ttc, rate, ht

    def _row(l):
        _, rate, ht = _eu(l)
        promo = f" <span style='color:#b45309;font-size:11px'>-{l['promo_percent']:g}%</span>" if l.get("promo_percent") else ""
        return (f"<tr><td style='padding:4px 8px'>{l['qty']} × {l['name']}{promo} · TVA {rate:g}%</td>"
                f"<td style='padding:4px 8px;text-align:right'>{ht / 100:.2f} € HT</td></tr>")

    items = order.get("items", [])
    rows = "".join(_row(l) for l in items)
    total_ht = 0
    tva_by_rate = {}
    for l in items:
        ttc, rate, ht = _eu(l)
        total_ht += ht
        tva_by_rate[rate] = tva_by_rate.get(rate, 0) + (ttc - ht)
    tva_rows = "".join(
        f"<tr><td style='padding:3px 8px;color:#666'>TVA {rate:.2f} %</td>"
        f"<td style='padding:3px 8px;text-align:right;color:#666'>{tva / 100:.2f} €</td></tr>"
        for rate, tva in sorted(tva_by_rate.items()))
    discount = order.get("promo_discount_cents") or 0
    pay_fr = {"CARD": "carte bancaire", "UC": "UC — CREDI'SCOP",
              "MIXED": "paiement combiné UC + " + ("CB" if order.get("rest_method") == "CARD" else "espèces")
              }.get(order.get("payment_method"), "espèces")
    subject = f"🧾 Ticket de caisse — {order['order_number']} ({point['name']})"
    body = f"""
      <p><strong>{point['name']}</strong> — vente au comptoir du {order['created_at'].strftime('%d/%m/%Y %H:%M')}</p>
      <table style='width:100%;border-collapse:collapse;font-size:13px;border-top:1px dashed #ccc;border-bottom:1px dashed #ccc'>{rows}</table>
      <table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:6px'>
        <tr><td style='padding:3px 8px'><strong>Sous-total HT</strong></td>
        <td style='padding:3px 8px;text-align:right'><strong>{total_ht / 100:.2f} €</strong></td></tr>
        {tva_rows}
        {f"<tr><td style='padding:3px 8px;color:#b45309'>⚡ Remise promo (déjà déduite des lignes)</td><td style='padding:3px 8px;text-align:right;color:#b45309'>−{discount / 100:.2f} €</td></tr>" if discount else ''}
      </table>
      <p style='margin:10px 0 0;font-size:15px;border-top:1px dashed #ccc;padding-top:8px'>Montant TTC : <strong>{order['total_cents'] / 100:.2f} €</strong>
      ({pay_fr})</p>
      {f"<p style='margin:6px 0 0;font-size:12px;color:#b8860b'>🪙 Payé en UC : <strong>{order['uc_paid']} UC</strong> débités du CREDI'SCOP</p>" if order.get('uc_paid') else ''}
      {f"<p style='margin:6px 0 0;font-size:12px;color:#777'>Encaissé par : <strong>{order['operator_name']}</strong></p>" if order.get('operator_name') else ''}
      <p style='color:#999;font-size:11px;margin-top:12px'>Merci de votre visite — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(to_email=email, to_name=None, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Ticket {order['order_number']} — total {order['total_cents'] / 100:.2f} €.",
                     tags=["counter_ticket"])
    return {"ok": True, "sent_to": email}


class CounterRechargeBody(BaseModel):
    customer_user_id: str
    amount_uc: int
    payment_method: str = "CASH"


@pos_counter_router.post("/pos/counter-recharge")
async def pos_counter_recharge(body: CounterRechargeBody, user: dict = Depends(get_current_user)):
    """Recharge du CREDI'SCOP d'un client au comptoir (espèces ou CB encaissés par l'opérateur)."""
    point = await _manager_point(user["id"])
    if body.amount_uc < 1 or body.amount_uc > 100000:
        raise HTTPException(status_code=400, detail="Montant UC invalide (1 à 100000)")
    method = "CARD" if (body.payment_method or "").upper() == "CARD" else "CASH"
    customer = await db.users.find_one({"id": body.customer_user_id},
                                       {"_id": 0, "id": 1, "contact_name": 1, "email": 1})
    if not customer:
        raise HTTPException(status_code=404, detail="Client introuvable")
    from lolodrive_helpers import get_or_create_wallet
    wallet = await get_or_create_wallet(customer["id"])
    now = datetime.utcnow()
    ref = f"RC-{now:%Y%m%d}-{str(uuid.uuid4())[:6].upper()}"
    await db.lolodrive_wallets.update_one(
        {"id": wallet["id"]}, {"$inc": {"balance_uc": body.amount_uc}, "$set": {"updated_at": now}})
    await db.lolodrive_wallet_ledger.insert_one({
        "id": str(uuid.uuid4()), "wallet_id": wallet["id"], "type": "CREDIT",
        "amount_uc": body.amount_uc, "reason": "COUNTER_RECHARGE",
        "order_number": ref, "point_id": point["id"], "created_at": now})
    await db.counter_recharges.insert_one({
        "id": str(uuid.uuid4()), "ref": ref, "point_id": point["id"], "point_code": point["code"],
        "customer_user_id": customer["id"], "customer_name": customer.get("contact_name"),
        "amount_uc": body.amount_uc, "amount_cents": body.amount_uc * 10, "payment_method": method,
        "operator_id": user["id"], "operator_name": user.get("contact_name") or user.get("email"),
        "created_at": now})
    fresh = await db.lolodrive_wallets.find_one({"id": wallet["id"]}, {"_id": 0, "balance_uc": 1})
    new_balance = (fresh or {}).get("balance_uc")
    from uc_receipt_email import send_uc_receipt
    await send_uc_receipt(db, customer["id"], body.amount_uc, new_balance, kind="CREDIT",
                          order_number=ref, point_name=point.get("name"),
                          context=f"Recharge au comptoir ({'CB' if method == 'CARD' else 'espèces'})")
    return {"ok": True, "ref": ref, "amount_uc": body.amount_uc, "payment_method": method,
            "customer_name": customer.get("contact_name"), "client_balance_uc": new_balance}


@pos_counter_router.get("/manager/bonus-history")
async def manager_bonus_history(user: dict = Depends(get_current_user)):
    """Historique des primes UC « meilleur vendeur » offertes par le gérant."""
    from routes_pos_operators import _owned_point
    point = await _owned_point(user["id"])
    rewards = await db.bonus_rewards.find(
        {"point_id": point["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    op_ids = list({r.get("operator_id") for r in rewards if r.get("operator_id")})
    names = {}
    async for u in db.users.find({"id": {"$in": op_ids}}, {"_id": 0, "id": 1, "contact_name": 1, "email": 1}):
        names[u["id"]] = u.get("contact_name") or u.get("email")
    for r in rewards:
        r["operator_name"] = names.get(r.get("operator_id"), "Opérateur")
    return {"count": len(rewards),
            "total_uc": sum(r.get("amount_uc", 0) for r in rewards),
            "rewards": rewards}


@pos_counter_router.post("/admin/network-report/send")
async def admin_send_network_report(payload: Optional[dict] = None, admin: dict = Depends(require_admin)):
    """Déclenche l'envoi du rapport comptable consolidé réseau aux super admins (mois courant par défaut)."""
    from accountant_report import send_network_report
    now = datetime.utcnow()
    month = ((payload or {}).get("month") or now.strftime("%Y-%m")).strip()
    try:
        y, m = map(int, month.split("-"))
        start = datetime(y, m, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format mois invalide (attendu : YYYY-MM)")
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    sent = await send_network_report(db, start, end, month)
    return {"ok": True, "sent": sent, "month": month}
