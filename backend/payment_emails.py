"""Emails Brevo + PDF du flux d'achat de crédits wallet (succès, échec, reçu)."""
import base64
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def build_receipt_pdf(db, user: dict, transaction: dict) -> bytes:
    """Génère la facture PDF d'un achat de crédits wallet."""
    from pdf_credit_invoice import generate_credit_invoice_pdf

    pack = await db.wallet_credit_packs.find_one({"id": transaction.get("package_id")}, {"_id": 0}) or \
        {"name": transaction.get("package_id", "Pack de crédits"), "credits": transaction["credits"]}
    client = {
        "company_name": user.get("company_name") or user.get("contact_name") or user["email"],
        "contact_name": user.get("contact_name") or "",
        "email": user["email"],
    }
    return generate_credit_invoice_pdf(
        client, pack, transaction["credits"], 0,
        float(transaction["amount"]), transaction["session_id"],
    )


async def send_wallet_receipt_email(db, user: dict, transaction: dict) -> None:
    """Notification de paiement réussi + facture PDF jointe."""
    try:
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        if not is_brevo_configured() or not user.get("email"):
            return
        pdf = await build_receipt_pdf(db, user, transaction)
        body = (
            f"<p>Bonjour {user.get('contact_name') or ''},</p>"
            f"<p>Merci pour votre achat ! <strong>{transaction['credits']} crédits</strong> "
            f"ont été ajoutés à votre solde CREDI&rsquo;SCOP pour <strong>{float(transaction['amount']):.2f} €</strong>.</p>"
            "<p>Vous trouverez votre facture en pièce jointe. Elle reste re-téléchargeable "
            "à tout moment depuis votre espace CREDI&rsquo;SCOP.</p>"
        )
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject=f"✓ Paiement réussi — Votre facture KDMARCHÉ ({transaction['credits']} crédits)",
            html_content=_wrap_html("Reçu — Achat de crédits", body),
            tags=["wallet-credit-receipt"],
            attachments=[{
                "content": base64.b64encode(pdf).decode(),
                "name": f"facture-credits-{transaction['session_id'][-8:]}.pdf",
            }],
        )
        logger.info(f"Wallet receipt email sent to {user['email']} (session {transaction['session_id']})")
    except Exception as exc:
        logger.error(f"Wallet receipt email failed: {exc}")


async def send_payment_failed_email(user: dict, transaction: dict, reason: str = "expiré") -> None:
    """Email à l'acheteur quand le paiement carte échoue ou expire."""
    try:
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        if not is_brevo_configured() or not user.get("email"):
            return
        body = (
            f"<p>Bonjour {user.get('contact_name') or ''},</p>"
            f"<p>Votre paiement par carte de <strong>{float(transaction['amount']):.2f} €</strong> "
            f"({transaction['credits']} crédits) n'a pas abouti : <strong>paiement {reason}</strong>.</p>"
            "<p>Aucun montant n'a été débité et aucun crédit n'a été ajouté.</p>"
            "<p>Vous pouvez relancer l'achat à tout moment depuis votre espace CREDI&rsquo;SCOP "
            "(bouton « Acheter des crédits »).</p>"
        )
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject="✗ Échec du paiement — Achat de crédits KDMARCHÉ",
            html_content=_wrap_html("Paiement non abouti", body),
            tags=["wallet-payment-failed"],
        )
        logger.info(f"Payment failed email sent to {user['email']} (session {transaction['session_id']})")
    except Exception as exc:
        logger.error(f"Payment failed email error: {exc}")


async def notify_payment_failure_once(db, user: dict, transaction: dict, reason: str) -> None:
    """Envoie l'email d'échec une seule fois par transaction (idempotent)."""
    claim = await db.payment_transactions.update_one(
        {"session_id": transaction["session_id"], "failure_notified": {"$ne": True}},
        {"$set": {"failure_notified": True, "updated_at": datetime.now(timezone.utc)}},
    )
    if claim.modified_count == 1:
        await send_payment_failed_email(user, transaction, reason)
