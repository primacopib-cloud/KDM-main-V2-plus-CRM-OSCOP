"""Emails transactionnels du cycle de vie vendeur — multilingues (FR/EN/ES) selon la locale de l'adhérent."""
import base64
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _locale(ob: dict) -> str:
    return ob.get("locale") if ob.get("locale") in ("en", "es") else "fr"


def _frontend() -> str:
    return os.environ.get("FRONTEND_PUBLIC_URL", "")


def _btn(link: str, label: str) -> str:
    if not link:
        return ""
    return (f'<p style="margin:24px 0;"><a href="{link}" style="background:#D4AF37;color:#1F0A33;'
            f'padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">{label}</a></p>')


EMAILS = {
    "activation": {
        "fr": {
            "subject": "Activez votre espace — convention signée ✔",
            "attached": " — copie jointe",
            "btn": "Activer mon espace",
            "html": """<h2 style="color:#451F6B;">Bienvenue dans la Communityplace, {name} !</h2>
<p>Votre adhésion <strong>{plan}</strong> est payée et votre convention tripartite est signée
(code de vérification : <strong>{code}</strong>{attached}).</p>
<p>Dernière étape : activez votre espace et choisissez votre mot de passe :</p>
{btn}
<p style="color:#777;font-size:12px;">Vous pourrez ensuite soumettre vos produits, guidé pas à pas par notre assistant COOP'IA (gratuit).</p>""",
        },
        "en": {
            "subject": "Activate your space — agreement signed ✔",
            "attached": " — copy attached",
            "btn": "Activate my space",
            "html": """<h2 style="color:#451F6B;">Welcome to the Communityplace, {name}!</h2>
<p>Your <strong>{plan}</strong> membership is paid and your tripartite agreement is signed
(verification code: <strong>{code}</strong>{attached}).</p>
<p>Last step: activate your space and choose your password:</p>
{btn}
<p style="color:#777;font-size:12px;">You will then be able to submit your products, guided step by step by our COOP'IA assistant (free).</p>""",
        },
        "es": {
            "subject": "Active su espacio — convenio firmado ✔",
            "attached": " — copia adjunta",
            "btn": "Activar mi espacio",
            "html": """<h2 style="color:#451F6B;">¡Bienvenido a la Communityplace, {name}!</h2>
<p>Su adhesión <strong>{plan}</strong> está pagada y su convenio tripartito está firmado
(código de verificación: <strong>{code}</strong>{attached}).</p>
<p>Último paso: active su espacio y elija su contraseña:</p>
{btn}
<p style="color:#777;font-size:12px;">Después podrá enviar sus productos, guiado paso a paso por nuestro asistente COOP'IA (gratuito).</p>""",
        },
    },
    "dunning": {
        "fr": {
            "subject": "⚠ Échec de prélèvement — régularisez votre adhésion",
            "btn": "Régulariser mon paiement",
            "html": """<h2 style="color:#451F6B;">Prélèvement refusé</h2>
<p>Bonjour {name},</p>
<p>Le prélèvement mensuel de votre adhésion <strong>{plan}</strong> a échoué.
Une nouvelle tentative automatique sera effectuée par notre prestataire de paiement,
et nous vous relancerons chaque jour jusqu'à régularisation.</p>
{btn}
<p style="color:#777;font-size:12px;">Sans régularisation, l'accès à votre espace vendeur pourra être suspendu.</p>""",
        },
        "en": {
            "subject": "⚠ Payment failed — settle your membership",
            "btn": "Settle my payment",
            "html": """<h2 style="color:#451F6B;">Payment declined</h2>
<p>Hello {name},</p>
<p>The monthly payment for your <strong>{plan}</strong> membership has failed.
Our payment provider will automatically retry, and we will remind you every day until it is settled.</p>
{btn}
<p style="color:#777;font-size:12px;">Without settlement, access to your seller space may be suspended.</p>""",
        },
        "es": {
            "subject": "⚠ Fallo en el cobro — regularice su adhesión",
            "btn": "Regularizar mi pago",
            "html": """<h2 style="color:#451F6B;">Cobro rechazado</h2>
<p>Hola {name}:</p>
<p>El cobro mensual de su adhesión <strong>{plan}</strong> ha fallado.
Nuestro proveedor de pago realizará un nuevo intento automático,
y le recordaremos cada día hasta la regularización.</p>
{btn}
<p style="color:#777;font-size:12px;">Sin regularización, el acceso a su espacio vendedor podrá ser suspendido.</p>""",
        },
    },
    "warning": {
        "fr": {
            "subject": "⚠ Dernier rappel — suspension de votre espace vendeur imminente",
            "btn": "Régulariser mon paiement",
            "html": """<h2 style="color:#451F6B;">Impayé depuis {days} jours</h2>
<p>Bonjour {name},</p>
<p>Le prélèvement de votre adhésion <strong>{plan}</strong> est impayé depuis {days} jours.
Sans régularisation sous {remaining} jour(s), l'accès à votre espace vendeur sera automatiquement suspendu.</p>
{btn}""",
        },
        "en": {
            "subject": "⚠ Final reminder — your seller space is about to be suspended",
            "btn": "Settle my payment",
            "html": """<h2 style="color:#451F6B;">Unpaid for {days} days</h2>
<p>Hello {name},</p>
<p>The payment for your <strong>{plan}</strong> membership has been outstanding for {days} days.
Without settlement within {remaining} day(s), access to your seller space will be automatically suspended.</p>
{btn}""",
        },
        "es": {
            "subject": "⚠ Último aviso — suspensión inminente de su espacio vendedor",
            "btn": "Regularizar mi pago",
            "html": """<h2 style="color:#451F6B;">Impago desde hace {days} días</h2>
<p>Hola {name}:</p>
<p>El cobro de su adhesión <strong>{plan}</strong> lleva {days} días impagado.
Sin regularización en {remaining} día(s), el acceso a su espacio vendedor será suspendido automáticamente.</p>
{btn}""",
        },
    },
    "suspended": {
        "fr": {
            "subject": "🔒 Espace vendeur suspendu — impayé de plus de 15 jours",
            "btn": "Régulariser mon paiement",
            "html": """<h2 style="color:#451F6B;">Votre espace vendeur est suspendu</h2>
<p>Bonjour {name},</p>
<p>Malgré nos relances, le prélèvement de votre adhésion <strong>{plan}</strong>
est impayé depuis plus de 15 jours. L'accès à votre espace vendeur est suspendu.</p>
{btn}
<p style="color:#777;font-size:12px;">Votre espace sera réactivé automatiquement dès réception du paiement.</p>""",
        },
        "en": {
            "subject": "🔒 Seller space suspended — unpaid for more than 15 days",
            "btn": "Settle my payment",
            "html": """<h2 style="color:#451F6B;">Your seller space is suspended</h2>
<p>Hello {name},</p>
<p>Despite our reminders, the payment for your <strong>{plan}</strong> membership
has been outstanding for more than 15 days. Access to your seller space is suspended.</p>
{btn}
<p style="color:#777;font-size:12px;">Your space will be reactivated automatically upon receipt of payment.</p>""",
        },
        "es": {
            "subject": "🔒 Espacio vendedor suspendido — impago de más de 15 días",
            "btn": "Regularizar mi pago",
            "html": """<h2 style="color:#451F6B;">Su espacio vendedor está suspendido</h2>
<p>Hola {name}:</p>
<p>A pesar de nuestros avisos, el cobro de su adhesión <strong>{plan}</strong>
lleva más de 15 días impagado. El acceso a su espacio vendedor está suspendido.</p>
{btn}
<p style="color:#777;font-size:12px;">Su espacio se reactivará automáticamente en cuanto se reciba el pago.</p>""",
        },
    },
    "reactivated": {
        "fr": {
            "subject": "✅ Espace vendeur réactivé — merci pour votre paiement",
            "html": """<h2 style="color:#451F6B;">Votre espace vendeur est réactivé</h2>
<p>Bonjour {name},</p>
<p>Votre paiement a bien été reçu : l'accès à votre espace vendeur
<strong>{plan}</strong> est de nouveau actif. Merci !</p>""",
        },
        "en": {
            "subject": "✅ Seller space reactivated — thank you for your payment",
            "html": """<h2 style="color:#451F6B;">Your seller space is reactivated</h2>
<p>Hello {name},</p>
<p>Your payment has been received: access to your <strong>{plan}</strong>
seller space is active again. Thank you!</p>""",
        },
        "es": {
            "subject": "✅ Espacio vendedor reactivado — gracias por su pago",
            "html": """<h2 style="color:#451F6B;">Su espacio vendedor está reactivado</h2>
<p>Hola {name}:</p>
<p>Su pago ha sido recibido: el acceso a su espacio vendedor
<strong>{plan}</strong> vuelve a estar activo. ¡Gracias!</p>""",
        },
    },
    "sign_reminder": {
        "fr": {
            "subject": "Finalisez votre adhésion — signature de votre convention",
            "btn": "Signer ma convention",
            "html": """<p>Bonjour {name},</p>
<p>Votre paiement est bien enregistré. Il ne reste qu'à compléter et signer votre convention :</p>
{btn}""",
        },
        "en": {
            "subject": "Finalize your membership — sign your agreement",
            "btn": "Sign my agreement",
            "html": """<p>Hello {name},</p>
<p>Your payment has been recorded. All that remains is to complete and sign your agreement:</p>
{btn}""",
        },
        "es": {
            "subject": "Finalice su adhesión — firma de su convenio",
            "btn": "Firmar mi convenio",
            "html": """<p>Hola {name}:</p>
<p>Su pago ha quedado registrado. Solo falta completar y firmar su convenio:</p>
{btn}""",
        },
    },
    "resume": {
        "fr": {
            "subject": "Votre adhésion vous attend — reprenez là où vous en étiez",
            "btn": "Reprendre mon adhésion",
            "html": """<p>Bonjour {name},</p>
<p>Votre adhésion <strong>{plan}</strong> n'a pas été finalisée. Reprenez votre inscription en un clic :</p>
{btn}
<p style="color:#777;font-size:12px;">Paiement sécurisé, convention signée en ligne, activation immédiate.</p>""",
        },
        "en": {
            "subject": "Your membership is waiting — pick up where you left off",
            "btn": "Resume my membership",
            "html": """<p>Hello {name},</p>
<p>Your <strong>{plan}</strong> membership was not finalized. Resume your registration in one click:</p>
{btn}
<p style="color:#777;font-size:12px;">Secure payment, agreement signed online, immediate activation.</p>""",
        },
        "es": {
            "subject": "Su adhesión le espera — retome donde lo dejó",
            "btn": "Retomar mi adhesión",
            "html": """<p>Hola {name}:</p>
<p>Su adhesión <strong>{plan}</strong> no fue finalizada. Retome su inscripción con un clic:</p>
{btn}
<p style="color:#777;font-size:12px;">Pago seguro, convenio firmado en línea, activación inmediata.</p>""",
        },
    },
}


def _tpl(kind: str, ob: dict) -> dict:
    return EMAILS[kind].get(_locale(ob), EMAILS[kind]["fr"])


async def send_activation_email(ob: dict, activation_token: str, pdf: bytes | None = None):
    from brevo_service import send_email
    t = _tpl("activation", ob)
    link = f"{_frontend()}/activation-vendeur?token={activation_token}&lang={_locale(ob)}"
    code = (ob.get("signature") or {}).get("verification_code", "")
    html = t["html"].format(name=ob["contact_name"], plan=ob.get("plan_name"), code=code,
                            attached=t["attached"] if pdf else "", btn=_btn(link, t["btn"]))
    attachments = [{"content": base64.b64encode(pdf).decode(), "name": f"convention-signee-{ob['id'][:8]}.pdf"}] if pdf else None
    await send_email(to_email=ob["email"], to_name=ob["contact_name"], subject=t["subject"],
                     html_content=html, tags=["vendor-activation"], attachments=attachments)


async def send_dunning_email(db, ob: dict, invoice_url: str | None = None):
    """Relance impayé — dédupliquée à 1 email/jour."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if ob.get("dunning_sent_on") == today:
        return
    try:
        from brevo_service import send_email
        t = _tpl("dunning", ob)
        link = invoice_url or ob.get("hosted_invoice_url") or ""
        html = t["html"].format(name=ob.get("contact_name"), plan=ob.get("plan_name"), btn=_btn(link, t["btn"]))
        await send_email(to_email=ob["email"], to_name=ob.get("contact_name"), subject=t["subject"],
                         html_content=html, tags=["vendor-dunning"])
        await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {"dunning_sent_on": today}})
        logger.info("Relance impayé envoyée à %s", ob["email"])
    except Exception as exc:
        logger.warning("Relance impayé %s : %s", ob.get("id"), exc)


async def _send_simple(ob: dict, kind: str, **params):
    try:
        from brevo_service import send_email
        t = _tpl(kind, ob)
        link = params.pop("link", ob.get("hosted_invoice_url") or "")
        html = t["html"].format(name=ob.get("contact_name"), plan=ob.get("plan_name"),
                                btn=_btn(link, t.get("btn", "")), **params)
        await send_email(to_email=ob["email"], to_name=ob.get("contact_name"), subject=t["subject"],
                         html_content=html, tags=[f"vendor-{kind.replace('_', '-')}"])
    except Exception as exc:
        logger.warning("Email %s %s : %s", kind, ob.get("id"), exc)


async def send_warning_email(ob: dict, days: int, remaining: int):
    await _send_simple(ob, "warning", days=days, remaining=remaining)


async def send_suspended_email(ob: dict):
    await _send_simple(ob, "suspended")


async def send_reactivated_email(ob: dict):
    await _send_simple(ob, "reactivated")


async def send_sign_reminder_email(ob: dict, link: str):
    await _send_simple(ob, "sign_reminder", link=link)


async def send_resume_email(ob: dict, link: str | None = None):
    link = link or f"{_frontend()}/adhesion-vendeur?plan={ob.get('plan_slug') or ''}&lang={_locale(ob)}"
    await _send_simple(ob, "resume", link=link)


async def check_abandoned_onboardings(db):
    """Cron : 1 email de reprise pour les adhésions abandonnées avant paiement (entre 1h et 7 jours)."""
    now = datetime.now(timezone.utc)
    cursor = db.vendor_onboarding.find(
        {"status": "PAYMENT_PENDING", "abandon_reminder_sent_at": {"$exists": False}},
        {"_id": 0}).limit(50)
    async for ob in cursor:
        try:
            created = datetime.fromisoformat(str(ob.get("created_at")).replace("Z", "+00:00"))
            age_h = (now - created).total_seconds() / 3600
            if age_h < 1:
                continue
            if age_h > 24 * 7:
                await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {"abandon_reminder_sent_at": "expired"}})
                continue
            await send_resume_email(ob)
            await db.vendor_onboarding.update_one({"id": ob["id"]}, {"$set": {"abandon_reminder_sent_at": now.isoformat()}})
            logger.info("Relance adhésion abandonnée envoyée à %s", ob["email"])
        except Exception as exc:
            logger.warning("Relance abandon %s : %s", ob.get("id"), exc)
