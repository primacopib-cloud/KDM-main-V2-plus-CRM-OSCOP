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
