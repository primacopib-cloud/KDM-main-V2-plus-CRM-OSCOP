"""LOLODRIVE by O'SCOP — Gérant LOLO POINT routes (split from routes_lolodrive_oscoop.py)."""
import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from lolodrive_helpers import get_current_user, require_admin
from lolodrive_models import OrderStatus

logger = logging.getLogger(__name__)

lolodrive_manager_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE by O'SCOP"])

db = None

def set_lolodrive_manager_database(database):
    global db
    db = database

# =======================
# Gérant LOLO POINT — vue dédiée
# =======================

@lolodrive_manager_router.get("/manager/pro-status")
async def manager_pro_status(user: dict = Depends(get_current_user)):
    """Statut de l'abonnement Acheteur Pro du gérant (règle métier obligatoire)."""
    if user.get("role") == "OPERATEUR_POS":
        return {"pro_active": True, "org_name": None, "operator_exempt": True}
    membership = await db.org_memberships.find_one({"user_id": user["id"]})
    org = await db.orgs.find_one({"id": membership["org_id"]}, {"_id": 0, "status": 1, "legal_name": 1}) if membership else None
    sub = await db.subscriptions.find_one(
        {"org_id": membership["org_id"], "status": "ACTIVE"},
        {"_id": 0, "current_period_end": 1}) if membership else None
    active = bool(org and org.get("status") == "APPROVED" and sub)
    return {"pro_active": active,
            "org_name": (org or {}).get("legal_name"),
            "org_status": (org or {}).get("status"),
            "period_end": (sub or {}).get("current_period_end")}


@lolodrive_manager_router.get("/manager/my-point")
async def manager_my_point(user: dict = Depends(get_current_user)):
    """Retourne le LOLO POINT du gérant connecté (via manager_user_id)."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    return point


class RelayCalendarBody(BaseModel):
    pickup_days: List[int] = []    # 0=lundi … 6=dimanche ; vide = tous les jours
    delivery_days: List[int] = []
    closed_dates: List[str] = []   # fermetures exceptionnelles YYYY-MM-DD
    slot_capacity: int = 0         # commandes max par jour+créneau (retrait) ; 0 = illimité
    delivery_slot_capacity: Optional[int] = None  # capacité livraison distincte ; None = même que retrait


def _date_closed(date_str: str, weekday: int, days: List[int], closed: List[str]) -> bool:
    return (bool(days) and weekday not in days) or date_str in closed


@lolodrive_manager_router.put("/manager/my-point/calendar")
async def manager_update_calendar(body: RelayCalendarBody, user: dict = Depends(get_current_user)):
    """Le gérant programme jours de retrait/livraison, fermetures exceptionnelles et capacité par créneau."""
    for days in (body.pickup_days, body.delivery_days):
        if any(d < 0 or d > 6 for d in days):
            raise HTTPException(status_code=400, detail="Jours invalides (0=lundi à 6=dimanche)")
    closed_dates = []
    for d in body.closed_dates:
        try:
            closed_dates.append(datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Date de fermeture invalide : {d} (attendu YYYY-MM-DD)")
    if body.slot_capacity < 0:
        raise HTTPException(status_code=400, detail="La capacité doit être positive (0 = illimitée)")
    if body.delivery_slot_capacity is not None and body.delivery_slot_capacity < 0:
        raise HTTPException(status_code=400, detail="La capacité livraison doit être positive (0 = illimitée)")

    before = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    new_pickup, new_closed = sorted(set(body.pickup_days)), sorted(set(closed_dates))
    await db.lolodrive_points.update_one(
        {"manager_user_id": user["id"]},
        {"$set": {"pickup_days": new_pickup,
                  "delivery_days": sorted(set(body.delivery_days)),
                  "closed_dates": new_closed,
                  "slot_capacity": body.slot_capacity,
                  "delivery_slot_capacity": body.delivery_slot_capacity,
                  "updated_at": datetime.utcnow()}})
    notified = await _notify_calendar_change(before, new_pickup, new_closed)
    point = await db.lolodrive_points.find_one(
        {"manager_user_id": user["id"]},
        {"_id": 0, "pickup_days": 1, "delivery_days": 1, "closed_dates": 1,
         "slot_capacity": 1, "delivery_slot_capacity": 1})
    return {"ok": True, "members_notified": notified, **point}


async def _notify_calendar_change(point: dict, new_pickup_days: List[int], new_closed: List[str]) -> int:
    """Email aux membres dont une commande en cours tombe sur un jour désormais fermé."""
    old_days = point.get("pickup_days") or []
    old_closed = point.get("closed_dates") or []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point.get("id"), "pickup_date": {"$gte": today},
         "status": {"$nin": ["CANCELLED", "FULFILLED"]}},
        {"_id": 0, "id": 1, "order_number": 1, "user_id": 1, "pickup_date": 1,
         "pickup_slot_label": 1}).to_list(500)
    sent = 0
    for o in orders:
        d = o.get("pickup_date")
        try:
            wd = datetime.strptime(d, "%Y-%m-%d").weekday()
        except (ValueError, TypeError):
            continue
        was_closed = _date_closed(d, wd, old_days, old_closed)
        now_closed = _date_closed(d, wd, new_pickup_days, new_closed)
        if now_closed and not was_closed:
            u = await db.users.find_one({"id": o["user_id"]},
                                        {"_id": 0, "email": 1, "first_name": 1, "contact_name": 1})
            if not u or not u.get("email"):
                continue
            try:
                from brevo_service import send_email, _wrap_html
                name = u.get("first_name") or u.get("contact_name") or ""
                date_fr = "-".join(reversed(d.split("-")))
                subject = f"⚠️ Votre relais {point.get('name')} ferme le {date_fr}"
                body_html = (
                    f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                    f"<p style='font-size:14px;'>Le relais <b>{point.get('name')}</b> vient de modifier son calendrier : "
                    f"il sera <b>fermé le {date_fr}</b>, jour prévu pour le retrait de votre commande "
                    f"<b>{o.get('order_number')}</b>"
                    + (f" ({o.get('pickup_slot_label')})" if o.get("pickup_slot_label") else "") + ".</p>"
                    "<p style='font-size:14px;'>Merci de choisir une nouvelle date de retrait depuis votre espace, "
                    "ou de contacter directement votre relais.</p>"
                    "<p style='font-size:12px;color:#B8A98F;'>KDMARCHÉ × O'SCOP — LOLODRIVE</p>")
                await send_email(to_email=u["email"], to_name=name or None, subject=subject,
                                 html_content=_wrap_html(subject, body_html),
                                 text_content=f"Le relais {point.get('name')} sera fermé le {date_fr}, jour de retrait "
                                              f"de votre commande {o.get('order_number')}. Choisissez une nouvelle date.",
                                 tags=["relay-calendar-change"])
                sent += 1
            except Exception as exc:
                logger.warning("Email changement calendrier %s : %s", o.get("order_number"), exc)
    if sent:
        logger.info("Changement calendrier %s : %s membre(s) prévenu(s)", point.get("code"), sent)
    return sent


@lolodrive_manager_router.post("/manager/my-point/photo")
async def upload_my_point_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Le gérant téléverse la photo de devanture de son relais (jpg/png/webp, 4 Mo max)."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]})
    if not point:
        raise HTTPException(status_code=403, detail="Aucun relais géré par ce compte")
    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(status_code=400, detail="Format non supporté (jpg, png, webp)")
    data = await file.read()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 4 Mo)")
    fname = f"relay-{point['code'].lower()}-{uuid.uuid4().hex[:8]}.{ext}"
    from upload_storage import save_upload, mime_for_ext
    url = await save_upload(f"relays/{fname}", data, mime_for_ext(ext))
    await db.lolodrive_points.update_one({"id": point["id"]}, {"$set": {"photo_url": url, "updated_at": datetime.utcnow()}})
    return {"ok": True, "photo_url": url}


@lolodrive_manager_router.get("/manager/my-orders")
async def manager_my_orders(order_status: Optional[str] = None, user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    q = {"lolo_point_id": point["id"]}
    if order_status:
        q["status"] = order_status
    orders = await db.lolodrive_orders.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"point": point, "orders": orders}


@lolodrive_manager_router.get("/manager/planning")
async def manager_planning(week_start: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Planning hebdomadaire du relais : commandes actives agrégées par jour et créneau."""
    from datetime import timezone
    from routes_lolodrive_taxonomy import get_fees_config_doc
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point and user.get("role") == "OPERATEUR_POS":
        u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "pos_point_id": 1})
        if u and u.get("pos_point_id"):
            point = await db.lolodrive_points.find_one({"id": u["pos_point_id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    if week_start:
        try:
            start = datetime.strptime(week_start, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="week_start invalide (attendu YYYY-MM-DD)")
    else:
        start = datetime.now(timezone.utc).date()
    start = start - timedelta(days=start.weekday())  # normalisé au lundi
    end = start + timedelta(days=6)

    cfg = await get_fees_config_doc()
    ref_slots = cfg.get("pickup_slots") or cfg.get("delivery_slots") or []
    slot_ids = [s["id"] for s in ref_slots]

    orders = await db.lolodrive_orders.find(
        {"$or": [{"lolo_point_id": point["id"]}, {"reference_point_id": point["id"]}],
         "pickup_date": {"$gte": start.strftime("%Y-%m-%d"), "$lte": end.strftime("%Y-%m-%d")},
         "status": {"$in": ["PAID", "PREPARING", "READY"]}},
        {"_id": 0, "id": 1, "order_number": 1, "user_id": 1, "status": 1, "fulfillment_type": 1,
         "pickup_date": 1, "pickup_slot_id": 1, "total_cents": 1, "items": 1}).to_list(1000)

    user_ids = list({o["user_id"] for o in orders if o.get("user_id")})
    users = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}},
                                     {"_id": 0, "id": 1, "first_name": 1, "contact_name": 1, "email": 1}):
            users[u["id"]] = u.get("first_name") or u.get("contact_name") or u.get("email") or "Client"

    pickup_cap = int(point.get("slot_capacity") or 0)
    d_raw = point.get("delivery_slot_capacity")
    delivery_cap = int(d_raw) if d_raw is not None else pickup_cap
    distinct_caps = d_raw is not None
    pickup_days = point.get("pickup_days") or []
    delivery_days = point.get("delivery_days") or []
    closed = point.get("closed_dates") or []

    by_cell: Dict[Any, list] = {}
    for o in orders:
        key = (o.get("pickup_date"), o.get("pickup_slot_id") or "?")
        by_cell.setdefault(key, []).append({
            "id": o["id"], "order_number": o.get("order_number"), "status": o.get("status"),
            "fulfillment_type": o.get("fulfillment_type") or "DRIVE",
            "customer": users.get(o.get("user_id"), "Client"),
            "items_count": sum(int(i.get("qty", 1)) for i in (o.get("items") or [])),
            "total_cents": o.get("total_cents", 0),
        })

    days_out = []
    for i in range(7):
        d = start + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        wd = d.weekday()
        slots_out = {}
        for sid in slot_ids:
            cell = by_cell.get((ds, sid), [])
            pc = sum(1 for o in cell if o["fulfillment_type"] != "DELIVERY")
            dc = len(cell) - pc
            if distinct_caps:
                full = bool((pickup_cap and pc >= pickup_cap) or (delivery_cap and dc >= delivery_cap))
            else:
                full = bool(pickup_cap and len(cell) >= pickup_cap)
            slots_out[sid] = {
                "count": len(cell),
                "pickup_count": pc,
                "delivery_count": dc,
                "capacity": pickup_cap or None,
                "pickup_capacity": pickup_cap or None,
                "delivery_capacity": delivery_cap or None,
                "distinct_capacities": distinct_caps,
                "full": full,
                "orders": cell,
            }
        days_out.append({
            "date": ds, "weekday": wd,
            "pickup_open": not _date_closed(ds, wd, pickup_days, closed),
            "delivery_open": not _date_closed(ds, wd, delivery_days, closed),
            "closed": ds in closed,
            "slots": slots_out,
        })

    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "week_end": end.strftime("%Y-%m-%d"),
        "point": {"id": point["id"], "name": point["name"], "code": point["code"]},
        "capacity": pickup_cap,
        "delivery_capacity": delivery_cap,
        "distinct_capacities": distinct_caps,
        "slots": [{"id": s["id"], "label": s.get("label", s["id"])} for s in ref_slots],
        "days": days_out,
    }


@lolodrive_manager_router.get("/manager/affluence")
async def manager_affluence(days: int = 90, user: dict = Depends(get_current_user)):
    """Heatmap d'affluence : commandes servies par jour de semaine × créneau sur N jours."""
    from datetime import timezone
    from routes_lolodrive_taxonomy import get_fees_config_doc
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    days = max(7, min(days, 365))
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    cfg = await get_fees_config_doc()
    ref_slots = cfg.get("pickup_slots") or cfg.get("delivery_slots") or []
    slot_ids = [s["id"] for s in ref_slots]

    grid = {(wd, sid): 0 for wd in range(7) for sid in slot_ids}
    async for o in db.lolodrive_orders.find(
            {"$or": [{"lolo_point_id": point["id"]}, {"reference_point_id": point["id"]}],
             "pickup_date": {"$gte": start, "$lte": today.strftime("%Y-%m-%d")},
             "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]}},
            {"_id": 0, "pickup_date": 1, "pickup_slot_id": 1}):
        try:
            wd = datetime.strptime(o.get("pickup_date") or "", "%Y-%m-%d").weekday()
        except ValueError:
            continue
        sid = o.get("pickup_slot_id")
        if sid in slot_ids:
            grid[(wd, sid)] += 1

    cells = [{"weekday": wd, "slot_id": sid, "count": grid[(wd, sid)]} for wd in range(7) for sid in slot_ids]
    counts = [c["count"] for c in cells]
    return {
        "days": days,
        "since": start,
        "point": {"id": point["id"], "name": point["name"], "code": point["code"]},
        "slots": [{"id": s["id"], "label": s.get("label", s["id"])} for s in ref_slots],
        "cells": cells,
        "max": max(counts) if counts else 0,
        "total": sum(counts),
    }


class RemindResult(BaseModel):
    ok: bool
    channel: str


@lolodrive_manager_router.post("/manager/orders/{order_id}/remind")
async def manager_remind_order(order_id: str, user: dict = Depends(get_current_user)):
    """Relance le client d'une commande prête non retirée (SMS Brevo, fallback email)."""
    from datetime import timezone
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    order = await db.lolodrive_orders.find_one(
        {"id": order_id,
         "$or": [{"lolo_point_id": point["id"]}, {"reference_point_id": point["id"]}]},
        {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable sur votre relais")
    if order.get("status") != "READY":
        raise HTTPException(status_code=409, detail="Seules les commandes prêtes peuvent être relancées")
    now = datetime.now(timezone.utc)
    last = order.get("last_pickup_reminder_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if (now - last_dt).total_seconds() < 4 * 3600:
                raise HTTPException(status_code=429, detail="Client déjà relancé il y a moins de 4 h")
        except ValueError:
            pass
    client = await db.users.find_one({"id": order.get("user_id")},
                                     {"_id": 0, "email": 1, "phone": 1, "first_name": 1, "contact_name": 1})
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    first = client.get("first_name") or client.get("contact_name") or ""
    from brevo_service import send_sms, send_email, _wrap_html
    is_delivery = order.get("fulfillment_type") == "DELIVERY"
    channel = "none"
    if client.get("phone"):
        msg = (f"LOLODRIVE : bonjour {first}, votre commande {order.get('order_number')} "
               f"{'sera livree' if is_delivery else 'vous attend'} au relais {point['name']}. "
               f"{'Merci de vous rendre disponible.' if is_delivery else 'Pensez a la retirer !'}")
        res = await send_sms(client["phone"], msg, tag="lolodrive-pickup-reminder")
        if res:
            channel = "sms"
    if channel == "none" and client.get("email"):
        body = (f"<p>Bonjour {first},</p>"
                f"<p>Votre commande <strong>{order.get('order_number')}</strong> est prête au relais "
                f"<strong>{point['name']}</strong>. Pensez à la {'réceptionner' if is_delivery else 'retirer'} !</p>")
        await send_email(client["email"], first or None, "Votre commande LOLODRIVE vous attend",
                         _wrap_html("Commande à retirer", body), tags=["lolodrive-pickup-reminder"])
        channel = "email"
    if channel == "none":
        raise HTTPException(status_code=422, detail="Client sans téléphone ni email")
    await db.lolodrive_orders.update_one(
        {"id": order_id}, {"$set": {"last_pickup_reminder_at": now.isoformat()}})
    return RemindResult(ok=True, channel=channel)


@lolodrive_manager_router.get("/manager/my-payout-preview")
async def manager_my_payout_preview(user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=30)
    # Reuse existing payout calculation logic
    return await payout_preview_compute(point["id"], from_date, to_date)


@lolodrive_manager_router.get("/manager/my-timeseries")
async def manager_my_timeseries(days: int = 30, user: dict = Depends(get_current_user)):
    """Série temporelle quotidienne du Lolo Point du gérant : commandes + CA + retraits."""
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    days = max(7, min(days, 90))
    to_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
    from_date = (to_date - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "lolo_point_id": point["id"],
            "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
            "created_at": {"$gte": from_date, "$lte": to_date},
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "orders": {"$sum": 1},
            "revenue_cents": {"$sum": "$subtotal_cents"},
            "fulfilled": {"$sum": {"$cond": [{"$eq": ["$status", "FULFILLED"]}, 1, 0]}},
        }},
    ]
    rows = await db.lolodrive_orders.aggregate(pipeline).to_list(1000)
    by_day = {r["_id"]: r for r in rows}
    series = []
    cursor = from_date
    while cursor.date() <= to_date.date():
        key = cursor.strftime("%Y-%m-%d")
        r = by_day.get(key, {})
        series.append({
            "date": key,
            "orders": r.get("orders", 0),
            "revenue_cents": r.get("revenue_cents", 0),
            "fulfilled": r.get("fulfilled", 0),
        })
        cursor += timedelta(days=1)
    return {"point": {"id": point["id"], "name": point["name"], "code": point["code"]}, "days": days, "series": series}


@lolodrive_manager_router.get("/manager/network-ranking")
async def manager_network_ranking(days: int = 30, user: dict = Depends(get_current_user)):
    """Classement de tous les Lolo Points actifs par chiffre d'affaires sur N jours, et rang du gérant connecté."""
    days = max(7, min(days, 90))
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=days)
    points = await db.lolodrive_points.find({"status": "ACTIVE"}, {"_id": 0}).to_list(500)
    ids = [p["id"] for p in points]
    pipeline = [
        {"$match": {
            "lolo_point_id": {"$in": ids},
            "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
            "created_at": {"$gte": from_date, "$lte": to_date},
        }},
        {"$group": {
            "_id": "$lolo_point_id",
            "orders": {"$sum": 1},
            "revenue_cents": {"$sum": "$subtotal_cents"},
            "fulfilled": {"$sum": {"$cond": [{"$eq": ["$status", "FULFILLED"]}, 1, 0]}},
        }},
    ]
    by_id = {r["_id"]: r for r in await db.lolodrive_orders.aggregate(pipeline).to_list(1000)}
    enriched = []
    for p in points:
        s = by_id.get(p["id"], {})
        enriched.append({
            "point_id": p["id"],
            "code": p["code"],
            "name": p["name"],
            "territory": p.get("territory"),
            "city": p.get("city"),
            "orders": s.get("orders", 0),
            "revenue_cents": s.get("revenue_cents", 0),
            "fulfilled": s.get("fulfilled", 0),
        })
    enriched.sort(key=lambda x: (x["revenue_cents"], x["orders"]), reverse=True)
    for i, e in enumerate(enriched):
        e["rank"] = i + 1
    my_point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]}, {"_id": 0})
    my_rank = next((e for e in enriched if my_point and e["point_id"] == my_point.get("id")), None)
    return {
        "days": days,
        "ranking": enriched,
        "my_rank": my_rank,
        "total_points": len(enriched),
    }


async def payout_preview_compute(point_id: str, from_date: datetime, to_date: datetime) -> dict:
    """Re-usable payout preview computation."""
    point = await db.lolodrive_points.find_one({"id": point_id})
    if not point:
        raise HTTPException(status_code=404, detail="Point introuvable")
    orders = await db.lolodrive_orders.find({
        "lolo_point_id": point_id,
        "status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]},
        "created_at": {"$gte": from_date, "$lte": to_date},
    }, {"_id": 0}).to_list(2000)
    consumption_volume_cents = sum(o.get("subtotal_cents", 0) for o in orders)
    withdrawals = sum(1 for o in orders if o.get("status") == "FULFILLED")
    pass_activations = await db.lolodrive_passes.count_documents({
        "source_lolo_point_id": point_id,
        "starts_at": {"$gte": from_date, "$lte": to_date},
    })
    withdrawal_commission = withdrawals * point.get("withdrawal_commission_cents", 70)
    pass_commission = pass_activations * point.get("pass_activation_commission_cents", 400)
    volume_commission = int(consumption_volume_cents * (point.get("essential_volume_bps", 200) / 10000))
    calculated = withdrawal_commission + pass_commission + volume_commission
    percent_cap = int(consumption_volume_cents * (point.get("payout_cap_percent_bps", 600) / 10000))
    monthly_cap = point.get("payout_cap_cents_monthly", 120000)
    capped = min(calculated, percent_cap, monthly_cap)
    return {
        "point_id": point_id,
        "from_date": from_date,
        "to_date": to_date,
        "consumption_volume_cents": consumption_volume_cents,
        "withdrawals": withdrawals,
        "pass_activations": pass_activations,
        "components": {
            "withdrawal_commission_cents": withdrawal_commission,
            "pass_commission_cents": pass_commission,
            "volume_commission_cents": volume_commission,
        },
        "calculated_cents": calculated,
        "caps": {"percent_cap_cents": percent_cap, "monthly_cap_cents": monthly_cap},
        "capped_cents": capped,
    }


# =======================
# Reporting timeseries
# =======================

@lolodrive_manager_router.get("/admin/kpi/timeseries")
async def admin_kpi_timeseries(metric: str = "revenue", days: int = 30, admin: dict = Depends(require_admin)):
    """Daily aggregation for charts. metric: revenue|orders|uc_consumed|pass_activations"""
    days = min(max(days, 7), 365)
    from_date = datetime.utcnow() - timedelta(days=days)
    paid_statuses = [OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.READY.value, OrderStatus.FULFILLED.value]
    points = []
    if metric == "revenue":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": paid_statuses}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": "$total_cents"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "orders":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": paid_statuses}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "uc_consumed":
        rows = await db.lolodrive_wallet_ledger.aggregate([
            {"$match": {"type": "DEBIT", "created_at": {"$gte": from_date}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": "$amount_uc"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    elif metric == "pass_activations":
        rows = await db.lolodrive_passes.aggregate([
            {"$match": {"starts_at": {"$gte": from_date}, "status": "ACTIVE"}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$starts_at"}}, "value": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
        points = [{"date": r["_id"], "value": r["value"]} for r in rows]
    else:
        raise HTTPException(status_code=400, detail="metric invalide")
    return {"metric": metric, "days": days, "points": points}

