"""Facturation des Ordres de Transport LOGI'SCOP acceptés + rappels d'enlèvement J-1."""
import base64
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from vat import compute_vat

logger = logging.getLogger(__name__)

ZONE_COUNTRY = {"GUADELOUPE": "GP", "MARTINIQUE": "MQ", "GUYANE": "GF",
                "REUNION": "RE", "MAYOTTE": "YT", "HEXAGONE": "FR", "FRANCE": "FR"}
GOLD = colors.HexColor("#B8860B")
VIOLET = colors.HexColor("#2A1045")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


async def create_transport_invoice(db, ot: dict, conv: dict) -> dict:
    """Facture émise automatiquement à l'acceptation de l'OT (idempotent par OT)."""
    existing = await db.logiscop_transport_invoices.find_one({"ot_id": ot["id"]}, {"_id": 0})
    if existing:
        return existing
    country = ZONE_COUNTRY.get((ot.get("delivery") or {}).get("zone_code", ""), None)
    vat = compute_vat(ot.get("price_ht_cents") or 0, country)
    year = datetime.now(timezone.utc).strftime("%Y")
    n = await db.logiscop_transport_invoices.count_documents({"ref": {"$regex": f"^FAC-LOGI-{year}-"}}) + 1
    inv = {
        "id": str(uuid.uuid4()), "ref": f"FAC-LOGI-{year}-{n:04d}",
        "ot_id": ot["id"], "ot_ref": ot["ref"],
        "convention_ref": ot.get("convention_ref"),
        "org_id": ot["org_id"], "user_id": ot["user_id"],
        "company_name": ot.get("company_name"), "email": conv.get("email"),
        "amount_ht_cents": vat["ht_cents"], "vat_rate": vat["rate"],
        "vat_label": vat["label"], "vat_cents": vat["vat_cents"],
        "total_ttc_cents": vat["ttc_cents"],
        "status": "ISSUED", "email_sent_at": None,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.logiscop_transport_invoices.insert_one({**inv})
    logger.info("Facture transport %s émise pour OT %s (%s HT)", inv["ref"], ot["ref"], _eur(inv["amount_ht_cents"]))
    return inv


def build_transport_invoice_pdf(inv: dict, ot: dict, conv: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=VIOLET, fontSize=14)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    pk, dl = ot.get("pickup") or {}, ot.get("delivery") or {}
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BG), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])
    rows = [["Désignation", "Montant"],
            [f"Transport routier LOGI'SCOP Mode D — Ordre {ot['ref']}\n"
             f"{pk.get('zone_code')} ({(pk.get('address') or '')[:45]}) → {dl.get('zone_code')} "
             f"({(dl.get('address') or '')[:45]})", _eur(inv["amount_ht_cents"])],
            [f"{inv['vat_label']}", _eur(inv["vat_cents"])],
            ["TOTAL TTC", _eur(inv["total_ttc_cents"])]]
    tab = Table(rows, colWidths=[135 * mm, 43 * mm]); tab.setStyle(style)
    doc.build([
        Paragraph(f"FACTURE TRANSPORT — {inv['ref']}", h1),
        Paragraph(f"Émise le {inv['issued_at'][:10]} — Convention cadre {inv.get('convention_ref') or '—'}", small),
        Spacer(1, 4 * mm),
        Paragraph("<b>Émetteur :</b> SCIC SAS OBJECTIF SCOP OUTREMER — O'SCOP / LOGI'SCOP, Transporteur "
                  "Contractant — contact@objectifscopoutremer.com", n),
        Paragraph(f"<b>Donneur d'Ordre :</b> {inv.get('company_name') or '—'} — SIRET {conv.get('siret') or '—'} — "
                  f"{inv.get('email') or ''}", n),
        Spacer(1, 5 * mm), tab, Spacer(1, 5 * mm),
        Paragraph("Règlement à 30 jours maximum (article 15 de la Convention). La compensation avec un dommage "
                  "allégué est interdite sans accord écrit. Facture générée automatiquement à l'acceptation de "
                  "l'Ordre de Transport par LOGI'SCOP.", small),
        Paragraph("Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP Mode D V1.2.", small),
    ])
    return buf.getvalue()


async def send_invoice_email(db, invoice_id: str) -> None:
    """Envoi Brevo de la facture PDF au Donneur d'Ordre (best effort, tâche de fond)."""
    inv = await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv or not inv.get("email"):
        return
    try:
        ot = await db.logiscop_transport_orders.find_one({"id": inv["ot_id"]}, {"_id": 0}) or {}
        conv = await db.logiscop_transport_conventions.find_one({"id": ot.get("convention_id")}, {"_id": 0}) or {}
        pdf = build_transport_invoice_pdf(inv, ot, conv)
        from brevo_service import send_email
        html = (
            f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#5B2E8C'>Facture transport {inv['ref']}</h2>"
            f"<p>Bonjour,</p><p>LOGI'SCOP a accepté votre Ordre de Transport <b>{inv['ot_ref']}</b>. "
            f"Vous trouverez ci-joint la facture correspondante :</p>"
            f"<p style='font-size:18px'><b>{_eur(inv['total_ttc_cents'])} TTC</b> "
            f"({_eur(inv['amount_ht_cents'])} HT — {inv['vat_label']})</p>"
            "<p>Règlement à 30 jours maximum, conformément à l'article 15 de la Convention cadre.</p>"
            "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
        await send_email(
            to_email=inv["email"], to_name=inv.get("company_name"),
            subject=f"Facture transport {inv['ref']} — OT {inv['ot_ref']} accepté",
            html_content=html, tags=["logiscop-invoice"],
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{inv['ref']}.pdf"}])
        await db.logiscop_transport_invoices.update_one(
            {"id": invoice_id}, {"$set": {"email_sent_at": datetime.now(timezone.utc).isoformat()}})
        logger.info("Facture transport %s envoyée à %s", inv["ref"], inv["email"])
    except Exception as exc:
        logger.warning("Envoi facture transport %s échoué : %s", invoice_id, exc)


async def create_service_credit(db, ot: dict) -> dict | None:
    """Avoir de service automatique (article 22) : livraison en retard et/ou avec réserves (idempotent par OT)."""
    inv = await db.logiscop_transport_invoices.find_one({"ot_id": ot["id"]}, {"_id": 0})
    if not inv or await db.logiscop_transport_credits.find_one({"ot_id": ot["id"]}):
        return None
    late_doc = await db.logiscop_settings.find_one({"key": "service_credit_late_pct"}, {"_id": 0})
    res_doc = await db.logiscop_settings.find_one({"key": "service_credit_reserves_pct"}, {"_id": 0})
    late_pct = float(late_doc["value"]) if late_doc else 10.0
    res_pct = float(res_doc["value"]) if res_doc else 10.0
    epod = ot.get("epod") or {}
    reasons, pct = [], 0.0
    due = (ot.get("delivery") or {}).get("date")
    done = ((ot.get("execution") or {}).get("delivered_at") or epod.get("at") or "")[:10]
    if due and done and done > due:
        reasons.append("RETARD")
        pct += late_pct
    if epod.get("reserves"):
        reasons.append("RESERVES")
        pct += res_pct
    if not reasons or pct <= 0:
        return None
    ht = round((ot.get("price_ht_cents") or 0) * pct / 100)
    if ht <= 0:
        return None
    vat_cents = round(ht * (inv.get("vat_rate") or 0) / 100)
    year = datetime.now(timezone.utc).strftime("%Y")
    n = await db.logiscop_transport_credits.count_documents({"ref": {"$regex": f"^AV-LOGI-{year}-"}}) + 1
    credit = {
        "id": str(uuid.uuid4()), "ref": f"AV-LOGI-{year}-{n:04d}",
        "invoice_id": inv["id"], "invoice_ref": inv["ref"],
        "ot_id": ot["id"], "ot_ref": ot["ref"], "org_id": ot["org_id"], "user_id": ot["user_id"],
        "company_name": ot.get("company_name"),
        "reasons": reasons, "pct_total": pct,
        "amount_ht_cents": ht, "vat_rate": inv.get("vat_rate"), "vat_label": inv.get("vat_label"),
        "vat_cents": vat_cents, "total_ttc_cents": ht + vat_cents,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.logiscop_transport_credits.insert_one({**credit})
    logger.info("Avoir de service %s émis (%s, %.0f %%) sur facture %s",
                credit["ref"], "+".join(reasons), pct, inv["ref"])
    return credit


CREDIT_REASON_LABEL = {"RETARD": "Livraison hors délai convenu", "RESERVES": "Livraison avec réserves motivées"}


def build_credit_note_pdf(credit: dict, ot: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=VIOLET, fontSize=14)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BG), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])
    reasons = " + ".join(CREDIT_REASON_LABEL.get(r, r) for r in credit["reasons"])
    rows = [["Désignation", "Montant"],
            [f"Avoir de service (article 22) — {reasons}\nOT {credit['ot_ref']} — facture {credit['invoice_ref']} "
             f"({credit['pct_total']:.0f} % du transport HT)", f"-{_eur(credit['amount_ht_cents'])}"],
            [credit.get("vat_label") or "TVA", f"-{_eur(credit['vat_cents'])}"],
            ["TOTAL AVOIR TTC", f"-{_eur(credit['total_ttc_cents'])}"]]
    tab = Table(rows, colWidths=[135 * mm, 43 * mm]); tab.setStyle(style)
    doc.build([
        Paragraph(f"AVOIR DE SERVICE — {credit['ref']}", h1),
        Paragraph(f"Émis le {credit['created_at'][:10]} — niveaux de service, article 22 de la Convention", small),
        Spacer(1, 4 * mm),
        Paragraph("<b>Émetteur :</b> SCIC SAS OBJECTIF SCOP OUTREMER — O'SCOP / LOGI'SCOP", n),
        Paragraph(f"<b>Bénéficiaire :</b> {credit.get('company_name') or '—'}", n),
        Spacer(1, 5 * mm), tab, Spacer(1, 5 * mm),
        Paragraph("Avoir émis automatiquement au titre des niveaux de service (article 22) : les avoirs de service "
                  "compensent forfaitairement le préjudice de service, sans caractère punitif. Imputable sur la "
                  "facture visée ou sur la prochaine échéance.", small),
        Paragraph("Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP Mode D V1.2.", small),
    ])
    return buf.getvalue()


async def send_invoice_reminders(db) -> int:
    """Relance automatique des factures transport impayées à 30 jours (idempotent par facture)."""
    now = datetime.now(timezone.utc)
    sent = 0
    sent += await _send_demand_notices(db, now)
    async for inv in db.logiscop_transport_invoices.find(
            {"status": "ISSUED", "reminder_sent_at": None}, {"_id": 0}):
        try:
            issued = datetime.fromisoformat(inv["issued_at"])
        except ValueError:
            continue
        if now - issued < timedelta(days=30):
            continue
        html = (
            f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#B91C1C'>Relance — facture {inv['ref']} impayée</h2>"
            f"<p>Sauf erreur de notre part, la facture <b>{inv['ref']}</b> ({_eur(inv['total_ttc_cents'])} TTC) "
            f"relative à l'Ordre de Transport <b>{inv['ot_ref']}</b>, émise le {inv['issued_at'][:10]}, "
            "demeure impayée à l'échéance de 30 jours (article 15 de la Convention).</p>"
            "<p>Merci de procéder au règlement sous 8 jours ou de nous contacter en cas de difficulté.</p>"
            "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
        try:
            from brevo_service import send_email
            if inv.get("email"):
                await send_email(to_email=inv["email"], to_name=inv.get("company_name"),
                                 subject=f"Relance : facture transport {inv['ref']} impayée (30 jours)",
                                 html_content=html, tags=["logiscop-invoice-reminder"])
            admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
            if admin_email:
                await send_email(to_email=admin_email, to_name="LOGI'SCOP",
                                 subject=f"[LOGI'SCOP] Facture {inv['ref']} impayée à 30 j ({inv.get('company_name')})",
                                 html_content=html, tags=["logiscop-invoice-reminder"])
            await db.logiscop_transport_invoices.update_one(
                {"id": inv["id"]}, {"$set": {"reminder_sent_at": now.isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Relance facture %s échouée : %s", inv["ref"], exc)
    if sent:
        logger.info("Relances factures transport envoyées : %d", sent)
    return sent


async def _send_demand_notices(db, now) -> int:
    """2e relance à 45 jours : mise en demeure + suspension des nouveaux OT (idempotent par facture)."""
    sent = 0
    async for inv in db.logiscop_transport_invoices.find(
            {"status": "ISSUED", "demand_notice_sent_at": None,
             "reminder_sent_at": {"$ne": None}}, {"_id": 0}):
        try:
            issued = datetime.fromisoformat(inv["issued_at"])
        except ValueError:
            continue
        if now - issued < timedelta(days=45):
            continue
        html = (
            f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#B91C1C'>MISE EN DEMEURE — facture {inv['ref']}</h2>"
            f"<p>Malgré notre relance, la facture <b>{inv['ref']}</b> ({_eur(inv['total_ttc_cents'])} TTC), "
            f"relative à l'Ordre de Transport <b>{inv['ot_ref']}</b> et émise le {inv['issued_at'][:10]}, "
            "demeure impayée à 45 jours.</p>"
            "<p><b>Vous êtes mis en demeure de régler cette facture sous 8 jours.</b> À défaut, des intérêts de "
            "retard et l'indemnité forfaitaire de recouvrement seront appliqués (article 15 de la Convention).</p>"
            "<p style='color:#B91C1C'><b>L'émission de nouveaux Ordres de Transport est suspendue</b> jusqu'à "
            "régularisation complète de l'impayé.</p>"
            "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
        try:
            from brevo_service import send_email
            if inv.get("email"):
                await send_email(to_email=inv["email"], to_name=inv.get("company_name"),
                                 subject=f"MISE EN DEMEURE : facture transport {inv['ref']} impayée (45 jours)",
                                 html_content=html, tags=["logiscop-demand-notice"])
            admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
            if admin_email:
                await send_email(to_email=admin_email, to_name="LOGI'SCOP",
                                 subject=f"[LOGI'SCOP] Mise en demeure {inv['ref']} — OT suspendus ({inv.get('company_name')})",
                                 html_content=html, tags=["logiscop-demand-notice"])
            await db.logiscop_transport_invoices.update_one(
                {"id": inv["id"]}, {"$set": {"demand_notice_sent_at": now.isoformat()}})
            sent += 1
            logger.info("Mise en demeure envoyée pour %s — OT suspendus (org %s)", inv["ref"], inv.get("org_id"))
        except Exception as exc:
            logger.warning("Mise en demeure %s échouée : %s", inv["ref"], exc)
    return sent


async def get_ot_suspension(db, org_id: str) -> dict | None:
    """Facture en mise en demeure impayée (suspension non levée) → émission de nouveaux OT bloquée."""
    return await db.logiscop_transport_invoices.find_one(
        {"org_id": org_id, "status": {"$ne": "PAID"}, "demand_notice_sent_at": {"$ne": None},
         "suspension_lifted_at": None},
        {"_id": 0, "ref": 1, "total_ttc_cents": 1, "demand_notice_sent_at": 1})


async def archive_ot_documents_to_ged(db, ot_id: str) -> None:
    """Archive GEDESS de l'OT clôturé (PDF avec ePOD) et de sa facture (best effort, tâche de fond)."""
    try:
        from gedess_client import gedess_upload_file, is_gedess_configured
        if not is_gedess_configured():
            return
        ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
        if not ot:
            return
        conv = await db.logiscop_transport_conventions.find_one({"id": ot.get("convention_id")}, {"_id": 0}) or {}
        slug = ot["ref"].replace("/", "-")
        if not ot.get("ged_doc_id"):
            from logiscop_transport_pdf import build_transport_order_pdf
            doc = await gedess_upload_file(
                f"ot-logiscop-{slug}.pdf", build_transport_order_pdf(ot, conv), categorie="convention",
                description=f"OT LOGI'SCOP {ot['ref']} clôturé ({(ot.get('epod') or {}).get('outcome')}) — {ot.get('company_name')}",
                tags="logiscop,transport,ot", mime_type="application/pdf")
            await db.logiscop_transport_orders.update_one({"id": ot_id}, {"$set": {"ged_doc_id": doc.get("id")}})
        inv = await db.logiscop_transport_invoices.find_one({"ot_id": ot_id}, {"_id": 0})
        if inv and not inv.get("ged_doc_id"):
            doc = await gedess_upload_file(
                f"{inv['ref']}.pdf", build_transport_invoice_pdf(inv, ot, conv), categorie="facture",
                description=f"Facture transport {inv['ref']} — OT {ot['ref']} — {inv.get('company_name')}",
                tags="logiscop,transport,facture", mime_type="application/pdf")
            await db.logiscop_transport_invoices.update_one({"id": inv["id"]}, {"$set": {"ged_doc_id": doc.get("id")}})
        import base64 as _b64
        async for m in db.logiscop_cargo_media.find({"ot_id": ot_id, "ged_doc_id": None}):
            doc = await gedess_upload_file(
                f"{slug}-{m['stage'].lower()}-{m['name']}", _b64.b64decode(m["content_b64"]),
                categorie="convention",
                description=f"Média cargaison OT {ot['ref']} — {m['stage'].replace('_', ' ').lower()} ({m.get('operator_name')})",
                tags="logiscop,transport,cargo-media", mime_type=m["mime"])
            await db.logiscop_cargo_media.update_one({"id": m["id"]}, {"$set": {"ged_doc_id": doc.get("id")}})
        logger.info("Archivage GEDESS OT %s + facture terminé", ot["ref"])
    except Exception as exc:
        logger.warning("Archivage GEDESS OT %s échoué : %s", ot_id, exc)


async def send_pickup_reminders(db) -> int:
    """Rappel J-1 : email au Donneur d'Ordre + à LOGI'SCOP la veille de chaque enlèvement (idempotent par OT)."""
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    sent = 0
    async for ot in db.logiscop_transport_orders.find(
            {"status": "ACCEPTE", "pickup.date": tomorrow, "pickup_reminder_sent_at": None}, {"_id": 0}):
        conv = await db.logiscop_transport_conventions.find_one({"id": ot["convention_id"]}, {"_id": 0}) or {}
        pk, dl = ot.get("pickup") or {}, ot.get("delivery") or {}
        html = (
            f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#5B2E8C'>Enlèvement demain — {ot['ref']}</h2>"
            f"<p>Rappel : l'enlèvement de votre Ordre de Transport <b>{ot['ref']}</b> est prévu "
            f"<b>demain {pk.get('date')}</b>{' (' + pk['slot'] + ')' if pk.get('slot') else ''}.</p>"
            f"<p><b>Enlèvement :</b> {pk.get('address')} ({pk.get('zone_code')})<br/>"
            f"<b>Livraison :</b> {dl.get('address')} ({dl.get('zone_code')})<br/>"
            f"<b>Contact :</b> {pk.get('contact') or '—'}</p>"
            "<p>Merci de tenir la marchandise, les documents et l'accès prêts (article 5 de la Convention).</p>"
            "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>")
        try:
            from brevo_service import send_email
            if conv.get("email"):
                await send_email(to_email=conv["email"], to_name=conv.get("company_name"),
                                 subject=f"Rappel : enlèvement demain — OT {ot['ref']}",
                                 html_content=html, tags=["logiscop-pickup-reminder"])
            admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
            if admin_email:
                await send_email(to_email=admin_email, to_name="LOGI'SCOP",
                                 subject=f"[LOGI'SCOP] Enlèvement demain — OT {ot['ref']} ({ot.get('company_name')})",
                                 html_content=html, tags=["logiscop-pickup-reminder"])
            await db.logiscop_transport_orders.update_one(
                {"id": ot["id"]}, {"$set": {"pickup_reminder_sent_at": datetime.now(timezone.utc).isoformat()}})
            sent += 1
        except Exception as exc:
            logger.warning("Rappel enlèvement %s échoué : %s", ot["ref"], exc)
    if sent:
        logger.info("Rappels d'enlèvement LOGI'SCOP envoyés : %d", sent)
    return sent
