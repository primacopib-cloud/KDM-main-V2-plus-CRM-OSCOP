"""Espace COOPER — adhésions en attente, transporteurs LOGI'SCOP et assignation."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth import get_current_user_id
from admin_guard import require_admin, require_cooper

logger = logging.getLogger(__name__)

cooper_router = APIRouter(prefix="/api/cooper", tags=["Espace COOPER"])

db = None


def set_cooper_database(database) -> None:
    global db
    db = database


@cooper_router.get("/adhesions")
async def list_pending_adhesions(user_id: str = Depends(get_current_user_id)):
    await require_cooper(user_id)
    apps = await db.b2b_applications.find(
        {"status": "PENDING_REVIEW"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for a in apps:
        org = await db.orgs.find_one({"id": a["org_id"]}, {"_id": 0})
        a["org"] = {
            "legal_name": (org or {}).get("legal_name"),
            "registration_id": (org or {}).get("registration_id"),
            "territory": (org or {}).get("territory"),
            "member_type": (org or {}).get("member_type", "BUYER_PRO"),
        }
    return {"applications": apps, "count": len(apps)}


@cooper_router.get("/purchase-needs")
async def list_assigned_purchase_needs(user_id: str = Depends(get_current_user_id)):
    """Besoins d'achat assignés au COOPER'S connecté."""
    await require_cooper(user_id)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    email = (user or {}).get("email", "").lower()
    needs = await db.purchase_needs.find(
        {"assigned_vendor": email}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for n in needs:
        n["photos"] = n.get("photos") or []
        n["joiners_count"] = len(n.get("joiners") or [])
    return {"needs": needs, "count": len(needs)}


class CooperNeedResponse(BaseModel):
    price_eur: float = Field(gt=0)
    delay_days: Optional[int] = None
    note: Optional[str] = None


@cooper_router.post("/purchase-needs/{need_id}/respond")
async def cooper_respond_need(need_id: str, body: CooperNeedResponse, user_id: str = Depends(get_current_user_id)):
    """Le COOPER'S répond à un besoin assigné : offre de prix + délai."""
    await require_cooper(user_id)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
    email = (user or {}).get("email", "").lower()
    need = await db.purchase_needs.find_one({"id": need_id, "assigned_vendor": email}, {"_id": 0})
    if not need:
        raise HTTPException(status_code=404, detail="Besoin introuvable ou non assigné à ce COOPER'S")
    now = datetime.now(timezone.utc).isoformat()
    await db.purchase_needs.update_one({"id": need_id}, {"$set": {
        "status": "VENDOR_ACCEPTED", "vendor_price_eur": body.price_eur,
        "vendor_delay_days": body.delay_days, "vendor_note": body.note,
        "vendor_responded_at": now}})
    try:
        import os
        from brevo_service import send_email, _wrap_html
        base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
        delay_txt = f" · Délai : {body.delay_days} jours" if body.delay_days else ""
        html = _wrap_html("Offre reçue", (
            f"<p style='font-size:14px;'>Bonne nouvelle ! Un COOPER'S de la Centrale O'SCOP propose "
            f"<b style='font-size:16px;'>{body.price_eur:,.0f} €</b>{delay_txt} pour "
            f"<b>{need['reference']} — {need['product']}</b>."
            + (f"<br/>Note : {body.note}" if body.note else "") + "</p>"
            f"<p style='text-align:center;'><a href='{base}/api/public/purchase-needs/accept-offer/{need['reference']}' "
            "style='display:inline-block;background:#8CC63E;color:#1F0A33;font-weight:bold;"
            "padding:12px 26px;border-radius:12px;text-decoration:none;'>Accepter l'offre</a></p>").replace(",", " "))
        recipients = [need.get("email")] + [j.get("email") for j in (need.get("joiners") or [])]
        for to in {r.lower() for r in recipients if r}:
            try:
                await send_email(to_email=to, to_name=None,
                                 subject=f"💼 Offre COOPER'S reçue — {need['reference']}",
                                 html_content=html, tags=["purchase-need"])
            except Exception:
                pass
    except Exception:
        logger.warning("Emails offre COOPER non envoyés")
    return {"status": "VENDOR_ACCEPTED", "price_eur": body.price_eur}


# ============== TRANSPORTEURS LOGI'SCOP ==============

class CarrierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    territory: str = Field(..., min_length=2)


class CarrierUpdate(BaseModel):
    is_active: Optional[bool] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@cooper_router.get("/carriers")
async def list_carriers(user_id: str = Depends(get_current_user_id)):
    await require_cooper(user_id)
    carriers = await db.logiscop_carriers.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return {"carriers": carriers}


@cooper_router.post("/carriers")
async def create_carrier(carrier: CarrierCreate, user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    doc = carrier.dict()
    doc.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": datetime.utcnow()})
    await db.logiscop_carriers.insert_one(doc)
    doc.pop("_id", None)
    return doc


@cooper_router.patch("/carriers/{carrier_id}")
async def update_carrier(carrier_id: str, update: CarrierUpdate, user_id: str = Depends(get_current_user_id)):
    await require_admin(user_id)
    fields = {k: v for k, v in update.dict().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Aucune modification")
    res = await db.logiscop_carriers.update_one({"id": carrier_id}, {"$set": fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    return {"ok": True}


class CarrierAssign(BaseModel):
    carrier_id: str


@cooper_router.post("/orders/{order_id}/assign-carrier")
async def assign_carrier(order_id: str, payload: CarrierAssign, user_id: str = Depends(get_current_user_id)):
    user = await require_cooper(user_id)
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    carrier = await db.logiscop_carriers.find_one({"id": payload.carrier_id, "is_active": True}, {"_id": 0})
    if not carrier:
        raise HTTPException(status_code=404, detail="Transporteur introuvable ou inactif")
    mission_token = str(uuid.uuid4())
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "carrier": {"id": carrier["id"], "name": carrier["name"], "territory": carrier.get("territory")},
            "carrier_assigned_at": datetime.utcnow(),
            "carrier_assigned_by": user.get("email"),
            "carrier_mission_token": mission_token,
            "carrier_pickup_confirmed_at": None,
            "carrier_delivery_confirmed_at": None,
            "updated_at": datetime.utcnow(),
        }}
    )
    logger.info("Carrier %s assigned to order %s by %s", carrier["name"], order_id, user.get("email"))

    # Notification Brevo au transporteur avec le détail de l'enlèvement
    if carrier.get("contact_email"):
        try:
            import brevo_service
            from brevo_service import _wrap_html
            pickup = await db.pickup_locations.find_one({"id": order.get("pickup_location_id")}, {"_id": 0}) or {}
            items_rows = "".join(
                f"<tr><td style='padding:6px 10px;color:rgba(255,255,255,0.85);font-size:13px;'>{i['product_name']}</td>"
                f"<td style='padding:6px 10px;color:rgba(255,255,255,0.6);font-size:13px;'>{i['quantity']} × {i['unit']}</td></tr>"
                for i in order.get("items", [])
            )
            import os as _os
            _base = (_os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
            mission_url = f"{_base}/api/cooper/mission/{mission_token}"
            body = f"""
              <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Nouvelle mission de transport LOGI'SCOP</h2>
              <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
                Bonjour {carrier.get('contact_name') or carrier['name']},<br/><br/>
                La commande <strong>{order.get('order_number', order_id)}</strong> vous a été assignée par la coopérative.
              </p>
              <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
                <strong>Enlèvement (EXW) :</strong> {pickup.get('name') or 'Point de retrait coopératif'}
                {f"— {pickup.get('address')}" if pickup.get('address') else ''} ({order.get('zone_code')})<br/>
                <strong>Articles :</strong> {order.get('items_count', len(order.get('items', [])))} ligne(s) —
                <strong>Total :</strong> {order.get('total_ttc_cents', 0) / 100:.2f} € TTC
              </p>
              <table style=\"width:100%;border-collapse:collapse;background:rgba(255,255,255,0.05);border-radius:12px;\">{items_rows}</table>
              <p style=\"text-align:center;margin:20px 0;\">
                <a href=\"{mission_url}\" style=\"display:inline-block;background:#D9B35A;color:#111;font-weight:bold;padding:12px 24px;border-radius:12px;text-decoration:none;\">
                  Suivre la mission — confirmer l'enlèvement et la livraison
                </a>
              </p>
              <p style=\"color:rgba(255,255,255,0.55);font-size:12px;margin-top:14px;\">Merci de confirmer la prise en charge auprès de la coopérative.</p>
            """
            await brevo_service.send_email(
                to_email=carrier["contact_email"], to_name=carrier.get("contact_name") or carrier["name"],
                subject=f"[LOGI'SCOP] Mission de transport — commande {order.get('order_number', order_id)}",
                html_content=_wrap_html("Mission de transport", body),
                tags=["carrier-assignment"],
            )
            logger.info("Carrier notification sent to %s", carrier["contact_email"])
        except Exception as e:
            logger.error("Carrier notification failed: %s", e)

    return {"ok": True, "carrier": carrier["name"]}


# ============== SUIVI DE MISSION TRANSPORTEUR (liens publics tokenisés) ==============

@cooper_router.get("/mission/{token}")
async def get_mission(token: str):
    order = await db.orders.find_one({"carrier_mission_token": token}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    pickup = await db.pickup_locations.find_one({"id": order.get("pickup_location_id")}, {"_id": 0}) or {}
    return {
        "order_number": order.get("order_number"),
        "zone_code": order.get("zone_code"),
        "carrier_name": (order.get("carrier") or {}).get("name"),
        "pickup_location": {"name": pickup.get("name"), "address": pickup.get("address")},
        "items": [{"product_name": i["product_name"], "quantity": i["quantity"], "unit": i["unit"]} for i in order.get("items", [])],
        "total_ttc_cents": order.get("total_ttc_cents", 0),
        "assigned_at": order.get("carrier_assigned_at"),
        "pickup_confirmed_at": order.get("carrier_pickup_confirmed_at"),
        "delivery_confirmed_at": order.get("carrier_delivery_confirmed_at"),
    }


class MissionConfirm(BaseModel):
    step: str  # PICKUP | DELIVERY


@cooper_router.post("/mission/{token}/confirm")
async def confirm_mission_step(token: str, payload: MissionConfirm):
    if payload.step not in ("PICKUP", "DELIVERY"):
        raise HTTPException(status_code=400, detail="Étape invalide (PICKUP ou DELIVERY)")
    order = await db.orders.find_one({"carrier_mission_token": token}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    field = "carrier_pickup_confirmed_at" if payload.step == "PICKUP" else "carrier_delivery_confirmed_at"
    if order.get(field):
        raise HTTPException(status_code=400, detail="Étape déjà confirmée")
    if payload.step == "DELIVERY" and not order.get("carrier_pickup_confirmed_at"):
        raise HTTPException(status_code=400, detail="Confirmez d'abord l'enlèvement")
    now = datetime.utcnow()
    await db.orders.update_one({"carrier_mission_token": token}, {"$set": {field: now, "updated_at": now}})
    logger.info("Mission %s: %s confirmed for order %s", token[:8], payload.step, order["id"])
    return {"ok": True, "step": payload.step, "at": now.isoformat()}
