"""Relances automatiques des impayés RàR : réception confirmée mais paiement en retard (cron)."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_rar_payment_reminders(db) -> int:
    """J+3 après confirmation de réception, toutes les 72 h, max 3 relances par commande."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=3)
    orders = await db.orders.find({
        "rar": True, "payment_status": "cod_pending",
        "rar_proof_at": {"$lt": cutoff},
        "cod_amount_due_cents": {"$gt": 0},
        "rar_reminder_count": {"$not": {"$gte": 3}},
        "$or": [{"rar_last_reminder_at": {"$exists": False}}, {"rar_last_reminder_at": {"$lt": cutoff}}],
    }).to_list(20)
    if not orders:
        return 0
    from brevo_service import send_email, _wrap_html
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    sent = 0
    for o in orders:
        amount = (o.get("cod_amount_due_cents") or 0) / 100
        n = (o.get("rar_reminder_count") or 0) + 1
        members = await db.org_memberships.find({"org_id": o["org_id"]}).to_list(3)
        users = await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                    {"email": 1, "contact_name": 1}).to_list(3)
        subject = f"⏰ Relance {n}/3 — facture de la commande {o.get('order_number')} en attente de règlement"
        body = (f"<p>Bonjour,</p><p>Vous avez confirmé la réception de la commande "
                f"<b>{o.get('order_number')}</b> le {str(o.get('rar_proof_at'))[:10]}, mais son règlement "
                f"de <b>{amount:.2f} € TTC</b> n'a pas encore été encaissé.</p>"
                f"<p><a href='{base}/espace-acheteur?tab=invoices' style='background:#D9B35A;color:#000;"
                f"padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Régler ma facture</a></p>"
                f"<p style='font-size:11px;color:#888'>Votre plafond Règlement à Réception Pro reste mobilisé "
                f"tant que le paiement n'est pas définitivement encaissé. Un incident de paiement peut entraîner "
                f"la réduction ou la suspension de votre plafond.</p>")
        ok = False
        for u in users:
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_payment_reminder"])
                ok = True
            except Exception as exc:
                logger.warning("Relance RàR échouée %s : %s", u.get("email"), exc)
        if ok:
            sent += 1
            await db.orders.update_one({"id": o["id"]},
                                       {"$set": {"rar_last_reminder_at": now},
                                        "$inc": {"rar_reminder_count": 1}})
    if sent:
        logger.info("Relances impayés RàR envoyées : %s", sent)
    return sent


async def run_rar_overdue_alerts(db) -> int:
    """J+14 impayé : dernier rappel ferme au client + alerte email à l'administration (une seule fois)."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=14)
    orders = await db.orders.find({
        "rar": True, "payment_status": "cod_pending",
        "rar_proof_at": {"$lt": cutoff},
        "cod_amount_due_cents": {"$gt": 0},
        "rar_overdue_alert_sent": {"$ne": True},
    }).to_list(20)
    if not orders:
        return 0
    from brevo_service import send_email, _wrap_html
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    admin_email = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    sent = 0
    for o in orders:
        amount = (o.get("cod_amount_due_cents") or 0) / 100
        days = (now - o["rar_proof_at"]).days
        org = await db.organizations.find_one({"id": o.get("org_id")}, {"legal_name": 1, "name": 1})
        org_name = (org or {}).get("legal_name") or (org or {}).get("name") or o.get("org_id", "")
        members = await db.org_memberships.find({"org_id": o["org_id"]}).to_list(3)
        users = await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                    {"email": 1, "contact_name": 1}).to_list(3)
        subject = f"🔴 Dernier rappel — facture {o.get('order_number')} impayée depuis {days} jours"
        body = (f"<p>Bonjour,</p><p>Malgré nos relances, le règlement de la commande "
                f"<b>{o.get('order_number')}</b> (<b>{amount:.2f} € TTC</b>), dont vous avez confirmé la réception "
                f"le {str(o.get('rar_proof_at'))[:10]}, reste impayé depuis <b>{days} jours</b>.</p>"
                f"<p>Sans règlement sous 72 h, votre plafond Règlement à Réception Pro pourra être "
                f"<b>réduit ou suspendu</b> et le dossier transmis à notre service recouvrement.</p>"
                f"<p><a href='{base}/espace-acheteur?tab=invoices' style='background:#D9B35A;color:#000;"
                f"padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Régler ma facture maintenant</a></p>")
        ok = False
        for u in users:
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_overdue_final_notice"])
                ok = True
            except Exception as exc:
                logger.warning("Dernier rappel RàR échoué %s : %s", u.get("email"), exc)
        try:
            admin_subject = f"⚠️ Impayé RàR J+{days} — {o.get('order_number')} ({amount:.2f} €) — {org_name}"
            admin_body = (f"<p>La commande <b>{o.get('order_number')}</b> de <b>{org_name}</b> "
                          f"({amount:.2f} € TTC, Règlement à Réception Pro) est impayée depuis <b>{days} jours</b> "
                          f"après confirmation de réception ({(o.get('rar_reminder_count') or 0)} relance(s) déjà envoyée(s)).</p>"
                          f"<p>Dernier rappel envoyé au client. Actions possibles : suspension du plafond, recouvrement.</p>"
                          f"<p><a href='{base}/superadmin'>Ouvrir la console admin</a></p>")
            await send_email(to_email=admin_email, to_name="Équipe KDMARCHÉ", subject=admin_subject,
                             html_content=_wrap_html(admin_subject, admin_body), text_content=admin_subject,
                             tags=["rar_overdue_admin_alert"])
        except Exception as exc:
            logger.warning("Alerte admin impayé RàR échouée : %s", exc)
        if ok:
            sent += 1
            await db.orders.update_one({"id": o["id"]},
                                       {"$set": {"rar_overdue_alert_sent": True,
                                                 "rar_overdue_alert_at": now}})
    if sent:
        logger.info("Derniers rappels impayés RàR J+14 envoyés : %s", sent)
    return sent


async def run_rar_auto_suspensions(db) -> int:
    """72 h après le dernier rappel J+14 sans encaissement : suspension automatique du plafond."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=3)
    orders = await db.orders.find({
        "rar": True, "payment_status": "cod_pending",
        "cod_amount_due_cents": {"$gt": 0},
        "rar_overdue_alert_sent": True,
        "rar_overdue_alert_at": {"$lt": cutoff},
        "rar_suspension_done": {"$ne": True},
    }).to_list(20)
    if not orders:
        return 0
    from brevo_service import send_email, _wrap_html
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    admin_email = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    suspended = 0
    for o in orders:
        await db.orders.update_one({"id": o["id"]}, {"$set": {"rar_suspension_done": True}})
        account = await db.rar_accounts.find_one({"org_id": o["org_id"]})
        if not account or account.get("status") != "APPROVED":
            continue
        amount = (o.get("cod_amount_due_cents") or 0) / 100
        await db.rar_accounts.update_one(
            {"org_id": o["org_id"]},
            {"$set": {"status": "SUSPENDED", "auto_suspended": True,
                      "suspended_at": now,
                      "suspended_reason": f"Impayé {o.get('order_number')} ({amount:.2f} €) — suspension automatique après dernier rappel"}})
        org = await db.organizations.find_one({"id": o.get("org_id")}, {"legal_name": 1, "name": 1})
        org_name = (org or {}).get("legal_name") or (org or {}).get("name") or o.get("org_id", "")
        members = await db.org_memberships.find({"org_id": o["org_id"]}).to_list(3)
        users = await db.users.find({"id": {"$in": [m["user_id"] for m in members]}},
                                    {"email": 1, "contact_name": 1}).to_list(3)
        subject = f"⛔ Plafond Règlement à Réception Pro suspendu — impayé {o.get('order_number')}"
        body = (f"<p>Bonjour,</p><p>Malgré notre dernier rappel, le règlement de la commande "
                f"<b>{o.get('order_number')}</b> (<b>{amount:.2f} € TTC</b>) n'a pas été encaissé.</p>"
                f"<p>Conformément aux CGV, votre plafond Règlement à Réception Pro est "
                f"<b>suspendu</b> : les nouvelles commandes sans acompte ne sont plus possibles.</p>"
                f"<p>Le plafond pourra être réactivé par notre équipe après régularisation.</p>"
                f"<p><a href='{base}/espace-acheteur?tab=invoices' style='background:#D9B35A;color:#000;"
                f"padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Régulariser maintenant</a></p>")
        for u in users:
            if not u.get("email"):
                continue
            try:
                await send_email(to_email=u["email"], to_name=u.get("contact_name"), subject=subject,
                                 html_content=_wrap_html(subject, body), text_content=subject,
                                 tags=["rar_auto_suspension"])
            except Exception as exc:
                logger.warning("Email suspension RàR échoué %s : %s", u.get("email"), exc)
        try:
            admin_subject = f"⛔ Plafond suspendu automatiquement — {org_name} (impayé {o.get('order_number')}, {amount:.2f} €)"
            admin_body = (f"<p>Le plafond RàR de <b>{org_name}</b> a été <b>suspendu automatiquement</b> : "
                          f"la commande <b>{o.get('order_number')}</b> ({amount:.2f} € TTC) est restée impayée "
                          f"plus de 72 h après le dernier rappel.</p>"
                          f"<p>Réactivation possible depuis la console admin après régularisation.</p>"
                          f"<p><a href='{base}/superadmin'>Ouvrir la console admin</a></p>")
            await send_email(to_email=admin_email, to_name="Équipe KDMARCHÉ", subject=admin_subject,
                             html_content=_wrap_html(admin_subject, admin_body), text_content=admin_subject,
                             tags=["rar_auto_suspension_admin"])
        except Exception as exc:
            logger.warning("Alerte admin suspension RàR échouée : %s", exc)
        try:
            from consultation_audit import audit
            await audit("RAR_ACCOUNT_AUTO_SUSPENDED", "scheduler", None,
                        {"org_id": o["org_id"], "order_number": o.get("order_number"),
                         "amount_cents": o.get("cod_amount_due_cents")})
        except Exception:
            pass
        suspended += 1
        logger.info("Plafond RàR suspendu automatiquement : org %s (impayé %s)", o["org_id"], o.get("order_number"))
    return suspended
