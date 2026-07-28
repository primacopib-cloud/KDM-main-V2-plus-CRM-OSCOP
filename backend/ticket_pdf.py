"""Ticket de caisse PDF (format reçu 80 mm, standard européen HT / TVA par taux / TTC)."""
import io
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

W = 80 * mm
PAY_FR = {"CARD": "CB", "UC": "UC - CREDI'SCOP", "MIXED": "UC + complement"}


def _eu_lines(items):
    out, total_ht, tva_by_rate = [], 0, {}
    for l in items:
        ttc = l["unit_cents"] * l["qty"]
        rate = float(l.get("tva_rate") or 8.5)
        ht = round(ttc / (1 + rate / 100))
        out.append((l, rate, ht))
        total_ht += ht
        tva_by_rate[rate] = tva_by_rate.get(rate, 0) + (ttc - ht)
    return out, total_ht, tva_by_rate


def build_ticket_pdf(order: dict, point: dict, public_url: str = None) -> bytes:
    items = order.get("items", [])
    lines, total_ht, tva_by_rate = _eu_lines(items)
    n_extra = len(tva_by_rate) + (1 if order.get("promo_discount_cents") else 0)
    height = (60 + len(lines) * 5 + n_extra * 4.5 + 55) * mm / 10 + 60 * mm + (30 * mm if public_url else 0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, height))
    y = height - 10 * mm

    def line(txt, right=None, font="Courier", size=7.5, dy=4 * mm, bold=False):
        nonlocal y
        c.setFont(f"{font}-Bold" if bold else font, size)
        c.drawString(4 * mm, y, txt)
        if right is not None:
            c.drawRightString(W - 4 * mm, y, right)
        y -= dy

    def dashes():
        nonlocal y
        c.setFont("Courier", 7)
        c.drawCentredString(W / 2, y, "-" * 42)
        y -= 4 * mm

    c.setFont("Courier-Bold", 9)
    c.drawCentredString(W / 2, y, (point.get("name") or "Relais LOLODRIVE")[:38])
    y -= 4.5 * mm
    c.setFont("Courier", 6.5)
    if point.get("siret"):
        c.drawCentredString(W / 2, y, f"SIRET {point['siret']}")
        y -= 3.2 * mm
    if point.get("vat_number"):
        c.drawCentredString(W / 2, y, f"N° TVA {point['vat_number']}")
        y -= 3.2 * mm
    c.drawCentredString(W / 2, y, f"Vente au comptoir - {order.get('created_at').strftime('%d/%m/%Y %H:%M') if order.get('created_at') else ''}")
    y -= 3.2 * mm
    c.drawCentredString(W / 2, y, order.get("order_number", ""))
    y -= 4 * mm
    dashes()
    for l, rate, ht in lines:
        name = f"{l['qty']} x {l['name']}"[:30]
        promo = f" -{l['promo_percent']:g}%" if l.get("promo_percent") else ""
        line(f"{name}{promo}", None, size=7.5, dy=3.4 * mm)
        ttc = l["unit_cents"] * l["qty"]
        line(f"   TVA {rate:g}% · {round(ttc / 10, 1):g} UC", f"{ht / 100:.2f} EUR HT", size=7, dy=4 * mm)
    dashes()
    line("Sous-total HT", f"{total_ht / 100:.2f} EUR", bold=True)
    for rate, tva in sorted(tva_by_rate.items()):
        line(f"TVA {rate:.2f} %".replace(".", ","), f"{tva / 100:.2f} EUR", size=7)
    if order.get("promo_discount_cents"):
        line("Remise promo (deja deduite)", f"-{order['promo_discount_cents'] / 100:.2f} EUR", size=7)
    dashes()
    pay = PAY_FR.get(order.get("payment_method"), "Especes")
    line(f"MONTANT TTC ({pay})", f"{order.get('total_cents', 0) / 100:.2f} EUR", size=8.5, bold=True, dy=4 * mm)
    line("", f"soit {round(order.get('total_cents', 0) / 10, 1):g} UC", size=7, dy=4.5 * mm)
    if order.get("uc_paid"):
        line(f"Paye en UC : {order['uc_paid']} UC", size=7)
    if order.get("operator_name"):
        line(f"Encaisse par : {order['operator_name']}", size=7)
    y -= 2 * mm
    if public_url:
        widget = qr.QrCodeWidget(public_url, barLevel="M")
        b = widget.getBounds()
        size = 20 * mm
        d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0])
        d.add(widget)
        y -= size
        renderPDF.draw(d, c, (W - size) / 2, y)
        y -= 3.5 * mm
        c.setFont("Courier", 6)
        c.drawCentredString(W / 2, y, "Scannez pour le detail de la vente en ligne")
        y -= 4 * mm
    c.setFont("Courier", 6.5)
    c.drawCentredString(W / 2, y, "Merci de votre visite !")
    y -= 3.2 * mm
    c.drawCentredString(W / 2, y, "LOLODRIVE by O'SCOP")
    c.save()
    return buf.getvalue()
