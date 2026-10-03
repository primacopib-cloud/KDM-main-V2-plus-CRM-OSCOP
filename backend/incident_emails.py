"""Emails multilingues des avoirs COOP'ACT (article manquant au retrait) : enregistrement puis règlement."""
import logging

logger = logging.getLogger(__name__)

INCIDENT_T = {
 "fr": {"rec_subject": "Avoir de {credit} € enregistré — lot {ref}",
        "rec_body": "Lors du retrait de votre lot <strong>{title}</strong> ({ref}), le(s) article(s) suivant(s) étai(en)t indisponible(s) : <strong>{missing}</strong>.<br/>Conformément à la procédure, aucun remplacement par un autre produit ou une autre marque n'est autorisé : un avoir de <strong>{credit} €</strong> vous est dû et sera réglé prochainement.",
        "set_subject": "Avoir de {credit} € réglé ✓ — lot {ref}",
        "set_body": "Votre avoir de <strong>{credit} €</strong> pour le lot <strong>{title}</strong> ({ref}) vient d'être réglé : <strong>{credits} crédits COOP'ACT</strong> ont été ajoutés à votre compte (10 crédits = 1 €).",
        "hello": "Bonjour {first},", "default_name": "cher membre"},
 "en": {"rec_subject": "Credit note of €{credit} recorded — lot {ref}",
        "rec_body": "When collecting your lot <strong>{title}</strong> ({ref}), the following item(s) were unavailable: <strong>{missing}</strong>.<br/>As per the procedure, no replacement with another product or brand is allowed: a credit of <strong>€{credit}</strong> is owed to you and will be settled shortly.",
        "set_subject": "Credit of €{credit} settled ✓ — lot {ref}",
        "set_body": "Your credit of <strong>€{credit}</strong> for lot <strong>{title}</strong> ({ref}) has been settled: <strong>{credits} COOP'ACT credits</strong> were added to your account (10 credits = €1).",
        "hello": "Hello {first},", "default_name": "dear member"},
 "es": {"rec_subject": "Abono de {credit} € registrado — lote {ref}",
        "rec_body": "Al retirar su lote <strong>{title}</strong> ({ref}), el/los artículo(s) siguiente(s) no estaban disponibles: <strong>{missing}</strong>.<br/>Según el procedimiento, no se permite ninguna sustitución por otro producto u otra marca: se le debe un abono de <strong>{credit} €</strong> que se liquidará próximamente.",
        "set_subject": "Abono de {credit} € liquidado ✓ — lote {ref}",
        "set_body": "Su abono de <strong>{credit} €</strong> por el lote <strong>{title}</strong> ({ref}) ha sido liquidado: se añadieron <strong>{credits} créditos COOP'ACT</strong> a su cuenta (10 créditos = 1 €).",
        "hello": "Hola {first},", "default_name": "estimado miembro"},
 "gcf": {"rec_subject": "Avwa {credit} € anrejistré — lo {ref}",
        "rec_body": "Lè ou té vin rétré lo a'w <strong>{title}</strong> ({ref}), atik-lasa pa té disponib : <strong>{missing}</strong>.<br/>Dapré pwosédi-la, pa ni ranplasman èvè on dòt pwodui oben on dòt mak : on avwa <strong>{credit} €</strong> ka dû ba'w é i ké réglé talè.",
        "set_subject": "Avwa {credit} € réglé ✓ — lo {ref}",
        "set_body": "Avwa a'w <strong>{credit} €</strong> pou lo <strong>{title}</strong> ({ref}) réglé : <strong>{credits} kredi COOP'ACT</strong> ajouté asi kont a'w (10 kredi = 1 €).",
        "hello": "Bonjou {first},", "default_name": "chè manm"},
 "ar": {"rec_subject": "تم تسجيل رصيد {credit} € — الحصة {ref}",
        "rec_body": "عند استلام حصتكم <strong>{title}</strong> ({ref})، كان(ت) المادة (المواد) التالية غير متوفرة: <strong>{missing}</strong>.<br/>وفقاً للإجراء، لا يُسمح بأي استبدال بمنتج أو علامة تجارية أخرى: يُستحق لكم رصيد قدره <strong>{credit} €</strong> وسيُسوّى قريباً.",
        "set_subject": "تمت تسوية رصيد {credit} € ✓ — الحصة {ref}",
        "set_body": "تمت تسوية رصيدكم البالغ <strong>{credit} €</strong> عن الحصة <strong>{title}</strong> ({ref}): أُضيف <strong>{credits} نقطة COOP'ACT</strong> إلى حسابكم (10 نقاط = 1 €).",
        "hello": "مرحباً {first}،", "default_name": "عزيزي العضو"},
}


PICKUP_REMINDER_T = {
 "fr": {"subject": "N'oubliez pas votre lot {ref} — prêt au retrait",
        "body": "Votre lot <strong>{title}</strong> ({ref}), remporté le {won}, n'a pas encore été retiré.<br/>Présentez votre QR d'enlèvement (disponible dans votre espace COOP'ACT, rubrique Historique) chez votre POP'S pour le récupérer."},
 "en": {"subject": "Don't forget your lot {ref} — ready for pickup",
        "body": "Your lot <strong>{title}</strong> ({ref}), won on {won}, has not been collected yet.<br/>Show your pickup QR code (available in your COOP'ACT space, History section) at your POP'S to collect it."},
 "es": {"subject": "No olvide su lote {ref} — listo para recoger",
        "body": "Su lote <strong>{title}</strong> ({ref}), ganado el {won}, aún no ha sido recogido.<br/>Presente su código QR de retirada (disponible en su espacio COOP'ACT, sección Historial) en su POP'S para recogerlo."},
 "gcf": {"subject": "Pa obliyé lo a'w {ref} — paré pou rétré",
        "body": "Lo a'w <strong>{title}</strong> ({ref}), ou genyen'y jou {won}, pòkò rétré.<br/>Vin èvè QR-kòd a'w (adan espas COOP'ACT a'w, riborik Istwa) akaz POP'S a'w pou pran'y."},
 "ar": {"subject": "لا تنسوا حصتكم {ref} — جاهزة للاستلام",
        "body": "حصتكم <strong>{title}</strong> ({ref})، التي ربحتموها في {won}، لم تُستلم بعد.<br/>قدّموا رمز QR الخاص بالاستلام (متوفر في فضاء COOP'ACT، قسم السجل) لدى POP'S لاستلامها."},
}


async def send_pickup_reminder(db, auction: dict):
    """Rappel de retrait (lot non récupéré) dans la langue du gagnant."""
    w = auction.get("winner") or {}
    if not w.get("email"):
        return False
    user = await db.users.find_one(
        {"id": w.get("user_id")},
        {"_id": 0, "first_name": 1, "contact_name": 1, "preferred_language": 1}) or {}
    lang = user.get("preferred_language") or "fr"
    t = PICKUP_REMINDER_T.get(lang) or PICKUP_REMINDER_T["fr"]
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
                         html_content=_wrap_html(subject, body), tags=["auction-pickup-reminder"])
        return True
    except Exception as exc:
        logger.warning("Rappel retrait non envoyé (%s) : %s", auction.get("reference"), exc)
        return False


async def run_pickup_reminders(db) -> int:
    """Relance les gagnants dont le lot n'est pas retiré 7 jours après le gain (1 seul rappel)."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    sent = 0
    async for a in db.auctions.find(
            {"status": "WON", "pickup_confirmed_at": {"$exists": False},
             "pickup_reminder_sent_at": {"$exists": False},
             "winner.won_at": {"$lte": cutoff}},
            {"_id": 0, "id": 1, "reference": 1, "title": 1, "winner": 1}).limit(50):
        ok = await send_pickup_reminder(db, a)
        await db.auctions.update_one(
            {"id": a["id"]},
            {"$set": {"pickup_reminder_sent_at": datetime.now(timezone.utc).isoformat(),
                      "pickup_reminder_email_ok": ok}})
        sent += 1
    if sent:
        logger.info("Rappels retrait lot envoyés : %d", sent)
    return sent


async def pickup_reminder_loop(db):
    import asyncio
    while True:
        try:
            await run_pickup_reminders(db)
        except Exception as exc:
            logger.warning("Boucle rappels retrait : %s", exc)
        await asyncio.sleep(6 * 3600)


async def send_incident_email(db, auction: dict, incident: dict, phase: str, credits: int = 0):
    """phase = 'recorded' | 'settled'. Envoie dans la langue du gagnant."""
    w = auction.get("winner") or {}
    if not w.get("email"):
        return
    user = await db.users.find_one(
        {"id": w.get("user_id")},
        {"_id": 0, "first_name": 1, "contact_name": 1, "preferred_language": 1}) or {}
    lang = user.get("preferred_language") or "fr"
    t = INCIDENT_T.get(lang) or INCIDENT_T["fr"]
    first = user.get("first_name") or ((user.get("contact_name") or "").split() or [""])[0]
    fmt = {"credit": f"{incident['credit_eur']:.2f}", "ref": auction.get("reference"),
           "title": auction.get("title"), "missing": ", ".join(incident.get("missing_names") or []),
           "credits": credits}
    key = "rec" if phase == "recorded" else "set"
    subject = t[f"{key}_subject"].format(**fmt)
    from order_email_i18n import rtl_wrap
    from brevo_service import _wrap_html, send_email
    body = rtl_wrap(lang, f"<p>{t['hello'].format(first=first or t['default_name'])}</p><p>{t[f'{key}_body'].format(**fmt)}</p>")
    try:
        await send_email(to_email=w["email"], to_name=w.get("name"), subject=subject,
                         html_content=_wrap_html(subject, body), tags=["auction-incident", phase])
    except Exception as exc:
        logger.warning("Email avoir (%s) non envoyé : %s", phase, exc)
