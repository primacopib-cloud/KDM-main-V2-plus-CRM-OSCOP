"""Rapport comptable mensuel : relevés d'heures + caisse du mois envoyés au comptable de chaque relais."""
import base64
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SEND_UNTIL_DAY = 3
TEAM_EMAIL = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")


async def _cash_csv(db, point, start, end):
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
        {"_id": 0}).sort("created_at", 1).to_list(3000)
    from routes_pos_counter import _pay_label, split_totals
    rows = ["date;heure;numero;operateur;paiement;articles;remise_promo_eur;total_eur"]
    for o in orders:
        items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
        rows.append(f"{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};"
                    f"{o.get('operator_name') or 'Gerant'};{_pay_label(o)};\"{items}\";"
                    f"{(o.get('promo_discount_cents') or 0) / 100:.2f};{o.get('total_cents', 0) / 100:.2f}")
    cash, card, uc = split_totals(orders)
    rows += ["", f"TOTAL ESPECES;;;;;;;{cash / 100:.2f}", f"TOTAL CB;;;;;;;{card / 100:.2f}",
             f"TOTAL UC;;;;;;;{uc / 100:.2f}", f"TOTAL CAISSE;;;;;;;{(cash + card + uc) / 100:.2f}"]
    return "\ufeff" + "\n".join(rows), len(orders), cash + card + uc


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


async def send_network_report(db, start, end, month_tag) -> int:
    """Rapport consolidé réseau (toutes caisses comptoir) envoyé aux super admins."""
    from brevo_service import send_email, _wrap_html
    from routes_pos_counter import _pay_label
    points = {p["id"]: p async for p in db.lolodrive_points.find({}, {"_id": 0})}
    rows = ["relais;date;heure;numero;operateur;paiement;articles;remise_promo_eur;total_eur"]
    by_point, g_total = {}, 0
    async for o in db.lolodrive_orders.find(
            {"channel": "COUNTER", "created_at": {"$gte": start, "$lt": end}},
            {"_id": 0}).sort([("lolo_point_id", 1), ("created_at", 1)]):
        pt = points.get(o.get("lolo_point_id"), {})
        label = f"{pt.get('code', '?')} — {pt.get('name', '')}".strip(" —")
        items = " + ".join(f"{l['name']} x{l['qty']}" for l in o.get("items", []))
        total = o.get("total_cents", 0)
        rows.append(f"{label};{o['created_at']:%d/%m/%Y};{o['created_at']:%H:%M};{o['order_number']};"
                    f"{o.get('operator_name') or 'Gerant'};{_pay_label(o)};\"{items}\";"
                    f"{(o.get('promo_discount_cents') or 0) / 100:.2f};{total / 100:.2f}")
        e = by_point.setdefault(label, {"count": 0, "total": 0})
        e["count"] += 1
        e["total"] += total
        g_total += total
    rows += ["", f"TOTAL RESEAU;;;;;{sum(e['count'] for e in by_point.values())} vente(s);;;{g_total / 100:.2f}"]
    csv = "\ufeff" + "\n".join(rows)
    table = "".join(
        f"<tr><td style='padding:5px 8px;border-bottom:1px solid #eee'>{label}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:center'>{e['count']}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:bold'>{e['total'] / 100:.2f} €</td></tr>"
        for label, e in sorted(by_point.items(), key=lambda x: -x[1]["total"]))
    month_label = start.strftime("%m/%Y")
    subject = f"📊 Rapport comptable réseau — {month_label} ({g_total / 100:.2f} €)"
    body = f"""
      <p>Bonjour,</p>
      <p>Rapport comptable consolidé des caisses comptoir du réseau LOLODRIVE pour <strong>{month_label}</strong> :</p>
      <table style='width:100%;border-collapse:collapse;font-size:13px;margin:10px 0'>
        <tr style='color:#888;font-size:11px;text-transform:uppercase'>
          <td style='padding:4px 8px'>Relais</td><td style='padding:4px 8px;text-align:center'>Ventes</td>
          <td style='padding:4px 8px;text-align:right'>Caisse</td></tr>
        {table}
        <tr><td style='padding:6px 8px;font-weight:bold'>TOTAL RÉSEAU</td><td></td>
        <td style='padding:6px 8px;text-align:right;font-weight:bold'>{g_total / 100:.2f} €</td></tr>
      </table>
      <p style='font-size:12px'>Le détail complet vente par vente est joint en CSV.</p>
    """
    recipients = {TEAM_EMAIL.lower()}
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if u.get("email"):
            recipients.add(u["email"].lower())
    sent = 0
    for email in recipients:
        await send_email(to_email=email, to_name=None, subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"Rapport réseau {month_label} : {g_total / 100:.2f} €.",
                         tags=["rapport_reseau"],
                         attachments=[{"content": base64.b64encode(csv.encode("utf-8")).decode(),
                                       "name": f"caisses-reseau-{month_tag}.csv"}])
        sent += 1
    return sent


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
    if not await db.accountant_report_sent.find_one({"month": month_tag, "point_id": "__NETWORK__"}):
        try:
            n = await send_network_report(db, prev_start, cur_start, month_tag)
            if n:
                await db.accountant_report_sent.insert_one(
                    {"month": month_tag, "point_id": "__NETWORK__", "sent_at": now, "recipients": n})
                sent += 1
        except Exception as exc:
            logger.warning("Rapport réseau %s : %s", month_tag, exc)
    if sent:
        logger.info("Rapports comptables envoyés : %s", sent)
    return sent
