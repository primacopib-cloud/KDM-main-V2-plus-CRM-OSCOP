"""Suivi automatique des échéanciers de paiement (levée de suspension avec accord d'échelonnement)."""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


async def check_payment_plans(db) -> int:
    """Marque les échéances dépassées, notifie et ré-active la suspension d'OT (idempotent par échéance)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    breaches = 0
    async for inv in db.logiscop_transport_invoices.find(
            {"status": {"$ne": "PAID"}, "payment_plan.installments": {"$exists": True}}, {"_id": 0}):
        plan = inv.get("payment_plan") or {}
        installments = plan.get("installments") or []
        changed, new_breach = False, None
        for i, inst in enumerate(installments):
            if inst.get("status") == "PENDING" and inst.get("due_date") and inst["due_date"] < today:
                inst["status"] = "OVERDUE"
                changed = True
            if inst.get("status") == "OVERDUE" and not inst.get("breach_notified_at"):
                inst["breach_notified_at"] = datetime.now(timezone.utc).isoformat()
                new_breach = (i, inst)
                changed = True
        if not changed:
            continue
        update = {"payment_plan.installments": installments}
        if new_breach:
            update["plan_breached_at"] = datetime.now(timezone.utc).isoformat()
        await db.logiscop_transport_invoices.update_one({"id": inv["id"]}, {"$set": update})
        if not new_breach:
            continue
        breaches += 1
        idx, inst = new_breach
        html = (
            f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#B91C1C'>Échéance non respectée — facture {inv['ref']}</h2>"
            f"<p>L'échéance n°{idx + 1} de votre échéancier ({_eur(inst.get('amount_cents'))}, "
            f"exigible le {inst.get('due_date')}) sur la facture <b>{inv['ref']}</b> n'a pas été honorée.</p>"
            "<p style='color:#B91C1C'><b>L'émission de nouveaux Ordres de Transport est de nouveau suspendue</b> "
            "jusqu'à régularisation (article 15 de la Convention).</p>"
            "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
        try:
            from brevo_service import send_email
            if inv.get("email"):
                await send_email(to_email=inv["email"], to_name=inv.get("company_name"),
                                 subject=f"Échéance non respectée — facture {inv['ref']} (OT suspendus)",
                                 html_content=html, tags=["logiscop-plan-breach"])
            admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
            if admin_email:
                await send_email(to_email=admin_email, to_name="LOGI'SCOP",
                                 subject=f"[LOGI'SCOP] Échéancier rompu — {inv['ref']} ({inv.get('company_name')})",
                                 html_content=html, tags=["logiscop-plan-breach"])
        except Exception as exc:
            logger.warning("Email rupture échéancier %s échoué : %s", inv["ref"], exc)
        try:
            from core_deps import create_notification
            await create_notification(
                "logiscop_plan_breach", "Échéancier de paiement rompu",
                f"L'échéance n°{idx + 1} de la facture {inv['ref']} ({inv.get('company_name')}) est dépassée — "
                "OT de nouveau suspendus.",
                target_roles=["oscop_super_admin", "kdm_b2b_admin"],
                data={"invoice_id": inv["id"], "ref": inv["ref"]})
        except Exception as exc:
            logger.warning("Notification rupture échéancier échouée : %s", exc)
    if breaches:
        logger.info("Échéanciers rompus détectés : %d", breaches)
    return breaches
