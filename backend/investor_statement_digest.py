"""Récap mensuel des crédits bonifiés FCRL : envoyé aux investisseurs le 1er du mois, dans leur langue."""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
db = None


def set_investor_statement_database(database):
    global db
    db = database


ST_T = {
 "fr": {"subject": "Relevé mensuel FCRL — {month}", "hello": "Bonjour {first},",
        "intro": "Voici le récapitulatif de vos crédits bonifiés FCRL pour <strong>{month}</strong>.",
        "opening": "Solde d'ouverture", "credited": "Crédité", "consumed": "Consommé", "closing": "Solde de clôture",
        "detail": "Le détail ligne par ligne est disponible dans votre Espace Investisseur (Relevé mensuel).",
        "default_name": "cher investisseur"},
 "en": {"subject": "FCRL monthly statement — {month}", "hello": "Hello {first},",
        "intro": "Here is the summary of your FCRL bonus credits for <strong>{month}</strong>.",
        "opening": "Opening balance", "credited": "Credited", "consumed": "Consumed", "closing": "Closing balance",
        "detail": "The line-by-line detail is available in your Investor Space (Monthly statement).",
        "default_name": "dear investor"},
 "es": {"subject": "Extracto mensual FCRL — {month}", "hello": "Hola {first},",
        "intro": "Este es el resumen de sus créditos bonificados FCRL para <strong>{month}</strong>.",
        "opening": "Saldo inicial", "credited": "Acreditado", "consumed": "Consumido", "closing": "Saldo final",
        "detail": "El detalle línea por línea está disponible en su Espacio Inversor (Extracto mensual).",
        "default_name": "estimado inversor"},
 "gcf": {"subject": "Rilve chak mwa FCRL — {month}", "hello": "Bonjou {first},",
        "intro": "Mi rézimé a kredi bonifyé FCRL a'w pou <strong>{month}</strong>.",
        "opening": "Sòld ouvèti", "credited": "Kredité", "consumed": "Konsonmé", "closing": "Sòld fèmti",
        "detail": "Détay lign pa lign la disponib adan Espas Envestisè a'w (Rilve chak mwa).",
        "default_name": "chè envestisè"},
 "ar": {"subject": "كشف الحساب الشهري FCRL — {month}", "hello": "مرحباً {first}،",
        "intro": "إليكم ملخص أرصدتكم المعززة FCRL لشهر <strong>{month}</strong>.",
        "opening": "الرصيد الافتتاحي", "credited": "المُضاف", "consumed": "المستهلَك", "closing": "الرصيد الختامي",
        "detail": "التفاصيل سطراً بسطر متاحة في فضاء المستثمر الخاص بكم (كشف الحساب الشهري).",
        "default_name": "عزيزي المستثمر"},
}


def _statement(entries, month):
    sel = [e for e in entries if str(e["created_at"])[:7] == month]
    credited = sum(e["amount_eur"] for e in sel if e["amount_eur"] > 0)
    consumed = sum(-e["amount_eur"] for e in sel if e["amount_eur"] < 0)
    opening = sum(e["amount_eur"] for e in entries if str(e["created_at"])[:7] < month)
    return {"opening": round(opening, 2), "credited": round(credited, 2),
            "consumed": round(consumed, 2), "closing": round(opening + credited - consumed, 2),
            "has_activity": bool(sel) or opening != 0}


def _eur(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


async def send_investor_statements(force: bool = False, month: str = ""):
    now = datetime.now(timezone.utc)
    if not month:
        prev = (now.replace(day=1) - __import__("datetime").timedelta(days=1))
        month = prev.strftime("%Y-%m")
    flag_id = f"investor_statement_{month}"
    if not force:
        if now.day != 1:
            return None
        if await db.digest_flags.find_one({"id": flag_id}):
            return None
    from brevo_service import send_email
    from order_email_i18n import rtl_wrap
    user_ids = await db.investor_privilege_subs.distinct("user_id", {"status": "ACTIVE"})
    sent = 0
    for uid in user_ids:
        user = await db.users.find_one(
            {"id": uid}, {"_id": 0, "email": 1, "contact_name": 1, "first_name": 1, "preferred_language": 1})
        if not user or not user.get("email"):
            continue
        entries = await db.privilege_credit_ledger.find({"user_id": uid}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        st = _statement(entries, month)
        if not st["has_activity"]:
            continue
        lang = user.get("preferred_language") or "fr"
        t = ST_T.get(lang) or ST_T["fr"]
        first = user.get("first_name") or (user.get("contact_name") or "").split()[0] if user.get("contact_name") else ""
        subject = t["subject"].format(month=month)
        rows = "".join(
            f"<tr><td style='padding:6px 12px;color:#bbb;'>{t[k]}</td>"
            f"<td style='padding:6px 12px;text-align:right;font-weight:600;color:{c};'>{_eur(st[v])}</td></tr>"
            for k, v, c in [("opening", "opening", "#fff"), ("credited", "credited", "#57D19A"),
                            ("consumed", "consumed", "#f0a0a0"), ("closing", "closing", "#F2D07A")])
        body = rtl_wrap(lang, f"""
          <p>{t['hello'].format(first=first or t['default_name'])}</p>
          <p>{t['intro'].format(month=month)}</p>
          <table style="width:100%;border-collapse:collapse;background:rgba(217,179,90,0.06);border:1px solid rgba(217,179,90,0.25);border-radius:12px;margin:16px 0;">{rows}</table>
          <p style="color:#999;font-size:12px;">{t['detail']}</p>
        """)
        from brevo_service import _wrap_html
        await send_email(to_email=user["email"], to_name=user.get("contact_name"),
                         subject=subject, html_content=_wrap_html(subject, body),
                         tags=["investor-statement"])
        sent += 1
    await db.digest_flags.update_one(
        {"id": flag_id},
        {"$set": {"id": flag_id, "sent": sent, "sent_at": now.isoformat()}}, upsert=True)
    logger.info("Récap mensuel investisseurs %s : %d envoyé(s)", month, sent)
    return {"month": month, "sent": sent}


async def investor_statement_loop():
    while True:
        try:
            await send_investor_statements()
        except Exception as exc:
            logger.warning("Boucle récap investisseurs : %s", exc)
        await asyncio.sleep(6 * 3600)
