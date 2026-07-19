"""Parcours d'adhésion Vendeur Pro : paiement CB (Stripe LIVE) → convention dynamique signée → activation → assistant produits gratuit."""
import asyncio
import base64
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr

from auth import get_password_hash, create_access_token, get_current_user_id, set_auth_cookie

logger = logging.getLogger(__name__)

vendor_onboarding_router = APIRouter(prefix="/api/vendor-onboarding", tags=["vendor-onboarding"])

db = None
CONVENTIONS_DIR = "/app/backend/uploads/conventions"


def set_vendor_onboarding_database(database):
    global db
    db = database


def _stripe_key() -> str:
    from routes_payment import _wallet_stripe_key
    return _wallet_stripe_key()


class StartBody(BaseModel):
    company: str
    contact_name: str
    email: EmailStr
    phone: str
    siret: str
    plan_slug: str
    origin_url: str


class ConventionFieldsBody(BaseModel):
    forme_sociale: Optional[str] = None
    capital: str
    rcs_ville: str
    adresse: str
    rep_nom: str
    rep_prenom: str
    rep_qualite: str
    territoires: List[str]
    lieu_signature: str


class SignBody(BaseModel):
    nom: str
    qualite: str
    lu_approuve: bool


class ActivateBody(BaseModel):
    token: str
    password: str


@vendor_onboarding_router.post("/start")
async def start_onboarding(body: StartBody):
    plan = await db.subscription_plans.find_one({"slug": body.plan_slug, "active": True}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=400, detail="Formule d'adhésion invalide")
    oid = str(uuid.uuid4())
    origin = body.origin_url.rstrip("/")
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(),
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": plan["price_cents"],
                "product_data": {"name": f"Adhésion Vendeur Pro — {plan['name']} (1er mois HT)"},
            },
            "quantity": 1,
        }],
        customer_email=body.email,
        success_url=f"{origin}/adhesion-vendeur?step=paid&onboarding_id={oid}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/adhesion-vendeur?step=cancelled&onboarding_id={oid}",
        metadata={"source": "vendor_onboarding", "onboarding_id": oid, "plan": body.plan_slug},
    )
    now = datetime.now(timezone.utc).isoformat()
    await db.vendor_onboarding.insert_one({
        "id": oid, "company": body.company, "contact_name": body.contact_name,
        "email": body.email.lower(), "phone": body.phone,
        "siret": "".join(c for c in body.siret if c.isdigit()),
        "plan_slug": body.plan_slug, "plan_name": plan["name"],
        "amount_cents": plan["price_cents"], "stripe_session_id": session.id,
        "status": "PAYMENT_PENDING", "created_at": now, "updated_at": now,
    })
    try:
        from company_extract import schedule_extract
        schedule_extract(db, body.siret, legal_name=body.company)
    except Exception:
        pass
    return {"onboarding_id": oid, "checkout_url": session.url}


async def _get_ob(oid: str) -> dict:
    ob = await db.vendor_onboarding.find_one({"id": oid}, {"_id": 0})
    if not ob:
        raise HTTPException(status_code=404, detail="Parcours d'adhésion introuvable")
    return ob


@vendor_onboarding_router.get("/{oid}/status")
async def onboarding_status(oid: str):
    ob = await _get_ob(oid)
    if ob["status"] == "PAYMENT_PENDING" and ob.get("stripe_session_id"):
        try:
            stripe.api_base = "https://api.stripe.com"
            session = stripe.checkout.Session.retrieve(ob["stripe_session_id"], api_key=_stripe_key())
            if session.payment_status == "paid":
                await db.vendor_onboarding.update_one(
                    {"id": oid}, {"$set": {"status": "PAID", "paid_at": datetime.now(timezone.utc).isoformat()}})
                ob["status"] = "PAID"
        except Exception as exc:
            logger.warning("Vérification Stripe onboarding %s : %s", oid, exc)
    return {"id": ob["id"], "status": ob["status"], "company": ob["company"],
            "plan_name": ob.get("plan_name"), "email": ob["email"],
            "convention": ob.get("convention"), "amount_cents": ob.get("amount_cents")}


@vendor_onboarding_router.post("/{oid}/convention-fields")
async def save_convention_fields(oid: str, body: ConventionFieldsBody):
    ob = await _get_ob(oid)
    if ob["status"] not in ("PAID", "INFO_COMPLETED"):
        raise HTTPException(status_code=400, detail="Le paiement doit être confirmé avant de compléter la convention")
    await db.vendor_onboarding.update_one({"id": oid}, {"$set": {
        "convention": body.dict(), "status": "INFO_COMPLETED",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    return {"status": "INFO_COMPLETED"}


@vendor_onboarding_router.get("/{oid}/convention.pdf")
async def convention_pdf(oid: str):
    ob = await _get_ob(oid)
    from vendor_convention import build_convention_pdf
    if ob["status"] == "SIGNED" or ob["status"] == "ACTIVATED":
        path = ob.get("signed_pdf_path")
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                pdf = f.read()
        else:
            pdf = build_convention_pdf(ob, ob.get("signature"))
    else:
        pdf = build_convention_pdf(ob, None)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="convention-adhesion-{oid[:8]}.pdf"'})


@vendor_onboarding_router.post("/{oid}/sign")
async def sign_convention(oid: str, body: SignBody):
    ob = await _get_ob(oid)
    if ob["status"] != "INFO_COMPLETED":
        raise HTTPException(status_code=400, detail="Complétez d'abord les informations de la convention")
    if not body.lu_approuve:
        raise HTTPException(status_code=400, detail="Vous devez cocher « Lu et approuvé » pour signer")
    now = datetime.now(timezone.utc)
    signature = {
        "nom": body.nom, "qualite": body.qualite,
        "signed_at": now.isoformat(),
        "signed_at_display": now.strftime("%d/%m/%Y à %H:%M UTC"),
        "verification_code": f"CONV-{secrets.token_hex(4).upper()}",
        "ip": "web",
    }
    from vendor_convention import build_convention_pdf
    pdf = build_convention_pdf(ob, signature)
    os.makedirs(CONVENTIONS_DIR, exist_ok=True)
    pdf_path = os.path.join(CONVENTIONS_DIR, f"convention-{oid}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf)

    activation_token = secrets.token_urlsafe(32)
    user = await db.users.find_one({"email": ob["email"]})
    if not user:
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": user_id, "email": ob["email"], "full_name": ob["contact_name"],
            "company_name": ob["company"], "siret": ob.get("siret"), "phone": ob.get("phone"),
            "role": "vendor", "account_type": "vendor", "is_admin": False,
            "is_active": False, "password_hash": get_password_hash(secrets.token_urlsafe(24)),
            "plan": ob.get("plan_slug"), "created_at": now,
        })
    else:
        user_id = user["id"]

    await db.vendor_onboarding.update_one({"id": oid}, {"$set": {
        "status": "SIGNED", "signature": signature, "signed_pdf_path": pdf_path,
        "user_id": user_id, "activation_token": activation_token,
        "updated_at": now.isoformat(),
    }})

    asyncio.create_task(_post_sign_tasks(oid, ob, signature, pdf, activation_token))
    return {"status": "SIGNED", "verification_code": signature["verification_code"]}


async def _post_sign_tasks(oid: str, ob: dict, signature: dict, pdf: bytes, activation_token: str):
    """GEDESS + email d'activation Brevo (avec convention signée en pièce jointe)."""
    try:
        from gedess_client import is_gedess_configured, gedess_upload_file
        if is_gedess_configured():
            doc = await gedess_upload_file(
                filename=f"convention-adhesion-{ob['company'][:30]}-{oid[:8]}.pdf",
                content=pdf, categorie="rapport",
                description=f"Convention-cadre tripartite V1.5 signée électroniquement — {ob['company']} ({signature['verification_code']}).",
                tags="communityplace,convention,adhesion-vendeur,signee",
                mime_type="application/pdf")
            await db.vendor_onboarding.update_one({"id": oid}, {"$set": {"ged_document_id": doc.get("id")}})
    except Exception as exc:
        logger.warning("Push GEDESS convention %s : %s", oid, exc)
    try:
        from brevo_service import send_email
        frontend = os.environ.get("FRONTEND_PUBLIC_URL", "")
        link = f"{frontend}/activation-vendeur?token={activation_token}"
        html = f"""
        <h2 style="color:#451F6B;">Bienvenue dans la Communityplace, {ob['contact_name']} !</h2>
        <p>Votre adhésion <strong>{ob.get('plan_name')}</strong> est payée et votre convention tripartite est signée
        (code de vérification : <strong>{signature['verification_code']}</strong> — copie jointe).</p>
        <p>Dernière étape : activez votre espace vendeur et choisissez votre mot de passe :</p>
        <p style="margin:24px 0;"><a href="{link}" style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Activer mon espace vendeur</a></p>
        <p style="color:#777;font-size:12px;">Vous pourrez ensuite soumettre vos produits, guidé pas à pas par notre assistant COOP'IA (gratuit).</p>
        """
        await send_email(
            to_email=ob["email"], to_name=ob["contact_name"],
            subject="Activez votre espace vendeur — convention signée ✔",
            html_content=html, tags=["vendor-activation"],
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"convention-signee-{oid[:8]}.pdf"}],
        )
    except Exception as exc:
        logger.warning("Email activation vendeur %s : %s", oid, exc)


@vendor_onboarding_router.post("/activate")
async def activate_account(body: ActivateBody, response: Response):
    ob = await db.vendor_onboarding.find_one({"activation_token": body.token}, {"_id": 0})
    if not ob:
        raise HTTPException(status_code=404, detail="Lien d'activation invalide ou expiré")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères")
    await db.users.update_one({"id": ob["user_id"]}, {"$set": {
        "is_active": True, "password_hash": get_password_hash(body.password),
    }})
    await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {
        "status": "ACTIVATED", "activated_at": datetime.now(timezone.utc).isoformat(),
    }})
    token = create_access_token(data={"sub": ob["user_id"]})
    set_auth_cookie(response, token)
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": ob["user_id"], "email": ob["email"], "role": "vendor", "company": ob["company"]}}


# ============ Assistant produits gratuit (COOP'IA) ============

class AssistantBody(BaseModel):
    question: str
    session_id: Optional[str] = None


ASSISTANT_PROMPT = (
    "Tu es COOP'IA, l'assistant GRATUIT d'accompagnement des vendeurs de Communityplace (KDMARCHÉ × O'SCOP). "
    "Ta mission : guider pas à pas le vendeur pour soumettre ses produits sur la plateforme. Étapes clés : "
    "1) Depuis l'Espace Vendeur, cliquer sur « Proposer un produit » ; 2) Renseigner nom, description, catégorie, "
    "photo, prix HT, conditionnement, volume disponible ; 3) Préciser le territoire de livraison et les conditions "
    "logistiques (chaîne du froid si applicable) ; 4) Soumettre — le produit passe en validation par l'équipe conformité ; "
    "5) Suivre le statut dans l'onglet « Mes produits ». Réponds en français, pas à pas, de façon simple et encourageante. "
    "Si la question sort de ce cadre, ramène poliment vers la soumission de produits."
)


@vendor_onboarding_router.post("/assistant")
async def product_assistant(body: AssistantBody, user_id: str = Depends(get_current_user_id)):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide")
    session_id = body.session_id or str(uuid.uuid4())
    history = await db.vendor_assistant_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1}
    ).sort("created_at", -1).limit(8).to_list(8)
    context = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in reversed(history))
    prompt = question if not context else f"Historique:\n{context}\n\nNouvelle question: {question}"
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY"), session_id=session_id,
                   system_message=ASSISTANT_PROMPT).with_model("openai", "gpt-5.4-mini")
    try:
        answer = await chat.send_message(UserMessage(text=prompt))
    except Exception as exc:
        logger.exception("Assistant produits : %s", exc)
        raise HTTPException(status_code=502, detail="Assistant momentanément indisponible")
    now = datetime.now(timezone.utc).isoformat()
    await db.vendor_assistant_messages.insert_many([
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id, "role": "user", "content": question, "created_at": now},
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": user_id, "role": "assistant", "content": answer or "", "created_at": now},
    ])
    return {"answer": answer, "session_id": session_id}
