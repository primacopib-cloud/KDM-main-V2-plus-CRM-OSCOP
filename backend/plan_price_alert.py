"""Alerte email aux membres abonnés lors d'un changement de tarif de leur formule."""
import logging

logger = logging.getLogger(__name__)


async def _collect_subscriber_emails(db, plan: dict) -> list:
    keys = {k for k in (plan.get("id"), plan.get("slug")) if k}
    emails = set()
    async for u in db.users.find({"subscription": {"$in": list(keys)}}, {"_id": 0, "email": 1}):
        if u.get("email"):
            emails.add(u["email"].lower())
    subs = await db.subscriptions.find(
        {"plan_id": {"$in": list(keys)}, "status": "ACTIVE"}, {"_id": 0, "org_id": 1}).to_list(500)
    org_ids = [s["org_id"] for s in subs if s.get("org_id")]
    if org_ids:
        memberships = await db.org_memberships.find(
            {"org_id": {"$in": org_ids}}, {"_id": 0, "user_id": 1}).to_list(1000)
        user_ids = [m["user_id"] for m in memberships if m.get("user_id")]
        async for u in db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "email": 1}):
            if u.get("email"):
                emails.add(u["email"].lower())
    return sorted(emails)[:200]


async def send_price_notice_alerts(db, plan: dict, old_cents: int, new_cents: int, effective_date: str) -> None:
    """Préavis : informe les abonnés qu'un changement de tarif prendra effet à une date future."""
    try:
        emails = await _collect_subscriber_emails(db, plan)
        if not emails:
            logger.info("Préavis tarif %s : aucun abonné à prévenir", plan.get("name"))
            return
        from brevo_service import send_email
        old_eur, new_eur = round((old_cents or 0) / 100, 2), round((new_cents or 0) / 100, 2)
        try:
            eff_fr = "/".join(reversed(effective_date.split("-")))
        except Exception:
            eff_fr = effective_date
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:560px'>
          <h2 style='color:#5B2E8C'>Préavis : évolution du tarif de votre formule</h2>
          <p style='font-size:14px;color:#333'>Bonjour,</p>
          <p style='font-size:14px;color:#333'>
            À compter du <strong>{eff_fr}</strong>, le tarif de votre formule
            <strong>{plan.get('name')}</strong> passera de <strong>{old_eur:g} € HT/mois</strong>
            à <strong style='color:#5B2E8C'>{new_eur:g} € HT/mois</strong>.
          </p>
          <p style='font-size:13px;color:#555'>
            Conformément à nos engagements, nous vous en informons au moins 30 jours à l'avance.
            Aucune action n'est requise de votre part. Pour toute question, contactez votre référent réseau.
          </p>
          <p style='color:#999;font-size:11px;margin-top:20px'>Communityplace B2B ESS — KDMARCHÉ × O'SCOP</p>
        </div>"""
        sent = 0
        for email in emails:
            try:
                await send_email(
                    to_email=email, to_name=None,
                    subject=f"Préavis tarifaire — votre formule {plan.get('name')} évoluera le {eff_fr}",
                    html_content=html, tags=["plan-price-notice"],
                )
                sent += 1
            except Exception as exc:
                logger.warning("Préavis tarif non envoyé à %s : %s", email, exc)
        logger.info("Préavis tarif %s (effet %s) envoyé à %s/%s abonnés",
                    plan.get("name"), effective_date, sent, len(emails))
    except Exception as exc:
        logger.error("Préavis tarifaires échoués : %s", exc)


async def send_price_change_alerts(db, plan: dict, old_cents: int, new_cents: int) -> None:
    try:
        emails = await _collect_subscriber_emails(db, plan)
        if not emails:
            logger.info("Changement tarif %s : aucun abonné à prévenir", plan.get("name"))
            return
        from brevo_service import send_email
        old_eur, new_eur = round((old_cents or 0) / 100, 2), round((new_cents or 0) / 100, 2)
        direction = "évolue" if new_cents > (old_cents or 0) else "baisse"
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:560px'>
          <h2 style='color:#5B2E8C'>Le tarif de votre formule {direction}</h2>
          <p style='font-size:14px;color:#333'>Bonjour,</p>
          <p style='font-size:14px;color:#333'>
            Le tarif de votre formule <strong>{plan.get('name')}</strong> passe de
            <strong>{old_eur:g} € HT/mois</strong> à <strong style='color:#5B2E8C'>{new_eur:g} € HT/mois</strong>.
          </p>
          <p style='font-size:13px;color:#555'>
            Ce nouveau tarif s'appliquera à votre prochaine échéance de facturation.
            Pour toute question, répondez à cet email ou contactez votre référent réseau.
          </p>
          <p style='color:#999;font-size:11px;margin-top:20px'>Communityplace B2B ESS — KDMARCHÉ × O'SCOP</p>
        </div>"""
        sent = 0
        for email in emails:
            try:
                await send_email(
                    to_email=email, to_name=None,
                    subject=f"Évolution du tarif de votre formule {plan.get('name')} — KDMARCHÉ × O'SCOP",
                    html_content=html, tags=["plan-price-change"],
                )
                sent += 1
            except Exception as exc:
                logger.warning("Alerte tarif non envoyée à %s : %s", email, exc)
        logger.info("Alerte changement tarif %s (%s→%s €) envoyée à %s/%s abonnés",
                    plan.get("name"), old_eur, new_eur, sent, len(emails))
    except Exception as exc:
        logger.error("Alertes changement tarif échouées : %s", exc)
