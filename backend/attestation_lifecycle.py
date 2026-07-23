"""Cycle de vie des attestations : envoi PDF signé + GEDESS, renouvellement J-30, remboursements RCR."""
import base64
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from attestation_nominative import compute_rcr_ledger, create_attestation_for_product
from attestation_pdf import build_attestation_pdf
from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
lifecycle_router = APIRouter(prefix="/api/attestations", tags=["attestations"])

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


async def _notify_vendor(db, vendor_id: str, ntype: str, title: str, message: str, data: dict = None):
    """Notification in-app (cloche) pour l'utilisateur rattaché au vendeur — best effort."""
    try:
        user = await db.users.find_one({"vendor_id": vendor_id}, {"_id": 0, "id": 1})
        if not user:
            return
        from core_deps import create_notification
        await create_notification(ntype, title, message,
                                  target_roles=["vendor_member"], target_user_id=user["id"], data=data or {})
    except Exception as exc:
        logger.warning("Notification vendeur %s impossible : %s", vendor_id, exc)


# ============== ENVOI EMAIL + ARCHIVAGE GEDESS À LA CONTRE-SIGNATURE ==============

async def send_signed_attestation(db, product_id: str) -> None:
    """Envoie le PDF signé au fournisseur + archive dans la GEDESS (best effort, idempotent)."""
    att = await db.attestations_nominatives.find_one(
        {"product_id": product_id, "status": "signed"}, {"_id": 0}, sort=[("created_at", -1)])
    if not att:
        return
    vendor = await db.vendors.find_one({"id": att["vendor_id"]}, {"_id": 0}) or {}
    pdf = build_attestation_pdf(att)
    if not att.get("notified_signed_at"):
        await _notify_vendor(
            db, att["vendor_id"], "attestation_signed",
            f"Attestation {att['ref']} signée",
            f"Votre attestation « {att.get('product_name')} » a été contre-signée par O'SCOP et KDMARCHÉ PRO. "
            "Elle est désormais active — PDF disponible dans l'onglet Contrats.",
            {"attestation_id": att["id"], "ref": att["ref"]})
        await db.attestations_nominatives.update_one(
            {"id": att["id"]}, {"$set": {"notified_signed_at": datetime.now(timezone.utc).isoformat()}})
    if not att.get("delivered_email_at"):
        try:
            from brevo_service import is_brevo_configured, send_email, _wrap_html
            if is_brevo_configured() and vendor.get("email"):
                body = (
                    f"<p>Bonjour {vendor.get('contact_name') or ''},</p>"
                    f"<p>Votre attestation nominative <strong>{att['ref']}</strong> "
                    f"(produit « {att.get('product_name')} ») a été contre-signée par O'SCOP et KDMARCHÉ PRO. "
                    "Elle est désormais <strong>active</strong>.</p>"
                    "<p>Le document signé est en pièce jointe. Le QR code qu'il contient permet à toute partie "
                    "d'en vérifier l'authenticité en ligne à tout moment.</p>")
                await send_email(
                    to_email=vendor["email"], to_name=vendor.get("contact_name"),
                    subject=f"✓ Attestation {att['ref']} signée par les trois parties",
                    html_content=_wrap_html("Attestation nominative signée", body),
                    tags=["attestation-signee"],
                    attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{att['ref']}.pdf"}])
                await db.attestations_nominatives.update_one(
                    {"id": att["id"]}, {"$set": {"delivered_email_at": datetime.now(timezone.utc).isoformat()}})
                logger.info("Attestation %s envoyée par email à %s", att["ref"], vendor["email"])
        except Exception as exc:
            logger.warning("Envoi email attestation %s impossible : %s", att["ref"], exc)
    if not att.get("ged_doc_id"):
        try:
            from gedess_client import is_gedess_configured, gedess_upload_file
            if is_gedess_configured():
                doc = await gedess_upload_file(
                    filename=f"{att['ref']}.pdf", content=pdf, categorie="rapport",
                    description=f"Attestation nominative signée — {att.get('vendor_name')} / {att.get('product_name')}",
                    tags="attestation-nominative,rcr,fogedom", mime_type="application/pdf")
                await db.attestations_nominatives.update_one(
                    {"id": att["id"]}, {"$set": {"ged_doc_id": doc.get("id")}})
                logger.info("Attestation %s archivée GEDESS (doc %s)", att["ref"], doc.get("id"))
        except Exception as exc:
            logger.warning("Archivage GEDESS attestation %s impossible : %s", att["ref"], exc)


# ============== RENOUVELLEMENT J-30 ==============

async def check_attestation_renewals(db) -> int:
    """Cron : alerte email à J-30 de l'expiration des attestations signées non renouvelées."""
    limit = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    sent = 0
    cursor = db.attestations_nominatives.find(
        {"status": "signed", "date_expiration": {"$lte": limit},
         "next_ref": None, "renewal_alert_sent_at": None}, {"_id": 0, "ai_text": 0})
    async for att in cursor:
        vendor = await db.vendors.find_one({"id": att["vendor_id"]}, {"_id": 0}) or {}
        exp_txt = (att.get("date_expiration") or "")[:10]
        await _notify_vendor(
            db, att["vendor_id"], "attestation_expiring",
            f"Attestation {att['ref']} expire bientôt",
            f"Expiration le {exp_txt} — renouvelez-la en un clic depuis l'onglet Contrats de votre espace vendeur.",
            {"attestation_id": att["id"], "ref": att["ref"], "date_expiration": att.get("date_expiration")})
        try:
            from brevo_service import is_brevo_configured, send_email, _wrap_html
            if is_brevo_configured() and vendor.get("email"):
                base = (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
                exp = (att.get("date_expiration") or "")[:10]
                body = (
                    f"<p>Bonjour {vendor.get('contact_name') or ''},</p>"
                    f"<p>Votre attestation nominative <strong>{att['ref']}</strong> "
                    f"(produit « {att.get('product_name')} ») arrive à expiration le <strong>{exp}</strong>.</p>"
                    "<p>Renouvelez-la <strong>en un clic</strong> depuis votre espace vendeur (onglet Contrats) "
                    "pour maintenir la commercialisation de vos volumes : une nouvelle attestation sera générée "
                    "et soumise à contre-signature.</p>"
                    f"<p style='text-align:center;margin:18px 0'><a href='{base}/espace-vendeur' "
                    "style='background:#D4AF37;color:#1F0A33;padding:11px 22px;border-radius:10px;"
                    "text-decoration:none;font-weight:bold'>Renouveler mon attestation</a></p>")
                await send_email(
                    to_email=vendor["email"], to_name=vendor.get("contact_name"),
                    subject=f"⏳ Attestation {att['ref']} — expiration le {exp}, renouvelez en un clic",
                    html_content=_wrap_html("Renouvellement d'attestation", body),
                    tags=["attestation-renouvellement"])
                sent += 1
        except Exception as exc:
            logger.warning("Alerte renouvellement %s impossible : %s", att["ref"], exc)
        await db.attestations_nominatives.update_one(
            {"id": att["id"]}, {"$set": {"renewal_alert_sent_at": datetime.now(timezone.utc).isoformat()}})
    if sent:
        logger.info("Alertes renouvellement attestation envoyées : %s", sent)
    return sent


@lifecycle_router.post("/{att_id}/renew")
async def renew_attestation(att_id: str, current_user: dict = Depends(get_current_user)):
    """Renouvellement en un clic : nouvelle attestation liée (replaced_ref/next_ref)."""
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0, "ai_text": 0})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    if not current_user.get("is_admin") and current_user.get("vendor_id") != att["vendor_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if att.get("status") != "signed":
        raise HTTPException(status_code=400, detail="Seule une attestation signée peut être renouvelée")
    if att.get("next_ref"):
        raise HTTPException(status_code=409, detail=f"Déjà renouvelée ({att['next_ref']})")
    product = await db.vendor_products.find_one({"id": att["product_id"]}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=409, detail="Produit introuvable — renouvellement impossible")
    vendor = await db.vendors.find_one({"id": att["vendor_id"]}, {"_id": 0})
    new_att = await create_attestation_for_product(db, product, vendor)
    await db.attestations_nominatives.update_one(
        {"id": new_att["id"]}, {"$set": {"replaced_ref": att["ref"]}})
    await db.attestations_nominatives.update_one(
        {"id": att["id"]},
        {"$set": {"next_ref": new_att["ref"], "renewed_at": datetime.now(timezone.utc).isoformat()}})
    logger.info("Attestation %s renouvelée → %s", att["ref"], new_att["ref"])
    return {"success": True, "new_id": new_att["id"], "new_ref": new_att["ref"],
            "message": "Nouvelle attestation générée — en attente de contre-signature O'SCOP / KDMARCHÉ"}


# ============== FILE D'ATTENTE & CONTRE-SIGNATURE GROUPÉE ==============

@lifecycle_router.get("/admin/pending")
async def pending_attestations(current_user: dict = Depends(get_current_user)):
    """File d'attente des attestations en attente de contre-signature."""
    await check_admin(current_user)
    db = get_database()
    pending = await db.attestations_nominatives.find(
        {"status": "pending_countersign"}, {"_id": 0, "ai_text": 0}).sort("created_at", 1).to_list(200)
    return {"pending": pending, "count": len(pending)}


@lifecycle_router.post("/admin/countersign-bulk")
async def countersign_bulk(body: dict, current_user: dict = Depends(get_current_user)):
    """Contre-signe en un clic une sélection d'attestations (O'SCOP + KDMARCHÉ)."""
    await check_admin(current_user)
    db = get_database()
    ids = list(body.get("ids") or [])[:100]
    if not ids:
        raise HTTPException(status_code=400, detail="Aucune attestation sélectionnée")
    import asyncio
    now_iso = datetime.now(timezone.utc).isoformat()
    admin_email = current_user.get("email") or ""
    signed = []
    for att_id in ids:
        att = await db.attestations_nominatives.find_one(
            {"id": att_id, "status": "pending_countersign"}, {"_id": 0, "id": 1, "ref": 1, "product_id": 1})
        if not att:
            continue
        await db.attestations_nominatives.update_one(
            {"id": att_id},
            {"$set": {"status": "signed",
                      "signatures.oscop": {"name": f"O'SCOP ({admin_email})", "at": now_iso},
                      "signatures.kdmarche": {"name": "KDMARCHÉ PRO", "at": now_iso}}})
        asyncio.create_task(send_signed_attestation(db, att["product_id"]))
        signed.append(att["ref"])
    logger.info("Contre-signature groupée : %s attestation(s) par %s", len(signed), admin_email)
    return {"success": True, "count": len(signed), "signed": signed}


# ============== REMBOURSEMENTS RCR (CLÔTURE) ==============

def build_reimbursement_receipt_pdf(r: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=14)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, textColor=colors.grey)
    rows = [
        ["Référence du reçu", r["ref"]],
        ["Date du remboursement", (r.get("created_at") or "")[:10]],
        ["Attestation clôturée", r.get("attestation_ref", "")],
        ["Fournisseur bénéficiaire", r.get("vendor_name", "")],
        ["Produit", r.get("product_name", "")],
        ["Montant RCR remboursé", _eur(r.get("amount_cents"))],
        ["Opérateur d'exécution monétaire", "O'SCOP pour le compte du FOGEDOM-SCIC"],
        ["Validé par", r.get("admin_email", "")],
        ["Note", r.get("note") or "—"],
    ]
    t = Table(rows, colWidths=[70 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (0, -1), BG),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    doc.build([
        Paragraph("REÇU DE REMBOURSEMENT RCR — FOGEDOM-SCIC", h1),
        Paragraph("Restitution de la Retenue Contributive Remboursable à l'expiration de l'Attestation", small),
        Spacer(1, 6 * mm), t, Spacer(1, 6 * mm),
        Paragraph("Le présent reçu atteste du remboursement de la RCR non mobilisée au Fournisseur, bénéficiaire "
                  "économique du solde, conformément à la Convention en vigueur et au règlement de gestion "
                  "FOGEDOM-SCIC. L'attestation nominative correspondante est clôturée et le sous-compte "
                  "FOGEDOM-RCR associé est soldé.", n),
        Spacer(1, 4 * mm),
        Paragraph("Document généré automatiquement par le Dashboard KDMARCHÉ × O'SCOP — "
                  "il fait preuve entre les Parties.", small),
    ])
    return buf.getvalue()


@lifecycle_router.get("/admin/rcr-closures")
async def rcr_closures(current_user: dict = Depends(get_current_user)):
    """Attestations expirées à clôturer + historique des remboursements."""
    await check_admin(current_user)
    db = get_database()
    now_iso = datetime.now(timezone.utc).isoformat()
    expired = []
    async for att in db.attestations_nominatives.find(
            {"status": "signed", "date_expiration": {"$lte": now_iso}}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        expired.append({"id": att["id"], "ref": att["ref"], "vendor_name": att.get("vendor_name"),
                        "product_name": att.get("product_name"),
                        "date_expiration": att.get("date_expiration"),
                        "solde_cents": ledger["solde_cents"],
                        "remboursement_prevu": ledger["remboursement_prevu"]})
    reimbursements = await db.rcr_reimbursements.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"expired": expired, "reimbursements": reimbursements}


@lifecycle_router.post("/{att_id}/reimburse")
async def reimburse_attestation(att_id: str, body: dict = None,
                                current_user: dict = Depends(get_current_user)):
    """Enregistre le remboursement RCR et clôture l'attestation (admin)."""
    await check_admin(current_user)
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0, "ai_text": 0})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    if att.get("status") == "closed":
        raise HTTPException(status_code=409, detail="Attestation déjà clôturée")
    if att.get("status") != "signed":
        raise HTTPException(status_code=400, detail="Seule une attestation signée peut être clôturée")
    ledger = await compute_rcr_ledger(db, att)
    body = body or {}
    amount = int(body.get("amount_cents") if body.get("amount_cents") is not None else ledger["solde_cents"])
    if amount < 0:
        raise HTTPException(status_code=400, detail="Montant invalide")
    seq = await db.rcr_reimbursements.count_documents({}) + 1
    now_iso = datetime.now(timezone.utc).isoformat()
    r = {"id": str(uuid.uuid4()), "ref": f"RBT-{datetime.utcnow().strftime('%Y%m%d')}-{seq:03d}",
         "attestation_id": att["id"], "attestation_ref": att["ref"],
         "vendor_id": att["vendor_id"], "vendor_name": att.get("vendor_name"),
         "product_name": att.get("product_name"),
         "amount_cents": amount, "note": str(body.get("note") or "")[:500],
         "admin_email": current_user.get("email"), "created_at": now_iso}
    await db.rcr_reimbursements.insert_one({**r})
    await db.attestations_nominatives.update_one(
        {"id": att["id"]},
        {"$set": {"status": "closed", "reimbursed_at": now_iso, "reimbursement_id": r["id"]}})
    await _notify_vendor(
        db, att["vendor_id"], "rcr_reimbursed",
        f"RCR remboursée — {_eur(amount)}",
        f"La RCR de votre attestation {att['ref']} vous a été remboursée par le FOGEDOM-SCIC. "
        "L'attestation est clôturée — reçu disponible dans l'onglet Contrats.",
        {"attestation_id": att["id"], "ref": att["ref"], "reimbursement_id": r["id"], "amount_cents": amount})
    try:
        from brevo_service import is_brevo_configured, send_email, _wrap_html
        vendor = await db.vendors.find_one({"id": att["vendor_id"]}, {"_id": 0}) or {}
        if is_brevo_configured() and vendor.get("email"):
            pdf = build_reimbursement_receipt_pdf(r)
            body_html = (
                f"<p>Bonjour {vendor.get('contact_name') or ''},</p>"
                f"<p>La RCR constituée sur votre attestation <strong>{att['ref']}</strong> vous a été "
                f"remboursée par le FOGEDOM-SCIC : <strong>{_eur(amount)}</strong>.</p>"
                "<p>L'attestation est désormais clôturée. Votre reçu est en pièce jointe.</p>")
            await send_email(
                to_email=vendor["email"], to_name=vendor.get("contact_name"),
                subject=f"✓ Remboursement RCR {_eur(amount)} — attestation {att['ref']} clôturée",
                html_content=_wrap_html("Remboursement RCR — FOGEDOM-SCIC", body_html),
                tags=["rcr-remboursement"],
                attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"{r['ref']}.pdf"}])
    except Exception as exc:
        logger.warning("Email reçu remboursement %s impossible : %s", r["ref"], exc)
    logger.info("Remboursement RCR %s (%s c) — attestation %s clôturée", r["ref"], amount, att["ref"])
    return {"success": True, "reimbursement": r}


@lifecycle_router.get("/{att_id}/ged-info")
async def attestation_ged_info(att_id: str, current_user: dict = Depends(get_current_user)):
    """Métadonnées live du document GEDESS archivé pour cette attestation (admin)."""
    await check_admin(current_user)
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0, "ged_doc_id": 1, "ref": 1})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    if not att.get("ged_doc_id"):
        return {"archived": False}
    import os as _os
    import httpx
    from gedess_client import is_gedess_configured, _login
    if not is_gedess_configured():
        return {"archived": True, "doc_id": att["ged_doc_id"], "live": False}
    base = _os.environ["GEDESS_BASE_URL"].rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token = await _login(client, base)
            resp = await client.get(f"{base}/api/ged/documents/{att['ged_doc_id']}",
                                    headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            doc = resp.json()
        return {"archived": True, "live": True, "doc_id": att["ged_doc_id"], "gedess_url": base,
                "document": {"original_filename": doc.get("original_filename"),
                             "file_size": doc.get("file_size"), "categorie": doc.get("categorie"),
                             "description": doc.get("description"), "created_at": doc.get("created_at"),
                             "tags": doc.get("tags")}}
    except Exception as exc:
        logger.warning("GEDESS info %s : %s", att["ged_doc_id"], exc)
        return {"archived": True, "live": False, "doc_id": att["ged_doc_id"], "gedess_url": base}


@lifecycle_router.get("/reimbursements/{rid}/receipt.pdf")
async def reimbursement_receipt(rid: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    r = await db.rcr_reimbursements.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Remboursement introuvable")
    if not current_user.get("is_admin") and current_user.get("vendor_id") != r["vendor_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    pdf = build_reimbursement_receipt_pdf(r)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={r['ref']}.pdf"})
