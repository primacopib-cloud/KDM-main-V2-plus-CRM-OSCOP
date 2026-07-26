"""Digest hebdomadaire (lundi) : nouveaux produits et promos correspondant aux alertes de l'adhérent."""
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_I18N = {
    "fr": {
        "subject": "Votre récap hebdo KDMARCHÉ — nouveautés et promos de vos alertes",
        "hello": "Bonjour",
        "intro": "Voici les nouveautés de la semaine correspondant à vos alertes :",
        "news_title": "Nouveaux produits (incoterms suivis : {codes})",
        "promo_title": "Alertes sur vos produits favoris",
        "btn": "Voir le catalogue",
        "footer": "Vous recevez ce récap car vous avez des alertes actives. Gérez-les depuis votre espace « Alertes & favoris ».",
    },
    "en": {
        "subject": "Your KDMARCHÉ weekly digest — new products and deals from your alerts",
        "hello": "Hello",
        "intro": "Here is this week's news matching your alerts:",
        "news_title": "New products (followed incoterms: {codes})",
        "promo_title": "Alerts on your favorite products",
        "btn": "Browse the catalog",
        "footer": "You receive this digest because you have active alerts. Manage them from your alerts center.",
    },
}


async def run_weekly_digest(db) -> int:
    """Envoie le lundi (idempotent par semaine ISO) un email récap aux adhérents ayant des alertes."""
    now = datetime.utcnow()
    if now.weekday() != 0:
        return 0
    week_key = now.strftime("%G-W%V")
    cutoff_iso = (now - timedelta(days=7)).isoformat()
    base = os.environ.get("PUBLIC_BASE_URL") or "https://kdmarche-oscop.fr"

    users = await db.users.find(
        {"favorite_incoterms": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "email": 1, "contact_name": 1, "preferred_language": 1,
         "favorite_incoterms": 1, "digest_last_week": 1},
    ).to_list(1000)
    new_products = await db.products.find(
        {"status": "ACTIVE", "created_at": {"$gte": cutoff_iso}},
        {"_id": 0, "id": 1, "name": 1, "incoterms": 1},
    ).to_list(300)

    sent = 0
    for u in users:
        if u.get("digest_last_week") == week_key:
            continue
        await db.users.update_one({"id": u["id"]}, {"$set": {"digest_last_week": week_key}})
        codes = set(u.get("favorite_incoterms") or [])
        matches = [p for p in new_products
                   if codes & {c for lst in (p.get("incoterms") or {}).values() for c in (lst or [])}]
        promo_notifs = await db.notifications.find(
            {"target_user_id": u["id"], "type": {"$regex": "^favorite_"}, "created_at": {"$gte": cutoff_iso}},
            {"_id": 0, "title": 1},
        ).to_list(20)
        if (not matches and not promo_notifs) or not u.get("email"):
            continue
        lang = u.get("preferred_language") if u.get("preferred_language") in _I18N else "fr"
        t = _I18N[lang]
        news_html = "".join(
            f'<li><a href="{base}/catalogue?produit={p["id"]}" style="color:#451F6B;">{p["name"]}</a></li>'
            for p in matches[:10])
        promo_html = "".join(f"<li>{n['title']}</li>" for n in promo_notifs[:10])
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#451F6B;">{t['subject']}</h2>
          <p>{t['hello']} {u.get('contact_name') or ''},</p>
          <p>{t['intro']}</p>
          {f"<h3 style='color:#b8923e;'>{t['news_title'].format(codes=', '.join(sorted(codes)))}</h3><ul>{news_html}</ul>" if matches else ""}
          {f"<h3 style='color:#b8923e;'>{t['promo_title']}</h3><ul>{promo_html}</ul>" if promo_notifs else ""}
          <p><a href="{base}/catalogue" style="display:inline-block;background:#D9B35A;color:#2A1045;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">{t['btn']}</a></p>
          <p style="color:#777;font-size:12px;margin-top:24px;">{t['footer']}</p>
        </div>
        """
        try:
            from brevo_service import send_email
            await send_email(to_email=u["email"], to_name=u.get("contact_name") or None,
                             subject=t["subject"], html_content=html, tags=["weekly-digest"])
            sent += 1
        except Exception as exc:
            logger.warning("Digest hebdo non envoyé à %s : %s", u.get("email"), exc)
    if sent:
        logger.info("Digest hebdo %s : %d email(s) envoyé(s)", week_key, sent)
    return sent
