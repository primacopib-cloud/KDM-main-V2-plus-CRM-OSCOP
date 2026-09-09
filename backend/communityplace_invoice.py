"""Facture acquittée PDF — frais de publication CommunityPlace (logo O'SCOP + pied de page)."""
import io
import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

LOGO_PATH = "/app/frontend/public/icon-512.png"
GOLD = (0.85, 0.70, 0.35)
PURPLE = (0.12, 0.04, 0.20)


def build_paid_invoice_pdf(need: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    now = datetime.now(timezone.utc)
    fee = float(need.get("communityplace_fee_eur") or 50)

    c.setFillColorRGB(*PURPLE)
    c.rect(0, h - 34 * mm, w, 34 * mm, stroke=0, fill=1)
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 14 * mm, h - 30 * mm, 24 * mm, 24 * mm, mask='auto')
        except Exception:
            pass
    c.setFillColorRGB(*GOLD)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(44 * mm, h - 18 * mm, "O'SCOP — Centrale coopérative")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 10)
    c.drawString(44 * mm, h - 25 * mm, "KDMARCHÉ CommunityPlace — Frais de publication")

    c.setFillColorRGB(0.2, 0.55, 0.25)
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(w - 16 * mm, h - 50 * mm, "FACTURE ACQUITTÉE")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    c.drawString(16 * mm, h - 50 * mm, f"Facture n° CP-{need.get('reference')}")
    c.drawString(16 * mm, h - 56 * mm, f"Date : {now.strftime('%d/%m/%Y')}")
    paid_at = str(need.get("communityplace_paid_at") or "")[:10]
    c.drawString(16 * mm, h - 62 * mm, f"Payée le : {paid_at or now.strftime('%Y-%m-%d')}")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, h - 76 * mm, "Facturé à :")
    c.setFont("Helvetica", 10)
    y = h - 82 * mm
    for line in [need.get("company") or "", need.get("contact_name") or "", need.get("email") or "", need.get("territory") or ""]:
        if line:
            c.drawString(16 * mm, y, str(line))
            y -= 5.5 * mm

    ty = h - 112 * mm
    c.setFillColorRGB(*GOLD)
    c.rect(16 * mm, ty, w - 32 * mm, 9 * mm, stroke=0, fill=1)
    c.setFillColorRGB(*PURPLE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(19 * mm, ty + 3 * mm, "Désignation")
    c.drawRightString(w - 19 * mm, ty + 3 * mm, "Montant TTC")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    label = "offre produit" if (need.get("listing_type") or "").upper() == "OFFRE" else "besoin d'achat"
    c.drawString(19 * mm, ty - 6 * mm, f"Publication CommunityPlace — {label} {need.get('reference')} ({need.get('product')})")
    c.drawRightString(w - 19 * mm, ty - 6 * mm, f"{fee:.2f} €")
    c.line(16 * mm, ty - 10 * mm, w - 16 * mm, ty - 10 * mm)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 19 * mm, ty - 18 * mm, f"TOTAL ACQUITTÉ : {fee:.2f} €")
    c.setFont("Helvetica", 8)
    c.drawString(16 * mm, ty - 26 * mm, "TVA non applicable, art. 293 B du CGI. Règlement reçu par carte bancaire (Stripe).")

    c.setFillColorRGB(*PURPLE)
    c.rect(0, 0, w, 20 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 12 * mm, "SCIC SAS OBJECTIF SCOP OUTREMER — Centrale coopérative multi-territoires")
    c.drawCentredString(w / 2, 7 * mm, "contact@objectifscopoutremer.com · centrale.objectifscopoutremer.com · Guadeloupe · Martinique · Guyane · La Réunion · Mayotte")

    c.showPage()
    c.save()
    return buf.getvalue()


def build_financing_invoice_pdf(fp: dict) -> bytes:
    """Facture acquittée — financement produit investisseur, vendu et facturé par O'SCOP."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    now = datetime.now(timezone.utc)
    total = float(fp.get("total_price_eur") or 0)
    base = float(fp.get("base_price_eur") or 0)
    margin = float(fp.get("margin_percent") or 0)

    c.setFillColorRGB(*PURPLE)
    c.rect(0, h - 34 * mm, w, 34 * mm, stroke=0, fill=1)
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 14 * mm, h - 30 * mm, 24 * mm, 24 * mm, mask='auto')
        except Exception:
            pass
    c.setFillColorRGB(*GOLD)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(44 * mm, h - 18 * mm, "O'SCOP — Centrale coopérative")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 10)
    c.drawString(44 * mm, h - 25 * mm, "Financements — Espace investisseurs")

    c.setFillColorRGB(0.2, 0.55, 0.25)
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(w - 16 * mm, h - 50 * mm, "FACTURE ACQUITTÉE")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    c.drawString(16 * mm, h - 50 * mm, f"Facture n° {fp.get('reference')}")
    c.drawString(16 * mm, h - 56 * mm, f"Date : {now.strftime('%d/%m/%Y')}")
    paid_at = str(fp.get("paid_at") or "")[:10]
    c.drawString(16 * mm, h - 62 * mm, f"Payée le : {paid_at or now.strftime('%Y-%m-%d')}")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, h - 76 * mm, "Facturé à (investisseur) :")
    c.setFont("Helvetica", 10)
    c.drawString(16 * mm, h - 82 * mm, str(fp.get("paid_by") or ""))

    ty = h - 100 * mm
    c.setFillColorRGB(*GOLD)
    c.rect(16 * mm, ty, w - 32 * mm, 9 * mm, stroke=0, fill=1)
    c.setFillColorRGB(*PURPLE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(19 * mm, ty + 3 * mm, "Désignation")
    c.drawRightString(w - 19 * mm, ty + 3 * mm, "Montant TTC")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    kind_label = "logistique" if (fp.get("kind") or "").upper() == "LOGISTIQUE" else "produit"
    c.drawString(19 * mm, ty - 6 * mm, f"Financement {kind_label} — {fp.get('reference')} ({fp.get('name')})")
    c.drawRightString(w - 19 * mm, ty - 6 * mm, f"{total:.2f} €")
    c.setFont("Helvetica", 8)
    c.drawString(19 * mm, ty - 11 * mm, f"Base HT : {base:.2f} € · Marge bénéficiaire O'SCOP : {margin:.2f} %")
    c.line(16 * mm, ty - 15 * mm, w - 16 * mm, ty - 15 * mm)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 19 * mm, ty - 23 * mm, f"TOTAL ACQUITTÉ : {total:.2f} €")
    c.setFillColorRGB(0.2, 0.55, 0.25)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, ty - 33 * mm, "✔ Produit vendu et facturé par O'SCOP")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    c.drawString(16 * mm, ty - 40 * mm, "Règlement reçu par carte bancaire (Stripe). TVA non applicable, art. 293 B du CGI.")

    c.setFillColorRGB(*PURPLE)
    c.rect(0, 0, w, 20 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 12 * mm, "SCIC SAS OBJECTIF SCOP OUTREMER — Centrale coopérative multi-territoires")
    c.drawCentredString(w / 2, 7 * mm, "contact@objectifscopoutremer.com · centrale.objectifscopoutremer.com · Guadeloupe · Martinique · Guyane · La Réunion · Mayotte")

    c.showPage()
    c.save()
    return buf.getvalue()



def build_api_subscription_invoice_pdf(sub: dict) -> bytes:
    """Facture acquittée — abonnement annuel API coopérative O'SCOP."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    now = datetime.now(timezone.utc)
    total = float(sub.get("amount_eur") or 2500)

    c.setFillColorRGB(*PURPLE)
    c.rect(0, h - 34 * mm, w, 34 * mm, stroke=0, fill=1)
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 14 * mm, h - 30 * mm, 24 * mm, 24 * mm, mask='auto')
        except Exception:
            pass
    c.setFillColorRGB(*GOLD)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(44 * mm, h - 18 * mm, "O'SCOP — Centrale coopérative")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 10)
    c.drawString(44 * mm, h - 25 * mm, "API coopérative — Abonnement annuel")

    c.setFillColorRGB(0.2, 0.55, 0.25)
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(w - 16 * mm, h - 50 * mm, "FACTURE ACQUITTÉE")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    c.drawString(16 * mm, h - 50 * mm, f"Facture n° {sub.get('reference')}")
    c.drawString(16 * mm, h - 56 * mm, f"Date : {now.strftime('%d/%m/%Y')}")
    paid_at = str(sub.get("paid_at") or "")[:10]
    c.drawString(16 * mm, h - 62 * mm, f"Payée le : {paid_at or now.strftime('%Y-%m-%d')}")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, h - 76 * mm, "Facturé à (membre) :")
    c.setFont("Helvetica", 10)
    y = h - 82 * mm
    for line in [sub.get("company") or "", sub.get("contact_name") or "", sub.get("email") or ""]:
        if line:
            c.drawString(16 * mm, y, str(line))
            y -= 5.5 * mm

    ty = h - 108 * mm
    c.setFillColorRGB(*GOLD)
    c.rect(16 * mm, ty, w - 32 * mm, 9 * mm, stroke=0, fill=1)
    c.setFillColorRGB(*PURPLE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(19 * mm, ty + 3 * mm, "Désignation")
    c.drawRightString(w - 19 * mm, ty + 3 * mm, "Montant TTC")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10)
    c.drawString(19 * mm, ty - 6 * mm, f"Abonnement annuel API coopérative — {sub.get('reference')}")
    c.drawRightString(w - 19 * mm, ty - 6 * mm, f"{total:.2f} €")
    valid_until = str(sub.get("valid_until") or "")[:10]
    c.setFont("Helvetica", 8)
    if valid_until:
        c.drawString(19 * mm, ty - 11 * mm,
                     f"Validité : 12 mois — jusqu'au {valid_until[8:10]}/{valid_until[5:7]}/{valid_until[:4]} · "
                     f"Clé API : {sub.get('api_key_prefix') or ''}")
    c.line(16 * mm, ty - 15 * mm, w - 16 * mm, ty - 15 * mm)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 19 * mm, ty - 23 * mm, f"TOTAL ACQUITTÉ : {total:.2f} €")
    c.setFillColorRGB(0.2, 0.55, 0.25)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, ty - 33 * mm, "✔ Accès API coopérative activé — facturé par O'SCOP")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    c.drawString(16 * mm, ty - 40 * mm, "Règlement reçu par carte bancaire (Stripe). TVA non applicable, art. 293 B du CGI.")

    c.setFillColorRGB(*PURPLE)
    c.rect(0, 0, w, 20 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 12 * mm, "SCIC SAS OBJECTIF SCOP OUTREMER — Centrale coopérative multi-territoires")
    c.drawCentredString(w / 2, 7 * mm, "contact@objectifscopoutremer.com · centrale.objectifscopoutremer.com · Guadeloupe · Martinique · Guyane · La Réunion · Mayotte")

    c.showPage()
    c.save()
    return buf.getvalue()
