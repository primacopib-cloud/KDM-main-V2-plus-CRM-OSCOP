"""Alerte admin J-7 avant chaque échéance de remboursement investisseur (financing_products)."""
import logging
import os
from datetime import date, datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def run_repayment_alerts(db) -> int:
    """Email admin à J-7 avant chaque échéance non honorée. Idempotent (repayment_alerts_sent)."""
    from brevo_service import send_email, _wrap_html, is_brevo_configured
    from routes_product_financing import build_repayment_schedule
    if not is_brevo_configured():
        return 0
    today = date.today()
    team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    sent = 0
    async for fp in db.financing_products.find(
            {"status": "PAID", "repayment_date": {"$ne": None}}, {"_id": 0}):
        schedule = build_repayment_schedule(fp)
        alerts_sent = set(fp.get("repayment_alerts_sent") or [])
        for step in schedule:
            if step["paid"] or step["due_date"] in alerts_sent:
                continue
            due = date.fromisoformat(step["due_date"])
            if not (today <= due <= today + timedelta(days=7)):
                continue
            try:
                await send_email(
                    to_email=team, to_name=None,
                    subject=f"⏰ Échéance de remboursement J-{(due - today).days} — {fp['reference']} · {fp['name']}",
                    html_content=_wrap_html("Échéance de remboursement investisseur", (
                        f"<p style='font-size:14px;'>L'échéance du <b>{due.strftime('%d/%m/%Y')}</b> "
                        f"({step['amount_eur']:,.2f} €) du financement <b>{fp['reference']} — {fp['name']}</b> "
                        f"arrive dans <b>{(due - today).days} jour(s)</b>.</p>"
                        f"<p style='font-size:14px;'>Investisseur : <b>{fp.get('paid_by') or '—'}</b> · "
                        f"Total : {fp.get('repayment_amount_eur', 0):,.2f} € sur {fp.get('repayment_duration_months')} mois.</p>"
                        "<p style='font-size:13px;'>Marquez l'échéance « Remboursé » dans le superadmin (Achat-Revente) "
                        "une fois le virement effectué.</p>")),
                    tags=["repayment-alert-j7"])
                await db.financing_products.update_one(
                    {"id": fp["id"]}, {"$addToSet": {"repayment_alerts_sent": step["due_date"]}})
                sent += 1
            except Exception as exc:
                logger.warning("Alerte échéance %s %s : %s", fp["id"], step["due_date"], exc)
    if sent:
        logger.info("Alertes échéance remboursement envoyées : %d", sent)
    return sent
