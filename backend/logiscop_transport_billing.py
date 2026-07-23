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
