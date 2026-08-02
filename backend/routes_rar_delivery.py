"""Lot E — Preuve électronique de livraison LOGI'SCOP (OTP, signature, photos, réserves partielles).
Déclenche la facture et le lien de paiement ; le plafond n'est rétabli qu'après encaissement."""
import base64
import logging
import os
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from checkout_common import get_current_user_checkout, get_order_with_access_check
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
rar_delivery_router = APIRouter(prefix="/api/rar/delivery", tags=["rar-delivery"])
db = None

PENDING_STATUSES = ["Commande acceptée sous plafond", "Préparation fournisseur", "Expédiée",
                    "En cours de livraison", "Livrée — réception à confirmer"]


def set_rar_delivery_database(database):
    global db
    db = database


def _save_data_url(data_url: str, folder: str, prefix: str) -> str | None:
    if not (data_url or "").startswith("data:image"):
        return None
    try:
        d = os.path.join(os.path.dirname(__file__), "uploads", folder)
        os.makedirs(d, exist_ok=True)
        ext = "jpg" if "jpeg" in data_url[:22] else "png"
        fname = f"{prefix}-{int(datetime.utcnow().timestamp())}-{random.randint(100, 999)}.{ext}"
        with open(os.path.join(d, fname), "wb") as f:
            f.write(base64.b64decode(data_url.split(",", 1)[1]))
        return f"/api/uploads/{folder}/{fname}"
    except Exception as exc:
        logger.warning("Fichier livraison non sauvegardé : %s", exc)
        return None


async def _order_client(order: dict) -> dict | None:
    uid = order.get("created_by_user_id")
    if not uid:
        m = await db.org_memberships.find_one({"org_id": order.get("org_id")})
        uid = m["user_id"] if m else None
    return await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "contact_name": 1}) if uid else None


@rar_delivery_router.get("/my-pending")
async def my_pending_deliveries(user: dict = Depends(get_current_user_checkout)):
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        return {"orders": []}
    orders = await db.orders.find(
        {"org_id": m["org_id"], "rar": True, "payment_status": {"$ne": "succeeded"}},
        {"_id": 0, "id": 1, "order_number": 1, "rar_status": 1, "total_ttc_cents": 1,
         "rar_disputed_cents": 1, "items": 1, "rar_delivery": 1}).sort("created_at", -1).to_list(20)
    for o in orders:
        o["awaiting_confirmation"] = o.get("rar_status") == "Livrée — réception à confirmer"
        o["items"] = [{"product_id": i.get("product_id"), "product_name": i.get("product_name"),
                       "quantity": i.get("quantity")} for i in (o.get("items") or [])]
        (o.get("rar_delivery") or {}).pop("otp", None)
    return {"orders": orders}


@rar_delivery_router.post("/{order_id}/start")
async def start_delivery(order_id: str, body: dict = None, admin: dict = Depends(require_admin)):
    """LOGI'SCOP démarre la livraison : génère l'OTP et l'envoie au client."""
    order = await db.orders.find_one({"id": order_id})
    if not order or not order.get("rar"):
        raise HTTPException(status_code=404, detail="Commande RàR introuvable")
    if order.get("payment_status") == "succeeded":
        raise HTTPException(status_code=400, detail="Commande déjà encaissée")
    otp = f"{random.randint(0, 999999):06d}"
    carrier = ((body or {}).get("carrier_name") or "LOGI'SCOP").strip()[:80]
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"rar_status": "Livrée — réception à confirmer",
                  "rar_delivery": {"otp": otp, "carrier_name": carrier, "otp_attempts": 0,
                                   "started_at": datetime.utcnow(), "started_by": admin.get("email")},
                  "updated_at": datetime.utcnow()}})
    client = await _order_client(order)
    if client and client.get("email"):
        try:
            from brevo_service import send_email, _wrap_html
            subject = f"🚚 Livraison {order['order_number']} — votre code de réception"
            body_html = (f"<p>Bonjour,</p><p>Votre commande <b>{order['order_number']}</b> est livrée par "
                         f"<b>{carrier}</b>.</p><p>Code de validation de réception : "
                         f"<span style='font-size:24px;font-weight:bold;letter-spacing:4px'>{otp}</span></p>"
                         f"<p>Saisissez ce code dans votre espace acheteur (bloc « Mon plafond à réception ») "
                         f"pour signer électroniquement le bon de livraison. Le règlement sera déclenché après votre validation.</p>")
            await send_email(to_email=client["email"], to_name=client.get("contact_name"),
                             subject=subject, html_content=_wrap_html(subject, body_html),
                             text_content=f"Code de réception commande {order['order_number']} : {otp}",
                             tags=["rar_delivery_otp"])
        except Exception as exc:
            logger.warning("Email OTP livraison non envoyé : %s", exc)
    return {"ok": True, "order_number": order["order_number"], "rar_status": "Livrée — réception à confirmer"}


@rar_delivery_router.post("/{order_id}/confirm")
async def confirm_delivery(order_id: str, body: dict, user: dict = Depends(get_current_user_checkout)):
    """Preuve électronique : OTP + signature + quantités + photos + réserves partielles → facture + lien de paiement."""
    order, _ = await get_order_with_access_check(order_id, user)
    if not order.get("rar"):
        raise HTTPException(status_code=400, detail="Commande hors dispositif RàR")
    delivery = order.get("rar_delivery") or {}
    if order.get("rar_status") != "Livrée — réception à confirmer":
        raise HTTPException(status_code=400, detail="Livraison non démarrée ou déjà confirmée")
    if delivery.get("otp_attempts", 0) >= 5:
        raise HTTPException(status_code=429, detail="Trop de tentatives — contactez le support")
    if (body or {}).get("otp") != delivery.get("otp"):
        await db.orders.update_one({"id": order_id}, {"$inc": {"rar_delivery.otp_attempts": 1}})
        raise HTTPException(status_code=403, detail="Code OTP invalide")
    receiver = (body.get("receiver_name") or "").strip()[:80]
    if not receiver:
        raise HTTPException(status_code=400, detail="Identité du réceptionnaire requise")
    signature_url = _save_data_url(body.get("signature") or "", "signatures", f"rar-{order_id[-8:]}")
    if not signature_url:
        raise HTTPException(status_code=400, detail="Signature électronique requise")
    photos = [u for u in (_save_data_url(p, "deliveries", f"rar-{order_id[-8:]}")
                          for p in (body.get("photos") or [])[:3]) if u]

    # Réserves partielles : seule la valeur des produits contestés est suspendue
    items = order.get("items") or []
    by_pid = {i.get("product_id"): i for i in items}
    disputed_ht = 0
    reserves = []
    for res in (body.get("reserves") or []):
        it = by_pid.get(res.get("product_id"))
        if not it:
            continue
        qty = max(0, min(int(res.get("qty") or 0), it.get("quantity", 0)))
        if qty <= 0:
            continue
        disputed_ht += it.get("price_ht_cents", 0) * qty
        reserves.append({"product_id": it["product_id"], "product_name": it.get("product_name"),
                         "qty": qty, "reason": (res.get("reason") or "")[:300]})
    total_ht = order.get("subtotal_ht_cents") or 1
    total_ttc = order.get("total_ttc_cents", 0)
    disputed_ttc = min(total_ttc, round(disputed_ht * total_ttc / total_ht)) if disputed_ht else 0
    payable_now = total_ttc - disputed_ttc

    proof = {
        "order_id": order_id, "order_number": order.get("order_number"),
        "receiver_name": receiver, "confirmed_by_user_id": user["id"],
        "confirmed_at": datetime.utcnow(),
        "geolocation": body.get("geolocation"),
        "quantities": [{"product_id": q.get("product_id"), "qty_received": int(q.get("qty_received") or 0)}
                       for q in (body.get("quantities") or [])],
        "signature_url": signature_url, "otp_verified": True,
        "photos": photos, "reserves": reserves,
        "carrier_name": delivery.get("carrier_name", "LOGI'SCOP"),
    }
    await db.delivery_proofs.insert_one({**proof})

    new_status = "Réserves en cours de traitement" if reserves else "Règlement déclenché"
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"rar_status": new_status, "rar_disputed_cents": disputed_ttc,
                  "cod_amount_due_cents": payable_now, "rar_proof_at": datetime.utcnow(),
                  "status": "PICKED_UP", "updated_at": datetime.utcnow()},
         "$unset": {"rar_delivery.otp": ""}})

    # Facture + lien de paiement (solution de démarrage simple)
    invoice_number = None
    try:
        from routes_invoices import generate_invoice_for_order
        invoice = await generate_invoice_for_order(order_id)
        invoice_number = invoice.get("invoice_number")
    except Exception as exc:
        logger.error("Facture RàR non générée : %s", exc)
    client = await _order_client(order)
    pay_link = f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/espace-acheteur?tab=invoices"
    if client and client.get("email"):
        try:
            from brevo_service import send_email, _wrap_html
            subject = f"🧾 Facture {invoice_number or order['order_number']} — règlement déclenché"
            res_txt = (f"<p style='color:#b45309'>⚠️ Réserves enregistrées : {disputed_ttc / 100:.2f} € suspendus "
                       f"({len(reserves)} produit(s)). Le reste demeure exigible.</p>") if reserves else ""
            body_html = (f"<p>Bonjour {receiver},</p>"
                         f"<p>Votre réception de la commande <b>{order['order_number']}</b> est confirmée "
                         f"(signature électronique + code sécurisé).</p>{res_txt}"
                         f"<p>Montant exigible : <b>{payable_now / 100:.2f} € TTC</b></p>"
                         f"<p><a href='{pay_link}' style='background:#D9B35A;color:#000;padding:10px 18px;"
                         f"border-radius:10px;text-decoration:none;font-weight:bold'>Régler ma facture</a></p>"
                         f"<p style='font-size:11px;color:#888'>Votre plafond sera rétabli après encaissement définitif du paiement.</p>")
            await send_email(to_email=client["email"], to_name=client.get("contact_name"),
                             subject=subject, html_content=_wrap_html(subject, body_html),
                             text_content=f"Facture {invoice_number} — {payable_now / 100:.2f} € à régler : {pay_link}",
                             tags=["rar_invoice_payment_link"])
        except Exception as exc:
            logger.warning("Email facture RàR non envoyé : %s", exc)
    logger.info("Réception RàR confirmée %s (exigible %s, réserves %s)", order["order_number"], payable_now, disputed_ttc)
    return {"ok": True, "rar_status": new_status, "invoice_number": invoice_number,
            "payable_now_cents": payable_now, "disputed_cents": disputed_ttc, "payment_link": pay_link}


@rar_delivery_router.get("/{order_id}/proof")
async def get_delivery_proof(order_id: str, user: dict = Depends(get_current_user_checkout)):
    await get_order_with_access_check(order_id, user)
    proof = await db.delivery_proofs.find_one({"order_id": order_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Aucune preuve de livraison")
    return proof


@rar_delivery_router.get("/admin/list")
async def admin_deliveries(admin: dict = Depends(require_admin)):
    orders = await db.orders.find(
        {"rar": True}, {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "rar_status": 1,
                        "total_ttc_cents": 1, "rar_disputed_cents": 1, "payment_status": 1,
                        "cod_amount_due_cents": 1}).sort("created_at", -1).to_list(100)
    return {"orders": orders}
