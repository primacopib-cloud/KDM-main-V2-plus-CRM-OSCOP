"""Conversion d'une demande de devis en compte membre + objectif mensuel de conversion."""
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_password_hash
from core_deps import get_current_user, check_admin
from db import get_database
from models import UserInDB
from subscriptions import get_plan_default_credits

logger = logging.getLogger(__name__)
quote_convert_router = APIRouter(prefix="/api/admin/quotes", tags=["quote-convert"])


@quote_convert_router.put("/target")
async def set_quote_monthly_target(body: dict, current_user: dict = Depends(get_current_user)):
    """Définit l'objectif mensuel de devis convertis."""
    await check_admin(current_user)
    db = get_database()
    try:
        target = max(0, int(body.get("target", 0)))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Objectif invalide")
    await db.system_flags.update_one(
        {"key": "quote_monthly_target"},
        {"$set": {"target": target, "updated_by": current_user.get("email"),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    return {"ok": True, "target": target}


def _member_invite_html(name: str, email: str, password: str, role: str, login_url: str) -> str:
    role_label = "Vendeur Pro" if role == "vendor" else "Acheteur Pro"
    base = login_url.rsplit("/", 1)[0]
    if role == "vendor":
        steps = [
            ("Connectez-vous et personnalisez votre mot de passe",
             "Utilisez vos identifiants ci-dessus puis Mon compte → Changer le mot de passe."),
            ("Complétez votre profil et publiez vos premiers produits",
             f"Rendez-vous dans votre <a href='{base}/espace-vendeur' style='color:#D4AF37'>espace vendeur</a> pour présenter votre offre."),
            ("Répondez aux consultations d'achat",
             "Positionnez-vous sur les appels d'offres mutualisés pour décrocher vos premiers marchés."),
        ]
    else:
        steps = [
            ("Connectez-vous et personnalisez votre mot de passe",
             "Utilisez vos identifiants ci-dessus puis Mon compte → Changer le mot de passe."),
            ("Choisissez votre territoire et explorez le catalogue",
             f"Découvrez les <a href='{base}/catalogue' style='color:#D4AF37'>prix mutualisés du catalogue</a> de votre zone."),
            ("Passez votre première commande coopérative",
             "Paiement sécurisé en ligne ou à la livraison — l'équipe vous accompagne à chaque étape."),
        ]
    steps_html = "".join(
        f"<tr><td style='vertical-align:top;padding:8px 10px 8px 0'>"
        f"<span style='display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;"
        f"background:#D4AF37;color:#1F0A33;border-radius:50%;font-weight:bold'>{i}</span></td>"
        f"<td style='padding:8px 0'><b style='color:#fff'>{t}</b><br>"
        f"<span style='color:#ccc;font-size:13px'>{d}</span></td></tr>"
        for i, (t, d) in enumerate(steps, 1))
    return (
        "<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto'>"
        "<div style='background:#2A1045;border-radius:14px;padding:28px;color:#fff'>"
        "<h2 style='color:#D4AF37;margin-top:0'>Bienvenue sur KDMARCHÉ × O'SCOP</h2>"
        f"<p>Bonjour <b>{name}</b>,</p>"
        f"<p>Suite à votre demande de devis, votre compte <b>{role_label}</b> vient d'être créé "
        "sur la plateforme coopérative Communityplace.</p>"
        "<div style='background:rgba(255,255,255,0.08);border:1px solid #D4AF3766;border-radius:10px;padding:14px;margin:18px 0'>"
        f"<p style='margin:4px 0'>Identifiant : <b>{email}</b></p>"
        f"<p style='margin:4px 0'>Mot de passe temporaire : <b style='color:#E9CF8E'>{password}</b></p>"
        "</div>"
        "<h3 style='color:#E9CF8E;margin:22px 0 6px'>Vos 3 premières étapes</h3>"
        f"<table style='border-collapse:collapse'>{steps_html}</table>"
        f"<p style='text-align:center;margin:24px 0'><a href='{login_url}' "
        "style='background:#D4AF37;color:#1F0A33;padding:12px 26px;border-radius:999px;"
        "text-decoration:none;font-weight:bold'>Me connecter</a></p>"
        "</div>"
        "<p style='color:#999;font-size:11px;text-align:center;margin-top:14px'>"
        "KDMARCHÉ × O'SCOP — Plateforme coopérative B2B2C</p></div>"
    )


@quote_convert_router.post("/{quote_id}/convert-to-member")
async def convert_quote_to_member(quote_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    """Crée un compte membre (acheteur/vendeur) pré-rempli à partir d'une demande de devis."""
    await check_admin(current_user)
    db = get_database()
    quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    email = (quote.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="La demande ne contient pas d'email")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")

    role = "vendor" if body.get("role") == "vendor" else "buyer"
    contact = (f"{quote.get('first_name') or ''} {quote.get('last_name') or ''}".strip()
               or quote.get("contact_name") or quote.get("company") or email)
    temp_password = secrets.token_urlsafe(9)
    plan = "ess-acces-pro"
    user = UserInDB(
        email=email,
        password_hash=get_password_hash(temp_password),
        company_name=quote.get("company") or contact,
        siret=quote.get("siret") or "",
        contact_name=contact,
        phone=quote.get("phone") or "",
        subscription=plan,
        credits=await get_plan_default_credits(db, plan),
    )
    doc = user.dict()
    doc["role"] = role
    doc["from_quote_id"] = quote_id
    if role == "vendor":
        vendor_id = f"vendor-{uuid.uuid4().hex[:12]}"
        await db.vendors.insert_one({
            "id": vendor_id,
            "company_name": doc["company_name"],
            "contact_name": contact,
            "email": email,
            "phone": doc["phone"],
            "siret": doc["siret"] or f"quote-{quote_id[:8]}",
            "status": "pending",
            "credits": 0,
            "created_at": user.created_at.isoformat(),
        })
        doc["vendor_id"] = vendor_id
    await db.users.insert_one(doc)

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.quote_requests.update_one(
        {"id": quote_id},
        {"$set": {"status": "converted", "converted_user_id": user.id,
                  "converted_role": role, "member_invite_sent_at": now_iso},
         "$push": {"status_history": {"from": quote.get("status"), "to": "converted",
                                      "by": f"{current_user.get('email')} (conversion membre)",
                                      "at": now_iso}}})

    role_label = "Vendeur Pro" if role == "vendor" else "Acheteur Pro"
    email_sent = False
    if body.get("send_email", True):
        try:
            from brevo_service import send_email
            base = (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
            await send_email(
                to_email=email, to_name=contact,
                subject="Bienvenue sur KDMARCHÉ × O'SCOP — votre compte membre est prêt",
                html_content=_member_invite_html(contact, email, temp_password, role, f"{base}/connexion"),
                tags=["quote-member-invite"])
            email_sent = True
        except Exception as e:
            logger.warning("Email d'invitation membre non envoyé (%s): %s", email, e)

    logger.info("Devis %s converti en membre %s (%s) par %s", quote_id, email, role, current_user.get("email"))
    return {"ok": True, "user_id": user.id, "email": email, "role": role,
            "temp_password": temp_password, "email_sent": email_sent}
