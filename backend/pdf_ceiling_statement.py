"""Relevé mensuel de plafond — Règlement à Réception Pro (PDF comptable)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOLD = colors.HexColor("#B8933D")
DARK = colors.HexColor("#2A1045")
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]

TYPE_LABELS = {"GRANT": "Attribution", "RESERVE": "Réservation", "CREDIT": "Avoir", "RESTORE": "Rétablissement"}


def _eur(cents: int, signed: bool = True) -> str:
    v = (cents or 0) / 100
    return f"{v:+,.2f} €".replace(",", " ").replace(".", ",") if signed else f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def build_ceiling_statement_pdf(org_name: str, month: str, events: list, ceiling_cents: int) -> bytes:
    y, m = month.split("-")
    period = f"{MONTHS_FR[int(m) - 1].capitalize()} {y}"
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    h1 = ParagraphStyle("h1", fontSize=15, textColor=DARK, fontName="Helvetica-Bold", spaceAfter=2)
    sub = ParagraphStyle("sub", fontSize=8, textColor=colors.HexColor("#666666"))
    st = ParagraphStyle("st", fontSize=9, leading=13)
    h2 = ParagraphStyle("h2", fontSize=10.5, textColor=GOLD, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
    el = [
        Paragraph("RELEVÉ DE PLAFOND — RÈGLEMENT À RÉCEPTION PRO", h1),
        Paragraph("KDMARCHÉ × O'SCOP — document à joindre à votre comptabilité", sub),
        Paragraph("KDMARCHÉ, service exploité par PRIMACOP INTERNATIONAL BUSINESS — SIRET 433 230 703 00020", sub),
        Spacer(1, 6),
    ]
    meta = [["Organisation", org_name], ["Période", period],
            ["Plafond accordé en vigueur", _eur(ceiling_cents, signed=False)],
            ["Mouvements sur la période", str(len(events))]]
    t = Table(meta, colWidths=[55 * mm, 115 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    el += [t, Paragraph("Détail des mouvements", h2)]

    if events:
        rows = [["Date", "Type", "Libellé", "Commande", "Montant"]]
        for e in sorted(events, key=lambda x: str(x["date"] or "")):
            rows.append([str(e["date"])[:10], TYPE_LABELS.get(e["type"], e["type"]),
                         Paragraph(e["label"], st), e.get("order_number") or "—", _eur(e["amount_cents"])])
        t = Table(rows, colWidths=[20 * mm, 26 * mm, 72 * mm, 32 * mm, 24 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
            ("ALIGN", (4, 0), (4, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        el.append(t)
    else:
        el.append(Paragraph("Aucun mouvement de plafond sur cette période.", st))

    tot = {k: sum(e["amount_cents"] for e in events if e["type"] == k) for k in TYPE_LABELS}
    net = sum(e["amount_cents"] for e in events)
    rows = [["Réservations (commandes sans acompte)", _eur(tot["RESERVE"])],
            ["Rétablissements (paiements encaissés)", _eur(tot["RESTORE"])],
            ["Avoirs accordés (réserves instruites)", _eur(tot["CREDIT"])],
            ["Attributions de plafond", _eur(tot["GRANT"])],
            ["Mouvement net de la période", _eur(net)]]
    t = Table(rows, colWidths=[120 * mm, 50 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, GOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    el += [Paragraph("Synthèse de la période", h2), t, Spacer(1, 10), Paragraph(
        "Le plafond est mobilisé à la confirmation d'une commande sans acompte et rétabli après confirmation "
        "effective du paiement (encaissement définitif), conformément aux CGV KDMARCHÉ.", sub)]
    doc.build(el)
    return buf.getvalue()


def build_ceiling_annual_pdf(org_name: str, year: str, events: list, ceiling_cents: int) -> bytes:
    """Relevé annuel : synthèse mensuelle des mouvements de plafond pour le bilan comptable."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    h1 = ParagraphStyle("h1", fontSize=15, textColor=DARK, fontName="Helvetica-Bold", spaceAfter=2)
    sub = ParagraphStyle("sub", fontSize=8, textColor=colors.HexColor("#666666"))
    h2 = ParagraphStyle("h2", fontSize=10.5, textColor=GOLD, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
    el = [
        Paragraph("RELEVÉ ANNUEL DE PLAFOND — RÈGLEMENT À RÉCEPTION PRO", h1),
        Paragraph("KDMARCHÉ × O'SCOP — document récapitulatif à joindre à votre bilan comptable", sub),
        Paragraph("KDMARCHÉ, service exploité par PRIMACOP INTERNATIONAL BUSINESS — SIRET 433 230 703 00020", sub),
        Spacer(1, 6),
    ]
    meta = [["Organisation", org_name], ["Exercice", year],
            ["Plafond accordé en vigueur", _eur(ceiling_cents, signed=False)],
            ["Mouvements sur l'exercice", str(len(events))]]
    t = Table(meta, colWidths=[55 * mm, 115 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    el += [t, Paragraph("Synthèse mensuelle des mouvements", h2)]

    monthly = {f"{year}-{m:02d}": {k: 0 for k in TYPE_LABELS} for m in range(1, 13)}
    for e in events:
        mk = str(e["date"] or "")[:7]
        if mk in monthly:
            monthly[mk][e["type"]] = monthly[mk].get(e["type"], 0) + (e["amount_cents"] or 0)
    rows = [["Mois", "Attributions", "Réservations", "Rétablissements", "Avoirs", "Net"]]
    for mk in sorted(monthly):
        tot = monthly[mk]
        net = sum(tot.values())
        rows.append([MONTHS_FR[int(mk[5:]) - 1].capitalize(), _eur(tot["GRANT"]), _eur(tot["RESERVE"]),
                     _eur(tot["RESTORE"]), _eur(tot["CREDIT"]), _eur(net)])
    year_tot = {k: sum(monthly[mk][k] for mk in monthly) for k in TYPE_LABELS}
    rows.append(["TOTAL " + year, _eur(year_tot["GRANT"]), _eur(year_tot["RESERVE"]),
                 _eur(year_tot["RESTORE"]), _eur(year_tot["CREDIT"]), _eur(sum(year_tot.values()))])
    t = Table(rows, colWidths=[26 * mm, 29 * mm, 29 * mm, 31 * mm, 29 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, GOLD),
    ]))
    el += [t, Spacer(1, 10), Paragraph(
        "Réservations = commandes sans acompte confirmées · Rétablissements = paiements encaissés · "
        "Avoirs = réserves instruites en faveur de l'acheteur. Le mouvement net traduit l'évolution du plafond "
        "mobilisé sur l'exercice, conformément aux CGV KDMARCHÉ.", sub)]
    doc.build(el)
    return buf.getvalue()
