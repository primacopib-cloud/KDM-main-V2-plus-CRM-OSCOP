"""Préavis tarifaire — changements de prix programmés avec information des membres 30 jours avant."""
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

price_schedule_router = APIRouter(prefix="/api/admin/plans/price-schedule", tags=["price-schedule"])

db = None
NOTICE_DAYS = 30


def set_price_schedule_database(database):
    global db
    db = database


class ScheduleBody(BaseModel):
    plan_id: str
    new_price_cents: int
    effective_date: str


@price_schedule_router.get("")
async def list_schedules(admin: dict = Depends(require_admin)):
    items = await db.scheduled_price_changes.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": items, "notice_days": NOTICE_DAYS}


@price_schedule_router.post("")
async def create_schedule(body: ScheduleBody, admin: dict = Depends(require_admin)):
    if body.new_price_cents <= 0:
        raise HTTPException(status_code=400, detail="Le nouveau tarif doit être positif")
    try:
        eff = date.fromisoformat(body.effective_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide (format AAAA-MM-JJ)")
    if eff <= date.today():
        raise HTTPException(status_code=400, detail="La date d'effet doit être future")
    plan = await db.subscription_plans.find_one({"$or": [{"id": body.plan_id}, {"slug": body.plan_id}]}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    if body.new_price_cents == plan.get("price_cents"):
        raise HTTPException(status_code=400, detail="Le nouveau tarif est identique au tarif actuel")
    await db.scheduled_price_changes.update_many(
        {"plan_id": plan["id"], "status": {"$in": ["scheduled", "notified"]}},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat(), "cancelled_by": "replaced"}})
    doc = {
        "id": str(uuid.uuid4()), "plan_id": plan["id"], "plan_slug": plan.get("slug"),
        "plan_name": plan.get("name"), "old_price_cents": plan.get("price_cents"),
        "new_price_cents": body.new_price_cents, "effective_date": eff.isoformat(),
        "status": "scheduled", "notice_sent_at": None, "applied_at": None,
        "created_by": admin.get("email"), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.scheduled_price_changes.insert_one({**doc})
    from consultation_audit import audit
    await audit("PLAN_PRICE_SCHEDULED", admin.get("email"), None, {
        "plan_name": plan.get("name"), "old_price_cents": plan.get("price_cents"),
        "new_price_cents": body.new_price_cents, "effective_date": eff.isoformat()})
    await process_scheduled_price_changes(db)
    fresh = await db.scheduled_price_changes.find_one({"id": doc["id"]}, {"_id": 0})
    return fresh or doc


@price_schedule_router.delete("/{schedule_id}")
async def cancel_schedule(schedule_id: str, admin: dict = Depends(require_admin)):
    sched = await db.scheduled_price_changes.find_one({"id": schedule_id})
    if not sched:
        raise HTTPException(status_code=404, detail="Programmation introuvable")
    if sched.get("status") == "applied":
        raise HTTPException(status_code=400, detail="Changement déjà appliqué — modifiez le tarif manuellement")
    await db.scheduled_price_changes.update_one({"id": schedule_id}, {"$set": {
        "status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": admin.get("email")}})
    from consultation_audit import audit
    await audit("PLAN_PRICE_SCHEDULE_CANCELLED", admin.get("email"), None, {
        "plan_name": sched.get("plan_name"), "effective_date": sched.get("effective_date")})
    return {"ok": True}


async def process_scheduled_price_changes(database) -> None:
    """Appelé par le scheduler : envoie les préavis J-30 et applique les changements arrivés à échéance."""
    today = date.today()
    pending = await database.scheduled_price_changes.find(
        {"status": {"$in": ["scheduled", "notified"]}}, {"_id": 0}).to_list(100)
    for s in pending:
        try:
            eff = date.fromisoformat(s["effective_date"])
            plan = await database.subscription_plans.find_one(
                {"id": s["plan_id"]}, {"_id": 0})
            if not plan:
                continue
            if today >= eff:
                await database.subscription_plans.update_one({"id": s["plan_id"]}, {"$set": {
                    "price_cents": s["new_price_cents"],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
                await database.scheduled_price_changes.update_one({"id": s["id"]}, {"$set": {
                    "status": "applied", "applied_at": datetime.now(timezone.utc).isoformat()}})
                from consultation_audit import audit
                await audit("PLAN_PRICE_CHANGED", "scheduler:preavis", None, {
                    "plan_id": s["plan_id"], "plan_name": s["plan_name"],
                    "old_price_cents": plan.get("price_cents"), "new_price_cents": s["new_price_cents"],
                    "old_price_eur": round((plan.get("price_cents") or 0) / 100, 2),
                    "new_price_eur": round(s["new_price_cents"] / 100, 2),
                    "scheduled": True, "effective_date": s["effective_date"]})
                from plan_price_alert import send_price_change_alerts
                await send_price_change_alerts(database, plan, plan.get("price_cents"), s["new_price_cents"])
                logger.info("Préavis tarifaire appliqué : %s → %s cents", s["plan_name"], s["new_price_cents"])
            elif s["status"] == "scheduled" and (eff - today).days <= NOTICE_DAYS:
                from plan_price_alert import send_price_notice_alerts
                await send_price_notice_alerts(database, plan, plan.get("price_cents"),
                                               s["new_price_cents"], s["effective_date"])
                await database.scheduled_price_changes.update_one({"id": s["id"]}, {"$set": {
                    "status": "notified", "notice_sent_at": datetime.now(timezone.utc).isoformat()}})
                from consultation_audit import audit
                await audit("PLAN_PRICE_NOTICE_SENT", "scheduler:preavis", None, {
                    "plan_name": s["plan_name"], "new_price_cents": s["new_price_cents"],
                    "effective_date": s["effective_date"]})
                logger.info("Préavis tarifaire J-%s envoyé : %s", (eff - today).days, s["plan_name"])
        except Exception as exc:
            logger.error("Traitement préavis %s échoué : %s", s.get("id"), exc)
