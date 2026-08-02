"""Bon de livraison signé LOGI'SCOP — PDF pour litiges (signature, photos, réserves)."""
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8933D")
DARK = colors.HexColor("#2A1045")


def _local(url: str) -> str | None:
    if not url or "/uploads/" not in url:
        return None
    rel = url.split("/uploads/", 1)[1]
    path = os.path.join(os.path.dirname(__file__), "uploads", rel)
    return path if os.path.exists(path) else None


def build_delivery_note_pdf(order: dict, proof: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    h1 = ParagraphStyle("h1", fontSize=15, textColor=DARK, fontName="Helvetica-Bold", spaceAfter=2)
    sub = ParagraphStyle("sub", fontSize=8, textColor=colors.HexColor("#666666"))
    st = ParagraphStyle("st", fontSize=9, leading=13)
    h2 = ParagraphStyle("h2", fontSize=10.5, textColor=GOLD, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
    el = [
        Paragraph("BON DE LIVRAISON — PREUVE ÉLECTRONIQUE DE RÉCEPTION", h1),
        Paragraph("KDMARCHÉ × O'SCOP — livraison certifiée LOGI'SCOP", sub),
        Paragraph("KDMARCHÉ, service exploité par PRIMACOP INTERNATIONAL BUSINESS — SIRET 433 230 703 00020", sub),
        Spacer(1, 6),
    ]
    geo = proof.get("geolocation") or {}
    meta = [
        ["Commande", proof.get("order_number", "")],
        ["Réceptionnaire", proof.get("receiver_name", "")],
        ["Date et heure", str(proof.get("confirmed_at", ""))[:16].replace("T", " ")],
        ["Transporteur", proof.get("carrier_name", "LOGI'SCOP")],
        ["Géolocalisation", f"{geo.get('lat')}, {geo.get('lng')}" if geo else "—"],
        ["Authentification", "Code OTP sécurisé vérifié ✔" if proof.get("otp_verified") else "—"],
        ["Montant commande", f"{order.get('total_ttc_cents', 0) / 100:.2f} € TTC"],
    ]
    t = Table(meta, colWidths=[45 * mm, 125 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    el += [t, Paragraph("Quantités reçues", h2)]
    qty_by_pid = {q.get("product_id"): q.get("qty_received") for q in (proof.get("quantities") or [])}
    rows = [["Produit", "Commandé", "Reçu"]]
    for it in order.get("items") or []:
        rows.append([Paragraph(it.get("product_name", ""), st), str(it.get("quantity", "")),
                     str(qty_by_pid.get(it.get("product_id"), it.get("quantity", "")))])
    t = Table(rows, colWidths=[110 * mm, 30 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)

    reserves = proof.get("reserves") or []
    el.append(Paragraph("Réserves émises", h2))
    if reserves:
        rows = [["Produit", "Qté contestée", "Motif"]]
        for r in reserves:
            rows.append([Paragraph(r.get("product_name", ""), st), str(r.get("qty", "")),
                         Paragraph(r.get("reason", ""), st)])
        t = Table(rows, colWidths=[60 * mm, 25 * mm, 85 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B45309")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        el += [t, Paragraph(
            f"Valeur suspendue : {order.get('rar_disputed_cents', 0) / 100:.2f} € TTC — seule la valeur des produits "
            "précisément contestés est suspendue ; le reste de la livraison demeure payable.", sub)]
    else:
        el.append(Paragraph("Aucune réserve — livraison acceptée sans réserve.", st))

    sig = _local(proof.get("signature_url"))
    el.append(Paragraph("Signature électronique du réceptionnaire", h2))
    if sig:
        el.append(Image(sig, width=70 * mm, height=22 * mm, kind="proportional"))
    photos = [p for p in ((_local(u) for u in proof.get("photos") or [])) if p]
    if photos:
        el.append(Paragraph("Photographies — état apparent", h2))
        el.append(Table([[Image(p, width=48 * mm, height=36 * mm, kind="proportional") for p in photos[:3]]]))
    el += [Spacer(1, 10), Paragraph(
        "Preuve électronique conforme à l'article « Règlement à Réception Pro » des CGV KDMARCHÉ : la validation "
        "(signature + code sécurisé) rend le prix exigible et déclenche le règlement.", sub)]
    doc.build(el)
    return buf.getvalue()
