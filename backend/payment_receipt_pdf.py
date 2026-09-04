"""Reçu de paiement PDF officiel (logo + numérotation) pour les liens de paiement admin."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

GOLD = colors.HexColor("#B8923F")
VIOLET = colors.HexColor("#2A1045")
GREY = colors.HexColor("#666666")
LOGO_PATH = "/app/frontend/public/logos/kdmarche-pro.png"


async def next_receipt_number(db) -> str:
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"payment_receipt_{year}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return f"REC-{year}-{doc['seq']:04d}"


def build_receipt_pdf(link: dict, receipt_number: str, labels: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFillColor(VIOLET)
    c.rect(0, h - 42 * mm, w, 42 * mm, stroke=0, fill=1)
    if os.path.isfile(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 18 * mm, h - 34 * mm, width=42 * mm, height=24 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(w - 18 * mm, h - 20 * mm, "REÇU DE PAIEMENT")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 18 * mm, h - 27 * mm, f"N° {receipt_number}")
    paid_at = (link.get("paid_at") or datetime.now(timezone.utc).isoformat())[:10]
    c.drawRightString(w - 18 * mm, h - 33 * mm, f"Date : {paid_at[8:10]}/{paid_at[5:7]}/{paid_at[:4]}")

    y = h - 58 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Émis par")
    c.setFont("Helvetica", 10)
    c.drawString(18 * mm, y - 6 * mm, "KDMARCHÉ × O'SCOP — Coopérative ESS")
    c.drawString(18 * mm, y - 11 * mm, "Communityplace coopérative B2B2C des Outre-mer")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(110 * mm, y, "Reçu de")
    c.setFont("Helvetica", 10)
    c.drawString(110 * mm, y - 6 * mm, link.get("email", ""))

    y -= 26 * mm
    rows = [("Objet", labels.get(link.get("account_type"), link.get("account_type", "")))]
    if link.get("description"):
        rows.append(("Détail", str(link["description"])))
    rows += [("Référence du lien", link["id"][:8].upper()),
             ("Moyen de paiement", "Stripe — paiement sécurisé en ligne")]
    c.setFillColor(GOLD)
    c.rect(18 * mm, y, w - 36 * mm, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(21 * mm, y + 2.5 * mm, "DÉSIGNATION")
    for i, (k, v) in enumerate(rows):
        ry = y - (i + 1) * 8 * mm
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#F5F0E6"))
            c.rect(18 * mm, ry, w - 36 * mm, 8 * mm, stroke=0, fill=1)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 9)
        c.drawString(21 * mm, ry + 2.5 * mm, k)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(75 * mm, ry + 2.5 * mm, v[:80])

    y -= (len(rows) + 1) * 8 * mm + 12 * mm
    amount = f"{link['amount_cents'] / 100:,.2f}".replace(",", " ").replace(".", ",")
    c.setFillColor(VIOLET)
    c.rect(110 * mm, y, w - 128 * mm, 14 * mm, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(114 * mm, y + 8.5 * mm, "MONTANT RÉGLÉ")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(114 * mm, y + 2.5 * mm, f"{amount} EUR")

    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    c.drawString(18 * mm, 28 * mm, "Ce reçu atteste de l'encaissement intégral du montant indiqué ci-dessus.")
    c.drawString(18 * mm, 23 * mm, "Document généré automatiquement — valable comme justificatif comptable.")
    c.setStrokeColor(GOLD)
    c.line(18 * mm, 18 * mm, w - 18 * mm, 18 * mm)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(w / 2, 13 * mm, "KDMARCHÉ × O'SCOP — Économie Sociale et Solidaire — 1 personne = 1 voix")

    c.showPage()
    c.save()
    return buf.getvalue()
