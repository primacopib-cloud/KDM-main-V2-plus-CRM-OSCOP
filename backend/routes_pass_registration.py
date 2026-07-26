"""Inscriptions publiques au PASS LOLODRIVE + gestion admin."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

pass_registration_router = APIRouter(prefix="/api/public", tags=["pass-registration"])
pass_admin_router = APIRouter(prefix="/api/admin/pass-registrations", tags=["pass-admin"])

PASS_STATUSES = {"NEW": "Nouveau", "CONTACTED": "Contacté", "ACTIVATED": "PASS activé"}

db = None


def set_pass_registration_database(database):
    global db
    db = database


class PassRegistrationBody(BaseModel):
    first_name: str
    last_name: str
    address: str
    postal_code: str
    city: str
    phone: str
    phone_country: str = ""
    country: str = "GP"
    email: EmailStr
    relay: dict | None = None


@pass_registration_router.post("/pass-registration")
async def create_pass_registration(body: PassRegistrationBody):
    doc = {
        "id": str(uuid.uuid4()),
        "first_name": body.first_name.strip()[:80],
        "last_name": body.last_name.strip()[:80],
        "address": body.address.strip()[:200],
        "postal_code": body.postal_code.strip()[:12],
        "city": body.city.strip()[:80],
        "phone": body.phone.strip()[:30],
        "phone_country": body.phone_country.strip()[:5],
        "country": body.country.strip().upper()[:2],
        "email": body.email.lower(),
        "relay": body.relay or None,
        "status": "NEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.pass_registrations.insert_one(dict(doc))
    try:
        from core_deps import create_notification
        relay_name = (body.relay or {}).get("name")
        await create_notification(
            "new_pass_registration", "Nouvelle inscription PASS LOLODRIVE",
            f"{doc['first_name']} {doc['last_name']} ({doc['city']})"
            + (f" — relais : {relay_name}" if relay_name else ""),
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"email": doc["email"], "registration_id": doc["id"]})
    except Exception as exc:
        logger.warning("Notif inscription PASS : %s", exc)
    logger.info("Inscription PASS LOLODRIVE : %s (%s)", doc["email"], doc["city"])
    try:
        await _send_welcome_email(doc)
    except Exception as exc:
        logger.warning("Email bienvenue PASS %s : %s", doc["email"], exc)
    return {"ok": True, "id": doc["id"]}


async def _send_welcome_email(doc: dict):
    from brevo_service import send_email
    relay = doc.get("relay") or {}
    relay_html = (
        f"<p style='background:#f5efe2;border-radius:10px;padding:12px 14px'>📍 <b>Votre relais :</b> "
        f"{relay.get('name')}" + (f" ({relay.get('code')})" if relay.get('code') else "") + "</p>"
    ) if relay.get("name") else ""
    await send_email(
        to_email=doc["email"], to_name=f"{doc['first_name']} {doc['last_name']}".strip(),
        subject="🎫 Bienvenue — votre PASS LOLODRIVE",
        html_content=(
            "<div style='font-family:Arial,sans-serif;max-width:560px'>"
            f"<h2 style='color:#451F6B'>Bienvenue {doc['first_name']} !</h2>"
            "<p>Votre inscription au <b>PASS LOLODRIVE</b> est bien enregistrée.</p>"
            "<p>Le relais LOLODRIVE, c'est l'accès à des <b>produits de nécessité du quotidien à un coût "
            "mutualisé</b> : la coopérative regroupe les achats de ses adhérents pour négocier les meilleurs "
            "prix, et vous les retirez près de chez vous (drive coopératif ou livraison locale).</p>"
            f"{relay_html}"
            "<p>Notre équipe revient vers vous rapidement pour activer votre PASS.</p>"
            "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP — LOLODRIVE</p></div>"),
        tags=["pass-welcome"])


class PassStatusBody(BaseModel):
    status: str


@pass_admin_router.get("")
async def list_pass_registrations(admin: dict = Depends(require_admin)):
    regs = await db.pass_registrations.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"registrations": regs, "statuses": PASS_STATUSES}


@pass_admin_router.patch("/{reg_id}")
async def update_pass_registration(reg_id: str, body: PassStatusBody, admin: dict = Depends(require_admin)):
    if body.status not in PASS_STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")
    res = await db.pass_registrations.update_one(
        {"id": reg_id}, {"$set": {"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Inscription introuvable")
    return {"ok": True}


@pass_admin_router.get("/export")
async def export_pass_registrations(admin: dict = Depends(require_admin)):
    regs = await db.pass_registrations.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    lines = ["Date;Prénom;Nom;Email;Téléphone;Adresse;Code postal;Ville;Pays;Relais;Statut"]
    for r in regs:
        relay = (r.get("relay") or {}).get("name") or ""
        vals = [str(r.get("created_at", ""))[:10], r.get("first_name", ""), r.get("last_name", ""),
                r.get("email", ""), r.get("phone", ""), r.get("address", ""), r.get("postal_code", ""),
                r.get("city", ""), r.get("country", ""), relay, PASS_STATUSES.get(r.get("status"), r.get("status", ""))]
        lines.append(";".join(v.replace(";", ",") for v in vals))
    csv = "\ufeff" + "\n".join(lines)
    filename = f"inscriptions-pass-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
