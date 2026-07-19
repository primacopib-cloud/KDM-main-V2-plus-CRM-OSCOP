"""Parcours d'adhésion Vendeur Pro : paiement CB (Stripe LIVE) → convention dynamique signée → activation → assistant produits gratuit."""
import asyncio
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
    member_type: str = "vendor"
    locale: str = "fr"
    country: str = "GP"


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
    from vat import compute_vat
    vat = compute_vat(plan["price_cents"], body.country)
    vat_suffix = f" TTC — {vat['label']}" if vat["rate"] else f" HT — {vat['label']}"
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(),
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": vat["ttc_cents"],
                "recurring": {"interval": "month"},
                "product_data": {"name": f"Adhésion — {plan['name']} (mensuel{vat_suffix})"},
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
        "member_type": body.member_type if body.member_type else "vendor",
        "locale": body.locale if body.locale in ("fr", "en", "es") else "fr",
        "country": (body.country or "GP").upper(),
        "amount_ht_cents": vat["ht_cents"], "vat_rate": vat["rate"], "vat_cents": vat["vat_cents"],
        "plan_slug": body.plan_slug, "plan_name": plan["name"],
        "amount_cents": vat["ttc_cents"], "stripe_session_id": session.id,
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
    try:
        from routes_member_profiles import get_profile
        prof = await get_profile(ob.get("member_type", "vendor"))
        if prof:
            ob["convention_template"] = prof.get("convention_template")
    except Exception:
        pass
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
                    {"id": oid}, {"$set": {
                        "status": "PAID", "paid_at": datetime.now(timezone.utc).isoformat(),
                        "stripe_subscription_id": session.get("subscription"),
                        "stripe_customer_id": session.get("customer"),
                        "subscription_status": "active",
                    }})
                ob["status"] = "PAID"
        except Exception as exc:
            logger.warning("Vérification Stripe onboarding %s : %s", oid, exc)
    return {"id": ob["id"], "status": ob["status"], "company": ob["company"],
            "plan_name": ob.get("plan_name"), "email": ob["email"], "member_type": ob.get("member_type", "vendor"),
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
        member_type = ob.get("member_type", "vendor")
        await db.users.insert_one({
            "id": user_id, "email": ob["email"], "full_name": ob["contact_name"],
            "contact_name": ob["contact_name"], "company_name": ob["company"],
            "siret": ob.get("siret") or "", "phone": ob.get("phone") or "",
            "role": member_type, "account_type": member_type, "is_admin": False,
            "subscription": ob.get("plan_slug") or "ess-acces-pro", "credits": 0,
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
    """GEDESS + email d'activation Brevo multilingue (avec convention signée en pièce jointe)."""
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
        from vendor_emails import send_activation_email
        await send_activation_email({**ob, "id": oid, "signature": signature}, activation_token, pdf)
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
    existing_vendor = await db.vendors.find_one({"id": ob["user_id"]})
    from routes_member_profiles import get_profile
    profile = await get_profile(ob.get("member_type", "vendor")) or {}
    creates_vendor = profile.get("creates_vendor_record", ob.get("member_type", "vendor") == "vendor")
    if not existing_vendor and creates_vendor:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.vendors.insert_one({
            "id": ob["user_id"], "company_name": ob["company"], "contact_name": ob["contact_name"],
            "email": ob["email"], "phone": ob.get("phone") or "", "siret": ob.get("siret") or f"onb-{ob['id'][:12]}",
            "country": "GP",
            "status": "APPROVED", "approved_at": now_iso, "created_at": now_iso,
            "description": "", "source": "vendor_onboarding", "onboarding_id": ob["id"],
        })
    await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {
        "status": "ACTIVATED", "activated_at": datetime.now(timezone.utc).isoformat(),
    }})
    token = create_access_token(data={"sub": ob["user_id"]})
    set_auth_cookie(response, token)
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": ob["user_id"], "email": ob["email"], "role": ob.get("member_type", "vendor"),
                     "company": ob["company"], "space_route": profile.get("space_route")}}


# ============ Abonnement récurrent : webhooks & relances ============

async def handle_vendor_invoice_event(event_type: str, invoice: dict):
    """Appelé par le webhook Stripe pour invoice.paid / invoice.payment_failed."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    ob = await db.vendor_onboarding.find_one({"stripe_subscription_id": sub_id}, {"_id": 0})
    if not ob:
        return
    now = datetime.now(timezone.utc).isoformat()
    if event_type == "invoice.paid":
        await db.vendor_onboarding.update_one({"id": ob["id"]}, {
            "$set": {"subscription_status": "active", "last_renewal_at": now},
            "$push": {"renewals": {"at": now, "amount_cents": invoice.get("amount_paid"), "invoice_id": invoice.get("id")}},
        })
        if ob.get("access_suspended") or ob.get("first_payment_failure_at") or ob.get("suspension_warning_sent_at"):
            from vendor_suspension import reactivate_vendor_access
            await reactivate_vendor_access(ob)
        logger.info("Abonnement vendeur %s renouvelé (%s)", ob["company"], sub_id)
    elif event_type == "invoice.payment_failed":
        failure_update = {
            "subscription_status": "past_due", "last_payment_failure_at": now,
            "hosted_invoice_url": invoice.get("hosted_invoice_url"),
        }
        if not ob.get("first_payment_failure_at"):
            failure_update["first_payment_failure_at"] = now
        await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": failure_update})
        from vendor_emails import send_dunning_email
        await send_dunning_email(db, ob, invoice.get("hosted_invoice_url"))
        try:
            from core_deps import create_notification
            await create_notification(
                "subscription_past_due", "Prélèvement vendeur échoué",
                f"L'abonnement de {ob['company']} ({ob.get('plan_name')}) est en échec de prélèvement.",
                {"onboarding_id": ob["id"]})
        except Exception:
            pass


async def check_vendor_subscriptions(database):
    """Poll quotidien Stripe : synchronise le statut des abonnements et relance les impayés (1 email/jour)."""
    global db
    if db is None:
        db = database
    from vendor_emails import send_dunning_email
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = db.vendor_onboarding.find(
        {"stripe_subscription_id": {"$ne": None}, "status": {"$in": ["SIGNED", "ACTIVATED"]},
         "$or": [{"sub_checked_on": {"$ne": today}}, {"sub_checked_on": {"$exists": False}}]},
        {"_id": 0}).limit(50)
    async for ob in cursor:
        try:
            stripe.api_base = "https://api.stripe.com"
            sub = stripe.Subscription.retrieve(ob["stripe_subscription_id"], api_key=_stripe_key())
            await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {
                "subscription_status": sub.status, "sub_checked_on": today}})
            if sub.status in ("past_due", "unpaid"):
                await send_dunning_email(db, {**ob, "subscription_status": sub.status}, ob.get("hosted_invoice_url"))
        except Exception as exc:
            logger.warning("Check abonnement %s : %s", ob["id"], exc)


# ============ Admin : suivi des adhésions vendeurs ============

from lolodrive_helpers import require_admin  # noqa: E402


@vendor_onboarding_router.get("/admin/list")
async def admin_list_onboardings(admin: dict = Depends(require_admin)):
    items = await db.vendor_onboarding.find(
        {}, {"_id": 0, "activation_token": 0, "signed_pdf_path": 0}
    ).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items, "total": len(items)}


@vendor_onboarding_router.get("/admin/funnel")
async def admin_funnel(days: int = 0, admin: dict = Depends(require_admin)):
    """Entonnoir de conversion : adhésions initiées → payées → signées → activées (période optionnelle)."""
    match = {}
    if days > 0:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        match = {"created_at": {"$gte": cutoff}}
    counts = {}
    async for d in db.vendor_onboarding.aggregate([{"$match": match}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        counts[d["_id"]] = d["n"]
    started = sum(counts.values())
    paid = sum(v for k, v in counts.items() if k in ("PAID", "INFO_COMPLETED", "SIGNED", "ACTIVATED"))
    signed = counts.get("SIGNED", 0) + counts.get("ACTIVATED", 0)
    activated = counts.get("ACTIVATED", 0)
    return {"started": started, "paid": paid, "signed": signed, "activated": activated, "by_status": counts, "days": days}


@vendor_onboarding_router.get("/admin/export.csv")
async def admin_export_csv(admin: dict = Depends(require_admin)):
    """Export comptable des adhésions : statuts, montants, TVA et historique des relances."""
    import csv
    import io
    labels = {"activation": "Activation", "dunning": "Relance impayé", "warning": "Avertissement J+7",
              "suspended": "Suspension", "reactivated": "Réactivation", "sign_reminder": "Rappel signature",
              "resume": "Relance abandon", "resume2": "Rappel final abandon"}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["entreprise", "contact", "email", "telephone", "pays", "profil", "formule", "statut",
                "abonnement", "suspendu", "HT (EUR)", "TVA (EUR)", "TTC (EUR)", "taux TVA",
                "cree le", "paye le", "active le", "code convention", "relances"])
    async for ob in db.vendor_onboarding.find({}, {"_id": 0, "activation_token": 0, "signed_pdf_path": 0}).sort("created_at", -1):
        ttc = ob.get("amount_cents") or 0
        vatc = ob.get("vat_cents") or 0
        ht = ob.get("amount_ht_cents") or (ttc - vatc)
        rems = " | ".join(f"{labels.get(r['type'], r['type'])} {str(r.get('at'))[:10]}" for r in ob.get("reminders") or [])
        w.writerow([ob.get("company"), ob.get("contact_name"), ob.get("email"), ob.get("phone"),
                    ob.get("country") or "", ob.get("member_type"), ob.get("plan_name"), ob.get("status"),
                    ob.get("subscription_status") or "", "oui" if ob.get("access_suspended") else "",
                    f"{ht / 100:.2f}".replace(".", ","), f"{vatc / 100:.2f}".replace(".", ","),
                    f"{ttc / 100:.2f}".replace(".", ","), f"{ob.get('vat_rate') or 0}%",
                    str(ob.get("created_at"))[:10], str(ob.get("paid_at") or "")[:10],
                    str(ob.get("activated_at") or "")[:10],
                    (ob.get("signature") or {}).get("verification_code", ""), rems])
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="adhesions.csv"'})


@vendor_onboarding_router.post("/admin/{oid}/remind")
async def admin_remind(oid: str, admin: dict = Depends(require_admin)):
    ob = await db.vendor_onboarding.find_one({"id": oid}, {"_id": 0})
    if not ob:
        raise HTTPException(status_code=404, detail="Adhésion introuvable")
    frontend = os.environ.get("FRONTEND_PUBLIC_URL", "")
    from vendor_emails import send_activation_email, send_sign_reminder_email, send_resume_email
    lang = ob.get("locale") or "fr"
    if ob["status"] == "SIGNED":
        await send_activation_email(ob, ob.get("activation_token") or "", None)
        kind = "activation"
    elif ob["status"] in ("PAID", "INFO_COMPLETED"):
        await send_sign_reminder_email(ob, f"{frontend}/adhesion-vendeur?step=paid&onboarding_id={oid}&lang={lang}")
        kind = "signature"
    elif ob["status"] == "PAYMENT_PENDING":
        await send_resume_email(ob)
        kind = "paiement"
    else:
        raise HTTPException(status_code=400, detail="Cette adhésion est déjà active")
    await db.vendor_onboarding.update_one({"id": oid}, {"$set": {
        "last_remind_at": datetime.now(timezone.utc).isoformat(), "last_remind_by": admin.get("email")}})
    return {"reminded": True, "kind": kind}


@vendor_onboarding_router.get("/my-vendor")
async def my_vendor(user_id: str = Depends(get_current_user_id)):
    """Résout l'identifiant vendeur du compte connecté (espace vendeur)."""
    vendor = await db.vendors.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not vendor:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
        if user:
            vendor = await db.vendors.find_one({"email": user["email"]}, {"_id": 0, "id": 1})
    return {"vendor_id": (vendor or {}).get("id")}


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

