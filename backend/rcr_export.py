"""Export CSV / PDF du registre analytique FOGEDOM-RCR pour les comités de double validation."""
import csv
from datetime import datetime
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from convention_settings import build_rcr_registry, get_convention_settings
from core_deps import get_current_user, check_admin
from db import get_database

rcr_export_router = APIRouter(prefix="/api/convention", tags=["convention"])

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


@rcr_export_router.get("/admin/registres/export.csv")
async def export_registres_csv(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    reg = await build_rcr_registry(get_database())
    out = StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["Fournisseur", "Attestations", "Montant agrégé HT (EUR)", "Plafond-cible RCR (EUR)",
                "Plafond appliqué (EUR)", "Cap global atteint"])
    for v in reg["registre_rcr"]:
        w.writerow([v.get("vendor_name") or v["vendor_id"], v["attestations"],
                    f"{v['montant_agrege_cents'] / 100:.2f}".replace(".", ","),
                    f"{v['plafond_cible_cents'] / 100:.2f}".replace(".", ","),
                    f"{v.get('plafond_applique_cents', 0) / 100:.2f}".replace(".", ","),
                    "OUI" if v.get("cap_reached") else "NON"])
    t = reg["totaux"]
    w.writerow([])
    w.writerow(["TOTAUX", t["attestations"], "",
                f"{t['plafond_cible_total_cents'] / 100:.2f}".replace(".", ","),
                f"{t['retenues_effectives_cents'] / 100:.2f}".replace(".", ","),
                f"Cap global : {t['rcr_global_cap_eur']:.0f} EUR / fournisseur"])
    return Response(
        content="\ufeff" + out.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=registre-fogedom-rcr-{datetime.now().strftime('%Y%m%d')}.csv"})


@rcr_export_router.get("/admin/registres/export.pdf")
async def export_registres_pdf(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    reg = await build_rcr_registry(db)
    settings = await get_convention_settings(db)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=13, leading=17)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10.5, spaceBefore=8)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=8.5, leading=12)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    t = reg["totaux"]
    rows = [["Fournisseur", "Attestations", "Montant agrégé HT", "Plafond-cible RCR", "Plafond appliqué", "Cap global"]]
    for v in reg["registre_rcr"]:
        rows.append([v.get("vendor_name") or v["vendor_id"], str(v["attestations"]),
                     _eur(v["montant_agrege_cents"]), _eur(v["plafond_cible_cents"]),
                     _eur(v.get("plafond_applique_cents")), "ATTEINT" if v.get("cap_reached") else "OK"])
    rows.append(["TOTAUX", str(t["attestations"]), "", _eur(t["plafond_cible_total_cents"]),
                 _eur(t["retenues_effectives_cents"]), ""])
    table = Table(rows, colWidths=[80 * mm, 25 * mm, 40 * mm, 40 * mm, 40 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BG),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    sig = Table([["VALIDATEUR 1 — Comité FOGEDOM-RCR", "VALIDATEUR 2 — Comité FOGEDOM-RCR"],
                 ["Nom / qualité :\nDate :\nSignature :", "Nom / qualité :\nDate :\nSignature :"]],
                colWidths=[125 * mm, 125 * mm])
    sig.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 26)]))
    doc.build([
        Paragraph("REGISTRE ANALYTIQUE FOGEDOM-RCR — CONSOLIDATION PAR FOURNISSEUR", h1),
        Paragraph("Document de travail du Comité FOGEDOM-RCR — soumis à double validation", small),
        Paragraph(f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — "
                  f"{t['conventions']} convention(s) cadre · {t['attestations']} attestation(s) nominative(s) · "
                  f"Cap global : {t['rcr_global_cap_eur']:,.0f} € / fournisseur · "
                  f"Taux RCR défaut : {settings['rcr_default_rate']:.2f} %".replace(",", " "), n),
        Spacer(1, 4 * mm), table,
        Spacer(1, 3 * mm),
        Paragraph("Le plafond appliqué correspond au minimum entre le plafond-cible consolidé du fournisseur et le "
                  "cap global. Les retenues effectives correspondent aux fractions RCR constituées sur les contrats "
                  "d'engagement de volume en cours.", small),
        Paragraph("DOUBLE VALIDATION DU COMITÉ FOGEDOM-RCR", h2),
        Paragraph("Conformément au règlement de gestion FOGEDOM-SCIC, la présente consolidation est soumise à la "
                  "double validation des membres délégués du Comité FOGEDOM-RCR.", n),
        Spacer(1, 2 * mm), sig,
    ])
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=registre-fogedom-rcr-{datetime.now().strftime('%Y%m%d')}.pdf"})
