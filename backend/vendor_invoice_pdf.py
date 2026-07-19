"""Factures PDF d'adhésion avec TVA détaillée — numérotation FACT-YYYY-XXXX, email automatique, archivage."""
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lolodrive_helpers import require_admin
from vat import vat_label

logger = logging.getLogger(__name__)

vendor_invoices_router = APIRouter(prefix="/api/admin/vendor-invoices", tags=["vendor-invoices"])

db = None
VIOLET = colors.HexColor("#451F6B")
GOLD = colors.HexColor("#b8933e")


def set_vendor_invoices_database(database):
    global db
    db = database


async def _next_invoice_number() -> str:
    year = datetime.now(timezone.utc).year
    from pymongo import ReturnDocument
    doc = await db.counters.find_one_and_update(
        {"_id": f"vendor_invoice_{year}"}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER)
    return f"FACT-{year}-{doc['seq']:04d}"


def build_invoice_pdf(inv: dict) -> bytes:
    st = ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#2a2233"))
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, textColor=VIOLET, spaceAfter=2)
    small = ParagraphStyle("s", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#6b5a7a"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    eur = lambda c: f"{c / 100:.2f} €".replace(".", ",")
    head = Table([[
        Paragraph(f"FACTURE {inv['number']}", h1),
        Paragraph(f"Date : {inv['date'][:10]}<br/>Réf. adhésion : {inv['ob_id'][:8].upper()}", small),
    ]], colWidths=[100 * mm, 70 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    parties = Table([[
        Paragraph("<b>Émetteur</b><br/>SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP)<br/>Communityplace KDMARCHE<br/>contact@objectifscopoutremer.com", st),
        Paragraph(f"<b>Client</b><br/>{inv['company']}{(' — ' + inv['legal_form']) if inv.get('legal_form') else ''}<br/>"
                  f"SIRET : {inv.get('siret') or '—'}<br/>Pays : {inv.get('country') or '—'}<br/>{inv.get('email')}", st),
    ]], colWidths=[85 * mm, 85 * mm])
    parties.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbb8e0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbb8e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    lines = Table([
        ["Désignation", "Montant HT", "Taux TVA", "TVA", "Montant TTC"],
        [inv["label"], eur(inv["ht_cents"]), f"{inv['vat_rate']} %", eur(inv["vat_cents"]), eur(inv["ttc_cents"])],
        ["", "", "", Paragraph("<b>TOTAL TTC</b>", st), Paragraph(f"<b>{eur(inv['ttc_cents'])}</b>", st)],
    ], colWidths=[70 * mm, 26 * mm, 22 * mm, 26 * mm, 26 * mm])
    lines.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VIOLET), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, 1), 0.5, colors.HexColor("#cbb8e0")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    doc.build([
        head, Spacer(1, 8), parties, Spacer(1, 12), lines, Spacer(1, 10),
        Paragraph(f"Régime de TVA appliqué : {inv['vat_label']}.", small),
        Paragraph("Abonnement mensuel à la centrale coopérative — paiement par carte via Stripe. "
                  "Facture générée automatiquement et archivée par la coopérative.", small),
    ])
    return buf.getvalue()


async def issue_adhesion_invoice(database, ob: dict, kind: str, ttc_cents: int | None = None, ext_ref: str = ""):
    """Émet la facture (n° séquentiel), l'archive en base et l'envoie par email avec PDF joint."""
    global db
    if db is None:
        db = database
    try:
        ttc = ttc_cents if ttc_cents is not None else (ob.get("amount_cents") or 0)
        rate = ob.get("vat_rate") or 0
        ht = round(ttc / (1 + rate / 100)) if rate else ttc
        number = await _next_invoice_number()
        inv = {
            "number": number, "ob_id": ob["id"], "kind": kind,
            "label": f"{'Renouvellement' if kind == 'renouvellement' else 'Adhésion'} {ob.get('plan_name')} — abonnement mensuel",
            "company": ob.get("company"), "legal_form": ob.get("legal_form"), "siret": ob.get("siret"),
            "country": ob.get("country"), "email": ob.get("email"),
            "ht_cents": ht, "vat_rate": rate, "vat_cents": ttc - ht, "ttc_cents": ttc,
            "vat_label": vat_label(ob.get("country")), "ext_ref": ext_ref,
            "date": datetime.now(timezone.utc).isoformat(),
        }
        await db.vendor_invoices.insert_one({**inv})
        pdf = build_invoice_pdf(inv)
        import base64
        from brevo_service import send_email
        subjects = {"fr": f"Votre facture {number} — Communityplace",
                    "en": f"Your invoice {number} — Communityplace",
                    "es": f"Su factura {number} — Communityplace"}
        bodies = {
            "fr": f"<p>Bonjour {ob.get('contact_name')},</p><p>Veuillez trouver ci-joint votre facture <strong>{number}</strong> ({inv['label']}) d'un montant de <strong>{ttc / 100:.2f} € TTC</strong>.</p><p style='color:#777;font-size:12px;'>{inv['vat_label']}</p>",
            "en": f"<p>Hello {ob.get('contact_name')},</p><p>Please find attached your invoice <strong>{number}</strong> ({inv['label']}) for <strong>€{ttc / 100:.2f} incl. VAT</strong>.</p>",
            "es": f"<p>Hola {ob.get('contact_name')}:</p><p>Adjuntamos su factura <strong>{number}</strong> ({inv['label']}) por un importe de <strong>{ttc / 100:.2f} € con IVA</strong>.</p>",
        }
        loc = ob.get("locale") if ob.get("locale") in ("en", "es") else "fr"
        await send_email(to_email=ob["email"], to_name=ob.get("contact_name"),
                         subject=subjects[loc], html_content=bodies[loc], tags=["vendor-invoice"],
                         attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{number}.pdf"}])
        logger.info("Facture %s émise pour %s (%s)", number, ob.get("company"), kind)
        return number
    except Exception as exc:
        logger.warning("Émission facture %s : %s", ob.get("id"), exc)
        return None


@vendor_invoices_router.get("")
async def list_invoices(limit: int = 100, admin: dict = Depends(require_admin)):
    items = await db.vendor_invoices.find({}, {"_id": 0}).sort("date", -1).limit(limit).to_list(limit)
    return {"items": items, "total": len(items)}


@vendor_invoices_router.get("/{number}/pdf")
async def invoice_pdf(number: str, admin: dict = Depends(require_admin)):
    inv = await db.vendor_invoices.find_one({"number": number}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return Response(content=build_invoice_pdf(inv), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{number}.pdf"'})
