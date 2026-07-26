"""Clôture de caisse : email quotidien au gérant avec le récap comptoir du jour."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SEND_AFTER_HOUR_UTC = 21  # ~17h aux Antilles (UTC-4)


async def run_cash_closeout(db, force: bool = False) -> int:
    now = datetime.utcnow()
    if not force and now.hour < SEND_AFTER_HOUR_UTC:
        return 0
    day_tag = now.strftime("%Y-%m-%d")
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent = 0
    async for point in db.lolodrive_points.find(
            {"manager_user_id": {"$ne": None}}, {"_id": 0, "id": 1, "code": 1, "name": 1, "manager_user_id": 1}):
        if await db.cash_closeout_sent.find_one({"point_id": point["id"], "day": day_tag}):
            continue
        sales = await db.lolodrive_orders.find(
            {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start}},
            {"_id": 0, "order_number": 1, "total_cents": 1, "payment_method": 1, "created_at": 1}
        ).sort("created_at", 1).to_list(300)
        if not sales:
            continue
        mgr = await db.users.find_one({"id": point["manager_user_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        if not mgr or not mgr.get("email"):
            continue
        cash = sum(s.get("total_cents", 0) for s in sales if s.get("payment_method") == "CASH")
        card = sum(s.get("total_cents", 0) for s in sales if s.get("payment_method") == "CARD")
        rows = "".join(
            f"<tr><td style='padding:4px 8px;border-bottom:1px solid #eee'>{s['order_number']}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center'>{'💳 CB' if s.get('payment_method') == 'CARD' else '💵 Espèces'}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:right'>{s.get('total_cents', 0) / 100:.2f} €</td></tr>"
            for s in sales)
        try:
            from brevo_service import send_email, _wrap_html
            first = ((mgr.get("contact_name") or "").split() or [""])[0]
            subject = f"🧾 Clôture de caisse du {now.strftime('%d/%m/%Y')} — {point['name']}"
            body = f"""
              <p>Bonjour{f' {first}' if first else ''},</p>
              <p>Voici la clôture de caisse du jour pour <strong>{point['name']}</strong> :</p>
              <div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:12px;padding:14px;margin:12px 0;'>
                <p style='margin:0;'>🛒 Ventes au comptoir : <strong>{len(sales)}</strong></p>
                <p style='margin:6px 0 0;'>💵 Espèces : <strong>{cash / 100:.2f} €</strong> · 💳 CB : <strong>{card / 100:.2f} €</strong></p>
                <p style='margin:6px 0 0;font-size:15px'>Total caisse : <strong>{(cash + card) / 100:.2f} €</strong></p>
              </div>
              <table style='width:100%;border-collapse:collapse;font-size:13px'>{rows}</table>
              <p style='color:#999;font-size:11px;margin-top:12px'>Récapitulatif automatique — pensez à vérifier votre fond de caisse.</p>
            """
            await send_email(
                to_email=mgr["email"], to_name=mgr.get("contact_name"), subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"Clôture {point['name']} : {len(sales)} ventes, espèces {cash / 100:.2f} €, CB {card / 100:.2f} €, total {(cash + card) / 100:.2f} €.",
                tags=["cash_closeout"])
            await db.cash_closeout_sent.insert_one({"point_id": point["id"], "day": day_tag, "sent_at": now})
            sent += 1
        except Exception as exc:
            logger.warning("Clôture caisse %s : %s", point.get("code"), exc)
    if sent:
        logger.info("Clôtures de caisse envoyées : %s", sent)
    return sent
