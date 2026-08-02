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
        o["has_proof"] = bool(await db.delivery_proofs.find_one({"order_id": o["id"]}, {"_id": 1}))
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


async def _order_and_proof(order_id: str, user: dict):
    try:
        order, _ = await get_order_with_access_check(order_id, user)
    except HTTPException:
        u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "role": 1})
        if (u or {}).get("role") not in ("SUPER_ADMIN", "ADMIN"):
            raise
        order = await db.orders.find_one({"id": order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Commande introuvable")
    proof = await db.delivery_proofs.find_one({"order_id": order_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Aucune preuve de livraison")
    return order, proof


@rar_delivery_router.get("/{order_id}/proof-pdf")
async def delivery_proof_pdf(order_id: str, user: dict = Depends(get_current_user_checkout)):
    from fastapi.responses import Response
    order, proof = await _order_and_proof(order_id, user)
    from pdf_delivery_note import build_delivery_note_pdf
    pdf = build_delivery_note_pdf(order, proof)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=bon-livraison-{order.get('order_number')}.pdf"})


@rar_delivery_router.get("/ceiling-history")
async def ceiling_history(user: dict = Depends(get_current_user_checkout)):
    """Mouvements de plafond dérivés : attribution, réservations, avoirs, rétablissements."""
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    if not m:
        return {"events": []}
    events = []
    account = await db.rar_accounts.find_one({"org_id": m["org_id"]}, {"_id": 0})
    if account and account.get("decided_at") and account.get("ceiling_cents"):
        events.append({"date": account["decided_at"], "type": "GRANT",
                       "label": "Plafond accordé" + (" (pack CREDI'SCOP)" if account.get("source") == "CREDISCOP_PACK" else ""),
                       "amount_cents": account["ceiling_cents"], "order_number": None})
    async for o in db.orders.find({"org_id": m["org_id"], "rar": True},
                                  {"_id": 0, "order_number": 1, "confirmed_at": 1, "paid_at": 1,
                                   "payment_status": 1, "total_ttc_cents": 1, "rar_reserved_cents": 1,
                                   "rar_reserve_resolution": 1}):
        n = o.get("order_number")
        if o.get("confirmed_at"):
            events.append({"date": o["confirmed_at"], "type": "RESERVE",
                           "label": "Commande sans acompte — montant réservé",
                           "amount_cents": -(o.get("total_ttc_cents") or 0), "order_number": n})
        res = o.get("rar_reserve_resolution") or {}
        if res.get("action") == "CREDIT":
            events.append({"date": res.get("at"), "type": "CREDIT",
                           "label": "Avoir accordé — plafond libéré",
                           "amount_cents": res.get("amount_cents", 0), "order_number": n})
        if o.get("payment_status") == "succeeded" and o.get("paid_at"):
            events.append({"date": o["paid_at"], "type": "RESTORE",
                           "label": "Paiement encaissé — plafond rétabli",
                           "amount_cents": o.get("rar_reserved_cents") or o.get("total_ttc_cents") or 0,
                           "order_number": n})
    events.sort(key=lambda e: str(e["date"] or ""), reverse=True)
    return {"events": events[:50]}


@rar_delivery_router.get("/admin/litigation-export")
async def litigation_export(all: bool = False, admin: dict = Depends(require_admin)):
    """ZIP des bons de livraison + preuves (par défaut : uniquement les livraisons avec réserves)."""
    import io
    import json
    import zipfile
    from fastapi.responses import Response
    from pdf_delivery_note import build_delivery_note_pdf, _local
    query = {} if all else {"reserves.0": {"$exists": True}}
    proofs = await db.delivery_proofs.find(query, {"_id": 0}).sort("confirmed_at", -1).to_list(100)
    if not proofs:
        raise HTTPException(status_code=404, detail="Aucun litige à exporter")
    buf = io.BytesIO()
    csv_lines = ["commande;date;receptionnaire;transporteur;reserves;valeur_suspendue_eur;resolution"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in proofs:
            order = await db.orders.find_one({"id": p["order_id"]})
            if not order:
                continue
            folder = p.get("order_number", p["order_id"][:8])
            try:
                z.writestr(f"{folder}/bon-livraison-{folder}.pdf", build_delivery_note_pdf(order, p))
            except Exception as exc:
                logger.warning("BL PDF export %s : %s", folder, exc)
            for i, url in enumerate([p.get("signature_url")] + (p.get("photos") or []), 1):
                path = _local(url)
                if path:
                    name = "signature" if i == 1 else f"photo-{i - 1}"
                    z.write(path, f"{folder}/{name}{os.path.splitext(path)[1]}")
            z.writestr(f"{folder}/preuve.json", json.dumps(p, default=str, ensure_ascii=False, indent=2))
            res = order.get("rar_reserve_resolution") or {}
            csv_lines.append(";".join([
                folder, str(p.get("confirmed_at", ""))[:16], p.get("receiver_name", ""),
                p.get("carrier_name", ""), str(len(p.get("reserves") or [])),
                f"{(order.get('rar_disputed_cents') or res.get('amount_cents') or 0) / 100:.2f}",
                f"{res.get('action', 'EN COURS')}{(' — ' + res['note']) if res.get('note') else ''}"]))
        z.writestr("recapitulatif-litiges.csv", "\ufeff" + "\n".join(csv_lines))
    return Response(content=buf.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename=litiges-rar-{datetime.utcnow().strftime('%Y%m%d')}.zip"})


# ============ RÉSERVES : INSTRUCTION ADMIN ============

@rar_delivery_router.get("/reserves/admin/list")
async def admin_reserves(admin: dict = Depends(require_admin)):
    orders = await db.orders.find(
        {"rar": True, "rar_disputed_cents": {"$gt": 0}},
        {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "total_ttc_cents": 1,
         "rar_disputed_cents": 1, "cod_amount_due_cents": 1, "rar_status": 1,
         "rar_proof_at": 1}).sort("rar_proof_at", -1).to_list(100)
    for o in orders:
        proof = await db.delivery_proofs.find_one({"order_id": o["id"]}, {"_id": 0, "reserves": 1, "receiver_name": 1})
        o["reserves"] = (proof or {}).get("reserves", [])
        o["receiver_name"] = (proof or {}).get("receiver_name")
    return {"orders": orders}


@rar_delivery_router.post("/reserves/{order_id}/resolve")
async def admin_resolve_reserve(order_id: str, body: dict, admin: dict = Depends(require_admin)):
    """RELEASE : réserve levée, montant redevient exigible. CREDIT : avoir définitif, plafond libéré d'autant."""
    action = ((body or {}).get("action") or "").upper()
    if action not in ("RELEASE", "CREDIT"):
        raise HTTPException(status_code=400, detail="action RELEASE ou CREDIT requise")
    order = await db.orders.find_one({"id": order_id})
    if not order or not order.get("rar") or not order.get("rar_disputed_cents"):
        raise HTTPException(status_code=404, detail="Aucune réserve à instruire sur cette commande")
    disputed = order["rar_disputed_cents"]
    note = ((body or {}).get("note") or "")[:500]
    update = {"rar_disputed_cents": 0, "rar_status": "Règlement déclenché",
              "rar_reserve_resolution": {"action": action, "note": note, "amount_cents": disputed,
                                         "by": admin.get("email"), "at": datetime.utcnow()},
              "updated_at": datetime.utcnow()}
    if action == "RELEASE":
        update["cod_amount_due_cents"] = (order.get("cod_amount_due_cents") or 0) + disputed
    else:  # CREDIT : le montant contesté est crédité, le plafond mobilisé baisse d'autant
        update["rar_credit_cents"] = (order.get("rar_credit_cents") or 0) + disputed
        update["rar_reserved_cents"] = max(0, (order.get("rar_reserved_cents") or order["total_ttc_cents"]) - disputed)
    await db.orders.update_one({"id": order_id}, {"$set": update})
    client = await _order_client(order)
    if client and client.get("email"):
        try:
            from brevo_service import send_email, _wrap_html
            if action == "RELEASE":
                subject = f"Réserves levées — commande {order['order_number']}"
                body_html = (f"<p>Bonjour,</p><p>Après instruction, les réserves émises sur la commande "
                             f"<b>{order['order_number']}</b> ont été levées. Le montant de "
                             f"<b>{disputed / 100:.2f} € TTC</b> redevient exigible."
                             f"{('<p>Note : ' + note + '</p>') if note else ''}")
            else:
                subject = f"Avoir accordé — commande {order['order_number']}"
                body_html = (f"<p>Bonjour,</p><p>Suite à vos réserves sur la commande <b>{order['order_number']}</b>, "
                             f"un avoir de <b>{disputed / 100:.2f} € TTC</b> vous est accordé. Cette valeur est "
                             f"déduite définitivement et votre plafond est libéré d'autant."
                             f"{('<p>Note : ' + note + '</p>') if note else ''}")
            await send_email(to_email=client["email"], to_name=client.get("contact_name"), subject=subject,
                             html_content=_wrap_html(subject, body_html), text_content=subject,
                             tags=["rar_reserve_resolution"])
        except Exception as exc:
            logger.warning("Email résolution réserve non envoyé : %s", exc)
    logger.info("Réserve %s commande %s : %s (%s cents)", action, order["order_number"], admin.get("email"), disputed)
    return {"ok": True, "action": action, "amount_cents": disputed,
            "payable_now_cents": update.get("cod_amount_due_cents", order.get("cod_amount_due_cents"))}


@rar_delivery_router.get("/admin/list")
async def admin_deliveries(admin: dict = Depends(require_admin)):
    orders = await db.orders.find(
        {"rar": True}, {"_id": 0, "id": 1, "order_number": 1, "org_id": 1, "rar_status": 1,
                        "total_ttc_cents": 1, "rar_disputed_cents": 1, "payment_status": 1,
                        "cod_amount_due_cents": 1}).sort("created_at", -1).to_list(100)
    return {"orders": orders}
