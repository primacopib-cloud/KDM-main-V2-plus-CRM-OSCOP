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


async def run_auction_maintenance(database):
    """Tâche planifiée : transitions de statut + relance des enchères récurrentes."""
    if ah.db is None:
        ah.set_auction_database(database)
    await ah.sync_auction_statuses()
