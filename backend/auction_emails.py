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
