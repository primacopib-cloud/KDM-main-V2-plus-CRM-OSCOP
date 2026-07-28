"""Ticket de caisse : téléchargement PDF (archivage comptable) et envoi email au client (PDF joint)."""
import base64

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lolodrive_helpers import get_current_user
from routes_relay_products import _manager_point

ticket_pdf_router = APIRouter(prefix="/api/lolodrive", tags=["Ticket PDF"])
db = None


def set_ticket_pdf_database(database):
    global db
    db = database


async def _get_counter_order(user_id: str, order_id: str):
    point = await _manager_point(user_id)
    order = await db.lolodrive_orders.find_one(
        {"id": order_id, "lolo_point_id": point["id"], "channel": "COUNTER"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Vente introuvable pour ce relais")
    return point, order


@ticket_pdf_router.get("/pos/counter-sale/{order_id}/ticket.pdf")
async def download_ticket_pdf(order_id: str, user: dict = Depends(get_current_user)):
    point, order = await _get_counter_order(user["id"], order_id)
    from ticket_pdf import build_ticket_pdf
    pdf = build_ticket_pdf(order, point)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=ticket-{order.get('order_number')}.pdf"})


@ticket_pdf_router.post("/pos/counter-sale/{order_id}/email-ticket")
async def email_counter_ticket(order_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Envoie le ticket de caisse par email au client, avec le ticket PDF en pièce jointe."""
    email = ((payload or {}).get("email") or "").strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide")
    point, order = await _get_counter_order(user["id"], order_id)
    from brevo_service import send_email, _wrap_html
    from ticket_pdf import build_ticket_pdf

    def _eu(l):
        ttc = l["unit_cents"] * l["qty"]
        rate = float(l.get("tva_rate") or 8.5)
        return ttc, rate, round(ttc / (1 + rate / 100))

    def _row(l):
        ttc, rate, ht = _eu(l)
        promo = f" <span style='color:#b45309;font-size:11px'>-{l['promo_percent']:g}%</span>" if l.get("promo_percent") else ""
        return (f"<tr><td style='padding:4px 8px'>{l['qty']} × {l['name']}{promo} · TVA {rate:g}%</td>"
                f"<td style='padding:4px 8px;text-align:right'>{ht / 100:.2f} € HT "
                f"<span style='color:#b8860b;font-size:11px'>· {round(ttc / 10, 1):g} UC</span></td></tr>")

    items = order.get("items", [])
    rows = "".join(_row(l) for l in items)
    total_ht, tva_by_rate = 0, {}
    for l in items:
        ttc, rate, ht = _eu(l)
        total_ht += ht
        tva_by_rate[rate] = tva_by_rate.get(rate, 0) + (ttc - ht)
    tva_rows = "".join(
        f"<tr><td style='padding:3px 8px;color:#666'>TVA {rate:.2f} %</td>"
        f"<td style='padding:3px 8px;text-align:right;color:#666'>{tva / 100:.2f} €</td></tr>"
        for rate, tva in sorted(tva_by_rate.items()))
    discount = order.get("promo_discount_cents") or 0
    pay_fr = {"CARD": "carte bancaire", "UC": "UC — CREDI'SCOP",
              "MIXED": "paiement combiné UC + " + ("CB" if order.get("rest_method") == "CARD" else "espèces")
              }.get(order.get("payment_method"), "espèces")
    subject = f"🧾 Ticket de caisse — {order['order_number']} ({point['name']})"
    fiscal = " · ".join(x for x in (
        f"SIRET {point['siret']}" if point.get("siret") else None,
        f"N° TVA {point['vat_number']}" if point.get("vat_number") else None) if x)
    total_uc = round(order["total_cents"] / 10, 1)
    body = f"""
      <p><strong>{point['name']}</strong> — vente au comptoir du {order['created_at'].strftime('%d/%m/%Y %H:%M')}</p>
      {f"<p style='margin:-6px 0 8px;font-size:11px;color:#888'>{fiscal}</p>" if fiscal else ''}
      <table style='width:100%;border-collapse:collapse;font-size:13px;border-top:1px dashed #ccc;border-bottom:1px dashed #ccc'>{rows}</table>
      <table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:6px'>
        <tr><td style='padding:3px 8px'><strong>Sous-total HT</strong></td>
        <td style='padding:3px 8px;text-align:right'><strong>{total_ht / 100:.2f} €</strong></td></tr>
        {tva_rows}
        {f"<tr><td style='padding:3px 8px;color:#b45309'>⚡ Remise promo (déjà déduite des lignes)</td><td style='padding:3px 8px;text-align:right;color:#b45309'>−{discount / 100:.2f} €</td></tr>" if discount else ''}
      </table>
      <p style='margin:10px 0 0;font-size:15px;border-top:1px dashed #ccc;padding-top:8px'>Montant TTC : <strong>{order['total_cents'] / 100:.2f} €</strong>
      <span style='color:#b8860b;font-size:13px'>· {total_uc:g} UC</span> ({pay_fr})</p>
      {f"<p style='margin:6px 0 0;font-size:12px;color:#b8860b'>🪙 Payé en UC : <strong>{order['uc_paid']} UC</strong> débités du CREDI'SCOP</p>" if order.get('uc_paid') else ''}
      {f"<p style='margin:6px 0 0;font-size:12px;color:#777'>Encaissé par : <strong>{order['operator_name']}</strong></p>" if order.get('operator_name') else ''}
      <p style='color:#999;font-size:11px;margin-top:12px'>Votre ticket PDF est joint à cet email. Merci de votre visite — Réseau LOLODRIVE by O'SCOP.</p>
    """
    pdf = build_ticket_pdf(order, point)
    await send_email(to_email=email, to_name=None, subject=subject,
                     html_content=_wrap_html(subject, body),
                     text_content=f"Ticket {order['order_number']} — total {order['total_cents'] / 100:.2f} € ({total_uc:g} UC). PDF joint.",
                     tags=["counter_ticket"],
                     attachments=[{"content": base64.b64encode(pdf).decode(),
                                   "name": f"ticket-{order['order_number']}.pdf"}])
    return {"ok": True, "sent_to": email, "pdf_attached": True}
