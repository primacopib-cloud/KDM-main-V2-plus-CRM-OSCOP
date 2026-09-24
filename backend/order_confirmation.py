"""Email de confirmation de commande LOLODRIVE (reçu avec remise promo)."""
import logging

logger = logging.getLogger(__name__)


async def notify_order_confirmed(db, order: dict, paid_with: str):
    """paid_with: 'UC' ou 'CB'."""
    user = await db.users.find_one(
        {"id": order.get("user_id")}, {"_id": 0, "email": 1, "contact_name": 1, "preferred_language": 1})
    if not user or not user.get("email"):
        return
    from order_email_i18n import ORDER_T, order_lang, rtl_wrap
    lang = order_lang(user)
    t = ORDER_T[lang]
    point_name = None
    if order.get("lolo_point_id"):
        pt = await db.lolodrive_points.find_one(
            {"id": order["lolo_point_id"]}, {"_id": 0, "name": 1})
        point_name = (pt or {}).get("name")
    from brevo_service import send_email, _wrap_html
    num = order.get("order_number") or order.get("id")
    first = ((user.get("contact_name") or "").split() or [""])[0]
    in_uc = paid_with == "UC"

    def unit(line):
        return f"{line.get('unit_uc'):g} UC" if in_uc and line.get("unit_uc") is not None else f"{line.get('unit_cents', 0) / 100:.2f} €"

    def row(l):
        promo_tag = f" <span style='color:#b45309;font-size:11px'>⚡ -{l['promo_percent']:g} %</span>" if l.get("promo_percent") else ""
        return (f"<tr><td style='padding:5px 10px;border-bottom:1px solid #eee'>{l.get('name')}{promo_tag}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #eee;text-align:center'>× {l.get('qty')}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #eee;text-align:right'>{unit(l)}</td></tr>")

    rows = "".join(row(l) for l in order.get("items", []))
    discount = order.get("promo_discount_cents") or 0
    discount_html = (
        f"<p style='margin:10px 0 0;color:#b45309;font-weight:bold'>{t['promo'].format(amt=f'{discount / 100:.2f}')}</p>" if discount > 0 else "")
    total = f"{order.get('total_uc', 0):g} UC" if in_uc else f"{order.get('total_cents', 0) / 100:.2f} €"
    mode = {"DRIVE": t["mode_drive"], "DELIVERY": t["mode_delivery"],
            "LOLO_POINT": t["mode_point"].format(point=point_name or "LOLODRIVE")}.get(
        order.get("fulfillment_type"), order.get("fulfillment_type") or "")
    subject = t["subject"].format(num=num)
    slot_html = ""
    if order.get("pickup_slot_label"):
        fee = order.get("slot_fee_uc") or 0
        date_txt = ""
        if order.get("pickup_date"):
            try:
                from datetime import datetime as _dt
                date_txt = t["slot_date"].format(d=_dt.strptime(order["pickup_date"], "%Y-%m-%d").strftime("%d/%m/%Y"))
            except ValueError:
                pass
        slot_html = (f"<p style='margin:8px 0 0'>{t['slot'].format(date=date_txt, slot=order['pickup_slot_label'])}"
                     + (t["slot_fee"].format(fee=fee) if fee else "") + "</p>")
    body = rtl_wrap(lang, f"""
      <p>{t['hello'].format(first=f' {first}' if first else '')}</p>
      <p>{t['confirmed'].format(num=num, pay=t['pay_uc'] if in_uc else t['pay_cb'], mode=mode)}</p>
      {slot_html}
      <table style='width:100%;border-collapse:collapse;font-size:13px'>{rows}</table>
      {discount_html}
      <p style='margin:12px 0 0;font-size:15px'>{t['total'].format(total=total)}</p>
      <p style='color:#999;font-size:11px;margin-top:14px'>{t['notice']}</p>
    """)
    try:
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
            html_content=_wrap_html(subject, body),
            text_content=f"Commande {num} confirmée — total {total}."
                         + (f" Créneau : {order.get('pickup_slot_label')}." if order.get("pickup_slot_label") else "")
                         + (f" Remise promo : -{discount / 100:.2f} €." if discount > 0 else ""),
            tags=["order_confirmed"])
    except Exception as exc:
        logger.warning("Email confirmation commande %s échoué : %s", num, exc)
