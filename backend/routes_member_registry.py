"""Registres des membres Acheteurs pro / Vendeurs pro (Super Admin & Admin)."""
import io
import csv
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth import get_current_user_id
from admin_guard import require_admin

registry_router = APIRouter(prefix="/api/v2/admin", tags=["Registres membres"])

db = None


def set_registry_database(database) -> None:
    global db
    db = database


TYPE_LABELS = {"BUYER_PRO": "Acheteurs pro", "VENDOR_PRO": "Vendeurs pro"}
MEMBER_STATUSES = {"ACTIVE", "SUSPENDED", "RADIE"}


@registry_router.get("/member-registry")
async def list_member_registry(
    member_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    await require_admin(user_id)
    query = {}
    if member_type in ("BUYER_PRO", "VENDOR_PRO"):
        query["member_type"] = member_type
    members = await db.member_registry.find(query, {"_id": 0}).sort("registered_at", -1).to_list(500)
    counts = {
        "BUYER_PRO": await db.member_registry.count_documents({"member_type": "BUYER_PRO"}),
        "VENDOR_PRO": await db.member_registry.count_documents({"member_type": "VENDOR_PRO"}),
    }
    return {"members": members, "counts": counts}


class MemberStatusUpdate(BaseModel):
    status: str
    reason: str = Field(..., min_length=3, max_length=1000)


@registry_router.patch("/member-registry/{org_id}/status")
async def update_member_status(
    org_id: str,
    update: MemberStatusUpdate,
    user_id: str = Depends(get_current_user_id),
):
    """Suspendre / radier / réactiver un membre avec motif + historique."""
    admin = await require_admin(user_id)
    if update.status not in MEMBER_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide (ACTIVE, SUSPENDED, RADIE)")
    entry = {
        "action": update.status,
        "reason": update.reason.strip(),
        "by": admin.get("email"),
        "at": datetime.utcnow(),
    }
    res = await db.member_registry.update_one(
        {"org_id": org_id},
        {"$set": {"status": update.status, "updated_at": datetime.utcnow()}, "$push": {"history": entry}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membre introuvable au registre")
    return {"ok": True, "status": update.status}


@registry_router.get("/member-registry/extract/{siret}")
async def get_member_extract(siret: str, user_id: str = Depends(get_current_user_id)):
    """Extrait d'immatriculation PDF du membre (généré à la demande si absent)."""
    await require_admin(user_id)
    from company_extract import get_or_generate_extract
    pdf_bytes, filename, meta = await get_or_generate_extract(db, siret)
    if pdf_bytes is None:
        detail = "Entreprise introuvable dans la base officielle (SIRET inconnu)" \
            if meta.get("status") == "NOT_FOUND" else (meta.get("error") or "Extrait indisponible")
        raise HTTPException(status_code=404, detail=detail)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="{filename}"'})


@registry_router.get("/member-registry/export")
async def export_member_registry(
    member_type: str = "BUYER_PRO",
    format: str = "csv",
    user_id: str = Depends(get_current_user_id),
):
    """Export CSV ou PDF du registre pour les assemblées de la coopérative."""
    await require_admin(user_id)
    if member_type not in TYPE_LABELS:
        raise HTTPException(status_code=400, detail="member_type invalide")
    members = await db.member_registry.find(
        {"member_type": member_type}, {"_id": 0}
    ).sort("registered_at", 1).to_list(2000)
    label = TYPE_LABELS[member_type]
    date_str = datetime.utcnow().strftime("%d/%m/%Y")
    filename = f"registre-{label.replace(' ', '-').lower()}-{datetime.utcnow().strftime('%Y%m%d')}"

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow(["Raison sociale", "SIRET", "Territoire", "Contact", "Email", "Téléphone", "Inscrit le", "Statut"])
        for m in members:
            writer.writerow([
                m.get("legal_name") or "", m.get("siret") or "", m.get("territory") or "",
                m.get("contact_name") or "", m.get("contact_email") or "", m.get("contact_phone") or "",
                m["registered_at"].strftime("%d/%m/%Y") if m.get("registered_at") else "",
                m.get("status") or "ACTIVE",
            ])
        data = ("\ufeff" + buf.getvalue()).encode("utf-8")
        return StreamingResponse(io.BytesIO(data), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'})

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<b>Registre des membres — {label}</b>", styles["Title"]),
        Paragraph(f"Coopérative Communityplace / KDMARCHÉ × O'SCOP — édité le {date_str} — {len(members)} membre(s)", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]
    rows = [["Raison sociale", "SIRET", "Territoire", "Contact", "Email", "Inscrit le", "Statut"]]
    for m in members:
        rows.append([
            m.get("legal_name") or "", m.get("siret") or "", m.get("territory") or "",
            m.get("contact_name") or "", m.get("contact_email") or "",
            m["registered_at"].strftime("%d/%m/%Y") if m.get("registered_at") else "",
            m.get("status") or "ACTIVE",
        ])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C2A6E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9B35A")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBF6EC")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)
    pdf_buf.seek(0)
    return StreamingResponse(pdf_buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})
