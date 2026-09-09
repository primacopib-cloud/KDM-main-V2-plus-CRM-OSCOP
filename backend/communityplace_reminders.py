"""Relance automatique : frais de publication CommunityPlace impayés depuis plus de 48 h."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def run_communityplace_payment_reminders(db):
    """Email de rappel unique par publication (nouveau lien Stripe, l'ancien expire à 24 h)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    needs = await db.purchase_needs.find({
        "communityplace_payment_status": "PENDING",
        "communityplace_reminder_sent": {"$ne": True},
        "communityplace_at": {"$lt": cutoff},
    }).to_list(50)
    if not needs:
        return 0
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    sent = 0
    for need in needs:
        try:
            fee_eur = float(need.get("communityplace_fee_eur") or 50)
            session = stripe.checkout.Session.create(
                mode="payment",
                customer_email=need["email"],
                line_items=[{"price_data": {"currency": "eur", "unit_amount": int(fee_eur * 100),
                             "product_data": {"name": f"Frais de publication CommunityPlace — {need['reference']} {need['product']}"}},
                             "quantity": 1}],
                metadata={"purchase_need_id": need["id"], "kind": "COMMUNITYPLACE_FEE"},
                success_url=f"{base}/paiement/retour?session_id={{CHECKOUT_SESSION_ID}}&kind=COMMUNITYPLACE&ref={need['reference']}",
                cancel_url=f"{base}/?communityplace_cancelled=1",
            )
            from brevo_service import send_email, _wrap_html
            label = "offre produit" if (need.get("listing_type") or "").upper() == "OFFRE" else "besoin d'achat"
            await send_email(
                to_email=need["email"], to_name=need.get("contact_name"),
                subject=f"⏰ Rappel — frais de publication CommunityPlace impayés ({need['reference']})",
                html_content=_wrap_html("Rappel de paiement", (
                    f"<p style='font-size:14px;'>Bonjour {need.get('contact_name', '')},</p>"
                    f"<p style='font-size:14px;'>Les frais de publication de votre {label} "
                    f"<b>{need['reference']} — {need['product']}</b> ({fee_eur:,.0f} €) restent impayés "
                    "depuis plus de 48 heures. Votre publication ne sera visible sur la CommunityPlace "
                    "qu'après règlement.</p>"
                    f"<p style='text-align:center;'><a href='{session.url}' style='display:inline-block;background:#D9B35A;"
                    "color:#1F0A33;font-weight:bold;padding:12px 26px;border-radius:12px;text-decoration:none;'>"
                    "Payer les frais de publication</a></p>").replace(",", " ")),
                tags=["communityplace-reminder"])
            await db.purchase_needs.update_one({"id": need["id"]}, {"$set": {
                "communityplace_reminder_sent": True,
                "communityplace_reminder_at": datetime.now(timezone.utc).isoformat(),
                "communityplace_checkout_id": session.id}})
            sent += 1
        except Exception as exc:
            logger.warning("Relance CommunityPlace %s : %s", need.get("reference"), exc)
    if sent:
        logger.info("Relances CommunityPlace envoyées : %s", sent)
    return sent
