"""Bon de commande fournisseur en PDF A4 (à joindre à la comptabilité)."""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _date_s(v):
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y %H:%M")
    return str(v or "")[:16].replace("T", " ")


def build_restock_pdf(order: dict, point: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, _h = A4
    y = _h - 20 * mm

    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, y, f"BON DE COMMANDE {order['order_number']}")
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, f"Relais : {point.get('name', '')} ({point.get('code', '')}) — émis le {_date_s(order.get('created_at'))}")
    y -= 5 * mm
    if point.get("siret") or point.get("vat_number"):
        fisc = " · ".join(x for x in [f"SIRET {point['siret']}" if point.get("siret") else None,
                                      f"N° TVA {point['vat_number']}" if point.get("vat_number") else None] if x)
        c.drawString(20 * mm, y, fisc)
        y -= 5 * mm
    status = f"Réception pointée le {_date_s(order['received_at'])}" if order.get("received_at") else "En attente de réception"
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, y, f"Statut : {status}")
    y -= 9 * mm

    got = {r["sku"]: r["qty"] for r in (order.get("received_items") or [])}
    has_price = any(l.get("purchase_price_cents") for l in order.get("lines", []))
    cols = [20 * mm, 80 * mm, 116 * mm, 138 * mm, 158 * mm] if has_price else [20 * mm, 95 * mm, 145 * mm, 168 * mm, 0]
    headers = ["Produit", "Fournisseur", "PU achat", "Qté cdée", "Qté reçue"] if has_price else ["Produit", "Fournisseur", "Qté cdée", "Qté reçue"]
    c.setFont("Helvetica-Bold", 9)
    for x, label in zip(cols, headers):
        c.drawString(x, y, label)
    y -= 2 * mm
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    for l in order.get("lines", []):
        c.drawString(cols[0], y, (l.get("name") or l["sku"])[:44 if has_price else 52])
        c.drawString(cols[1], y, (l.get("supplier") or "—")[:24 if has_price else 32])
        recu = str(got.get(l["sku"], "—")) if order.get("received_at") else "—"
        if has_price:
            pp = l.get("purchase_price_cents")
            c.drawRightString(cols[2] + 14 * mm, y, f"{pp / 100:.2f} €" if pp else "—")
            c.drawRightString(cols[3] + 12 * mm, y, str(l["qty"]))
            c.drawRightString(cols[4] + 14 * mm, y, recu)
        else:
            c.drawRightString(cols[2] + 12 * mm, y, str(l["qty"]))
            c.drawRightString(cols[3] + 14 * mm, y, recu)
        y -= 5.5 * mm
        if y < 25 * mm:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = _h - 20 * mm
    if order.get("total_cents"):
        y -= 2 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(w - 20 * mm, y, f"Total achat : {order['total_cents'] / 100:.2f} €")
        y -= 6 * mm
    shortages = order.get("shortages") or []
    if shortages:
        y -= 3 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(20 * mm, y, "Écarts de livraison :")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        for s in shortages:
            c.drawString(24 * mm, y, f"- {s.get('name', s['sku'])} : {s['missing']} manquant(s) (fournisseur prévenu)")
            y -= 5 * mm
    y -= 6 * mm
    c.setFont("Helvetica", 7.5)
    c.drawString(20 * mm, y, "Document généré automatiquement — Réseau LOLODRIVE by O'SCOP.")
    c.save()
    return buf.getvalue()
