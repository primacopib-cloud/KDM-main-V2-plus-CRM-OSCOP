"""Reçu de paiement des factures transport LOGI'SCOP (avoir déduit détaillé) + archivage GEDESS."""
import logging
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

GOLD = colors.HexColor("#B8860B")
VIOLET = colors.HexColor("#2A1045")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")
METHOD_LABEL = {"stripe": "Carte bancaire (Stripe)", "avoir": "Compensation par avoir de service",
                "manual": "Règlement manuel (virement / chèque)"}


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


def build_payment_receipt_pdf(inv: dict, ot: dict, credit: dict | None, txn: dict | None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=VIOLET, fontSize=14)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    credit_cents = inv.get("credit_applied_cents") or (credit or {}).get("total_ttc_cents") or 0
    net = max(0, (inv.get("total_ttc_cents") or 0) - credit_cents)
    rows = [["Désignation", "Montant"],
            [f"Facture transport {inv['ref']} — OT {inv['ot_ref']} "
             f"({_eur(inv.get('amount_ht_cents'))} HT — {inv.get('vat_label') or 'TVA'})",
             _eur(inv.get("total_ttc_cents"))]]
    if credit and credit_cents:
        reasons = " + ".join(credit.get("reasons") or [])
        rows.append([f"Avoir de service {credit['ref']} déduit (article 22 — {reasons}, "
                     f"{credit.get('pct_total', 0):.0f} % du transport HT)", f"-{_eur(credit_cents)}"])
    rows.append(["NET RÉGLÉ TTC", _eur(net)])
    tab = Table(rows, colWidths=[135 * mm, 43 * mm])
    tab.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BG), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    method = METHOD_LABEL.get(inv.get("payment_method"), inv.get("payment_method") or "—")
    session_line = f" — session Stripe {inv.get('stripe_session_id') or (txn or {}).get('session_id') or '—'}" \
        if inv.get("payment_method") == "stripe" else ""
    doc.build([
        Paragraph(f"REÇU DE PAIEMENT — FACTURE {inv['ref']}", h1),
        Paragraph(f"Paiement enregistré le {(inv.get('paid_at') or '')[:10]} — {method}{session_line}", small),
        Spacer(1, 4 * mm),
        Paragraph("<b>Émetteur :</b> SCIC SAS OBJECTIF SCOP OUTREMER — O'SCOP / LOGI'SCOP, Transporteur Contractant", n),
        Paragraph(f"<b>Donneur d'Ordre :</b> {inv.get('company_name') or '—'} — {inv.get('email') or ''}", n),
        Paragraph(f"<b>Ordre de Transport :</b> {inv.get('ot_ref')} — "
                  f"{(ot.get('pickup') or {}).get('zone_code') or '—'} → {(ot.get('delivery') or {}).get('zone_code') or '—'}", n),
        Spacer(1, 5 * mm), tab, Spacer(1, 5 * mm),
        Paragraph("Le présent reçu atteste du règlement intégral de la facture visée, déduction faite des avoirs "
                  "de service applicables (article 22 de la Convention). Document généré et archivé "
                  "automatiquement en GEDESS.", small),
        Paragraph("Dashboard KDMARCHÉ × O'SCOP — LOGI'SCOP Mode D V1.2.", small),
    ])
    return buf.getvalue()


async def load_receipt_context(db, invoice_id: str) -> tuple[dict, dict, dict | None, dict | None]:
    inv = await db.logiscop_transport_invoices.find_one({"id": invoice_id}, {"_id": 0})
    ot = await db.logiscop_transport_orders.find_one({"id": (inv or {}).get("ot_id")}, {"_id": 0}) or {}
    credit = await db.logiscop_transport_credits.find_one({"invoice_id": invoice_id}, {"_id": 0})
    txn = await db.logiscop_invoice_payments.find_one(
        {"invoice_id": invoice_id, "status": "completed"}, {"_id": 0}, sort=[("created_at", -1)])
    return inv, ot, credit, txn


async def archive_payment_receipt_to_ged(db, invoice_id: str) -> None:
    """Archive GEDESS du reçu de paiement (best effort, tâche de fond, idempotent)."""
    try:
        from gedess_client import gedess_upload_file, is_gedess_configured
        if not is_gedess_configured():
            return
        inv, ot, credit, txn = await load_receipt_context(db, invoice_id)
        if not inv or inv.get("status") != "PAID" or inv.get("receipt_ged_doc_id"):
            return
        pdf = build_payment_receipt_pdf(inv, ot, credit, txn)
        doc = await gedess_upload_file(
            f"recu-{inv['ref']}.pdf", pdf, categorie="facture",
            description=f"Reçu de paiement facture transport {inv['ref']} — OT {inv['ot_ref']} — "
                        f"{inv.get('company_name')} ({inv.get('payment_method')})",
            tags="logiscop,transport,recu-paiement", mime_type="application/pdf")
        await db.logiscop_transport_invoices.update_one(
            {"id": invoice_id}, {"$set": {"receipt_ged_doc_id": doc.get("id")}})
        logger.info("Reçu de paiement %s archivé en GEDESS (%s)", inv["ref"], doc.get("id"))
    except Exception as exc:
        logger.warning("Archivage GEDESS reçu paiement %s échoué : %s", invoice_id, exc)
