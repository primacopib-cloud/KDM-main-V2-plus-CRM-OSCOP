"""Transport routier LOGI'SCOP Mode D pour Acheteurs Pro : convention cadre + ordres de transport nominatifs."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core_deps import get_current_user, check_admin, create_notification
from db import get_database
from logiscop_transport_billing import (archive_ot_documents_to_ged, build_transport_invoice_pdf,
                                        create_transport_invoice, send_invoice_email)
from logiscop_transport_pdf import build_logiscop_convention_pdf, build_transport_order_pdf
from role_guards import ensure_can_buy

logger = logging.getLogger(__name__)
logiscop_transport_router = APIRouter(prefix="/api/logiscop-transport", tags=["logiscop-transport"])


class SignBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    quality: str = Field(min_length=2, max_length=120)
    place: str = Field(default="", max_length=120)
    approved: bool = False


class StopIn(BaseModel):
    zone_code: str
    address: str = Field(min_length=4, max_length=300)
    date: str = ""
    slot: str = ""
    contact: str = ""


class GoodsLine(BaseModel):
    designation: str = Field(min_length=2, max_length=200)
    colis: Optional[int] = None
    poids_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    palettes: Optional[int] = None
    valeur_eur: Optional[float] = None
    temperature: str = ""


class OtCreate(BaseModel):
    pickup: StopIn
    delivery: StopIn
    goods: List[GoodsLine] = Field(min_length=1, max_length=20)
    mode: str = "route"
    temperature: str = ""
    temperature_tolerance: str = ""
    pre_cooling: bool = False
    valeur_declaree_eur: Optional[float] = None
    notes: str = Field(default="", max_length=1000)


class AcceptBody(BaseModel):
    price_ht_eur: Optional[float] = None


class RefuseBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


EPOD_OUTCOMES = ["LIVRE_CONFORME", "LIVRE_AVEC_RESERVES", "PARTIEL", "REFUSE_LIVRAISON"]


class EpodBody(BaseModel):
    outcome: str
    reserves: str = Field(default="", max_length=1000)
    name: str = Field(min_length=2, max_length=120)
    quality: str = Field(min_length=2, max_length=120)
    temperature_file_b64: Optional[str] = Field(default=None, max_length=8_000_000)
    temperature_file_name: Optional[str] = Field(default=None, max_length=150)
    temperature_file_mime: Optional[str] = Field(default=None, max_length=80)


class PaidBody(BaseModel):
    paid: bool = True


async def _buyer_context(user: dict) -> dict:
    """Contexte acheteur : organisation + zones souscrites (entitlements ACTIVE)."""
    ensure_can_buy(user)
    db = get_database()
    org_id = user.get("organization_id")
    if not org_id:
        m = await db.org_memberships.find_one({"user_id": user["id"]}, {"_id": 0, "org_id": 1})
        org_id = (m or {}).get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Aucune organisation associée à votre compte Acheteur Pro")
    zone_ids = [e["zone_id"] async for e in db.org_zone_entitlements.find(
        {"org_id": org_id, "status": "ACTIVE"}, {"_id": 0, "zone_id": 1})]
    zones = [z["code"] async for z in db.zones_v2.find(
        {"id": {"$in": zone_ids}, "is_active": True}, {"_id": 0, "code": 1})]
    return {"org_id": org_id, "zones": sorted(set(zones))}


async def _next_ref(db, kind: str) -> str:
    year = datetime.now(timezone.utc).strftime("%Y")
    coll = db.logiscop_transport_orders if kind == "OT" else db.logiscop_transport_conventions
    n = await coll.count_documents({"ref": {"$regex": f"^LOGI/{kind}/{year}/"}}) + 1
    return f"LOGI/{kind}/{year}/{n:04d}"


async def _push_convention_to_ged(conv_id: str):
    db = get_database()
    conv = await db.logiscop_transport_conventions.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        return
    try:
        from gedess_client import gedess_upload_file, is_gedess_configured
        if not is_gedess_configured():
            return
        pdf = build_logiscop_convention_pdf(conv)
        doc = await gedess_upload_file(
            f"convention-logiscop-{conv['ref'].replace('/', '-')}.pdf", pdf, categorie="convention",
            description=f"Convention cadre LOGI'SCOP Mode D V1.2 signée — {conv.get('company_name')}",
            tags="logiscop,transport,convention", mime_type="application/pdf")
        await db.logiscop_transport_conventions.update_one(
            {"id": conv_id}, {"$set": {"ged_doc_id": doc.get("id")}})
    except Exception as exc:
        logger.warning("Push GEDESS convention LOGISCOP %s échoué : %s", conv_id, exc)


@logiscop_transport_router.get("/my-subscription")
async def my_subscription(current_user: dict = Depends(get_current_user)):
    ctx = await _buyer_context(current_user)
    db = get_database()
    conv = await db.logiscop_transport_conventions.find_one(
        {"org_id": ctx["org_id"], "status": {"$ne": "CANCELED"}}, {"_id": 0})
    return {"convention": conv, "zones": ctx["zones"]}


@logiscop_transport_router.post("/subscribe")
async def subscribe(current_user: dict = Depends(get_current_user)):
    ctx = await _buyer_context(current_user)
    db = get_database()
    if await db.logiscop_transport_conventions.find_one(
            {"org_id": ctx["org_id"], "status": {"$ne": "CANCELED"}}):
        raise HTTPException(status_code=409, detail="Une convention LOGI'SCOP existe déjà pour votre organisation")
    if not ctx["zones"]:
        raise HTTPException(status_code=400, detail="Aucune zone souscrite — ajoutez au moins une zone à votre abonnement")
    now_iso = datetime.now(timezone.utc).isoformat()
    conv = {
        "id": str(uuid.uuid4()), "ref": await _next_ref(db, "CONV"),
        "version": "V1.2", "mode": "D",
        "org_id": ctx["org_id"], "user_id": current_user["id"],
        "company_name": current_user.get("company_name"),
        "contact_name": current_user.get("contact_name") or current_user.get("name"),
        "email": current_user.get("email"), "siret": current_user.get("siret"),
        "zones": ctx["zones"], "status": "PENDING_SIGNATURE",
        "signature": None, "signed_at": None, "signature_place": None,
        "ged_doc_id": None, "created_at": now_iso,
    }
    await db.logiscop_transport_conventions.insert_one({**conv})
    return conv


async def _get_convention(db, conv_id: str, user: dict) -> dict:
    conv = await db.logiscop_transport_conventions.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Convention introuvable")
    if not user.get("is_admin") and conv["user_id"] != user["id"]:
        m = await db.org_memberships.find_one({"user_id": user["id"], "org_id": conv["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    return conv


@logiscop_transport_router.get("/convention/{conv_id}/pdf")
async def convention_pdf(conv_id: str, current_user: dict = Depends(get_current_user)):
    conv = await _get_convention(get_database(), conv_id, current_user)
    pdf = build_logiscop_convention_pdf(conv)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f"attachment; filename=convention-logiscop-{conv['ref'].replace('/', '-')}.pdf"})


@logiscop_transport_router.post("/convention/{conv_id}/sign")
async def sign_convention(conv_id: str, body: SignBody, background_tasks: BackgroundTasks,
                          current_user: dict = Depends(get_current_user)):
    db = get_database()
    conv = await _get_convention(db, conv_id, current_user)
    if conv["status"] == "SIGNED":
        raise HTTPException(status_code=409, detail="Convention déjà signée")
    if not body.approved:
        raise HTTPException(status_code=400, detail="La mention « Lu et approuvé » est obligatoire")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.logiscop_transport_conventions.update_one({"id": conv_id}, {"$set": {
        "status": "SIGNED", "signed_at": now_iso,
        "signature_place": body.place or None,
        "signature": {"name": body.name, "quality": body.quality, "at": now_iso,
                      "mention": "Lu et approuvé"}}})
    background_tasks.add_task(_push_convention_to_ged, conv_id)
    await create_notification(
        "logiscop_convention_signed", "Convention LOGI'SCOP signée",
        f"{conv.get('company_name') or body.name} a signé la convention transport {conv['ref']}.",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={"convention_id": conv_id, "ref": conv["ref"]})
    return await db.logiscop_transport_conventions.find_one({"id": conv_id}, {"_id": 0})


@logiscop_transport_router.post("/orders")
async def create_transport_order(body: OtCreate, current_user: dict = Depends(get_current_user)):
    ctx = await _buyer_context(current_user)
    db = get_database()
    conv = await db.logiscop_transport_conventions.find_one(
        {"org_id": ctx["org_id"], "status": "SIGNED"}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=403, detail="Convention cadre LOGI'SCOP signée requise avant tout Ordre de Transport")
    from logiscop_transport_billing import get_ot_suspension
    susp = await get_ot_suspension(db, ctx["org_id"])
    if susp:
        raise HTTPException(status_code=403,
                            detail=f"Émission d'OT suspendue : mise en demeure en cours sur la facture {susp['ref']} "
                                   "impayée à 45 jours. Régularisez le règlement pour rétablir le service.")
    for stop, lbl in ((body.pickup, "d'enlèvement"), (body.delivery, "de livraison")):
        if stop.zone_code not in ctx["zones"]:
            raise HTTPException(status_code=403,
                                detail=f"La zone {lbl} {stop.zone_code} n'est pas couverte par votre abonnement")
    now_iso = datetime.now(timezone.utc).isoformat()
    ot = {
        "id": str(uuid.uuid4()), "ref": await _next_ref(db, "OT"),
        "convention_id": conv["id"], "convention_ref": conv["ref"],
        "org_id": ctx["org_id"], "user_id": current_user["id"],
        "created_by_name": current_user.get("contact_name") or current_user.get("name") or current_user.get("email"),
        "company_name": conv.get("company_name"),
        "status": "PROPOSE",
        "pickup": body.pickup.model_dump(), "delivery": body.delivery.model_dump(),
        "goods": [g.model_dump() for g in body.goods],
        "mode": body.mode, "temperature": body.temperature,
        "temperature_tolerance": body.temperature_tolerance, "pre_cooling": body.pre_cooling,
        "valeur_declaree_eur": body.valeur_declaree_eur, "notes": body.notes,
        "price_ht_cents": None, "acceptance": None, "created_at": now_iso,
    }
    await db.logiscop_transport_orders.insert_one({**ot})
    await create_notification(
        "logiscop_ot_created", "Nouvel Ordre de Transport LOGI'SCOP",
        f"{conv.get('company_name')} a émis l'OT {ot['ref']} "
        f"({body.pickup.zone_code} → {body.delivery.zone_code}).",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={"ot_id": ot["id"], "ref": ot["ref"]})
    return ot


@logiscop_transport_router.get("/orders")
async def list_my_orders(current_user: dict = Depends(get_current_user)):
    ctx = await _buyer_context(current_user)
    db = get_database()
    return await db.logiscop_transport_orders.find(
        {"org_id": ctx["org_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


async def _get_ot(db, ot_id: str, user: dict) -> dict:
    ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    if not ot:
        raise HTTPException(status_code=404, detail="Ordre de transport introuvable")
    if not user.get("is_admin") and ot["user_id"] != user["id"]:
        m = await db.org_memberships.find_one({"user_id": user["id"], "org_id": ot["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    return ot


@logiscop_transport_router.get("/orders/{ot_id}/pdf")
async def transport_order_pdf(ot_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    ot = await _get_ot(db, ot_id, current_user)
    conv = await db.logiscop_transport_conventions.find_one({"id": ot["convention_id"]}, {"_id": 0}) or {}
    pdf = build_transport_order_pdf(ot, conv)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f"attachment; filename=ot-logiscop-{ot['ref'].replace('/', '-')}.pdf"})


@logiscop_transport_router.post("/orders/{ot_id}/epod")
async def close_order_epod(ot_id: str, body: EpodBody, background_tasks: BackgroundTasks,
                           current_user: dict = Depends(get_current_user)):
    """Clôture de l'OT à la livraison : signature ePOD, réserves, relevé de température, statut final."""
    if body.outcome not in EPOD_OUTCOMES:
        raise HTTPException(status_code=400, detail=f"Résultat invalide ({', '.join(EPOD_OUTCOMES)})")
    if body.outcome != "LIVRE_CONFORME" and len(body.reserves.strip()) < 3:
        raise HTTPException(status_code=400, detail="Des réserves précises et motivées sont obligatoires (article 17)")
    db = get_database()
    ot = await _get_ot(db, ot_id, current_user)
    if ot["status"] != "ACCEPTE":
        raise HTTPException(status_code=409, detail=f"Seul un OT accepté peut être clôturé (statut : {ot['status']})")
    now_iso = datetime.now(timezone.utc).isoformat()
    epod = {"outcome": body.outcome, "reserves": body.reserves.strip() or None,
            "name": body.name, "quality": body.quality, "at": now_iso}
    if body.temperature_file_b64 and body.temperature_file_name:
        import base64
        raw = base64.b64decode(body.temperature_file_b64)
        file_id = str(uuid.uuid4())
        await db.logiscop_temperature_files.insert_one({
            "id": file_id, "ot_id": ot_id, "name": body.temperature_file_name,
            "mime": body.temperature_file_mime or "application/octet-stream",
            "content_b64": body.temperature_file_b64, "uploaded_at": now_iso})
        epod["temperature_file"] = {"id": file_id, "name": body.temperature_file_name}
        from logiscop_temperature import process_temperature_analysis
        analysis = await process_temperature_analysis(db, ot, raw, body.temperature_file_name)
        if analysis:
            epod["temperature_incident"] = analysis if analysis.get("incident") else None
            epod["temperature_analysis"] = analysis
    await db.logiscop_transport_orders.update_one(
        {"id": ot_id}, {"$set": {"status": body.outcome, "epod": epod}})
    ot_after = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    from logiscop_transport_billing import create_service_credit
    credit = await create_service_credit(db, ot_after)
    if credit:
        await create_notification(
            "logiscop_service_credit", "Avoir de service émis (article 22)",
            f"Un avoir {credit['ref']} de {credit['total_ttc_cents'] / 100:.2f} € TTC "
            f"({' + '.join(credit['reasons'])}, {credit['pct_total']:.0f} %) a été appliqué sur votre facture "
            f"{credit['invoice_ref']} — OT {ot['ref']}.",
            target_user_id=ot["user_id"], data={"credit_id": credit["id"], "ref": credit["ref"]})
    background_tasks.add_task(archive_ot_documents_to_ged, db, ot_id)
    await create_notification(
        "logiscop_ot_delivered", "Ordre de Transport clôturé (ePOD)",
        f"OT {ot['ref']} clôturé par {body.name} : {body.outcome.replace('_', ' ')}"
        + (f" — Réserves : {body.reserves.strip()[:120]}" if epod["reserves"] else "."),
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={"ot_id": ot_id, "ref": ot["ref"], "outcome": body.outcome})
    return await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})


@logiscop_transport_router.get("/orders/{ot_id}/temperature-file")
async def download_temperature_file(ot_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    await _get_ot(db, ot_id, current_user)
    f = await db.logiscop_temperature_files.find_one({"ot_id": ot_id}, {"_id": 0})
    if not f:
        raise HTTPException(status_code=404, detail="Aucun relevé de température joint")
    import base64
    return Response(content=base64.b64decode(f["content_b64"]), media_type=f["mime"],
                    headers={"Content-Disposition": f"attachment; filename={f['name']}"})


class RatingBody(BaseModel):
    stars: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=600)


@logiscop_transport_router.post("/orders/{ot_id}/rating")
async def rate_delivery(ot_id: str, body: RatingBody, current_user: dict = Depends(get_current_user)):
    """L'acheteur note la qualité de la livraison (modifiable), rattachée à l'opérateur exécutant."""
    db = get_database()
    ot = await _get_ot(db, ot_id, current_user)
    if ot["status"] not in ("LIVRE_CONFORME", "LIVRE_AVEC_RESERVES", "PARTIEL", "REFUSE_LIVRAISON"):
        raise HTTPException(status_code=409, detail="Seule une livraison clôturée peut être notée")
    rating = {"stars": body.stars, "comment": body.comment.strip() or None,
              "by": current_user.get("contact_name") or current_user.get("email"),
              "at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_transport_orders.update_one({"id": ot_id}, {"$set": {"rating": rating}})
    op_name = (ot.get("execution") or {}).get("operator_name")
    await create_notification(
        "logiscop_delivery_rated", "Livraison notée",
        f"OT {ot['ref']} noté {body.stars}/5 par {ot.get('company_name')}"
        + (f" (opérateur : {op_name})" if op_name else "")
        + (f" — « {body.comment.strip()[:100]} »" if body.comment.strip() else "."),
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={"ot_id": ot_id, "ref": ot["ref"], "stars": body.stars})
    return await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})


@logiscop_transport_router.get("/invoices")
async def list_my_invoices(current_user: dict = Depends(get_current_user)):
    ctx = await _buyer_context(current_user)
    db = get_database()
    return await db.logiscop_transport_invoices.find(
        {"org_id": ctx["org_id"]}, {"_id": 0}).sort("issued_at", -1).to_list(200)


@logiscop_transport_router.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    inv = await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    await _get_ot(db, inv["ot_id"], current_user)
    ot = await db.logiscop_transport_orders.find_one({"id": inv["ot_id"]}, {"_id": 0}) or {}
    conv = await db.logiscop_transport_conventions.find_one({"id": ot.get("convention_id")}, {"_id": 0}) or {}
    pdf = build_transport_invoice_pdf(inv, ot, conv)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={inv['ref']}.pdf"})


# ================= ADMIN =================

@logiscop_transport_router.get("/admin/overview")
async def admin_overview(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    conventions = await db.logiscop_transport_conventions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    orders = await db.logiscop_transport_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    invoices = await db.logiscop_transport_invoices.find({}, {"_id": 0}).sort("issued_at", -1).to_list(200)
    credits = await db.logiscop_transport_credits.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"conventions": conventions, "orders": orders, "invoices": invoices, "credits": credits,
            "pending_orders": sum(1 for o in orders if o["status"] == "PROPOSE")}


@logiscop_transport_router.post("/admin/orders/{ot_id}/accept")
async def admin_accept_order(ot_id: str, body: AcceptBody, background_tasks: BackgroundTasks,
                             current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    if not ot:
        raise HTTPException(status_code=404, detail="Ordre de transport introuvable")
    if ot["status"] != "PROPOSE":
        raise HTTPException(status_code=409, detail=f"Statut actuel : {ot['status']}")
    if body.price_ht_eur is None or body.price_ht_eur <= 0:
        raise HTTPException(status_code=400, detail="Prix HT requis : l'acceptation déclenche la facturation")
    now_iso = datetime.now(timezone.utc).isoformat()
    update = {"status": "ACCEPTE", "price_ht_cents": int(round(body.price_ht_eur * 100)),
              "acceptance": {"admin_name": f"O'SCOP / LOGI'SCOP ({current_user.get('email')})", "at": now_iso}}
    await db.logiscop_transport_orders.update_one({"id": ot_id}, {"$set": update})
    ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    conv = await db.logiscop_transport_conventions.find_one({"id": ot["convention_id"]}, {"_id": 0}) or {}
    invoice = await create_transport_invoice(db, ot, conv)
    background_tasks.add_task(send_invoice_email, db, invoice["id"])
    await create_notification(
        "logiscop_ot_accepted", "Ordre de Transport accepté",
        f"LOGI'SCOP a accepté votre OT {ot['ref']} — prix {body.price_ht_eur:.2f} € HT. "
        f"Facture {invoice['ref']} émise.",
        target_user_id=ot["user_id"], data={"ot_id": ot_id, "ref": ot["ref"], "invoice_ref": invoice["ref"]})
    return {**ot, "invoice": invoice}


@logiscop_transport_router.post("/admin/invoices/{invoice_id}/mark-paid")
async def admin_mark_invoice_paid(invoice_id: str, body: PaidBody,
                                  current_user: dict = Depends(get_current_user)):
    """Pointage d'une facture transport payée (ou annulation du pointage)."""
    await check_admin(current_user)
    db = get_database()
    inv = await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    update = ({"status": "PAID", "paid_at": datetime.now(timezone.utc).isoformat()}
              if body.paid else {"status": "ISSUED", "paid_at": None})
    await db.logiscop_transport_invoices.update_one({"id": invoice_id}, {"$set": update})
    if body.paid:
        await create_notification(
            "logiscop_invoice_paid", "Facture transport réglée",
            f"Votre règlement de la facture {inv['ref']} ({(inv['total_ttc_cents']) / 100:.2f} € TTC) a été pointé. Merci.",
            target_user_id=inv["user_id"], data={"invoice_id": invoice_id, "ref": inv["ref"]})
    return await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})


@logiscop_transport_router.post("/admin/orders/{ot_id}/refuse")
async def admin_refuse_order(ot_id: str, body: RefuseBody, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    if not ot:
        raise HTTPException(status_code=404, detail="Ordre de transport introuvable")
    if ot["status"] != "PROPOSE":
        raise HTTPException(status_code=409, detail=f"Statut actuel : {ot['status']}")
    await db.logiscop_transport_orders.update_one(
        {"id": ot_id}, {"$set": {"status": "REFUSE", "refusal_reason": body.reason,
                                 "refused_at": datetime.now(timezone.utc).isoformat()}})
    await create_notification(
        "logiscop_ot_refused", "Ordre de Transport refusé",
        f"LOGI'SCOP a refusé votre OT {ot['ref']} : {body.reason}",
        target_user_id=ot["user_id"], data={"ot_id": ot_id, "ref": ot["ref"]})
    return await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
