"""Rapport mensuel de conformité (PDF) : emails, garanties vendeur, adhésions."""
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from admin_plans_common import get_current_admin_from_request

compliance_router = APIRouter(prefix="/api/admin/compliance-report")

db = None

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")
GOLD = colors.HexColor("#D4AF37")

_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=17, textColor=VIOLET_DARK, spaceAfter=4)
_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#6b5a7a"), spaceAfter=10)
_H2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12.5, textColor=VIOLET, spaceBefore=14, spaceAfter=6)
_BODY = ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#2a2233"))


def set_compliance_database(database):
    global db
    db = database


def _table(rows, widths):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VIOLET),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4eefa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


async def build_compliance_report_pdf(month: str) -> bytes:
    prefix = {"$regex": f"^{re.escape(month)}"}

    # 1. Emails
    email_total = await db.email_logs.count_documents({"sent_at": prefix})
    by_tag = {}
    async for r in db.email_logs.aggregate([
        {"$match": {"sent_at": prefix}}, {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 12},
    ]):
        by_tag[r["_id"]] = r["n"]

    # 2. Garanties vendeur
    contracts = await db.vendor_contracts.find({}, {"_id": 0}).to_list(500)
    active = [c for c in contracts if c.get("status") in ("ACTIVE", "SIGNED", None)]
    total_retained = sum(c.get("total_guarantee_retained", 0) for c in contracts)

    # 3. Adhésions / registre
    memberships_month = await db.org_memberships.count_documents({"created_at": prefix})
    orgs_total = await db.orgs.count_documents({})
    suspended = await db.orgs.count_documents({"status": "SUSPENDED"})
    radiated = await db.orgs.count_documents({"status": "RADIATED"})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm)
    el = [
        Paragraph("Rapport mensuel de conformité", _TITLE),
        Paragraph(f"Communityplace — KDMARCHÉ × O'SCOP · Période : {month} · "
                  f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", _SUB),
        Paragraph("1. Emails transactionnels", _H2),
        Paragraph(f"Total d'envois journalisés sur la période : <b>{email_total}</b>", _BODY),
        Spacer(1, 4),
    ]
    if by_tag:
        el.append(_table([["Type d'email (tag)", "Envois"]] + [[k, str(v)] for k, v in by_tag.items()],
                         [110 * mm, 30 * mm]))
    el += [
        Paragraph("2. Garanties vendeur (rétention 5%)", _H2),
        _table([
            ["Indicateur", "Valeur"],
            ["Contrats d'engagement (total)", str(len(contracts))],
            ["Contrats actifs", str(len(active))],
            ["Garanties totales retenues", f"{total_retained / 100:.2f} €" if total_retained > 1000 else f"{total_retained:.2f} €"],
        ], [110 * mm, 40 * mm]),
        Paragraph("3. Adhésions & registre des membres", _H2),
        _table([
            ["Indicateur", "Valeur"],
            [f"Nouvelles adhésions ({month})", str(memberships_month)],
            ["Organisations enregistrées (total)", str(orgs_total)],
            ["Membres suspendus", str(suspended)],
            ["Membres radiés", str(radiated)],
        ], [110 * mm, 40 * mm]),
        Spacer(1, 12),
        Paragraph("Document généré automatiquement — destiné aux instances de la coopérative (CA, AG, commissions).", _SUB),
    ]
    doc.build(el)
    return buf.getvalue()


async def archive_compliance_report_to_ged(database, month: str, force: bool = False) -> dict:
    """Archive le rapport de conformité PDF du mois dans la GEDESS (idempotent par mois)."""
    global db
    if db is None:
        db = database
    existing = await db.compliance_archive_runs.find_one({"month": month, "status": "SUCCESS"})
    if existing and not force:
        return {"status": "ALREADY_ARCHIVED", "month": month}
    from gedess_client import is_gedess_configured, gedess_upload_file
    if not is_gedess_configured():
        return {"status": "GED_DISABLED", "month": month}
    pdf = await build_compliance_report_pdf(month)
    run = {"month": month, "archived_at": datetime.now(timezone.utc).isoformat()}
    try:
        doc = await gedess_upload_file(
            filename=f"rapport-conformite-{month}.pdf",
            content=pdf,
            categorie="rapport",
            description=f"Rapport mensuel de conformité Communityplace (emails, garanties, adhésions) — période {month}.",
            tags="communityplace,conformite,rapport-mensuel,archive-automatique",
            mime_type="application/pdf",
        )
        run.update({"status": "SUCCESS", "ged_document_id": doc.get("id"), "ged_filename": doc.get("original_filename")})
    except Exception as exc:
        run.update({"status": "ERROR", "error": str(exc)})
    await db.compliance_archive_runs.update_one({"month": month}, {"$set": run}, upsert=True)
    return run


@compliance_router.get("/archive-ged/runs")
async def list_compliance_archive_runs(request: Request):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    runs = await db.compliance_archive_runs.find({}, {"_id": 0}).sort("month", -1).to_list(36)
    return {"runs": runs, "total": len(runs)}


@compliance_router.post("/archive-ged")
async def archive_compliance_to_ged(request: Request):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    month = (body.get("month") or datetime.now(timezone.utc).strftime("%Y-%m")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="Format de mois invalide (attendu YYYY-MM)")
    return await archive_compliance_report_to_ged(db, month, force=bool(body.get("force")))


@compliance_router.get("/{month}.pdf")
async def download_compliance_report(request: Request, month: str):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="Format de mois invalide (attendu YYYY-MM)")
    pdf = await build_compliance_report_pdf(month)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport-conformite-{month}.pdf"'},
    )
