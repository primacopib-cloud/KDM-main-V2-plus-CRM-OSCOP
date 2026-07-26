"""Plans du PASS LOLODRIVE (adhésion + recharges UC) : public + gestion super admin."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

pass_plans_router = APIRouter(prefix="/api", tags=["pass-plans"])

db = None


def set_pass_plans_database(database):
    global db
    db = database


DEFAULT_PLANS = [
    {"id": "pass-adhesion", "kind": "adhesion", "label": "Adhésion PASS LOLODRIVE",
     "price_eur": 60, "uc": 600, "bonus_uc": 0, "active": True, "sort": 0},
    {"id": "recharge-10", "kind": "recharge", "label": "Recharge 10 €",
     "price_eur": 10, "uc": 100, "bonus_uc": 0, "active": True, "sort": 1},
    {"id": "recharge-25", "kind": "recharge", "label": "Recharge 25 €",
     "price_eur": 25, "uc": 250, "bonus_uc": 0, "active": True, "sort": 2},
    {"id": "recharge-100", "kind": "recharge", "label": "Recharge 100 €",
     "price_eur": 100, "uc": 1000, "bonus_uc": 200, "active": True, "sort": 3},
]


async def _ensure_seed():
    if await db.pass_plans.count_documents({}) == 0:
        await db.pass_plans.insert_many([dict(p) for p in DEFAULT_PLANS])
        logger.info("Plans PASS LOLODRIVE initialisés (%d)", len(DEFAULT_PLANS))


async def _active_recharge_boost():
    """Meilleure promo bonus_purchase active applicable au PASS → % de boost des UC bonus."""
    now = datetime.now(timezone.utc).isoformat()
    promos = await db.credit_promotions.find({
        "promo_type": "bonus_purchase", "active": True, "archived": {"$ne": True},
        "scope_profile": {"$in": ["all", "pass"]},
    }, {"_id": 0, "name": 1, "value_percent": 1, "starts_at": 1, "ends_at": 1, "audience": 1}).to_list(20)
    promos = [p for p in promos
              if (not p.get("starts_at") or p["starts_at"] <= now)
              and (not p.get("ends_at") or p["ends_at"] >= now)
              and p.get("audience", "all") != "emails"]
    return max(promos, key=lambda p: p["value_percent"], default=None)


@pass_plans_router.get("/public/pass-plans")
async def public_pass_plans():
    await _ensure_seed()
    adhesion = await db.pass_plans.find_one({"kind": "adhesion", "active": True}, {"_id": 0})
    recharges = await db.pass_plans.find(
        {"kind": "recharge", "active": True}, {"_id": 0}).sort("sort", 1).to_list(20)
    boost = await _active_recharge_boost()
    if boost:
        for r in recharges:
            r["promo_extra_uc"] = round(r["uc"] * boost["value_percent"] / 100)
            r["promo_name"] = boost["name"]
            r["promo_ends_at"] = boost.get("ends_at")
    return {"adhesion": adhesion, "recharges": recharges,
            "boost": {"name": boost["name"], "percent": boost["value_percent"], "ends_at": boost.get("ends_at")} if boost else None}


class PlanBody(BaseModel):
    label: str = ""
    price_eur: float
    uc: int
    bonus_uc: int = 0
    active: bool = True


@pass_plans_router.get("/admin/pass-plans")
async def admin_pass_plans(admin: dict = Depends(require_admin)):
    await _ensure_seed()
    plans = await db.pass_plans.find({}, {"_id": 0}).sort("sort", 1).to_list(50)
    return {"plans": plans}


@pass_plans_router.post("/admin/pass-plans")
async def create_pass_plan(body: PlanBody, admin: dict = Depends(require_admin)):
    if body.price_eur <= 0 or body.uc <= 0 or body.bonus_uc < 0:
        raise HTTPException(status_code=400, detail="Valeurs invalides")
    last = await db.pass_plans.find({}, {"_id": 0, "sort": 1}).sort("sort", -1).to_list(1)
    plan = {"id": str(uuid.uuid4()), "kind": "recharge",
            "label": body.label.strip() or f"Recharge {body.price_eur:g} €",
            "price_eur": body.price_eur, "uc": body.uc, "bonus_uc": body.bonus_uc,
            "active": body.active, "sort": (last[0]["sort"] + 1) if last else 1,
            "created_at": datetime.now(timezone.utc).isoformat()}
    await db.pass_plans.insert_one(dict(plan))
    return {"ok": True, "plan": plan}


@pass_plans_router.patch("/admin/pass-plans/{plan_id}")
async def update_pass_plan(plan_id: str, body: PlanBody, admin: dict = Depends(require_admin)):
    if body.price_eur <= 0 or body.uc <= 0 or body.bonus_uc < 0:
        raise HTTPException(status_code=400, detail="Valeurs invalides")
    upd = {"price_eur": body.price_eur, "uc": body.uc, "bonus_uc": body.bonus_uc,
           "active": body.active, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.label.strip():
        upd["label"] = body.label.strip()
    res = await db.pass_plans.update_one({"id": plan_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    return {"ok": True}


@pass_plans_router.delete("/admin/pass-plans/{plan_id}")
async def delete_pass_plan(plan_id: str, admin: dict = Depends(require_admin)):
    plan = await db.pass_plans.find_one({"id": plan_id}, {"_id": 0, "kind": 1})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    if plan["kind"] == "adhesion":
        raise HTTPException(status_code=400, detail="Le plan d'adhésion ne peut pas être supprimé")
    await db.pass_plans.delete_one({"id": plan_id})
    return {"ok": True}
