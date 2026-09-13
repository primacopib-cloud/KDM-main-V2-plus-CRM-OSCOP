"""Emails et notifications du circuit enchères produits (gagnant + équipe)."""
import logging

import auction_helpers as ah

logger = logging.getLogger(__name__)


async def send_winner_email(auction: dict):
    """Email au gagnant : invitation à choisir retrait LOLODRIVE ou livraison."""
    w = auction.get("winner") or {}
    if not w.get("email"):
        return
    try:
        from brevo_service import send_email, _wrap_html
        import os
        base = os.environ.get("FRONTEND_URL", "").rstrip("/")
        link = f"{base}/encheres?win={auction['id']}" if base else "/encheres"
        subject = f"🎉 Vous avez remporté l'enchère — {auction.get('title')}"
        body = (
            f"<p style='font-size:14px;'>Bonjour {w.get('name')},</p>"
            f"<p style='font-size:14px;'>Félicitations ! Vous venez de remporter l'enchère "
            f"<b>{auction.get('reference')}</b> — <b>{auction.get('title')}</b> "
            f"au prix de <b>{w.get('price_eur'):.2f} €</b> "
            f"({w.get('price_credits')} crédits CREDI'SCOP-Enchères).</p>"
            "<p style='font-size:14px;'>Il ne reste qu'une étape : choisissez comment récupérer votre produit :</p>"
            "<ul style='font-size:14px;'>"
            "<li><b>Retrait</b> dans le relais LOLODRIVE de votre choix ;</li>"
            "<li><b>Livraison</b> à l'adresse de votre choix.</li></ul>"
            f"<p style='font-size:14px;'><a href='{link}' "
            "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
            "text-decoration:none;font-weight:bold;'>Choisir retrait ou livraison</a></p>"
            "<p style='font-size:12px;color:#B8A98F;'>Les crédits CREDI'SCOP-Enchères sont des unités "
            "internes de services : ils ne constituent ni un solde financier, ni un moyen de paiement.</p>")
        await send_email(to_email=w["email"], to_name=w.get("name"), subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"Vous avez remporté l'enchère {auction.get('reference')} — "
                                      f"{auction.get('title')} à {w.get('price_eur'):.2f} €. "
                                      f"Choisissez retrait LOLODRIVE ou livraison : {link}",
                         tags=["auction-winner"])
    except Exception as exc:
        logger.warning("Email gagnant enchère %s : %s", auction.get("id"), exc)


async def notify_admin_win(auction: dict):
    w = auction.get("winner") or {}
    try:
        from core_deps import create_notification
        await create_notification(
            "auction_won", f"Enchère remportée — {auction.get('reference')}",
            f"{w.get('name')} ({w.get('email')}) a remporté « {auction.get('title')} » "
            f"à {w.get('price_eur'):.2f} € ({w.get('price_credits')} crédits).",
            {"auction_id": auction.get("id")})
    except Exception as exc:
        logger.warning("Notification admin victoire %s : %s", auction.get("id"), exc)


async def notify_admin_fulfillment(auction: dict, fulfillment: dict):
    w = auction.get("winner") or {}
    detail = (f"retrait au relais {fulfillment.get('point_name')}" if fulfillment.get("mode") == "PICKUP"
              else f"livraison : {fulfillment.get('address')}")
    try:
        from core_deps import create_notification
        await create_notification(
            "auction_fulfillment", f"Remise du lot — {auction.get('reference')}",
            f"{w.get('name')} a choisi {detail} pour « {auction.get('title')} ».",
            {"auction_id": auction.get("id")})
    except Exception as exc:
        logger.warning("Notification remise lot %s : %s", auction.get("id"), exc)
    try:
        from brevo_service import send_email, _wrap_html
        subject = f"Remise du lot enchère {auction.get('reference')}"
        body = (f"<p style='font-size:14px;'>Le gagnant <b>{w.get('name')}</b> ({w.get('email')}) a choisi : "
                f"<b>{detail}</b> pour le lot « {auction.get('title')} ».</p>")
        await send_email(to_email="contact@objectifscopoutremer.com", to_name="Équipe O'SCOP",
                         subject=subject, html_content=_wrap_html(subject, body),
                         text_content=f"{w.get('name')} : {detail}", tags=["auction-fulfillment"])
    except Exception as exc:
        logger.warning("Email équipe remise lot %s : %s", auction.get("id"), exc)


async def run_auction_ending_alerts(database=None):
    """Alerte « fin imminente » : email + cloche aux détenteurs de plan actif quand une enchère LIVE finit dans <1h."""
    if database is not None and ah.db is None:
        ah.set_auction_database(database)
    from datetime import timedelta
    now = ah.now_utc()
    sent = 0
    async for a in ah.db.auctions.find(
            {"status": "LIVE", "ending_alert_sent": {"$ne": True}}, {"_id": 0}):
        ends = ah.parse_dt(a.get("ends_at"))
        if not ends or not (now < ends <= now + timedelta(hours=1)):
            continue
        res = await ah.db.auctions.update_one(
            {"id": a["id"], "ending_alert_sent": {"$ne": True}},
            {"$set": {"ending_alert_sent": True, "ending_alert_at": now.isoformat()}})
        if res.modified_count == 0:
            continue
        mins = max(1, int((ends - now).total_seconds() // 60))
        price = round(float(a.get("current_price_eur") or a.get("value_eur") or 0), 2)
        holders = await ah.db.auction_accounts.find(
            {"valid_until": {"$gt": now.isoformat()}}, {"_id": 0, "user_id": 1}).to_list(500)
        for h in holders:
            user = await ah.db.users.find_one(
                {"id": h["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "first_name": 1})
            if not user:
                continue
            try:
                from core_deps import create_notification
                await create_notification(
                    "auction_ending", f"⏳ Fin imminente — {a.get('title')}",
                    f"L'enchère {a.get('reference')} se termine dans {mins} min — prix actuel {price:.2f} € "
                    f"({ah.eur_to_credits(price)} crédits). Premier à accepter = gagnant !",
                    target_user_id=h["user_id"],
                    data={"auction_id": a["id"], "action_url": "/encheres"})
            except Exception as exc:
                logger.warning("Cloche fin imminente %s : %s", h["user_id"], exc)
            if user.get("email"):
                try:
                    from brevo_service import send_email, _wrap_html
                    name = user.get("first_name") or user.get("contact_name") or ""
                    subject = f"⏳ Plus que {mins} min — {a.get('title')}"
                    import os
                    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
                    body = (
                        f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                        f"<p style='font-size:14px;'>L'enchère <b>{a.get('reference')}</b> — "
                        f"<b>{a.get('title')}</b> se termine dans <b>{mins} minute(s)</b>.</p>"
                        f"<p style='font-size:14px;'>Prix actuel : <b>{price:.2f} €</b> "
                        f"({ah.eur_to_credits(price)} crédits). Le premier membre qui accepte remporte le lot !</p>"
                        f"<p style='font-size:14px;'><a href='{base}/encheres' "
                        "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                        "text-decoration:none;font-weight:bold;'>Ouvrir la salle des enchères</a></p>")
                    await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                                     html_content=_wrap_html(subject, body),
                                     text_content=f"L'enchère {a.get('title')} finit dans {mins} min — "
                                                  f"prix actuel {price:.2f} €. {base}/encheres",
                                     tags=["auction-ending"])
                    sent += 1
                except Exception as exc:
                    logger.warning("Email fin imminente %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Alertes fin d'enchère envoyées : %s", sent)
    return sent


async def run_auction_maintenance(database):
    """Tâche planifiée : transitions de statut + relance des enchères récurrentes + alertes fin imminente."""
    if ah.db is None:
        ah.set_auction_database(database)
    await ah.sync_auction_statuses()
    await run_auction_ending_alerts()


STATUS_FR = {"SCHEDULED": "Programmée", "LIVE": "En cours", "WON": "Remportée",
             "EXPIRED": "Expirée", "CANCELLED": "Annulée"}


async def run_auction_monthly_report(database, force: bool = False):
    """Chaque 1er du mois : email au superadmin — CSV des mises par enchère + conversion des plans (mois écoulé)."""
    import base64
    import os
    from datetime import timedelta

    if ah.db is None:
        ah.set_auction_database(database)
    db = ah.db
    now = ah.now_utc()
    if not force and now.day != 1:
        return 0
    month_tag = now.strftime("%Y-%m")
    flag = f"auction_monthly_report_{month_tag}"
    if not force and await db.system_flags.find_one({"key": flag}):
        return 0
    prev = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    bids = await db.auction_bids.find(
        {"created_at": {"$regex": f"^{prev}"}}, {"_id": 0}).to_list(5000)
    spend = await db.auction_credit_ledger.find(
        {"type": "SPEND", "created_at": {"$regex": f"^{prev}"}}, {"_id": 0, "amount": 1}).to_list(5000)
    credits_collected = -sum(e["amount"] for e in spend)

    by_bid = {}
    for b in bids:
        e = by_bid.setdefault(b["auction_id"], {"bids": 0, "credits": 0})
        e["bids"] += 1
        e["credits"] += b.get("credits_spent", 0)
    won = await db.auctions.find(
        {"status": "WON", "winner.won_at": {"$regex": f"^{prev}"}}, {"_id": 0}).to_list(200)
    auc_ids = list(set(by_bid) | {a["id"] for a in won})
    auctions = {a["id"]: a async for a in db.auctions.find(
        {"id": {"$in": auc_ids}}, {"_id": 0})} if auc_ids else {}

    esc = lambda v: '"' + str(v if v is not None else "").replace('"', '""') + '"'
    csv_rows = [';'.join(esc(h) for h in ["Référence", "Enchère", "Statut", "Mises",
                                          "Crédits des mises", "Crédits du gagnant", "Total crédits"])]
    for aid in auc_ids:
        a = auctions.get(aid)
        if not a:
            continue
        b = by_bid.get(aid, {"bids": 0, "credits": 0})
        wc = (a.get("winner") or {}).get("price_credits") or 0
        csv_rows.append(";".join(esc(v) for v in [
            a.get("reference"), a.get("title"), STATUS_FR.get(ah.effective_status(a), a.get("status")),
            b["bids"], b["credits"], wc, b["credits"] + wc]))

    purchases = await db.auction_pass_purchases.find(
        {"created_at": {"$regex": f"^{prev}"}}, {"_id": 0}).to_list(500)
    paid = [p for p in purchases if p.get("status") == "ACTIVE"]
    revenue = round(sum(p.get("ttc_cents", 0) for p in paid) / 100, 2)
    conversion = round(100 * len(paid) / len(purchases), 1) if purchases else 0.0

    from brevo_service import send_email, _wrap_html
    subject = f"Rapport mensuel Enchères — {prev}"
    body = (
        f"<p style='font-size:14px;'>Récapitulatif des enchères produits pour le mois <b>{prev}</b> :</p>"
        "<table style='font-size:13px;border-collapse:collapse'>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Crédits collectés</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{credits_collected:,.0f} cr</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Mises</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(bids)}</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Enchères remportées</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(won)}</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Plans vendus (payés/sessions)</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(paid)}/{len(purchases)}</b> — {revenue:,.2f} € TTC</td></tr>"
        f"<tr><td style='padding:4px 10px'>Conversion des plans</td>"
        f"<td style='padding:4px 10px;text-align:right'><b>{conversion} %</b></td></tr></table>"
        + ("<p style='font-size:13px;'>Le détail des mises par enchère est joint en CSV.</p>" if len(csv_rows) > 1
           else "<p style='font-size:13px;'>Aucune activité d'enchère sur le mois écoulé.</p>"))
    attachments = [{"content": base64.b64encode(("\ufeff" + "\r\n".join(csv_rows)).encode("utf-8")).decode(),
                    "name": f"encheres_mises_{prev}.csv"}] if len(csv_rows) > 1 else []
    team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    result = await send_email(
        to_email=team, to_name="Super Admin", subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Rapport enchères {prev} : {credits_collected} crédits collectés, "
                     f"{len(bids)} mises, {len(won)} remportées, plans {len(paid)}/{len(purchases)} "
                     f"({conversion} %), {revenue} € TTC.",
        tags=["auction-monthly-report"], attachments=attachments)
    if result is None:
        logger.warning("Rapport mensuel enchères %s : envoi échoué, nouvel essai au prochain passage", prev)
        return 0
    await db.system_flags.update_one(
        {"key": flag}, {"$set": {"key": flag, "at": now.isoformat(), "month": prev}}, upsert=True)
    logger.info("Rapport mensuel enchères %s envoyé à %s", prev, team)
    return 1
