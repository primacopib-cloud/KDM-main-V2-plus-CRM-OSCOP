"""Programme de parrainage vendeur : code unique, bonus CREDI'SCOP au parrain
à la première inscription du filleul à une consultation."""
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

referral_router = APIRouter(prefix="/api/referral", tags=["referral"])

db = None


def set_referral_database(database):
    global db
    db = database


def _code_for(user_id: str) -> str:
    return "KDM-" + hashlib.sha256(f"parrain:{user_id}".encode()).hexdigest()[:6].upper()


async def _require_member(user_id: str) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if (user.get("role") or "").lower() not in ("vendor", "buyer"):
        raise HTTPException(status_code=403, detail="Réservé aux membres de la plateforme")
    return user


@referral_router.get("/me")
async def my_referral(user_id: str = Depends(get_current_user_id)):
    await _require_member(user_id)
    code = _code_for(user_id)
    await db.referral_codes.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"code": code, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    links = await db.referral_links.find({"sponsor_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    from routes_cpc_admin import get_cpc_settings
    bonus = (await get_cpc_settings()).get("referral_bonus", 10)
    mine = await db.referral_links.find_one({"filleul_id": user_id}, {"_id": 0, "code": 1})
    return {"code": code, "bonus": bonus,
            "total_earned": sum(l.get("bonus_amount", 0) for l in links if l.get("bonus_paid")),
            "referred": [{"email": l.get("filleul_email"), "bonus_paid": l.get("bonus_paid", False),
                          "created_at": l.get("created_at")} for l in links],
            "my_sponsor_code": (mine or {}).get("code")}


class ClaimBody(BaseModel):
    code: str


@referral_router.post("/claim")
async def claim_code(body: ClaimBody, user_id: str = Depends(get_current_user_id)):
    user = await _require_member(user_id)
    code = body.code.strip().upper()
    if code == _code_for(user_id):
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas utiliser votre propre code")
    sponsor = await db.referral_codes.find_one({"code": code}, {"_id": 0})
    if not sponsor:
        raise HTTPException(status_code=404, detail="Code parrain introuvable")
    if await db.referral_links.find_one({"filleul_id": user_id}, {"_id": 0, "code": 1}):
        raise HTTPException(status_code=409, detail="Un code parrain a déjà été enregistré pour votre compte")
    if await db.consultation_entries.find_one({"vendor_user_id": user_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=409, detail="Le parrainage est réservé aux vendeurs n'ayant pas encore participé à une consultation")
    await db.referral_links.insert_one({
        "filleul_id": user_id, "filleul_email": user.get("email"),
        "sponsor_id": sponsor["user_id"], "code": code, "bonus_paid": False,
        "created_at": datetime.now(timezone.utc).isoformat()})
    await audit("REFERRAL_CLAIMED", user_id, None, {"code": code, "sponsor_id": sponsor["user_id"]})
    import asyncio as _asyncio
    _asyncio.create_task(_notify_sponsor_new_filleul(sponsor["user_id"], user.get("email")))
    return {"ok": True, "message": "Code parrain enregistré — votre parrain recevra son bonus lors de votre première inscription à une consultation ou première commande"}


async def _notify_sponsor_new_filleul(sponsor_id: str, filleul_email: str):
    """Email au parrain dès qu'un filleul s'inscrit avec son code."""
    try:
        sponsor = await db.users.find_one({"id": sponsor_id}, {"email": 1, "first_name": 1})
        if not sponsor or not sponsor.get("email"):
            return
        from routes_cpc_admin import get_cpc_settings
        bonus = (await get_cpc_settings()).get("referral_bonus", 10)
        import os as _os
        base = _os.environ.get("FRONTEND_URL", "").rstrip("/")
        from brevo_service import send_email
        await send_email(
            to_email=sponsor["email"], to_name=sponsor.get("first_name"),
            subject="🎉 Un nouveau filleul vient d'utiliser votre code parrain !",
            html_content=("<div style='font-family:Arial,sans-serif;max-width:560px'><p>Bonne nouvelle !</p>"
                          f"<p><b>{filleul_email}</b> vient de s'inscrire avec votre code parrain. "
                          f"Vous recevrez <b>+{bonus} CREDI'SCOP</b> dès sa première commande ou inscription à une consultation.</p>"
                          "<p>Continuez à partager votre code pour grimper au classement du défi parrainage du mois !</p>"
                          f"<p><a href='{base}/espace-acheteur' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Voir mon parrainage</a></p>"
                          "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p></div>"),
            tags=["referral-new-filleul"])
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Email nouveau filleul échoué : %s", exc)


@referral_router.get("/admin/overview")
async def referral_admin_overview(admin: dict = Depends(require_admin)):
    """Tableau parrainage admin : liens, bonus versés, meilleurs ambassadeurs."""
    links = await db.referral_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    sponsor_ids = list({l["sponsor_id"] for l in links})
    sponsors = {}
    if sponsor_ids:
        async for u in db.users.find({"id": {"$in": sponsor_ids}}, {"_id": 0, "id": 1, "email": 1}):
            sponsors[u["id"]] = u.get("email", u["id"])
    by_sponsor = {}
    for l in links:
        s = by_sponsor.setdefault(l["sponsor_id"], {"sponsor": sponsors.get(l["sponsor_id"], l["sponsor_id"]),
                                                    "referred": 0, "bonus_paid": 0, "credited": 0})
        s["referred"] += 1
        if l.get("bonus_paid"):
            s["bonus_paid"] += 1
            s["credited"] += l.get("bonus_amount", 0)
    top = sorted(by_sponsor.values(), key=lambda s: (s["credited"], s["referred"]), reverse=True)[:10]
    return {
        "total_links": len(links),
        "total_bonus_paid": sum(1 for l in links if l.get("bonus_paid")),
        "total_credited": sum(l.get("bonus_amount", 0) for l in links if l.get("bonus_paid")),
        "top_ambassadors": top,
        "links": [{"sponsor": sponsors.get(l["sponsor_id"], l["sponsor_id"]),
                   "filleul": l.get("filleul_email"), "bonus_paid": l.get("bonus_paid", False),
                   "bonus_amount": l.get("bonus_amount"), "created_at": l.get("created_at"),
                   "bonus_paid_at": l.get("bonus_paid_at")} for l in links[:100]],
    }


async def maybe_pay_referral_bonus(filleul_id: str, event_label: str = "première inscription à une consultation"):
    """Appelé après une première inscription à une consultation OU une première commande :
    verse le bonus au parrain + le bonus de bienvenue au filleul (une seule fois)."""
    link = await db.referral_links.find_one({"filleul_id": filleul_id, "bonus_paid": False}, {"_id": 0})
    if not link:
        return
    from routes_cpc_admin import get_cpc_settings
    from cpc_ledger import add_cpc_movement
    settings = await get_cpc_settings()
    bonus = settings.get("referral_bonus", 10)
    entry = await add_cpc_movement(
        link["sponsor_id"], "PROMO_GRANT", bonus,
        idempotency_key=f"referral:{filleul_id}",
        reason=f"Bonus parrainage — {event_label} de {link.get('filleul_email', 'votre filleul')}")
    if entry is None:
        return
    welcome = settings.get("referral_welcome_bonus", 5)
    from routes_prefs import channel_allowed
    if welcome > 0:
        w_entry = await add_cpc_movement(
            filleul_id, "PROMO_GRANT", welcome,
            idempotency_key=f"referral-welcome:{filleul_id}",
            reason=f"Bonus de bienvenue parrainage — {event_label}")
        if w_entry:
            try:
                if await channel_allowed(filleul_id, "referral_welcome", "inapp"):
                    from core_deps import create_notification
                    await create_notification("referral_welcome", f"Bienvenue : +{welcome} CREDI'SCOP offerts",
                                          f"Votre bonus de bienvenue parrainage a été crédité (solde : {w_entry['balance_after']}).",
                                          target_roles=["direct"], target_user_id=filleul_id,
                                          data={"link": "/vendor?tab=cpc"})
            except Exception as exc:
                logger.warning("Notif bienvenue filleul %s : %s", filleul_id, exc)
    try:
        if await channel_allowed(link["sponsor_id"], "referral_bonus", "inapp"):
            from core_deps import create_notification
            await create_notification("referral_bonus", f"Parrainage réussi : +{bonus} CREDI'SCOP",
                                  f"Votre filleul {link.get('filleul_email')} s'est inscrit à sa première consultation (solde : {entry['balance_after']}).",
                                  target_roles=["direct"], target_user_id=link["sponsor_id"],
                                  data={"link": "/vendor?tab=cpc"})
    except Exception as exc:
        logger.warning("Notif bonus parrain %s : %s", link["sponsor_id"], exc)
    now = datetime.now(timezone.utc).isoformat()
    await db.referral_links.update_one({"filleul_id": filleul_id}, {"$set": {
        "bonus_paid": True, "bonus_amount": bonus, "bonus_paid_at": now}})
    await audit("REFERRAL_BONUS_PAID", "system", None,
                {"sponsor_id": link["sponsor_id"], "filleul_id": filleul_id, "bonus": bonus})
    sponsor = await db.users.find_one({"id": link["sponsor_id"]}, {"_id": 0, "email": 1, "full_name": 1, "name": 1})
    if sponsor and sponsor.get("email") and await channel_allowed(link["sponsor_id"], "referral_bonus", "email"):
        try:
            from brevo_service import send_email
            await send_email(
                to_email=sponsor["email"], to_name=sponsor.get("full_name") or sponsor.get("name"),
                subject=f"Parrainage réussi — +{bonus} CREDI'SCOP crédités",
                html_content=f"""<h2 style="color:#451F6B;">Félicitations, votre parrainage a porté ses fruits !</h2>
                <p>Votre filleul <strong>{link.get('filleul_email')}</strong> vient de s'inscrire à sa première
                consultation compétitive. <strong>+{bonus} CREDI'SCOP</strong> ont été crédités sur votre compte
                (solde : {entry['balance_after']}).</p>
                <p style="color:#777;font-size:12px;">Bonus tracé au registre CREDI'SCOP — programme de parrainage KDMARCHÉ × O'SCOP.</p>""",
                tags=["referral-bonus"])
        except Exception as exc:
            logger.warning("Email bonus parrainage %s : %s", sponsor["email"], exc)
    logger.info("Parrainage : +%d CREDI'SCOP versés à %s (filleul %s)", bonus, link["sponsor_id"], filleul_id)
