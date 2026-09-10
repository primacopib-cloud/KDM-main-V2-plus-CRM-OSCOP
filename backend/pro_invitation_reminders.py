"""Relances J+7 et J+14 des invitations pro CommunityPlace (non convertis en membres)."""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def run_pro_invitation_reminders(db) -> int:
    """Relance les invités des 3 annonces qui n'ont pas adhéré : J+7 puis J+14. Idempotent."""
    from brevo_service import send_email, _wrap_html, is_brevo_configured
    from routes_purchase_needs import _is_pro_subscriber, _pro_cta_table, _promo_block
    if not is_brevo_configured():
        return 0
    now = datetime.now(timezone.utc)
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    sent = 0
    async for inv in db.communityplace_pro_invitations.find(
            {"$or": [{"reminder2_sent_at": {"$exists": False}}, {"reminder2_sent_at": None}]}, {"_id": 0}):
        try:
            invited_at = datetime.fromisoformat(inv["invited_at"])
        except Exception:
            continue
        age = now - invited_at
        step = None
        if age >= timedelta(days=14) and not inv.get("reminder2_sent_at"):
            step = 2
        elif age >= timedelta(days=7) and not inv.get("reminder1_sent_at"):
            step = 1
        if not step:
            continue
        if await _is_pro_subscriber(inv["email"]):
            from routes_purchase_needs import handle_pro_conversion
            await handle_pro_conversion(inv["email"], "détectée lors des relances")
            continue
        code = inv.get("promo_code") or ""
        promo = _promo_block(code, inv.get("promo_expires_at")) if code else ""
        if step == 1:
            subject = "⏰ Votre invitation professionnelle KDMARCHÉ vous attend (-20 %)"
            body = (
                "<p style='font-size:14px;'>Bonjour,</p>"
                "<p style='font-size:14px;'>Il y a une semaine, vous avez rejoint votre 3ᵉ annonce sur la "
                "CommunityPlace et reçu une invitation à devenir <b>membre professionnel</b> de la coopérative O'SCOP.</p>"
                "<p style='font-size:14px;'>En tant que membre, vous rejoignez les annonces <b>gratuitement</b> et "
                "profitez des prix négociés, du catalogue B2B multi-territoires et de la logistique LOGI'SCOP.</p>")
        else:
            subject = "🎁 Dernière relance — votre code -20 % sur l'adhésion pro expire bientôt"
            body = (
                "<p style='font-size:14px;'>Bonjour,</p>"
                "<p style='font-size:14px;'>Dernier rappel : votre <b>offre de bienvenue -20 %</b> sur la première "
                "adhésion professionnelle KDMARCHÉ est toujours disponible.</p>"
                "<p style='font-size:14px;'>Sans adhésion, il n'est plus possible de rejoindre de nouvelles annonces "
                "sur la CommunityPlace. Les membres professionnels y participent <b>gratuitement</b> et sans limite.</p>")
        try:
            await send_email(
                to_email=inv["email"], to_name=None, subject=subject,
                html_content=_wrap_html("Devenez membre professionnel", body + promo + _pro_cta_table(base, code or None)),
                tags=[f"pro-invitation-reminder-j{7 * step}"])
            await db.communityplace_pro_invitations.update_one(
                {"email": inv["email"]},
                {"$set": {f"reminder{step}_sent_at": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Relance invitation pro %s (J+%d) : %s", inv["email"], 7 * step, exc)
    if sent:
        logger.info("Relances invitation pro envoyées : %d", sent)
    return sent
