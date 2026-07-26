"""Alertes incoterm favori : préférences adhérent + notification à l'arrivée d'un produit correspondant."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
import logging

from vendor_models import ALLOWED_INCOTERMS

logger = logging.getLogger(__name__)

incoterm_alerts_router = APIRouter(prefix="/api/v2/catalog")

db = None


def set_incoterm_alerts_database(database):
    global db
    db = database


async def _require_user(request: Request):
    from auth import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    user = await db.users.find_one({"id": user_id}) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")
    return user


class AlertCodes(BaseModel):
    codes: List[str]


@incoterm_alerts_router.get("/incoterm-alerts")
async def get_incoterm_alerts(request: Request):
    """Incoterms suivis par l'adhérent connecté."""
    user = await _require_user(request)
    return {"codes": user.get("favorite_incoterms") or []}


@incoterm_alerts_router.put("/incoterm-alerts")
async def set_incoterm_alerts(body: AlertCodes, request: Request):
    """Met à jour la liste des incoterms suivis."""
    user = await _require_user(request)
    codes = [c.upper() for c in body.codes if c.upper() in ALLOWED_INCOTERMS]
    await db.users.update_one({"id": user["id"]}, {"$set": {"favorite_incoterms": codes}})
    return {"success": True, "codes": codes}


_EMAIL_I18N = {
    "fr": {
        "subject": "Nouveau produit livrable en {codes} — KDMARCHÉ",
        "hello": "Bonjour",
        "body": "Le produit <strong>{name}</strong> vient d'arriver au catalogue avec l'incoterm <strong>{codes}</strong> que vous suivez.",
        "btn": "Voir la fiche produit",
        "footer": "Vous recevez cet email car vous suivez cet incoterm. Gérez vos alertes depuis votre espace.",
    },
    "en": {
        "subject": "New product available in {codes} — KDMARCHÉ",
        "hello": "Hello",
        "body": "The product <strong>{name}</strong> has just arrived in the catalog with the <strong>{codes}</strong> incoterm you follow.",
        "btn": "View the product",
        "footer": "You receive this email because you follow this incoterm. Manage your alerts from your space.",
    },
    "es": {
        "subject": "Nuevo producto disponible en {codes} — KDMARCHÉ",
        "hello": "Hola",
        "body": "El producto <strong>{name}</strong> acaba de llegar al catálogo con el incoterm <strong>{codes}</strong> que usted sigue.",
        "btn": "Ver el producto",
        "footer": "Recibe este correo porque sigue este incoterm. Gestione sus alertas desde su espacio.",
    },
    "gcf": {
        "subject": "Nouvo pwodui ka rivé an {codes} — KDMARCHÉ",
        "hello": "Bonjou",
        "body": "Pwodui <strong>{name}</strong> fèk rivé an katalog-la èvè incoterm <strong>{codes}</strong> ou ka suiv.",
        "btn": "Gadé fich pwodui-la",
        "footer": "Ou ka risivwè imel-lasa pas ou ka suiv incoterm-lasa. Jéré alèt a'w adan espas a'w.",
    },
}


async def _send_watcher_email(watcher: dict, product: dict, matched: list):
    import os
    from brevo_service import send_email
    email = watcher.get("email")
    if not email:
        return
    lang = watcher.get("preferred_language") or "fr"
    t = _EMAIL_I18N.get(lang, _EMAIL_I18N["fr"])
    codes = ", ".join(matched)
    base = os.environ.get("PUBLIC_BASE_URL") or "https://kdmarche-oscop.fr"
    link = f"{base}/catalogue?produit={product.get('id')}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#451F6B;">{t['subject'].format(codes=codes)}</h2>
      <p>{t['hello']} {watcher.get('contact_name') or ''},</p>
      <p>{t['body'].format(name=product.get('name'), codes=codes)}</p>
      <p><a href="{link}" style="display:inline-block;background:#D9B35A;color:#2A1045;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">{t['btn']}</a></p>
      <p style="color:#777;font-size:12px;margin-top:24px;">{t['footer']}</p>
    </div>
    """
    await send_email(to_email=email, to_name=watcher.get("contact_name") or None,
                     subject=t["subject"].format(codes=codes), html_content=html,
                     tags=["incoterm-alert"])


async def notify_incoterm_watchers(database, product: dict):
    """Notifie (in-app + email) les adhérents dont un incoterm favori correspond au nouveau produit publié."""
    codes = sorted({c for lst in (product.get("incoterms") or {}).values() for c in (lst or [])})
    if not codes:
        return 0
    from core_deps import create_notification
    watchers = await database.users.find(
        {"favorite_incoterms": {"$in": codes}},
        {"_id": 0, "id": 1, "email": 1, "contact_name": 1, "preferred_language": 1, "favorite_incoterms": 1},
    ).to_list(500)
    sent = 0
    for w in watchers:
        matched = sorted(set(w.get("favorite_incoterms") or []) & set(codes))
        await create_notification(
            notification_type="product_incoterm_match",
            title=f"Nouveau produit livrable en {', '.join(matched)}",
            message=f"« {product.get('name')} » vient d'arriver au catalogue avec l'incoterm {', '.join(matched)} que vous suivez.",
            target_roles=[],
            target_user_id=w["id"],
            data={"link": f"/catalogue?produit={product.get('id')}", "product_id": product.get("id")},
        )
        try:
            await _send_watcher_email(w, product, matched)
        except Exception as exc:
            logger.warning("Email alerte incoterm non envoyé à %s : %s", w.get("email"), exc)
        sent += 1
    if sent:
        logger.info("Alertes incoterm : %d adhérent(s) notifié(s) pour %s (%s)", sent, product.get("id"), codes)
    return sent
