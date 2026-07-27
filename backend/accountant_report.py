"""Rapport comptable mensuel : relevés d'heures + caisse du mois envoyés au comptable de chaque relais."""
import base64
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SEND_UNTIL_DAY = 3


async def _cash_csv(db, point, start, end):
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0}).sort("created_at", 1).to_list(3000)
    rows = ["date;heure;numero;operateur;paiement;articles;remise_promo_eur;total_eur"]
    cash = card = 0
    for o in orders:
        items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
        pay = "CB" if o.get("payment_method") == "CARD" else "Especes"
        if o.get("payment_method") == "CARD":
            card += o.get("total_cents", 0)
        else:
            cash += o.get("total_cents", 0)
        rows.append(f"{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};"
                    f"{o.get('operator_name') or 'Gerant'};{pay};\"{items}\";"
                    f"{(o.get('promo_discount_cents') or 0) / 100:.2f};{o.get('total_cents', 0) / 100:.2f}")
    rows += ["", f"TOTAL ESPECES;;;;;;;{cash / 100:.2f}", f"TOTAL CB;;;;;;;{card / 100:.2f}",
             f"TOTAL CAISSE;;;;;;;{(cash + card) / 100:.2f}"]
    return "\ufeff" + "\n".join(rows), len(orders), cash + card


async def _hours_csv(db, point, start, end):
    from routes_pos_operators import _hours_days, _hhmm
    ops = await db.users.find({"role": "OPERATEUR_POS", "pos_point_id": point["id"]},
                              {"_id": 0, "id": 1, "contact_name": 1, "email": 1}).to_list(100)
    rows = ["operateur;email;date;premiere_activite;derniere_activite;pauses_min;presence_min;presence_hhmm"]
    for op in ops:
        days = await _hours_days(op["id"], start, end)
        t = 0
        for d in days:
            rows.append(f"{op['contact_name']};{op['email']};{d['date']};{d['first']};{d['last']};"
                        f"{d['break_min']};{d['presence_min']};{_hhmm(d['presence_min'])}")
            t += d["presence_min"]
        rows.append(f"SOUS-TOTAL {op['contact_name']};;{len(days)} jour(s);;;;{t};{_hhmm(t)}")
    return "\ufeff" + "\n".join(rows)


async def send_accountant_report(db, point, start, end, month_tag) -> bool:
    """Construit et envoie les 2 CSV (caisse + heures) au comptable du relais."""
    from brevo_service import send_email, _wrap_html
    email = point.get("accountant_email")
    if not email:
        return False
    cash_csv, nb_sales, total = await _cash_csv(db, point, start, end)
    hours_csv = await _hours_csv(db, point, start, end)
    month_label = start.strftime("%m/%Y")
    subject = f"📊 Rapport mensuel {month_label} — {point['name']} ({point['code']})"
    body = f"""
      <p>Bonjour,</p>
      <p>Veuillez trouver ci-joint le rapport comptable du relais <strong>{point['name']} ({point['code']})</strong>
      pour <strong>{month_label}</strong> :</p>
      <ul style='font-size:13px'>
        <li><strong>Caisse comptoir</strong> : {nb_sales} vente(s) — total {total / 100:.2f} € (CSV joint)</li>
        <li><strong>Relevés d'heures des opérateurs</strong> (CSV joint, présence nette pauses déduites)</li>
      </ul>
      <p style='color:#999;font-size:11px;margin-top:12px'>Rapport automatique mensuel — Réseau LOLODRIVE by O'SCOP.</p>
    """
    await send_email(
        to_email=email, to_name=None, subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Rapport {month_label} {point['code']} : {nb_sales} ventes, {total / 100:.2f} €.",
        tags=["rapport_comptable"],
        attachments=[
            {"content": base64.b64encode(cash_csv.encode("utf-8")).decode(), "name": f"caisse-{point['code']}-{month_tag}.csv"},
            {"content": base64.b64encode(hours_csv.encode("utf-8")).decode(), "name": f"heures-{point['code']}-{month_tag}.csv"},
        ])
    return True


async def run_accountant_reports(db, force: bool = False, ref_date=None) -> int:
    now = ref_date or datetime.utcnow()
    if not force and now.day > SEND_UNTIL_DAY:
        return 0
    cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (cur_start - timedelta(days=1)).replace(day=1)
    month_tag = prev_start.strftime("%Y-%m")
    sent = 0
    async for point in db.lolodrive_points.find({"accountant_email": {"$nin": [None, ""]}}, {"_id": 0}):
        if await db.accountant_report_sent.find_one({"month": month_tag, "point_id": point["id"]}):
            continue
        try:
            if await send_accountant_report(db, point, prev_start, cur_start, month_tag):
                await db.accountant_report_sent.insert_one(
                    {"month": month_tag, "point_id": point["id"], "sent_at": now})
                sent += 1
        except Exception as exc:
            logger.warning("Rapport comptable %s : %s", point.get("code"), exc)
    if sent:
        logger.info("Rapports comptables envoyés : %s", sent)
    return sent
