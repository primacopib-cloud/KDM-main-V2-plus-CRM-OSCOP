"""Inscriptions publiques au PASS LOLODRIVE."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

pass_registration_router = APIRouter(prefix="/api/public", tags=["pass-registration"])

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
    return {"ok": True, "id": doc["id"]}
