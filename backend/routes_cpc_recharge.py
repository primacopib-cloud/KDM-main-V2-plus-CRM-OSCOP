"""Recharge CPC semi-automatique : sous le seuil choisi, email avec lien de paiement Stripe en 1 clic.
Aucune carte stockée, aucun débit sans action explicite du vendeur."""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth import get_current_user_id

logger = logging.getLogger(__name__)

recharge_router = APIRouter(prefix="/api/cpc/recharge", tags=["cpc-recharge"])

db = None

TOKEN_VALIDITY_DAYS = 7


def set_recharge_database(database):
    global db
    db = database


@recharge_router.get("/settings")
async def read_settings(user_id: str = Depends(get_current_user_id)):
    s = await db.cpc_recharge_settings.find_one({"user_id": user_id}, {"_id": 0})
    return s or {"user_id": user_id, "enabled": False, "threshold": 20, "pack_id": "cpc-pack-150"}


class SettingsBody(BaseModel):
    enabled: bool
    threshold: int
    pack_id: str


@recharge_router.put("/settings")
async def update_settings(body: SettingsBody, user_id: str = Depends(get_current_user_id)):
    if body.threshold <= 0:
        raise HTTPException(status_code=400, detail="Seuil invalide")
    pack = await db.cpc_packs.find_one({"id": body.pack_id, "active": True}, {"_id": 0, "id": 1})
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    await db.cpc_recharge_settings.update_one(
        {"user_id": user_id},
        {"$set": {**body.dict(), "alert_active": False,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    return {"ok": True}


@recharge_router.get("/checkout/{token}")
async def recharge_checkout(token: str):
    """Lien 1 clic depuis l'email : crée la session Stripe et redirige (jeton à usage unique, 7 jours)."""
    doc = await db.cpc_recharge_tokens.find_one({"token": token}, {"_id": 0})
    if not doc or doc.get("used") or doc["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=410, detail="Lien de recharge expiré — rechargez depuis votre Espace Vendeur, onglet CPC")
    user = await db.users.find_one({"id": doc["user_id"]}, {"_id": 0, "id": 1, "email": 1, "role": 1,
                                                           "name": 1, "full_name": 1, "country": 1})
    pack = await db.cpc_packs.find_one({"id": doc["pack_id"], "active": True}, {"_id": 0})
    if not user or not pack:
        raise HTTPException(status_code=410, detail="Recharge indisponible")
    from routes_cpc import create_pack_checkout
    origin = os.environ.get("FRONTEND_PUBLIC_URL", "")
    out = await create_pack_checkout(user, pack, origin)
    await db.cpc_recharge_tokens.update_one({"token": token}, {"$set": {
        "used": True, "used_at": datetime.now(timezone.utc).isoformat(),
        "stripe_session_id": out["session_id"]}})
    return RedirectResponse(url=out["checkout_url"], status_code=303)


async def maybe_send_recharge_link(user_id: str, balance_after: int):
    """Appelé après chaque mouvement CPC : envoie le lien si le solde passe sous le seuil (une fois par franchissement)."""
    s = await db.cpc_recharge_settings.find_one({"user_id": user_id})
    if not s or not s.get("enabled"):
        return
    if balance_after >= s["threshold"]:
        if s.get("alert_active"):
            await db.cpc_recharge_settings.update_one({"user_id": user_id}, {"$set": {"alert_active": False}})
        return
    if s.get("alert_active"):
        return
    pack = await db.cpc_packs.find_one({"id": s["pack_id"], "active": True}, {"_id": 0})
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "full_name": 1, "name": 1})
    if not pack or not user or not user.get("email"):
        return
    token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    await db.cpc_recharge_tokens.insert_one({
        "token": token, "user_id": user_id, "pack_id": pack["id"], "used": False,
        "created_at": now.isoformat(), "expires_at": (now + timedelta(days=TOKEN_VALIDITY_DAYS)).isoformat()})
    base = os.environ.get("FRONTEND_PUBLIC_URL", "")
    link = f"{base}/api/cpc/recharge/checkout/{token}"
    from brevo_service import send_email
    try:
        await send_email(
            to_email=user["email"], to_name=user.get("full_name") or user.get("name"),
            subject=f"Recharge CPC en 1 clic — solde sous votre seuil ({s['threshold']} CPC)",
            html_content=f"""<h2 style="color:#451F6B;">Votre solde CPC est passé à {balance_after}</h2>
            <p>Bonjour,</p>
            <p>Conformément à votre paramétrage de recharge automatique (seuil : <strong>{s['threshold']} CPC</strong>),
            voici votre lien de paiement sécurisé pour le <strong>{pack['label']}</strong>
            ({pack['credits']} CPC — {pack['price_ht_cents'] / 100:.2f} € HT) :</p>
            <p style="margin:24px 0;"><a href="{link}"
            style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Recharger en 1 clic ({pack['credits']} CPC)</a></p>
            <p style="color:#777;font-size:12px;">Aucune carte n'est enregistrée et aucun débit n'a lieu sans votre validation
            sur la page de paiement Stripe. Lien valable {TOKEN_VALIDITY_DAYS} jours — paramétrable ou désactivable depuis votre
            Espace Vendeur, onglet CPC.</p>""",
            tags=["cpc-auto-recharge"])
        await db.cpc_recharge_settings.update_one({"user_id": user_id}, {"$set": {
            "alert_active": True, "last_alert_at": now.isoformat()}})
        logger.info("Recharge CPC : lien envoyé à %s (solde %d < seuil %d)", user["email"], balance_after, s["threshold"])
    except Exception as exc:
        logger.warning("Recharge CPC %s : %s", user_id, exc)
