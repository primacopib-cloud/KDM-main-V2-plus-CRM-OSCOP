"""Espace LOGICOOP (opérateurs logistiques) + formulaire Devenir Partenaire.
Admin : opérateurs (zones EXW / CIF), types de partenariat, candidatures. Public : types + candidature."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from auth import get_current_user_id
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

logicoop_router = APIRouter(prefix="/api", tags=["logicoop"])

db = None

DEFAULT_PARTNER_TYPES = [
    {"code": "COOPERS", "label": "Devenir COOPER'S"},
    {"code": "LOGICOOP", "label": "Devenir LOGICOOP (opérateur logistique)"},
]


def set_logicoop_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------- Opérateurs LOGICOOP (admin) ----------

class OperatorBody(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    exw_zones: List[str] = []
    cif_zones: List[str] = []


class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    exw_zones: Optional[List[str]] = None
    cif_zones: Optional[List[str]] = None
    active: Optional[bool] = None


async def _valid_zones(codes: List[str]) -> List[str]:
    known = {z["code"] async for z in db.zones_v2.find({}, {"_id": 0, "code": 1})}
    bad = [c for c in codes if c.upper() not in known]
    if bad:
        raise HTTPException(status_code=400, detail=f"Zones inconnues : {', '.join(bad)}")
    return [c.upper() for c in codes]


@logicoop_router.get("/admin/logicoop/operators")
async def list_operators(admin: dict = Depends(require_admin)):
    items = await db.logicoop_operators.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@logicoop_router.post("/admin/logicoop/operators")
async def create_operator(body: OperatorBody, admin: dict = Depends(require_admin)):
    email = body.email.lower()
    if await db.logicoop_operators.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un opérateur existe déjà avec cet email")
    doc = {"id": str(uuid.uuid4()), "name": body.name.strip(), "email": email,
           "phone": body.phone, "exw_zones": await _valid_zones(body.exw_zones),
           "cif_zones": await _valid_zones(body.cif_zones), "active": True,
           "created_at": _now(), "created_by": admin.get("email")}
    await db.logicoop_operators.insert_one({**doc})
    logger.info("Opérateur LOGICOOP créé : %s par %s", email, admin.get("email"))
    return doc


@logicoop_router.patch("/admin/logicoop/operators/{op_id}")
async def update_operator(op_id: str, body: OperatorUpdate, admin: dict = Depends(require_admin)):
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if "exw_zones" in upd:
        upd["exw_zones"] = await _valid_zones(upd["exw_zones"])
    if "cif_zones" in upd:
        upd["cif_zones"] = await _valid_zones(upd["cif_zones"])
    if not upd:
        raise HTTPException(status_code=400, detail="Rien à mettre à jour")
    upd["updated_at"] = _now()
    res = await db.logicoop_operators.update_one({"id": op_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Opérateur introuvable")
    return {"ok": True}


@logicoop_router.delete("/admin/logicoop/operators/{op_id}")
async def delete_operator(op_id: str, admin: dict = Depends(require_admin)):
    res = await db.logicoop_operators.delete_one({"id": op_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Opérateur introuvable")
    return {"ok": True}


# ---------- Espace opérateur (utilisateur connecté) ----------

@logicoop_router.get("/logicoop/me")
async def my_operator_space(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    if not user or not user.get("email"):
        raise HTTPException(status_code=403, detail="Compte sans email")
    op = await db.logicoop_operators.find_one(
        {"email": user["email"].lower(), "active": True}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=403, detail="Accès réservé aux opérateurs LOGICOOP")
    zones = {z["code"]: z["name"] async for z in db.zones_v2.find({}, {"_id": 0, "code": 1, "name": 1})}
    op["exw_zones_detail"] = [{"code": c, "name": zones.get(c, c)} for c in op.get("exw_zones", [])]
    op["cif_zones_detail"] = [{"code": c, "name": zones.get(c, c)} for c in op.get("cif_zones", [])]
    return op


@logicoop_router.get("/logicoop/missions")
async def my_missions(user_id: str = Depends(get_current_user_id)):
    """Commandes à enlever (EXW dans mes zones entrepôt) ou à livrer (CIF dans mes zones de livraison)."""
    op = await my_operator_space(user_id)
    exw, cif = set(op.get("exw_zones", [])), set(op.get("cif_zones", []))
    zones = list(exw | cif)
    if not zones:
        return {"items": []}
    pickups = {p["id"]: p.get("name") async for p in db.pickup_locations.find({}, {"_id": 0, "id": 1, "name": 1})}
    items = []
    async for o in db.orders.find(
            {"zone_code": {"$in": zones}, "status": {"$nin": ["CANCELLED", "DELIVERED", "COMPLETED"]}},
            {"_id": 0, "id": 1, "order_number": 1, "status": 1, "zone_code": 1, "incoterm": 1,
             "subtotal_ht_cents": 1, "total_ttc_cents": 1, "pickup_location_id": 1, "created_at": 1, "items": 1, "logistics": 1}).sort("created_at", -1).limit(100):
        incoterm = o.get("incoterm") or "EXW"
        if incoterm == "CIF" and o["zone_code"] in cif:
            mission = "LIVRAISON"
        elif o["zone_code"] in exw:
            mission = "ENLEVEMENT"
        else:
            continue
        items.append({
            "order_id": o["id"], "order_number": o.get("order_number"), "status": o.get("status"),
            "zone_code": o["zone_code"], "incoterm": incoterm, "mission": mission,
            "pickup_location": pickups.get(o.get("pickup_location_id")),
            "total_ht_cents": o.get("subtotal_ht_cents", 0),
            "items_count": len(o.get("items", [])),
            "created_at": str(o.get("created_at", ""))[:16],
            "logistics": o.get("logistics"),
        })
    return {"items": items}


MISSION_STATUSES = ["PRISE_EN_CHARGE", "LIVREE"]


class MissionStatusBody(BaseModel):
    status: str


@logicoop_router.post("/logicoop/missions/{order_id}/status")
async def set_mission_status(order_id: str, body: MissionStatusBody, user_id: str = Depends(get_current_user_id)):
    """L'opérateur marque la mission prise en charge puis livrée — visible par l'acheteur."""
    if body.status not in MISSION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide (PRISE_EN_CHARGE ou LIVREE)")
    op = await my_operator_space(user_id)
    order = await db.orders.find_one({"id": order_id}, {"_id": 0, "id": 1, "zone_code": 1, "incoterm": 1, "logistics": 1, "order_number": 1})
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    zones = set(op.get("exw_zones", [])) | set(op.get("cif_zones", []))
    if order["zone_code"] not in zones:
        raise HTTPException(status_code=403, detail="Cette commande n'est pas dans vos zones")
    current = (order.get("logistics") or {}).get("status")
    if current == "LIVREE":
        raise HTTPException(status_code=409, detail="Mission déjà livrée")
    if body.status == "LIVREE" and current != "PRISE_EN_CHARGE":
        raise HTTPException(status_code=409, detail="Prenez d'abord la mission en charge")
    entry = {"status": body.status, "at": _now(), "operator": op["name"]}
    await db.orders.update_one({"id": order_id}, {
        "$set": {"logistics": {"status": body.status, "operator_id": op["id"], "operator_name": op["name"],
                               "updated_at": _now()}},
        "$push": {"logistics_history": entry}})
    logger.info("Mission %s → %s par %s", order.get("order_number"), body.status, op["name"])
    return {"ok": True, "status": body.status}


# ---------- Types de partenariat ----------

async def _ensure_types():
    if await db.partner_types.count_documents({}) == 0:
        for t in DEFAULT_PARTNER_TYPES:
            await db.partner_types.insert_one({"id": str(uuid.uuid4()), **t, "active": True, "created_at": _now()})


@logicoop_router.get("/partners/types")
async def public_partner_types():
    await _ensure_types()
    items = await db.partner_types.find({"active": True}, {"_id": 0}).to_list(50)
    return {"items": items}


class PartnerTypeBody(BaseModel):
    code: str
    label: str


@logicoop_router.get("/admin/partners/types")
async def admin_partner_types(admin: dict = Depends(require_admin)):
    await _ensure_types()
    return {"items": await db.partner_types.find({}, {"_id": 0}).to_list(50)}


@logicoop_router.post("/admin/partners/types")
async def add_partner_type(body: PartnerTypeBody, admin: dict = Depends(require_admin)):
    code = body.code.strip().upper().replace(" ", "_")
    if await db.partner_types.find_one({"code": code}):
        raise HTTPException(status_code=409, detail="Ce type existe déjà")
    doc = {"id": str(uuid.uuid4()), "code": code, "label": body.label.strip(), "active": True, "created_at": _now()}
    await db.partner_types.insert_one({**doc})
    return doc


@logicoop_router.patch("/admin/partners/types/{type_id}")
async def toggle_partner_type(type_id: str, admin: dict = Depends(require_admin)):
    t = await db.partner_types.find_one({"id": type_id})
    if not t:
        raise HTTPException(status_code=404, detail="Type introuvable")
    await db.partner_types.update_one({"id": type_id}, {"$set": {"active": not t.get("active", True)}})
    return {"ok": True, "active": not t.get("active", True)}


# ---------- Candidatures Devenir Partenaire ----------

class ApplicationBody(BaseModel):
    type: str
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None


@logicoop_router.post("/partners/apply")
async def apply_partner(body: ApplicationBody):
    await _ensure_types()
    t = await db.partner_types.find_one({"code": body.type.upper(), "active": True})
    if not t:
        raise HTTPException(status_code=400, detail="Type de partenariat inconnu")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nom requis")
    doc = {"id": str(uuid.uuid4()), "type": t["code"], "type_label": t["label"],
           "name": body.name.strip(), "email": body.email.lower(), "company": body.company,
           "phone": body.phone, "message": (body.message or "")[:2000],
           "status": "NOUVELLE", "created_at": _now()}
    await db.partner_applications.insert_one({**doc})
    logger.info("Candidature partenaire %s : %s", t["code"], body.email)
    import os
    try:
        from brevo_service import send_email
        await send_email(
            to_email=doc["email"], to_name=doc["name"],
            subject=f"Candidature reçue — {t['label']} | KDMARCHÉ × O'SCOP",
            html_content=f"""<h2 style="color:#451F6B;">Merci pour votre candidature !</h2>
            <p>Bonjour {doc['name']},</p>
            <p>Nous avons bien reçu votre demande « <strong>{t['label']}</strong> »
            {f"pour {doc['company']}" if doc.get('company') else ''}.
            Notre équipe l'étudie et reviendra vers vous rapidement.</p>
            <p style="color:#777;font-size:12px;">Référence : {doc['id'][:8].upper()} — La coopérative KDMARCHÉ × O'SCOP.</p>""",
            tags=["partner-application-ack"])
    except Exception as exc:
        logger.warning("Accusé réception candidature %s : %s", doc["email"], exc)
    try:
        from brevo_service import send_email
        from email_alerts import ADMIN_ALERT_EMAIL
        await send_email(
            to_email=os.environ.get("ADMIN_ALERT_EMAIL", ADMIN_ALERT_EMAIL), to_name="Admin KDMARCHÉ × O'SCOP",
            subject=f"Nouvelle candidature partenaire : {t['label']} — {doc['name']}",
            html_content=f"""<h2 style="color:#451F6B;">Nouvelle candidature « {t['label']} »</h2>
            <ul><li><strong>Nom :</strong> {doc['name']}</li>
            <li><strong>Société :</strong> {doc.get('company') or '—'}</li>
            <li><strong>Email :</strong> {doc['email']}</li>
            <li><strong>Téléphone :</strong> {doc.get('phone') or '—'}</li>
            <li><strong>Message :</strong> {doc.get('message') or '—'}</li></ul>
            <p>À traiter dans l'onglet LOGICOOP du Super Admin.</p>""",
            tags=["partner-application-admin"])
    except Exception as exc:
        logger.warning("Alerte admin candidature : %s", exc)
    try:
        from core_deps import create_notification
        await create_notification(
            "partner_application", f"Candidature {t['code']} — {doc['name']}",
            f"{doc['name']}{' (' + doc['company'] + ')' if doc.get('company') else ''} souhaite rejoindre l'espace {t['label']}.",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"link": "/superadmin", "application_id": doc["id"]})
    except Exception as exc:
        logger.warning("Notif candidature : %s", exc)
    return {"ok": True, "id": doc["id"]}


class AppStatusBody(BaseModel):
    status: str


@logicoop_router.get("/admin/partners/applications")
async def list_applications(admin: dict = Depends(require_admin)):
    items = await db.partner_applications.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@logicoop_router.patch("/admin/partners/applications/{app_id}")
async def update_application(app_id: str, body: AppStatusBody, admin: dict = Depends(require_admin)):
    if body.status not in ("NOUVELLE", "EN_COURS", "ACCEPTEE", "REFUSEE"):
        raise HTTPException(status_code=400, detail="Statut invalide")
    app_doc = await db.partner_applications.find_one({"id": app_id}, {"_id": 0})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    await db.partner_applications.update_one(
        {"id": app_id}, {"$set": {"status": body.status, "updated_at": _now(), "updated_by": admin.get("email")}})
    if body.status in ("ACCEPTEE", "REFUSEE"):
        accepted = body.status == "ACCEPTEE"
        try:
            from brevo_service import send_email
            await send_email(
                to_email=app_doc["email"], to_name=app_doc["name"],
                subject=(f"🎉 Candidature acceptée — {app_doc.get('type_label', app_doc['type'])}" if accepted
                         else f"Votre candidature {app_doc.get('type_label', app_doc['type'])} — réponse"),
                html_content=(
                    f"""<h2 style="color:#451F6B;">Bienvenue dans la coopérative !</h2>
                    <p>Bonjour {app_doc['name']},</p>
                    <p>Bonne nouvelle : votre candidature « <strong>{app_doc.get('type_label', app_doc['type'])}</strong> »
                    a été <strong style="color:#1E8449;">acceptée</strong>. Notre équipe vous contactera très vite pour
                    finaliser votre intégration et vos accès.</p>
                    <p style="color:#777;font-size:12px;">Référence : {app_doc['id'][:8].upper()} — KDMARCHÉ × O'SCOP.</p>""" if accepted else
                    f"""<h2 style="color:#451F6B;">Réponse à votre candidature</h2>
                    <p>Bonjour {app_doc['name']},</p>
                    <p>Après étude, nous ne pouvons pas donner suite à votre candidature
                    « <strong>{app_doc.get('type_label', app_doc['type'])}</strong> » pour le moment.
                    Vous pourrez candidater à nouveau ultérieurement — merci de l'intérêt porté à la coopérative.</p>
                    <p style="color:#777;font-size:12px;">Référence : {app_doc['id'][:8].upper()} — KDMARCHÉ × O'SCOP.</p>"""),
                tags=["partner-application-decision"])
        except Exception as exc:
            logger.warning("Email décision candidature %s : %s", app_doc["email"], exc)
    return {"ok": True}
