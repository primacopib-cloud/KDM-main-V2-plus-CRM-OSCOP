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
        subject = f"🎉 Vous avez remporté le COOP'ACT — {auction.get('title')}"
        body = (
            f"<p style='font-size:14px;'>Bonjour {w.get('name')},</p>"
            f"<p style='font-size:14px;'>Félicitations ! Vous venez de remporter le COOP'ACT "
            f"<b>{auction.get('reference')}</b> — <b>{auction.get('title')}</b> "
            f"au prix de <b>{w.get('price_eur'):.2f} €</b> "
            f"({w.get('price_credits')} crédits CREDI'SCOP-COOP'ACT).</p>"
            "<p style='font-size:14px;'>Il ne reste qu'une étape : choisissez comment récupérer votre produit :</p>"
            "<ul style='font-size:14px;'>"
            "<li><b>Retrait</b> dans le relais LOLODRIVE de votre choix ;</li>"
            "<li><b>Livraison</b> à l'adresse de votre choix.</li></ul>"
            + (f"<p style='font-size:14px;'>Votre <b>QR d'enlèvement</b> à présenter lors du retrait du lot :</p>"
               f"<p><img src='https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=coopact:{w.get('pickup_token')}' "
               f"alt='QR enlèvement' width='180' height='180' style='background:#fff;padding:8px;border-radius:8px;'/></p>"
               f"<p style='font-size:12px;color:#B8A98F;'>Code : <b>coopact:{w.get('pickup_token')}</b> — "
               "il est aussi affiché dans « Mes lots remportés » de la salle COOP'ACT.</p>"
               if w.get("pickup_token") else "")
            + f"<p style='font-size:14px;'><a href='{link}' "
            "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
            "text-decoration:none;font-weight:bold;'>Choisir retrait ou livraison</a></p>"
            "<p style='font-size:12px;color:#B8A98F;'>Les crédits CREDI'SCOP-COOP'ACT sont des unités "
            "internes de services : ils ne constituent ni un solde financier, ni un moyen de paiement.</p>"
            "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, agir ensemble pour la juste valeur.</p>")
        await send_email(to_email=w["email"], to_name=w.get("name"), subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"Vous avez remporté le COOP'ACT {auction.get('reference')} — "
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
            "auction_won", f"COOP'ACT remporté — {auction.get('reference')}",
            f"{w.get('name')} ({w.get('email')}) a remporté « {auction.get('title')} » "
            f"à {w.get('price_eur'):.2f} € ({w.get('price_credits')} crédits).",
            {"auction_id": auction.get("id")})
    except Exception as exc:
        logger.warning("Notification admin victoire %s : %s", auction.get("id"), exc)


async def notify_detaillant_win(auction: dict):
    """Cloche + email au détaillant quand un de ses lots est remporté en salle."""
    if auction.get("source") != "DETAILLANT" or not auction.get("detaillant_offer_id"):
        return
    w = auction.get("winner") or {}
    try:
        offer = await ah.db.detaillant_offers.find_one(
            {"id": auction["detaillant_offer_id"]}, {"_id": 0, "user_id": 1, "company_name": 1})
        if not offer:
            return
        seller = await ah.db.users.find_one(
            {"id": offer["user_id"]}, {"_id": 0, "email": 1, "company_name": 1})
        msg = (f"Votre lot « {auction.get('title')} » ({auction.get('reference')}) vient d'être remporté "
               f"par {w.get('name')} à {w.get('price_eur'):.2f} €. Le gagnant présentera son QR à l'enlèvement.")
        from core_deps import create_notification
        await create_notification(
            "detaillant_lot_won", f"🎉 Lot vendu — {auction.get('reference')}", msg,
            target_user_id=offer["user_id"], data={"auction_id": auction.get("id"), "action_url": "/espace-detaillant"})
        if seller and seller.get("email"):
            from brevo_service import send_email, _wrap_html
            name = seller.get("company_name") or offer.get("company_name") or ""
            subject = f"🎉 Votre lot a été remporté — {auction.get('title')}"
            body = (f"<p style='font-size:14px;'>Bonjour {name},</p>"
                    f"<p style='font-size:14px;'>{msg}</p>"
                    "<p style='font-size:14px;'>Retrouvez le détail dans « Mes ventes en salle » de votre espace détaillant.</p>"
                    "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, agir ensemble pour la juste valeur.</p>")
            await send_email(to_email=seller["email"], to_name=name or None, subject=subject,
                             html_content=_wrap_html(subject, body), text_content=msg,
                             tags=["detaillant-lot-won"])
    except Exception as exc:
        logger.warning("Alerte vente détaillant %s : %s", auction.get("id"), exc)


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
        subject = f"Remise du lot COOP'ACT {auction.get('reference')}"
        body = (f"<p style='font-size:14px;'>Le gagnant <b>{w.get('name')}</b> ({w.get('email')}) a choisi : "
                f"<b>{detail}</b> pour le lot « {auction.get('title')} ».</p>")
        await send_email(to_email="contact@objectifscopoutremer.com", to_name="Équipe O'SCOP",
                         subject=subject, html_content=_wrap_html(subject, body),
                         text_content=f"{w.get('name')} : {detail}", tags=["auction-fulfillment"])
    except Exception as exc:
        logger.warning("Email équipe remise lot %s : %s", auction.get("id"), exc)


async def notify_new_live_auction(a: dict) -> int:
    """Cloche + email aux Coop'acteurs actifs quand un lot entre en salle (idempotent via flag)."""
    if ah.db is None:
        return 0
    res = await ah.db.auctions.update_one(
        {"id": a["id"], "live_alert_sent": {"$ne": True}},
        {"$set": {"live_alert_sent": True}})
    if res.modified_count == 0:
        return 0
    now_iso = ah.now_utc().isoformat()
    price = round(float(a.get("current_price_eur") or a.get("value_eur") or 0), 2)
    holders = await ah.db.auction_accounts.find(
        {"valid_until": {"$gt": now_iso}}, {"_id": 0, "user_id": 1}).to_list(500)
    sent = 0
    import os
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    room = f"{base}/encheres" if base else "/encheres"
    for h in holders:
        user = await ah.db.users.find_one(
            {"id": h["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "first_name": 1, "phone": 1})
        if not user:
            continue
        from routes_prefs import channel_allowed
        if await channel_allowed(h["user_id"], "auction_new_live", "inapp"):
            try:
                from core_deps import create_notification
                await create_notification(
                    "auction_new_live", f"🆕 Nouveau lot en salle — {a.get('title')}",
                    f"Le COOP'ACT {a.get('reference')} vient de démarrer à {price:.2f} € "
                    f"({ah.eur_to_credits(price)} crédits) — chaque Coop'Act fait baisser le prix !",
                    target_user_id=h["user_id"],
                    data={"auction_id": a["id"], "action_url": "/encheres"})
            except Exception as exc:
                logger.warning("Cloche nouveau lot %s : %s", h["user_id"], exc)
        if a.get("featured") and user.get("phone"):
            try:
                from brevo_service import send_sms
                await send_sms(user["phone"],
                               f"COOP'ACT ⭐ Lot vedette en salle : {a.get('title')} — départ {price:.2f}€ "
                               f"({ah.eur_to_credits(price)} cr). Premier a accepter = gagnant ! {room}",
                               tag="auction-featured-live")
            except Exception as exc:
                logger.warning("SMS lot vedette %s : %s", h["user_id"], exc)
        if user.get("email") and await channel_allowed(h["user_id"], "auction_new_live", "email"):
            try:
                from brevo_service import send_email, _wrap_html
                name = user.get("first_name") or user.get("contact_name") or ""
                subject = f"🆕 Nouveau COOP'ACT en salle — {a.get('title')}"
                body = (
                    f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                    f"<p style='font-size:14px;'>Un nouveau lot vient d'entrer en salle : "
                    f"<b>{a.get('reference')}</b> — <b>{a.get('title')}</b>, prix de départ "
                    f"<b>{price:.2f} €</b> ({ah.eur_to_credits(price)} crédits).</p>"
                    f"<p style='font-size:14px;'>Chaque Coop'Act fait baisser le prix — le premier "
                    "qui accepte remporte le lot !</p>"
                    f"<p style='font-size:14px;'><a href='{room}' "
                    "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                    "text-decoration:none;font-weight:bold;'>Coop'acter maintenant</a></p>"
                    "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, "
                    "agir ensemble pour la juste valeur.</p>")
                await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                                 html_content=_wrap_html(subject, body),
                                 text_content=f"Nouveau COOP'ACT en salle : {a.get('title')} — "
                                              f"prix de départ {price:.2f} €. {room}",
                                 tags=["auction-new-live"])
                sent += 1
            except Exception as exc:
                logger.warning("Email nouveau lot %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Alertes nouveau lot %s envoyées : %s", a.get("reference"), sent)
    return sent


async def check_price_alerts(auction_id: str) -> int:
    """Cloche + email aux membres dont le prix cible est atteint (déclenché à chaque baisse de prix)."""
    if ah.db is None:
        return 0
    a = await ah.db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not a:
        return 0
    price = round(float(a.get("current_price_eur") or a.get("value_eur") or 0), 2)
    import os
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    room = f"{base}/encheres" if base else "/encheres"
    sent = 0
    alerts = await ah.db.auction_price_alerts.find(
        {"auction_id": auction_id, "triggered": {"$ne": True}, "target_eur": {"$gte": price}}).to_list(200)
    for al in alerts:
        res = await ah.db.auction_price_alerts.update_one(
            {"_id": al["_id"], "triggered": {"$ne": True}},
            {"$set": {"triggered": True, "triggered_at": ah.now_utc().isoformat(),
                      "triggered_price_eur": price}})
        if res.modified_count == 0:
            continue
        from routes_prefs import channel_allowed
        if await channel_allowed(al["user_id"], "auction_price_target", "inapp"):
            try:
                from core_deps import create_notification
                await create_notification(
                    "auction_price_target", f"🎯 Prix cible atteint — {a.get('title')}",
                    f"Le lot {a.get('reference')} est à {price:.2f} € ({ah.eur_to_credits(price)} crédits), "
                    f"sous votre cible de {al['target_eur']:.2f} €. Acceptez vite avant les autres !",
                    target_roles=[], target_user_id=al["user_id"],
                    data={"auction_id": auction_id, "action_url": "/encheres"})
            except Exception as exc:
                logger.warning("Cloche prix cible %s : %s", al["user_id"], exc)
        user = await ah.db.users.find_one(
            {"id": al["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "contact_name": 1})
        if user and user.get("email") and await channel_allowed(al["user_id"], "auction_price_target", "email"):
            try:
                from brevo_service import send_email, _wrap_html
                name = user.get("first_name") or user.get("contact_name") or ""
                subject = f"🎯 Prix cible atteint — {a.get('title')}"
                body = (
                    f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                    f"<p style='font-size:14px;'>Bonne nouvelle : le lot <b>{a.get('reference')}</b> — "
                    f"<b>{a.get('title')}</b> vient d'atteindre <b>{price:.2f} €</b> "
                    f"({ah.eur_to_credits(price)} crédits), sous votre prix cible de "
                    f"<b>{al['target_eur']:.2f} €</b>.</p>"
                    "<p style='font-size:14px;'>Le premier qui accepte remporte le lot — ne tardez pas !</p>"
                    f"<p style='font-size:14px;'><a href='{room}' "
                    "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                    "text-decoration:none;font-weight:bold;'>Accepter le prix en salle</a></p>")
                await send_email(user["email"], name or None, subject,
                                 _wrap_html(subject, body), tags=["auction-price-target"])
                sent += 1
            except Exception as exc:
                logger.warning("Email prix cible %s : %s", user.get("email"), exc)
    return sent


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
            from routes_prefs import channel_allowed
            if await channel_allowed(h["user_id"], "auction_ending", "inapp"):
                try:
                    from core_deps import create_notification
                    await create_notification(
                        "auction_ending", f"⏳ Fin imminente — {a.get('title')}",
                        f"Le COOP'ACT {a.get('reference')} se termine dans {mins} min — prix actuel {price:.2f} € "
                        f"({ah.eur_to_credits(price)} crédits). Premier à accepter = gagnant !",
                        target_user_id=h["user_id"],
                        data={"auction_id": a["id"], "action_url": "/encheres"})
                except Exception as exc:
                    logger.warning("Cloche fin imminente %s : %s", h["user_id"], exc)
            if user.get("email") and await channel_allowed(h["user_id"], "auction_ending", "email"):
                try:
                    from brevo_service import send_email, _wrap_html
                    name = user.get("first_name") or user.get("contact_name") or ""
                    subject = f"⏳ Plus que {mins} min — {a.get('title')}"
                    import os
                    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
                    body = (
                        f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                        f"<p style='font-size:14px;'>Le COOP'ACT <b>{a.get('reference')}</b> — "
                        f"<b>{a.get('title')}</b> se termine dans <b>{mins} minute(s)</b>.</p>"
                        f"<p style='font-size:14px;'>Prix actuel : <b>{price:.2f} €</b> "
                        f"({ah.eur_to_credits(price)} crédits). Le premier membre qui accepte remporte le lot !</p>"
                        f"<p style='font-size:14px;'><a href='{base}/encheres' "
                        "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                        "text-decoration:none;font-weight:bold;'>Ouvrir la salle COOP'ACT</a></p>"
                        "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, agir ensemble pour la juste valeur.</p>")
                    await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                                     html_content=_wrap_html(subject, body),
                                     text_content=f"Le COOP'ACT {a.get('title')} finit dans {mins} min — "
                                                  f"prix actuel {price:.2f} €. {base}/encheres",
                                     tags=["auction-ending"])
                    sent += 1
                except Exception as exc:
                    logger.warning("Email fin imminente %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Alertes fin d'enchère envoyées : %s", sent)
    return sent


async def run_auction_plan_expiry_reminders(database):
    """Rappel J-3 : invite chaque Coop'acteur à recharger avant l'expiration de son plan (idempotent par cycle)."""
    from datetime import timedelta
    import os
    if ah.db is None:
        ah.set_auction_database(database)
    db = ah.db
    now = ah.now_utc()
    limit = (now + timedelta(days=3)).isoformat()
    sent = 0
    async for acc in db.auction_accounts.find(
            {"valid_until": {"$gt": now.isoformat(), "$lte": limit}},
            {"_id": 0}):
        if acc.get("expiry_reminded_for") == acc.get("valid_until"):
            continue
        res = await db.auction_accounts.update_one(
            {"user_id": acc["user_id"], "expiry_reminded_for": {"$ne": acc["valid_until"]}},
            {"$set": {"expiry_reminded_for": acc["valid_until"]}})
        if res.modified_count == 0:
            continue
        user = await db.users.find_one(
            {"id": acc["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "contact_name": 1})
        if not user:
            continue
        name = user.get("first_name") or user.get("contact_name") or ""
        exp = (acc.get("valid_until") or "")[:10]
        plan_label = acc.get("plan_label") or "CREDI'SCOP COOP'ACT"
        try:
            exp_fr = "-".join(reversed(exp.split("-")))
        except Exception:
            exp_fr = exp
        from routes_prefs import channel_allowed
        if await channel_allowed(acc["user_id"], "auction_plan_expiry", "inapp"):
            try:
                from core_deps import create_notification
                await create_notification(
                    "auction_plan_expiry", "⏳ Votre plan COOP'ACT expire bientôt",
                    f"Votre plan {plan_label} expire le {exp_fr} — "
                    f"il vous reste {acc.get('credits', 0)} crédits. Rechargez pour continuer à coop'acter !",
                    target_user_id=acc["user_id"], data={"action_url": "/encheres"})
            except Exception as exc:
                logger.warning("Cloche expiration plan %s : %s", acc["user_id"], exc)
        if user.get("email") and await channel_allowed(acc["user_id"], "auction_plan_expiry", "email"):
            try:
                from brevo_service import send_email, _wrap_html
                base = os.environ.get("FRONTEND_URL", "").rstrip("/")
                subject = "⏳ Votre plan COOP'ACT expire bientôt"
                body = (
                    f"<p style='font-size:14px;'>Bonjour{f' {name}' if name else ''},</p>"
                    f"<p style='font-size:14px;'>Votre plan <b>{plan_label}</b> "
                    f"expire le <b>{exp_fr}</b> — il vous reste <b>{acc.get('credits', 0)} crédits</b>.</p>"
                    "<p style='font-size:14px;'>Rechargez dès maintenant pour continuer à coop'acter : "
                    "vos crédits s'ajoutent et votre validité est prolongée.</p>"
                    f"<p style='font-size:14px;'><a href='{base}/encheres' "
                    "style='background:#D9B35A;color:#2A1045;padding:10px 18px;border-radius:8px;"
                    "text-decoration:none;font-weight:bold;'>Recharger mon plan</a></p>"
                    "<p style='font-size:12px;color:#B8A98F;'><b>BOURSE COOPÉRATIVE — COOP'ACT</b>, "
                    "agir ensemble pour la juste valeur.</p>")
                await send_email(to_email=user["email"], to_name=name or None, subject=subject,
                                 html_content=_wrap_html(subject, body),
                                 text_content=f"Votre plan COOP'ACT expire le {exp_fr} — "
                                              f"rechargez sur {base}/encheres",
                                 tags=["auction-plan-expiry"])
                sent += 1
            except Exception as exc:
                logger.warning("Email expiration plan %s : %s", user.get("email"), exc)
    if sent:
        logger.info("Rappels expiration plan COOP'ACT envoyés : %s", sent)
    return sent


async def run_auction_maintenance(database):
    """Tâche planifiée : transitions de statut + relance des enchères récurrentes + alertes fin imminente."""
    if ah.db is None:
        ah.set_auction_database(database)
    await ah.sync_auction_statuses()
    await run_auction_ending_alerts()
    await run_auction_plan_expiry_reminders(ah.db)


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
    csv_rows = [';'.join(esc(h) for h in ["Référence", "COOP'ACT", "Statut", "Mises",
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
    subject = f"Rapport mensuel COOP'ACT — {prev}"
    body = (
        f"<p style='font-size:14px;'>Récapitulatif des COOP'ACT produits pour le mois <b>{prev}</b> :</p>"
        "<table style='font-size:13px;border-collapse:collapse'>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Crédits collectés</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{credits_collected:,.0f} cr</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Mises</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(bids)}</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>COOP'ACT remportés</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(won)}</b></td></tr>"
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>Plans vendus (payés/sessions)</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'><b>{len(paid)}/{len(purchases)}</b> — {revenue:,.2f} € TTC</td></tr>"
        f"<tr><td style='padding:4px 10px'>Conversion des plans</td>"
        f"<td style='padding:4px 10px;text-align:right'><b>{conversion} %</b></td></tr></table>"
        + ("<p style='font-size:13px;'>Le détail des mises par COOP'ACT est joint en CSV.</p>" if len(csv_rows) > 1
           else "<p style='font-size:13px;'>Aucune activité COOP'ACT sur le mois écoulé.</p>"))
    attachments = [{"content": base64.b64encode(("\ufeff" + "\r\n".join(csv_rows)).encode("utf-8")).decode(),
                    "name": f"coopact_mises_{prev}.csv"}] if len(csv_rows) > 1 else []
    team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    result = await send_email(
        to_email=team, to_name="Super Admin", subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Rapport COOP'ACT {prev} : {credits_collected} crédits collectés, "
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
