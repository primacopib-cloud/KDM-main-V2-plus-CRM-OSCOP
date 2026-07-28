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


async def _penalties_csv(db, point, start, end):
    """CSV des pénalités de non-retrait du relais pour le mois : (csv, nb, total_uc, net_uc)."""
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "no_pickup_penalty_uc": {"$gt": 0},
         "no_pickup_reminder_sent_at": {"$gte": start, "$lt": end}},
        {"_id": 0, "order_number": 1, "user_id": 1, "status": 1, "items": 1,
         "no_pickup_penalty_uc": 1, "no_pickup_reminder_sent_at": 1,
         "auto_cancelled": 1, "no_pickup_penalty_refunded": 1}
    ).sort("no_pickup_reminder_sent_at", 1).to_list(2000)
    users = {u["id"]: u async for u in db.users.find(
        {"id": {"$in": list({o["user_id"] for o in orders if o.get("user_id")})}},
        {"_id": 0, "id": 1, "contact_name": 1, "email": 1})}
    rows = ["date;numero;client;articles;penalite_uc;penalite_eur;statut"]
    total = refunded = 0.0
    for o in orders:
        u = users.get(o.get("user_id"), {})
        pen = o["no_pickup_penalty_uc"]
        statut = ("Remboursee (retrait tardif)" if o.get("no_pickup_penalty_refunded")
                  else "Annulee auto" if o.get("auto_cancelled")
                  else "Retiree" if o.get("status") == "FULFILLED" else "En attente")
        rows.append(f"{o['no_pickup_reminder_sent_at']:%d/%m/%Y %H:%M};{o.get('order_number')};"
                    f"{u.get('contact_name') or u.get('email') or '-'};"
                    f"{sum(l.get('qty', 0) for l in o.get('items', []))};{pen:g};{pen / 10:.2f};{statut}")
        total += pen
        if o.get("no_pickup_penalty_refunded"):
            refunded += pen
    net = total - refunded
    rows += ["", f"TOTAL PENALITES;;;{len(orders)} cde(s);{total:g};{total / 10:.2f};",
             f"DONT REMBOURSEES;;;;{refunded:g};{refunded / 10:.2f};",
             f"NET FACTURE;;;;{net:g};{net / 10:.2f};"]
    return "\ufeff" + "\n".join(rows), len(orders), net


async def _tickets_zip(db, point, start, end):
    """Archive ZIP des tickets PDF du mois : (zip_bytes, nb)."""
    import io
    import zipfile
    orders = await db.lolodrive_orders.find(
        {"lolo_point_id": point["id"], "channel": "COUNTER",
         "created_at": {"$gte": start, "$lt": end}}, {"_id": 0}).sort("created_at", 1).to_list(2000)
    if not orders:
        return None, 0
    from ticket_pdf import build_ticket_pdf
    from routes_ticket_pdf import _public_ticket_url
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for o in orders:
            z.writestr(f"ticket-{o.get('order_number')}.pdf",
                       build_ticket_pdf(o, point, public_url=_public_ticket_url(o["id"])))
    return buf.getvalue(), len(orders)


async def send_accountant_report(db, point, start, end, month_tag) -> bool:
    """Construit et envoie les CSV (caisse + heures + pénalités) au comptable du relais."""
    from brevo_service import send_email, _wrap_html
    email = point.get("accountant_email")
    if not email:
        return False
    cash_csv, nb_sales, total = await _cash_csv(db, point, start, end)
    hours_csv = await _hours_csv(db, point, start, end)
    pen_csv, nb_pen, pen_net = await _penalties_csv(db, point, start, end)
    tickets_zip, nb_tickets = await _tickets_zip(db, point, start, end)
    month_label = start.strftime("%m/%Y")
    subject = f"📊 Rapport mensuel {month_label} — {point['name']} ({point['code']})"
    pen_line = (f"<li><strong>Pénalités de non-retrait</strong> : {nb_pen} commande(s) — "
                f"net facturé {pen_net:g} UC ({pen_net / 10:.2f} €) (CSV joint)</li>"
                if nb_pen else "<li><strong>Pénalités de non-retrait</strong> : aucune ce mois-ci</li>")
    body = f"""
      <p>Bonjour,</p>
      <p>Veuillez trouver ci-joint le rapport comptable du relais <strong>{point['name']} ({point['code']})</strong>
      pour <strong>{month_label}</strong> :</p>
      <ul style='font-size:13px'>
        <li><strong>Caisse comptoir</strong> : {nb_sales} vente(s) — total {total / 100:.2f} € (CSV joint)</li>
        <li><strong>Relevés d'heures des opérateurs</strong> (CSV joint, présence nette pauses déduites)</li>
        {pen_line}
        {f"<li><strong>Tickets de caisse</strong> : {nb_tickets} ticket(s) PDF du mois (archive ZIP jointe)</li>" if nb_tickets else ''}
      </ul>
      <p style='color:#999;font-size:11px;margin-top:12px'>Rapport automatique mensuel — Réseau LOLODRIVE by O'SCOP.</p>
    """
    attachments = [
        {"content": base64.b64encode(cash_csv.encode("utf-8")).decode(), "name": f"caisse-{point['code']}-{month_tag}.csv"},
        {"content": base64.b64encode(hours_csv.encode("utf-8")).decode(), "name": f"heures-{point['code']}-{month_tag}.csv"},
    ]
    if nb_pen:
        attachments.append({"content": base64.b64encode(pen_csv.encode("utf-8")).decode(),
                            "name": f"penalites-{point['code']}-{month_tag}.csv"})
    if tickets_zip:
        attachments.append({"content": base64.b64encode(tickets_zip).decode(),
                            "name": f"tickets-{point['code']}-{month_tag}.zip"})
    await send_email(
        to_email=email, to_name=None, subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Rapport {month_label} {point['code']} : {nb_sales} ventes, {total / 100:.2f} €.",
        tags=["rapport_comptable"],
        attachments=attachments)
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
    rech_by_point, rech_uc_total = {}, 0
    async for r in db.counter_recharges.find({"created_at": {"$gte": start, "$lt": end}}, {"_id": 0}):
        pt = points.get(r.get("point_id"), {})
        label = f"{pt.get('code', '?')} — {pt.get('name', '')}".strip(" —")
        e = rech_by_point.setdefault(label, {"count": 0, "uc": 0})
        e["count"] += 1
        e["uc"] += r.get("amount_uc", 0)
        rech_uc_total += r.get("amount_uc", 0)
    if rech_by_point:
        rows += ["", "RECHARGES CREDI'SCOP AU COMPTOIR;relais;nombre;uc;eur_encaisses"]
        for label, e in sorted(rech_by_point.items(), key=lambda x: -x[1]["uc"]):
            rows.append(f"RECHARGE;{label};{e['count']};{e['uc']:g};{e['uc'] / 10:.2f}")
        rows.append(f"TOTAL RECHARGES;;{sum(e['count'] for e in rech_by_point.values())};{rech_uc_total:g};{rech_uc_total / 10:.2f}")
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
      {(lambda: f'''
      <p style='margin:14px 0 4px'><strong>🔋 Recharges CREDI'SCOP encaissées au comptoir : +{rech_uc_total:g} UC ({rech_uc_total / 10:.2f} €)</strong></p>
      <table style='width:100%;border-collapse:collapse;font-size:13px;margin:4px 0'>
        <tr style='color:#888;font-size:11px;text-transform:uppercase'>
          <td style='padding:4px 8px'>Relais</td><td style='padding:4px 8px;text-align:center'>Recharges</td>
          <td style='padding:4px 8px;text-align:right'>UC créditées</td></tr>
        {"".join(f"<tr><td style='padding:5px 8px;border-bottom:1px solid #eee'>{label}</td>"
                 f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:center'>{e['count']}</td>"
                 f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:bold'>+{e['uc']:g} UC ({e['uc'] / 10:.2f} €)</td></tr>"
                 for label, e in sorted(rech_by_point.items(), key=lambda x: -x[1]['uc']))}
      </table>''')() if rech_by_point else ''}
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
