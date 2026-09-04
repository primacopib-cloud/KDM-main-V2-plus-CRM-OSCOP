"""Liens de paiement Stripe personnalisés créés par le super admin — /api/admin/payment-links."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from admin_guard import require_admin
from auth import get_current_user_id
from stripe_accounts import get_stripe_key

logger = logging.getLogger(__name__)

payment_links_router = APIRouter(prefix="/api/admin/payment-links", tags=["Admin Payment Links"])

db = None


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)

ACCOUNT_TYPES = {
    "VENDOR_PRO": "Adhésion Vendeur Pro",
    "BUYER_PRO": "Adhésion Acheteur Pro",
    "SPONSOR": "Sponsoring",
}


def set_payment_links_database(database) -> None:
    global db
    db = database


def _stripe_key() -> str:
    key = get_stripe_key("oscop")
    if not key:
        raise HTTPException(status_code=500, detail="Clé Stripe non configurée")
    stripe.api_base = "https://api.stripe.com"
    return key


class CreateLinkPayload(BaseModel):
    email: EmailStr
    amount_eur: float = Field(..., gt=0)
    account_type: str
    description: Optional[str] = None


STRIPE_MAX_CENTS = 99_999_999  # 999 999,99 € — plafond Stripe par transaction


class SplitPayload(BaseModel):
    email: EmailStr
    total_eur: float = Field(..., gt=0)
    installments: int = Field(..., ge=2, le=12)
    account_type: str
    description: Optional[str] = None


async def _create_one_link(email: str, amount_cents: int, account_type: str,
                           description: Optional[str], admin_email: Optional[str]) -> dict:
    key = _stripe_key()
    label = ACCOUNT_TYPES[account_type]
    product_name = f"KDMARCHÉ × O'SCOP — {label}" + (f" — {description.strip()}" if description else "")
    link_id = str(uuid.uuid4())
    try:
        price = stripe.Price.create(
            api_key=key, currency="eur", unit_amount=amount_cents,
            product_data={"name": product_name})
        plink = stripe.PaymentLink.create(
            api_key=key,
            line_items=[{"price": price.id, "quantity": 1}],
            restrictions={"completed_sessions": {"limit": 1}},
            metadata={"kind": "ADMIN_PAYMENT_LINK", "link_db_id": link_id,
                      "account_type": account_type, "email": email})
    except stripe.error.StripeError as exc:
        logger.error("Création lien Stripe échouée : %s", exc)
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {getattr(exc, 'user_message', None) or str(exc)}")
    url = f"{plink.url}?prefilled_email={quote(email)}"
    doc = {
        "id": link_id, "email": email, "amount_cents": amount_cents,
        "account_type": account_type, "description": description,
        "stripe_payment_link_id": plink.id, "url": url, "status": "pending",
        "created_by": admin_email, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_payment_links.insert_one({**doc})
    return doc


@payment_links_router.post("")
async def create_payment_link(payload: CreateLinkPayload, admin: dict = Depends(_admin)):
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Type de compte invalide (VENDOR_PRO, BUYER_PRO, SPONSOR)")
    amount_cents = int(round(payload.amount_eur * 100))
    if amount_cents > STRIPE_MAX_CENTS:
        raise HTTPException(
            status_code=400,
            detail="Montant maximum Stripe : 999 999,99 € par lien. Pour un total supérieur (ex : 1 000 000 €), créez plusieurs liens.")
    doc = await _create_one_link(payload.email, amount_cents, payload.account_type,
                                 payload.description, admin.get("email"))
    logger.info("Lien de paiement admin créé : %s € pour %s", payload.amount_eur, payload.email)
    return doc


@payment_links_router.post("/split")
async def create_split_links(payload: SplitPayload, admin: dict = Depends(_admin)):
    """Découpe un montant total en N liens de paiement (échéances) générés d'un coup."""
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Type de compte invalide (VENDOR_PRO, BUYER_PRO, SPONSOR)")
    total_cents = int(round(payload.total_eur * 100))
    n = payload.installments
    base = total_cents // n
    if base < 1:
        raise HTTPException(status_code=400, detail="Montant total trop faible pour ce nombre d'échéances")
    amounts = [base + (total_cents - base * n if i == 0 else 0) for i in range(n)]
    if max(amounts) > STRIPE_MAX_CENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Chaque échéance dépasse le plafond Stripe (999 999,99 €). Augmentez le nombre d'échéances (min {(total_cents // STRIPE_MAX_CENTS) + 1}).")
    created = []
    for i, cents in enumerate(amounts):
        suffix = f"Échéance {i + 1}/{n}" + (f" — {payload.description.strip()}" if payload.description else "")
        created.append(await _create_one_link(payload.email, cents, payload.account_type, suffix, admin.get("email")))
    logger.info("Paiement échelonné : %s liens créés pour %s (total %s cents)", n, payload.email, total_cents)
    return {"links": created, "total_cents": total_cents, "installments": n}


@payment_links_router.get("")
async def list_payment_links(_: dict = Depends(_admin)):
    links = await db.admin_payment_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"links": links, "account_types": ACCOUNT_TYPES}


@payment_links_router.post("/{link_id}/refresh")
async def refresh_payment_link(link_id: str, _: dict = Depends(_admin)):
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    if link["status"] == "paid":
        return link
    key = _stripe_key()
    try:
        sessions = stripe.checkout.Session.list(api_key=key, payment_link=link["stripe_payment_link_id"], limit=5)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {exc}")
    paid = next((s for s in sessions.data if s.payment_status == "paid"), None)
    if paid:
        await _mark_paid(db, link, paid.id, "manual")
        link["status"] = "paid"
    return link


@payment_links_router.post("/{link_id}/deactivate")
async def deactivate_payment_link(link_id: str, _: dict = Depends(_admin)):
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    key = _stripe_key()
    try:
        stripe.PaymentLink.modify(link["stripe_payment_link_id"], api_key=key, active=False)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur Stripe : {exc}")
    await db.admin_payment_links.update_one({"id": link_id}, {"$set": {"status": "deactivated"}})
    return {"status": "SUCCESS"}


async def _send_client_receipt(db_, link: dict) -> None:
    """Email de reçu envoyé au client dès que son paiement est détecté."""
    try:
        from brevo_service import send_email, _wrap_html
        from payment_receipt_pdf import build_receipt_pdf, next_receipt_number
        import base64
        receipt_number = link.get("receipt_number") or await next_receipt_number(db_)
        pdf_bytes = build_receipt_pdf({**link, "paid_at": datetime.now(timezone.utc).isoformat()},
                                      receipt_number, ACCOUNT_TYPES)
        attachments = [{"content": base64.b64encode(pdf_bytes).decode(), "name": f"recu-{receipt_number}.pdf"}]
        amount = f"{link['amount_cents'] / 100:,.2f}".replace(",", " ").replace(".", ",")
        label = ACCOUNT_TYPES.get(link["account_type"], link["account_type"])
        desc = (f"<tr><td style='padding:4px 14px 4px 0;color:#777;'>Détail</td>"
                f"<td style='padding:4px 0;'>{link['description']}</td></tr>") if link.get("description") else ""
        now = datetime.now(timezone.utc)
        body = f"""
          <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:20px;\">Reçu de paiement</h2>
          <p>Bonjour,</p>
          <p>Nous confirmons la <strong>bonne réception de votre paiement</strong> :</p>
          <table style=\"border-collapse:collapse;margin:14px 0;font-size:14px;\">
            <tr><td style=\"padding:4px 14px 4px 0;color:#777;\">N° de reçu</td><td style=\"padding:4px 0;font-family:monospace;\">{receipt_number}</td></tr>
            <tr><td style=\"padding:4px 14px 4px 0;color:#777;\">Montant</td><td style=\"padding:4px 0;font-weight:bold;font-size:16px;\">{amount} €</td></tr>
            <tr><td style=\"padding:4px 14px 4px 0;color:#777;\">Objet</td><td style=\"padding:4px 0;\">{label}</td></tr>
            {desc}
            <tr><td style=\"padding:4px 14px 4px 0;color:#777;\">Date</td><td style=\"padding:4px 0;\">{now.strftime('%d/%m/%Y')}</td></tr>
            <tr><td style=\"padding:4px 14px 4px 0;color:#777;\">Référence</td><td style=\"padding:4px 0;font-family:monospace;\">{link['id'][:8].upper()}</td></tr>
          </table>
          <p>Ce message vaut confirmation de paiement. <strong>Votre reçu officiel PDF (n° {receipt_number}) est joint</strong> à cet email pour votre comptabilité.</p>
          <p style=\"margin-top:16px;\">Merci pour votre confiance,<br/>L'équipe KDMARCHÉ × O'SCOP</p>
        """
        res = await send_email(
            link["email"], None,
            f"Reçu de paiement — {amount} € — KDMARCHÉ × O'SCOP",
            _wrap_html("Reçu de paiement", body), tags=["payment_link_receipt"],
            attachments=attachments)
        if res is not None:
            await db_.admin_payment_links.update_one(
                {"id": link["id"]},
                {"$set": {"receipt_sent_at": now.isoformat(), "receipt_number": receipt_number},
                 "$push": {"send_history": {"channel": "email", "to": link["email"],
                                            "at": now.isoformat(), "by": "reçu automatique"}}})
            logger.info("Reçu client envoyé à %s (lien %s)", link["email"], link["id"])
    except Exception as exc:
        logger.warning("Envoi reçu client %s : %s", link.get("id"), exc)


async def _mark_paid(db_, link: dict, session_id: str, detected_by: str) -> bool:
    """Passe le lien à « payé » (claim atomique), notifie les admins et envoie le reçu client."""
    claim = await db_.admin_payment_links.update_one(
        {"id": link["id"], "status": "pending"},
        {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat(),
                  "stripe_session_id": session_id, "detected_by": detected_by}})
    if claim.modified_count != 1:
        return False
    amount = f"{link['amount_cents'] / 100:,.2f}".replace(",", " ").replace(".", ",")
    label = ACCOUNT_TYPES.get(link["account_type"], link["account_type"])
    desc = f" ({link['description']})" if link.get("description") else ""
    try:
        from core_deps import create_notification
        await create_notification(
            "payment_link_paid", "💶 Paiement reçu via lien Stripe",
            f"{amount} € réglés par {link['email']} — {label}{desc}. Le statut est passé à « Payé » dans Comptabilité.",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"],
            data={"link": "/superadmin", "payment_link_id": link["id"],
                  "amount_cents": link["amount_cents"], "email": link["email"]})
    except Exception as exc:
        logger.warning("Notification paiement %s : %s", link["id"], exc)
    await _send_client_receipt(db_, link)
    return True


async def check_pending_payment_links(db_):
    """Cron : détecte les liens payés et notifie les admins automatiquement (pas de clic « vérifier »)."""
    try:
        links = await db_.admin_payment_links.find(
            {"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(20)
        if not links:
            return
        key = get_stripe_key("oscop")
        if not key:
            return
        stripe.api_base = "https://api.stripe.com"
        from starlette.concurrency import run_in_threadpool
        for link in links:
            try:
                sessions = await run_in_threadpool(
                    lambda pl=link["stripe_payment_link_id"]: stripe.checkout.Session.list(
                        api_key=key, payment_link=pl, limit=5))
            except stripe.error.StripeError as exc:
                logger.warning("Poll lien %s : %s", link["id"], exc)
                continue
            paid = next((s for s in sessions.data if s.payment_status == "paid"), None)
            if not paid:
                continue
            if await _mark_paid(db_, link, paid.id, "cron"):
                logger.info("Paiement détecté automatiquement : lien %s (%s €)", link["id"], link["amount_cents"] / 100)
    except Exception as exc:
        logger.warning("check_pending_payment_links : %s", exc)


class SmsPayload(BaseModel):
    phone: str


@payment_links_router.post("/{link_id}/send-sms")
async def send_link_sms(link_id: str, payload: SmsPayload, admin: dict = Depends(_admin)):
    """Envoie le lien de paiement par SMS international (Brevo)."""
    import re
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    if link["status"] != "pending":
        raise HTTPException(status_code=400, detail="Ce lien n'est plus en attente de paiement")
    phone = re.sub(r"[^\d+]", "", payload.phone or "")
    if not re.fullmatch(r"\+\d{8,15}", phone):
        raise HTTPException(status_code=400, detail="Numéro international invalide (ex : +590 690 12 34 56)")
    amount = f"{link['amount_cents'] / 100:,.2f}".replace(",", " ").replace(".", ",")
    label = ACCOUNT_TYPES.get(link["account_type"], link["account_type"])
    short_url = link["url"].split("?")[0]
    msg = f"KDMARCHE x O'SCOP - Lien de paiement {label} : {amount} EUR. Payez en securite ici : {short_url}"
    from brevo_service import send_sms
    res = await send_sms(phone, msg, tag="payment_link")
    if res is None:
        raise HTTPException(status_code=502, detail="Envoi SMS échoué (Brevo) — vérifiez le numéro")
    await db.admin_payment_links.update_one(
        {"id": link_id},
        {"$set": {"sms_sent_at": datetime.now(timezone.utc).isoformat(), "sms_to": phone},
         "$push": {"send_history": {"channel": "sms", "to": phone,
                                    "at": datetime.now(timezone.utc).isoformat(),
                                    "by": admin.get("email")}}})
    logger.info("Lien de paiement %s envoyé par SMS à %s par %s", link_id, phone, admin.get("email"))
    return {"status": "SUCCESS", "sent_to": phone}


class LogSendPayload(BaseModel):
    channel: str
    to: str


@payment_links_router.post("/{link_id}/log-send")
async def log_link_send(link_id: str, payload: LogSendPayload, admin: dict = Depends(_admin)):
    """Trace un envoi manuel (ex : email via mailto) dans l'historique du lien."""
    if payload.channel not in ("email", "sms"):
        raise HTTPException(status_code=400, detail="Canal invalide (email, sms)")
    entry = {"channel": payload.channel, "to": payload.to.strip(),
             "at": datetime.now(timezone.utc).isoformat(), "by": admin.get("email")}
    result = await db.admin_payment_links.update_one({"id": link_id}, {"$push": {"send_history": entry}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    return {"status": "SUCCESS", "entry": entry}


@payment_links_router.get("/{link_id}/receipt.pdf")
async def download_receipt_pdf(link_id: str, _: dict = Depends(_admin)):
    """Télécharge le reçu PDF officiel d'un lien payé (numérotation conservée)."""
    from fastapi.responses import Response
    from payment_receipt_pdf import build_receipt_pdf, next_receipt_number
    link = await db.admin_payment_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    if link["status"] != "paid":
        raise HTTPException(status_code=400, detail="Le reçu n'est disponible que pour un lien payé")
    receipt_number = link.get("receipt_number")
    if not receipt_number:
        receipt_number = await next_receipt_number(db)
        await db.admin_payment_links.update_one({"id": link_id}, {"$set": {"receipt_number": receipt_number}})
    pdf_bytes = build_receipt_pdf(link, receipt_number, ACCOUNT_TYPES)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="recu-{receipt_number}.pdf"'})


@payment_links_router.get("/export.csv")
async def export_payment_links_csv(register: str = "receipts", _: dict = Depends(_admin)):
    """Registres comptables : reçus émis ou sponsors — export CSV pour l'expert-comptable."""
    from fastapi.responses import Response
    if register not in ("receipts", "sponsors"):
        raise HTTPException(status_code=400, detail="Registre invalide (receipts, sponsors)")
    q = {"status": "paid"} if register == "receipts" else {"account_type": "SPONSOR"}
    links = await db.admin_payment_links.find(q, {"_id": 0}).sort("created_at", 1).to_list(1000)
    st_fr = {"pending": "En attente", "paid": "Payé", "deactivated": "Désactivé"}
    if register == "receipts":
        lines = ["N° reçu;Date paiement;Client;Montant (EUR);Type;Description;Référence lien;Détection"]
        for l in links:
            amt = f"{l['amount_cents'] / 100:.2f}".replace(".", ",")
            lines.append(";".join([
                l.get("receipt_number") or "", (l.get("paid_at") or "")[:10], l["email"], amt,
                ACCOUNT_TYPES.get(l["account_type"], l["account_type"]),
                (l.get("description") or "").replace(";", ","), l["id"][:8].upper(),
                l.get("detected_by") or ""]))
        fname = "registre-recus.csv"
    else:
        lines = ["Date création;Sponsor (email);Montant (EUR);Statut;Date paiement;N° reçu;Description;Référence lien"]
        for l in links:
            amt = f"{l['amount_cents'] / 100:.2f}".replace(".", ",")
            lines.append(";".join([
                (l.get("created_at") or "")[:10], l["email"], amt, st_fr.get(l["status"], l["status"]),
                (l.get("paid_at") or "")[:10], l.get("receipt_number") or "",
                (l.get("description") or "").replace(";", ","), l["id"][:8].upper()]))
        fname = "registre-sponsors.csv"
    csv = "\ufeff" + "\n".join(lines)
    return Response(content=csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
