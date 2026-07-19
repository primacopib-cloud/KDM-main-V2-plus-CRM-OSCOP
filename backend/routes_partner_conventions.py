"""Conventions de partenariat (COOPER'S, EXPERTS, Partenaires) — rédaction admin, signature électronique par lien email."""
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

partner_conventions_router = APIRouter(prefix="/api", tags=["partner-conventions"])

db = None
PARTNER_TYPES = ["COOPER", "EXPERT", "PARTNER"]
STATUSES = ["DRAFT", "SENT", "SIGNED", "ACTIVE", "SUSPENDED"]


def set_partner_conventions_database(database):
    global db
    db = database


class ConventionBody(BaseModel):
    title: str
    partner_type: str = "PARTNER"
    partner_name: str
    partner_email: str
    content: str


def build_partner_convention_pdf(conv: dict) -> bytes:
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    violet = colors.HexColor("#451F6B")
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14, textColor=violet, spaceAfter=6)
    st = ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, leading=14)
    small = ParagraphStyle("s", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#6b5a7a"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    el = [Paragraph(conv["title"], h1),
          Paragraph(f"Convention de partenariat {conv['partner_type']} — O'SCOP Outremer × {conv['partner_name']}"
                    f" · Réf. {conv['id'][:8].upper()}", small),
          Spacer(1, 8)]
    for para in (conv.get("content") or "").split("\n"):
        if para.strip():
            el.append(Paragraph(para.strip().replace("&", "&amp;").replace("<", "&lt;"), st))
            el.append(Spacer(1, 4))
    sig = conv.get("signature")
    if sig:
        el += [Spacer(1, 12), Paragraph("Signature électronique", h1),
               Paragraph(f"Signé par : {sig.get('nom')} — {sig.get('qualite')}<br/>"
                         f"Le : {sig.get('signed_at', '')[:19]} UTC · Code de vérification : {sig.get('verification_code')}"
                         f" · Mention « Lu et approuvé » acceptée électroniquement", st),
               Spacer(1, 6),
               Paragraph("Signature électronique conforme aux articles 1366 et 1367 du Code civil.", small)]
    doc.build(el)
    return buf.getvalue()


@partner_conventions_router.get("/admin/partner-conventions")
async def list_conventions(admin: dict = Depends(require_admin)):
    items = await db.partner_conventions.find({}, {"_id": 0, "sign_token": 0}).sort("created_at", -1).limit(200).to_list(200)
    stats = {"COOPER": 0, "EXPERT": 0, "PARTNER": 0, "pending": 0, "suspended": 0}
    for c in items:
        if c["status"] == "ACTIVE":
            stats[c["partner_type"]] = stats.get(c["partner_type"], 0) + 1
        if c["status"] == "SENT":
            stats["pending"] += 1
        if c["status"] == "SUSPENDED":
            stats["suspended"] += 1
    return {"items": items, "stats": stats}


@partner_conventions_router.post("/admin/partner-conventions")
async def create_convention(body: ConventionBody, admin: dict = Depends(require_admin)):
    if body.partner_type not in PARTNER_TYPES:
        raise HTTPException(status_code=400, detail="Type de partenaire invalide")
    doc = {**body.dict(), "id": str(uuid.uuid4()), "status": "DRAFT",
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.partner_conventions.insert_one({**doc})
    return doc


@partner_conventions_router.put("/admin/partner-conventions/{cid}")
async def update_convention(cid: str, body: dict, admin: dict = Depends(require_admin)):
    allowed = {k: v for k, v in body.items()
               if k in ("title", "partner_type", "partner_name", "partner_email", "content", "status")}
    if "status" in allowed and allowed["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    r = await db.partner_conventions.update_one({"id": cid}, {"$set": allowed})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Convention introuvable")
    return {"ok": True}


@partner_conventions_router.delete("/admin/partner-conventions/{cid}")
async def delete_convention(cid: str, admin: dict = Depends(require_admin)):
    conv = await db.partner_conventions.find_one({"id": cid}, {"_id": 0})
    if conv and conv.get("status") in ("SIGNED", "ACTIVE"):
        raise HTTPException(status_code=400, detail="Convention signée : suspendez-la plutôt que de la supprimer")
    await db.partner_conventions.delete_one({"id": cid})
    return {"deleted": True}


@partner_conventions_router.post("/admin/partner-conventions/{cid}/send")
async def send_convention(cid: str, admin: dict = Depends(require_admin)):
    import os
    conv = await db.partner_conventions.find_one({"id": cid}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Convention introuvable")
    token = secrets.token_urlsafe(32)
    await db.partner_conventions.update_one({"id": cid}, {"$set": {
        "status": "SENT", "sign_token": token, "sent_at": datetime.now(timezone.utc).isoformat()}})
    link = f"{os.environ.get('FRONTEND_PUBLIC_URL', '')}/signature-partenariat?token={token}"
    from brevo_service import send_email
    await send_email(
        to_email=conv["partner_email"], to_name=conv["partner_name"],
        subject=f"Convention de partenariat à signer — {conv['title']}",
        html_content=f"""<h2 style="color:#451F6B;">Convention de partenariat</h2>
        <p>Bonjour {conv['partner_name']},</p>
        <p>O'SCOP Outremer vous invite à relire et signer électroniquement la convention
        <strong>{conv['title']}</strong>.</p>
        <p style="margin:24px 0;"><a href="{link}" style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Relire et signer la convention</a></p>""",
        tags=["partner-convention"])
    return {"sent": True}


@partner_conventions_router.get("/partner-conventions/by-token/{token}")
async def convention_by_token(token: str):
    conv = await db.partner_conventions.find_one({"sign_token": token}, {"_id": 0, "sign_token": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Lien de signature invalide ou expiré")
    return conv


class SignBody(BaseModel):
    nom: str
    qualite: str
    lu_approuve: bool = False


@partner_conventions_router.post("/partner-conventions/by-token/{token}/sign")
async def sign_convention(token: str, body: SignBody):
    conv = await db.partner_conventions.find_one({"sign_token": token}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Lien de signature invalide")
    if conv["status"] in ("SIGNED", "ACTIVE"):
        raise HTTPException(status_code=400, detail="Convention déjà signée")
    if not body.lu_approuve or not body.nom.strip() or not body.qualite.strip():
        raise HTTPException(status_code=400, detail="Signature incomplète (« Lu et approuvé » requis)")
    code = f"PART-{conv['id'][:6].upper()}-{secrets.token_hex(3).upper()}"
    signature = {"nom": body.nom.strip(), "qualite": body.qualite.strip(),
                 "verification_code": code, "signed_at": datetime.now(timezone.utc).isoformat()}
    await db.partner_conventions.update_one({"sign_token": token}, {"$set": {
        "status": "SIGNED", "signature": signature, "signed_at": signature["signed_at"]}})
    try:
        from gedess_client import is_gedess_configured, gedess_upload_file
        if is_gedess_configured():
            pdf = build_partner_convention_pdf({**conv, "signature": signature})
            await gedess_upload_file(filename=f"convention-partenariat-{conv['id'][:8]}.pdf",
                                     content=pdf, categorie="conventions_partenariat",
                                     description=f"Convention {conv['partner_type']} — {conv['partner_name']}",
                                     mime_type="application/pdf")
    except Exception as exc:
        logger.warning("Archivage GED convention partenariat %s : %s", conv["id"], exc)
    return {"signed": True, "verification_code": code}


@partner_conventions_router.get("/admin/partner-conventions/{cid}/pdf")
async def convention_pdf(cid: str, admin: dict = Depends(require_admin)):
    conv = await db.partner_conventions.find_one({"id": cid}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Convention introuvable")
    return Response(content=build_partner_convention_pdf(conv), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="convention-{cid[:8]}.pdf"'})
