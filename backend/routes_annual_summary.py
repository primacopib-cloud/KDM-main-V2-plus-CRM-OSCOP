"""Récapitulatif annuel des transactions (art. 242 bis CGI / CGU art. 8) — PDF par vendeur, superadmin."""
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

logger = logging.getLogger(__name__)
annual_summary_router = APIRouter(prefix="/api/admin", tags=["Récapitulatif annuel"])
db = None

VIOLET = colors.HexColor("#451F6B")
_T = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=12.5, textColor=colors.HexColor("#2A1045"), leading=16, alignment=1, spaceAfter=2)
_T2 = ParagraphStyle("t2", fontName="Helvetica-Bold", fontSize=9.5, textColor=VIOLET, alignment=1, spaceAfter=10)
_B = ParagraphStyle("b", fontName="Helvetica", fontSize=8.8, textColor=colors.HexColor("#2a2233"), leading=12.5, spaceAfter=4)
_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10, textColor=VIOLET, spaceBefore=9, spaceAfter=3)
_META = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=7.4, textColor=colors.HexColor("#6b5a7a"), spaceBefore=8)

ORDER_OK = ["CONFIRMED", "PICKED_UP", "DELIVERED"]


def set_annual_summary_database(database):
    global db
    db = database


def _eur(cents_or_eur: float, is_cents=True) -> str:
    v = (cents_or_eur / 100) if is_cents else cents_or_eur
    return f"{v:,.2f}".replace(",", " ").replace(".", ",") + " €"


async def _aggregate(year: int) -> list[dict]:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    rows = []
    # Circuit partenaire directe (KDMARCHE) — commandes marchandises confirmées
    n, tot = 0, 0
    async for o in db.orders.find({"status": {"$in": ORDER_OK},
                                   "created_at": {"$gte": start.replace(tzinfo=None), "$lt": end.replace(tzinfo=None)}},
                                  {"_id": 0, "total_ttc_cents": 1, "subtotal_ht_cents": 1}):
        n += 1
        tot += o.get("total_ttc_cents") or o.get("subtotal_ht_cents") or 0
    rows.append({"seller": "KDMARCHÉ (PRIMACOP INTERNATIONAL BUSINESS) — circuit partenaire directe",
                 "count": n, "gross": _eur(tot)})
    # Circuit achat-revente O'SCOP — opérations financées payées
    n2, tot2 = 0, 0.0
    async for fp in db.financing_products.find({"status": {"$in": ["PAID", "REPAID"]}}, {"_id": 0, "paid_at": 1, "total_price_eur": 1}):
        pa = fp.get("paid_at")
        if pa and str(pa)[:4] == str(year):
            n2 += 1
            tot2 += float(fp.get("total_price_eur") or 0)
    rows.append({"seller": "O'SCOP — circuit achat-revente « Vendu et facturé par O'SCOP »",
                 "count": n2, "gross": _eur(tot2, is_cents=False)})
    return rows


@annual_summary_router.get("/annual-transactions-summary/{year}.pdf")
async def annual_summary_pdf(year: int, admin: dict = Depends(require_admin)):
    if year < 2020 or year > 2100:
        raise HTTPException(status_code=400, detail="Année invalide")
    rows = await _aggregate(year)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm, leftMargin=17 * mm, rightMargin=17 * mm)
    table_rows = [["Vendeur", "Nombre de transactions", "Montant brut"]]
    for r in rows:
        table_rows.append([Paragraph(r["seller"], _B), str(r["count"]), r["gross"]])
    t = Table(table_rows, colWidths=[100 * mm, 35 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efe6f8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el = [
        Paragraph(f"RÉCAPITULATIF ANNUEL DES TRANSACTIONS — ANNÉE {year}", _T),
        Paragraph("Article 242 bis du Code général des impôts — CGU CommunityPlace, article 8", _T2),
        Paragraph("Conformément à l'article 242 bis du Code général des impôts et à l'article 8 des CGU de la plateforme "
                  "CommunityPlace, l'Opérateur (SCIC SAS OBJECTIF SCOP OUTREMER, SIREN 903 459 139) met à disposition de "
                  "chaque Vendeur, avant le 31 janvier, le document récapitulant le nombre et le montant brut des transactions "
                  "réalisées par son intermédiaire au cours de l'année précédente.", _B),
        Spacer(1, 6),
        Paragraph("Synthèse par vendeur", _H),
        t,
        Paragraph("Les Vendeurs professionnels demeurent seuls responsables du calcul, de la déclaration et du paiement de la "
                  "TVA (taux applicables dans les territoires d'Outre-mer), de l'impôt et des cotisations sociales afférents "
                  "à leurs ventes (CGU, article 8).", _META),
        Paragraph(f"Document généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC par "
                  "SCIC SAS OBJECTIF SCOP OUTREMER — 13 rue Rodrigue Youyoute, 97139 Les Abymes.", _META),
    ]
    doc.build(el)
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="recapitulatif-transactions-{year}.pdf"'})
