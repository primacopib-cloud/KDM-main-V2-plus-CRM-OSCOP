"""Règle J+30 des lots COOP'ACT jamais retirés : abandon automatique puis décision admin (remise en salle ou don)."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

ABANDON_T = {
 "fr": {"subject": "Lot {ref} considéré comme abandonné",
        "body": "Votre lot <strong>{title}</strong> ({ref}), remporté le {won}, n'a pas été retiré dans les 30 jours.<br/>Conformément au règlement COOP'ACT, il est désormais considéré comme abandonné et ne peut plus être retiré ; les crédits coop'actés demeurent définitivement engagés. Le lot sera remis en salle ou orienté vers un don solidaire."},
 "en": {"subject": "Lot {ref} considered abandoned",
        "body": "Your lot <strong>{title}</strong> ({ref}), won on {won}, was not collected within 30 days.<br/>As per COOP'ACT rules, it is now considered abandoned and can no longer be collected; committed credits remain engaged. The lot will be relisted or donated to charity."},
 "es": {"subject": "Lote {ref} considerado abandonado",
        "body": "Su lote <strong>{title}</strong> ({ref}), ganado el {won}, no fue recogido en un plazo de 30 días.<br/>Según el reglamento COOP'ACT, ahora se considera abandonado y ya no puede retirarse; los créditos comprometidos siguen vinculados. El lote volverá a la sala o se donará."},
 "gcf": {"subject": "Lo {ref} konsidéré kon abandonné",
        "body": "Lo a'w <strong>{title}</strong> ({ref}), ou genyen'y jou {won}, pa té rétré adan 30 jou.<br/>Dapré règ COOP'ACT, i abandonné é ou pa ké sa rétré'y anko ; kredi yo résté angajé. Lo-la ké tounen an sal oben ké donnay solidè."},
 "ar": {"subject": "اعتُبرت الحصة {ref} مهجورة",
        "body": "حصتكم <strong>{title}</strong> ({ref})، التي ربحتموها في {won}، لم تُستلم خلال 30 يوماً.<br/>وفقاً لنظام COOP'ACT، أصبحت الآن مهجورة ولا يمكن استلامها بعد؛ وتبقى النقاط الملتزم بها مرتبطة نهائياً. ستُعاد الحصة إلى الساحة أو تُوجَّه لتبرع تضامني."},
}


async def send_abandonment_email(db, auction: dict) -> bool:
    w = auction.get("winner") or {}
    if not w.get("email"):
        return False
    user = await db.users.find_one(
        {"id": w.get("user_id")},
        {"_id": 0, "first_name": 1, "contact_name": 1, "preferred_language": 1}) or {}
    lang = user.get("preferred_language") or "fr"
    t = ABANDON_T.get(lang) or ABANDON_T["fr"]
    from incident_emails import INCIDENT_T
    base = INCIDENT_T.get(lang) or INCIDENT_T["fr"]
    first = user.get("first_name") or ((user.get("contact_name") or "").split() or [""])[0]
    fmt = {"ref": auction.get("reference"), "title": auction.get("title"),
           "won": (w.get("won_at") or "")[:10]}
    subject = t["subject"].format(**fmt)
    from order_email_i18n import rtl_wrap
    from brevo_service import _wrap_html, send_email
    body = rtl_wrap(lang, f"<p>{base['hello'].format(first=first or base['default_name'])}</p><p>{t['body'].format(**fmt)}</p>")
    try:
        await send_email(to_email=w["email"], to_name=w.get("name"), subject=subject,
                         html_content=_wrap_html(subject, body), tags=["auction-abandoned"])
        return True
    except Exception as exc:
        logger.warning("Email abandon non envoyé (%s) : %s", auction.get("reference"), exc)
        return False


async def run_abandoned_lots(db) -> int:
    """Lots WON non retirés depuis ≥30 j : statut EXPIRED, abandon consigné, gagnant + admin prévenus."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    marked = 0
    async for a in db.auctions.find(
            {"status": "WON", "pickup_confirmed_at": {"$exists": False},
             "abandoned_at": {"$exists": False},
             "winner.won_at": {"$lte": cutoff}},
            {"_id": 0, "id": 1, "reference": 1, "title": 1, "winner": 1}).limit(50):
        now = datetime.now(timezone.utc).isoformat()
        await db.auctions.update_one(
            {"id": a["id"]},
            {"$set": {"status": "EXPIRED", "abandoned_at": now, "abandoned_action": "PENDING",
                      "abandon_reason": "Jamais retiré sous 30 jours (règle J+30)"}})
        await send_abandonment_email(db, a)
        from core_deps import create_notification
        await create_notification(
            "AUCTION_ABANDONED", f"Lot abandonné J+30 — {a.get('reference')}",
            f"Le lot « {a.get('title')} » remporté par {(a.get('winner') or {}).get('name')} n'a jamais été retiré. "
            "Décidez : remise en salle ou don solidaire (panneau Bourse COOP'ACT).",
            data={"reference": a.get("reference")})
        marked += 1
    if marked:
        logger.info("Lots marqués abandonnés (J+30) : %d", marked)
    return marked


async def abandoned_lots_loop(db):
    import asyncio
    while True:
        try:
            await run_abandoned_lots(db)
        except Exception as exc:
            logger.warning("Boucle lots abandonnés : %s", exc)
        await asyncio.sleep(6 * 3600)
