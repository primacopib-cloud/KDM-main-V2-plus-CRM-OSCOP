"""Factures PDF abonnement investisseur, export financements et rappel quota."""
from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)
VIOLET = colors.HexColor("#3D2B6B")
GOLD = colors.HexColor("#D9B35A")
GREY = colors.HexColor("#6B6B7B")


def _eur(n):
    return f"{(n or 0):,.2f} €".replace(",", " ").replace(".", ",")


def _header(c, w, h, title, subtitle, number):
    c.setFillColor(VIOLET)
    c.rect(0, h - 30 * mm, w, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, h - 15 * mm, title)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 22 * mm, "O'SCOP OUTRE-MER — KDMARCHÉ · centrale.objectifscopoutremer.com")
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 20 * mm, h - 15 * mm, number)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawRightString(w - 20 * mm, h - 21 * mm, subtitle)


def _footer(c, w):
    c.setFillColor(GREY)
    c.setFont("Helvetica", 7)
    c.drawCentredString(w / 2, 12 * mm, "Document confidentiel — O'SCOP OUTRE-MER. CREDI'SCOP est un compteur "
                                        "d'unités de services internes, sans valeur monétaire ni conversion possible.")


def build_subscription_invoice_pdf(invoice: dict) -> bytes:
    """Facture d'abonnement mensuel investisseur."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    _header(c, w, h, "FACTURE — ABONNEMENT INVESTISSEUR", f"Émise le {invoice['issued_at'][:10]}", f"N° {invoice['number']}")
    y = h - 45 * mm
    rows = [
        ("Client", invoice["client_name"]),
        ("Email", invoice["client_email"]),
        ("Plan", invoice["plan_code"]),
        ("Période", invoice["period_label"]),
        ("Abonnement mensuel HT", _eur(invoice["amount_eur"])),
        ("Capacité CREDI'SCOP allouée", f"{invoice['monthly_invest_uc']:,} uc".replace(",", " ")),
        ("Mode de règlement", "Prélèvement carte bancaire (Stripe)"),
        ("Statut", "PAYÉE"),
    ]
    for label, value in rows:
        c.setFillColor(GREY)
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, y, str(label))
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(85 * mm, y, str(value))
        y -= 8 * mm
    _footer(c, w)
    c.save()
    return buf.getvalue()


def build_financings_pdf(user: dict, account: dict, entries: list) -> bytes:
    """Export comptable des financements acceptés de l'investisseur."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    now = datetime.now(timezone.utc)
    _header(c, w, h, "HISTORIQUE DES FINANCEMENTS", f"Édité le {now.isoformat()[:10]}",
            f"Plan {account['plan_code']}")
    y = h - 42 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, f"Investisseur : {user.get('contact_name') or user.get('name') or user.get('email')}")
    y -= 10 * mm
    c.setFillColor(GREY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20 * mm, y, "DATE")
    c.drawString(55 * mm, y, "OPÉRATION FINANCÉE")
    c.drawRightString(w - 20 * mm, y, "MONTANT (uc)")
    y -= 3 * mm
    c.setStrokeColor(GOLD)
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 6 * mm
    total = 0
    for e in entries:
        if y < 30 * mm:
            _footer(c, w)
            c.showPage()
            y = h - 25 * mm
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(20 * mm, y, e["created_at"][:10])
        c.drawString(55 * mm, y, (e.get("label") or "")[:60])
        c.drawRightString(w - 20 * mm, y, f"{-e['amount_uc']:,}".replace(",", " "))
        total += -e["amount_uc"]
        y -= 6 * mm
    y -= 3 * mm
    c.setStrokeColor(GOLD)
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, f"TOTAL FINANCÉ : {len(entries)} opération(s)")
    c.drawRightString(w - 20 * mm, y, f"{total:,} uc".replace(",", " "))
    _footer(c, w)
    c.save()
    return buf.getvalue()


async def send_monthly_invoice(db, user: dict, account: dict, plan: dict):
    """Génère, archive et envoie la facture PDF du prélèvement mensuel."""
    now = datetime.now(timezone.utc)
    number = f"FAC-INV-{now.strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"
    invoice = {
        "id": str(uuid.uuid4()), "number": number, "user_id": user["id"],
        "client_name": user.get("contact_name") or user.get("name") or user["email"],
        "client_email": user["email"], "plan_code": account["plan_code"],
        "amount_eur": plan["price_eur"], "monthly_invest_uc": account["monthly_invest_uc"],
        "period_label": now.strftime("%m/%Y"), "issued_at": now.isoformat(),
    }
    pdf = build_subscription_invoice_pdf(invoice)
    await db.investor_invoices.insert_one(dict(invoice))
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=user["email"], to_name=invoice["client_name"],
            subject=f"Votre facture d'abonnement investisseur {account['plan_code']} — {invoice['period_label']}",
            html_content=_wrap_html("Facture d'abonnement", (
                f"<p style='font-size:14px;'>Bonjour {invoice['client_name']},</p>"
                f"<p style='font-size:14px;'>Votre prélèvement mensuel <b>{account['plan_code']}</b> de "
                f"<b>{_eur(plan['price_eur'])}</b> a bien été effectué. Vous trouverez votre facture "
                f"<b>{number}</b> en pièce jointe. Votre capacité CREDI'SCOP a été rechargée.</p>")),
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{number}.pdf"}],
            tags=["investor-billing"],
        )
    except Exception as exc:
        logger.error("Envoi facture investisseur : %s", exc)
    return number


def build_annual_statement_pdf(user: dict, account: dict, year: int, invoices: list, financings: list, repayments: list) -> bytes:
    """Relevé annuel fiscal : abonnements, financements et remboursements."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    _header(c, w, h, f"RELEVÉ ANNUEL FISCAL {year}", f"Édité le {datetime.now(timezone.utc).isoformat()[:10]}",
            f"Plan {account['plan_code']}")
    y = h - 42 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, f"Investisseur : {user.get('contact_name') or user.get('name') or user.get('email')}")
    y -= 12 * mm

    def section(title, headers, rows, total_label, total_value):
        nonlocal y
        if y < 60 * mm:
            _footer(c, w)
            c.showPage()
            y = h - 25 * mm
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, title)
        y -= 7 * mm
        c.setFillColor(GREY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(20 * mm, y, headers[0])
        c.drawString(60 * mm, y, headers[1])
        c.drawRightString(w - 20 * mm, y, headers[2])
        y -= 5 * mm
        for r in rows:
            if y < 30 * mm:
                _footer(c, w)
                c.showPage()
                y = h - 25 * mm
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(20 * mm, y, r[0])
            c.drawString(60 * mm, y, r[1][:55])
            c.drawRightString(w - 20 * mm, y, r[2])
            y -= 5.5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawString(20 * mm, y, total_label)
        c.drawRightString(w - 20 * mm, y, total_value)
        y -= 12 * mm

    section(f"ABONNEMENTS RÉGLÉS ({len(invoices)})", ("MOIS", "FACTURE", "MONTANT"),
            [(i["period_label"], f"{i['number']} — plan {i['plan_code']}", _eur(i["amount_eur"])) for i in invoices],
            "TOTAL ABONNEMENTS", _eur(sum(i["amount_eur"] for i in invoices)))
    section(f"FINANCEMENTS CREDI'SCOP ({len(financings)})", ("DATE", "OPÉRATION", "MONTANT (uc)"),
            [(e["created_at"][:10], e.get("label") or "", f"{-e['amount_uc']:,}".replace(",", " ")) for e in financings],
            "TOTAL FINANCÉ", f"{-sum(e['amount_uc'] for e in financings):,} uc".replace(",", " "))
    section(f"REMBOURSEMENTS REÇUS ({len(repayments)})", ("DATE", "RÉFÉRENCE VIREMENT", "MONTANT"),
            [(r["paid_at"][:10], r["reference"] + (f" — {r['operation_ref']}" if r.get("operation_ref") else ""),
              _eur(r["amount_eur"])) for r in repayments],
            "TOTAL REMBOURSÉ", _eur(sum(r["amount_eur"] for r in repayments)))
    _footer(c, w)
    c.save()
    return buf.getvalue()


def build_investor_360_pdf(data: dict) -> bytes:
    """Fiche investisseur 360 pour comités d'investissement."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    inv = data["investor"]
    _header(c, w, h, "FICHE INVESTISSEUR 360", f"Éditée le {datetime.now(timezone.utc).isoformat()[:10]}",
            "COMITÉ D'INVESTISSEMENT")
    y = h - 42 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, inv.get("name") or inv.get("email") or "")
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawString(20 * mm, y - 5.5 * mm, inv.get("email") or "")
    y -= 16 * mm

    def block(title, rows):
        nonlocal y
        if y < 50 * mm:
            _footer(c, w)
            c.showPage()
            y = h - 25 * mm
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, title)
        y -= 2.5 * mm
        c.setStrokeColor(GOLD)
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 6 * mm
        for label, value in rows:
            if y < 30 * mm:
                _footer(c, w)
                c.showPage()
                y = h - 25 * mm
            c.setFillColor(GREY)
            c.setFont("Helvetica", 8.5)
            c.drawString(20 * mm, y, str(label))
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(85 * mm, y, str(value)[:70])
            y -= 6 * mm
        y -= 5 * mm

    def _uc(n):
        return f"{(n or 0):,}".replace(",", " ") + " uc"

    sub = data.get("subscription") or {}
    block("ABONNEMENT", [
        ("Plan", sub.get("plan_code") or "—"),
        ("Statut", sub.get("status") or "—"),
        ("Période en cours depuis", (sub.get("period_start") or "")[:10] or "—"),
        ("Quota mensuel", _uc(sub.get("monthly_invest_uc"))),
    ])
    cr = data["credits"]
    block("CREDI'SCOP", [
        ("Solde", _uc(cr.get("balance_uc"))),
        ("Consommé", _uc(cr.get("consumed_uc"))),
        ("Mouvements", cr.get("entries")),
    ])
    bank = data.get("bank")
    block("COORDONNÉES BANCAIRES", [
        ("Titulaire", (bank or {}).get("holder") or "Non renseigné"),
        ("IBAN", ("…" + (bank or {}).get("iban", "")[-6:]) if bank and bank.get("iban") else "Non renseigné"),
        ("Statut RIB", (bank or {}).get("rib_status") or ("PENDING" if bank and bank.get("rib_filename") else "NON TÉLÉVERSÉ")),
    ])
    fin = data["financings"]
    fin_rows = [("Total financé", _uc(fin.get("total_uc"))), ("Nombre d'opérations", fin.get("count"))]
    for e in fin.get("items", [])[:8]:
        fin_rows.append((e["created_at"][:10], f"{e.get('label', '')} — {_uc(-e['amount_uc'])}"))
    block("FINANCEMENTS", fin_rows)
    rep = data["repayments"]
    rep_rows = [("Total confirmé", _eur(rep.get("total_eur"))), ("Nombre de virements", rep.get("count"))]
    for r in rep.get("items", [])[:8]:
        rep_rows.append(((r.get("paid_at") or "")[:10],
                         f"Réf. {r['reference']} — {_eur(r['amount_eur'])}"
                         f"{' — rapproché' if r.get('reconciled') else ''}"))
    block("VIREMENTS DE REMBOURSEMENT", rep_rows)
    invc = data["invoices"]
    inv_rows = [("Total encaissé", _eur(invc.get("total_eur"))), ("Nombre de factures", invc.get("count"))]
    for i in invc.get("items", [])[:8]:
        inv_rows.append((i.get("period_label", ""), f"{i['number']} — {_eur(i['amount_eur'])}"))
    block("FACTURES D'ABONNEMENT", inv_rows)
    _footer(c, w)
    c.save()
    return buf.getvalue()


async def check_low_quota_alert(db, user_id: str):
    """Email de rappel quand le solde passe sous 10 % du quota (1 envoi par période)."""
    account = await db.investor_accounts.find_one({"user_id": user_id, "status": {"$in": ["ACTIVE", "PAST_DUE"]}})
    if not account:
        return
    ledger = await db.invest_credit_ledger.find({"user_id": user_id}, {"amount_uc": 1}).to_list(1000)
    balance = sum(e["amount_uc"] for e in ledger)
    quota = account["monthly_invest_uc"]
    if quota <= 0 or balance >= quota * 0.10:
        return
    period_key = account["period_start"][:7]
    if account.get("low_quota_alerted_period") == period_key:
        return
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=user["email"], to_name=user.get("contact_name"),
            subject="⚠ Votre CREDI'SCOP passe sous 10 % du quota",
            html_content=_wrap_html("Capacité presque épuisée", (
                f"<p style='font-size:14px;'>Bonjour {user.get('contact_name') or ''},</p>"
                f"<p style='font-size:14px;'>Votre solde CREDI'SCOP est de "
                f"<b>{balance:,} uc</b>, soit moins de 10 % de votre quota mensuel "
                f"<b>{quota:,} uc</b> (plan {account['plan_code']}). "
                "Pensez à acheter un pack Crédits INVEST depuis votre espace pour continuer à financer.</p>"
            ).replace(",", " ")),
            tags=["investor-quota"],
        )
        await db.investor_accounts.update_one({"id": account["id"]}, {"$set": {"low_quota_alerted_period": period_key}})
    except Exception as exc:
        logger.error("Rappel quota investisseur : %s", exc)
