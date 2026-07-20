"""Export comptable des revenus CREDI'SCOP (packs, abonnements, consommations) — CSV et PDF."""
import csv
import logging
from datetime import datetime, timezone
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

cpc_export_router = APIRouter(prefix="/api/admin/cpc", tags=["cpc-export"])

db = None


def set_cpc_export_database(database):
    global db
    db = database


async def _collect_rows(month: str = None):
    """Lignes d'export : ventes de packs (€), factures d'abonnements (€), consommations (unités)."""
    rows = []
    q_month = {"created_at": {"$regex": f"^{month}"}} if month else {}
    async for p in db.cpc_purchases.find({"status": "SETTLED", "ttc_cents": {"$gt": 0}, **q_month},
                                         {"_id": 0}).sort("created_at", 1):
        rows.append(["PACK", str(p.get("settled_at") or p.get("created_at"))[:10], p.get("email", ""),
                     p.get("pack_label", ""), p.get("credits", 0),
                     f"{p.get('price_ht_cents', 0) / 100:.2f}", f"{p.get('vat_cents', 0) / 100:.2f}",
                     f"{p.get('ttc_cents', 0) / 100:.2f}"])
    subs = {s["user_id"]: s async for s in db.cpc_subscriptions.find({}, {"_id": 0}).sort("created_at", 1)}
    async for p in db.cpc_purchases.find({"stripe_invoice_id": {"$ne": None}, **q_month},
                                         {"_id": 0}).sort("created_at", 1):
        sub = subs.get(p.get("user_id"), {})
        ttc = sub.get("ttc_cents", 0)
        ht = sub.get("price_ht_cents", 0)
        rows.append(["ABONNEMENT", str(p.get("created_at"))[:10], p.get("email") or sub.get("email", ""),
                     p.get("pack_label", ""), p.get("credits", 0),
                     f"{ht / 100:.2f}", f"{(ttc - ht) / 100:.2f}", f"{ttc / 100:.2f}"])
    q_led = {"created_at": {"$regex": f"^{month}"}} if month else {}
    async for m in db.cpc_ledger.find({"qty": {"$lt": 0}, "type": {"$in": ["CONSULTATION_ENTRY", "REPORT_PURCHASE"]},
                                       **q_led}, {"_id": 0}).sort("created_at", 1):
        u = await db.users.find_one({"id": m["user_id"]}, {"_id": 0, "email": 1})
        rows.append(["CONSOMMATION", str(m.get("created_at"))[:10], (u or {}).get("email", m["user_id"]),
                     m.get("reason") or m.get("type"), m.get("qty", 0), "", "", ""])
    return rows


HEADERS = ["Type", "Date", "Compte", "Libellé", "Crédits", "HT (€)", "TVA (€)", "TTC (€)"]


@cpc_export_router.get("/export.csv")
async def export_csv(month: str = None, admin: dict = Depends(require_admin)):
    rows = await _collect_rows(month)
    buf = StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(HEADERS)
    w.writerows(rows)
    fname = f"crediscop-compta-{month or 'complet'}.csv"
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@cpc_export_router.get("/export.pdf")
async def export_pdf(month: str = None, admin: dict = Depends(require_admin)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    rows = await _collect_rows(month)
    total_ttc = sum(float(r[7]) for r in rows if r[7])
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=14 * mm, bottomMargin=12 * mm,
                            leftMargin=12 * mm, rightMargin=12 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=colors.HexColor("#1F2A3A"), fontSize=16)
    elements = [
        Paragraph("EXPORT COMPTABLE CREDI'SCOP — Services numériques O'SCOP", title),
        Paragraph(f"Période : {month or 'intégralité'} — Édité le {datetime.now(timezone.utc).isoformat()[:10]} — "
                  f"{len(rows)} ligne(s) — Total encaissé TTC : {total_ttc:.2f} €", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]
    data = [HEADERS] + [[str(c)[:46] for c in r] for r in rows[:400]]
    t = Table(data, colWidths=[26 * mm, 20 * mm, 52 * mm, 88 * mm, 16 * mm, 20 * mm, 20 * mm, 20 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2A3A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F2E9")]),
    ]))
    elements.append(t)
    doc.build(elements)
    fname = f"crediscop-compta-{month or 'complet'}.pdf"
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
