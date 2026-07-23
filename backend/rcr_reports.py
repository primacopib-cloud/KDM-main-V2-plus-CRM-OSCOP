"""Relevés RCR mensuels (email PDF au fournisseur) et alertes plafond RCR (80 % du cap global)."""
import base64
import logging
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

from attestation_nominative import compute_rcr_ledger
from convention_settings import build_rcr_registry
from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
rcr_reports_router = APIRouter(prefix="/api/convention", tags=["convention"])

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


# ============== RELEVÉ RCR MENSUEL ==============

async def _collect_statement_data(db, vendor_id: str, month: str) -> dict:
    atts = await db.attestations_nominatives.find(
        {"vendor_id": vendor_id}, {"_id": 0, "ai_text": 0}).sort("created_at", 1).to_list(200)
    lines, soldes = [], []
    for att in atts:
        ledger = await compute_rcr_ledger(db, att)
        for f in ledger["fractions"]:
            if (f.get("date") or "").startswith(month):
                lines.append({**f, "attestation_ref": att["ref"], "product_name": att.get("product_name")})
        soldes.append({"attestation_ref": att["ref"], "product_name": att.get("product_name"),
                       "status": att.get("status"), "solde_cents": ledger["solde_cents"],
                       "plafond_cible_cents": ledger["plafond_cible_cents"]})
    reimbursements = await db.rcr_reimbursements.find(
        {"vendor_id": vendor_id, "created_at": {"$regex": f"^{month}"}}, {"_id": 0}).to_list(100)
    return {"lines": lines, "soldes": soldes, "reimbursements": reimbursements,
            "total_constitue_cents": sum(l["fraction_cents"] for l in lines),
            "total_rembourse_cents": sum(r["amount_cents"] for r in reimbursements)}


def build_monthly_statement_pdf(vendor: dict, month: str, data: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=13)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10, spaceBefore=8)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=8.5, leading=12)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
    els = [
        Paragraph("RELEVÉ MENSUEL RCR — FOGEDOM-SCIC", h1),
        Paragraph(f"Fournisseur : {vendor.get('company_name')} — Période : {month} — "
                  f"édité le {datetime.now().strftime('%d/%m/%Y')}", small),
        Spacer(1, 3 * mm),
        Paragraph(f"Fractions RCR constituées sur la période : <b>{_eur(data['total_constitue_cents'])}</b> · "
                  f"Remboursements sur la période : <b>{_eur(data['total_rembourse_cents'])}</b>", n),
        Paragraph("1. FRACTIONS RCR CONSTITUÉES (facture par facture)", h2),
    ]
    if data["lines"]:
        rows = [["Facture / commande", "Date", "Attestation", "Base HT", "Fraction RCR"]]
        rows += [[l["order_ref"], l["date"], l["attestation_ref"], _eur(l["base_ht_cents"]), _eur(l["fraction_cents"])]
                 for l in data["lines"]]
        t = Table(rows, colWidths=[42 * mm, 22 * mm, 66 * mm, 26 * mm, 26 * mm]); t.setStyle(style)
        els.append(t)
    else:
        els.append(Paragraph("Aucune fraction constituée sur la période.", n))
    els.append(Paragraph("2. REMBOURSEMENTS RCR DE LA PÉRIODE", h2))
    if data["reimbursements"]:
        rows = [["Référence", "Date", "Attestation clôturée", "Montant remboursé"]]
        rows += [[r["ref"], (r.get("created_at") or "")[:10], r.get("attestation_ref", ""), _eur(r["amount_cents"])]
                 for r in data["reimbursements"]]
        t = Table(rows, colWidths=[42 * mm, 22 * mm, 80 * mm, 36 * mm]); t.setStyle(style)
        els.append(t)
    else:
        els.append(Paragraph("Aucun remboursement sur la période.", n))
    els.append(Paragraph("3. SOLDES RCR PAR ATTESTATION (à date d'édition)", h2))
    rows = [["Attestation", "Produit", "Statut", "Solde RCR", "Plafond-cible"]]
    labels = {"signed": "Active", "pending_countersign": "En attente", "closed": "Clôturée"}
    rows += [[s["attestation_ref"], (s.get("product_name") or "")[:38], labels.get(s["status"], s["status"]),
              _eur(s["solde_cents"]), _eur(s["plafond_cible_cents"])] for s in data["soldes"]]
    t = Table(rows, colWidths=[58 * mm, 58 * mm, 22 * mm, 22 * mm, 22 * mm]); t.setStyle(style)
    els += [t, Spacer(1, 4 * mm),
            Paragraph("La RCR demeure une contribution individualisée et remboursable dont le Fournisseur reste "
                      "le bénéficiaire économique jusqu'à son remboursement ou sa mobilisation conforme. "
                      "Document généré automatiquement par le Dashboard KDMARCHÉ × O'SCOP.", small)]
    doc.build(els)
    return buf.getvalue()


async def send_monthly_rcr_statements(db, month: str = None) -> int:
    """Cron mensuel idempotent : envoie le relevé du mois précédent à chaque fournisseur concerné."""
    if not month:
        month = (datetime.now(timezone.utc).replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    vendor_ids = await db.attestations_nominatives.distinct("vendor_id")
    sent = 0
    for vid in vendor_ids:
        if await db.rcr_monthly_statements.find_one({"vendor_id": vid, "month": month}):
            continue
        vendor = await db.vendors.find_one({"id": vid}, {"_id": 0}) or {}
        data = await _collect_statement_data(db, vid, month)
        record = {"id": str(uuid.uuid4()), "vendor_id": vid,
                  "vendor_name": vendor.get("company_name"), "month": month,
                  "total_constitue_cents": data["total_constitue_cents"],
                  "total_rembourse_cents": data["total_rembourse_cents"],
                  "lines_count": len(data["lines"]), "email_sent": False,
                  "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            from brevo_service import is_brevo_configured, send_email, _wrap_html
            if is_brevo_configured() and vendor.get("email"):
                pdf = build_monthly_statement_pdf(vendor, month, data)
                body = (
                    f"<p>Bonjour {vendor.get('contact_name') or ''},</p>"
                    f"<p>Veuillez trouver ci-joint votre relevé RCR FOGEDOM-SCIC du mois <strong>{month}</strong> :</p>"
                    f"<ul><li>Fractions constituées : <strong>{_eur(data['total_constitue_cents'])}</strong></li>"
                    f"<li>Remboursements : <strong>{_eur(data['total_rembourse_cents'])}</strong></li></ul>"
                    "<p>Le détail facture par facture ainsi que les soldes par attestation figurent dans le PDF.</p>")
                await send_email(
                    to_email=vendor["email"], to_name=vendor.get("contact_name"),
                    subject=f"Relevé RCR {month} — FOGEDOM-SCIC",
                    html_content=_wrap_html("Relevé RCR mensuel", body),
                    tags=["rcr-releve-mensuel"],
                    attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"releve-rcr-{month}.pdf"}])
                record["email_sent"] = True
                sent += 1
        except Exception as exc:
            logger.warning("Relevé RCR %s / %s : envoi email impossible : %s", vid, month, exc)
        await db.rcr_monthly_statements.insert_one({**record})
    if sent:
        logger.info("Relevés RCR mensuels %s envoyés : %s", month, sent)
    return sent


@rcr_reports_router.get("/admin/rcr-statements")
async def list_rcr_statements(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    statements = await db.rcr_monthly_statements.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"statements": statements}


@rcr_reports_router.post("/admin/rcr-statements/run")
async def run_rcr_statements(body: dict = None, current_user: dict = Depends(get_current_user)):
    """Force la génération/envoi des relevés d'un mois (défaut : mois précédent)."""
    await check_admin(current_user)
    db = get_database()
    month = (body or {}).get("month")
    sent = await send_monthly_rcr_statements(db, month)
    return {"success": True, "sent": sent}


@rcr_reports_router.get("/admin/rcr-statements/{sid}/pdf")
async def rcr_statement_pdf(sid: str, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    rec = await db.rcr_monthly_statements.find_one({"id": sid}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Relevé introuvable")
    vendor = await db.vendors.find_one({"id": rec["vendor_id"]}, {"_id": 0}) or {}
    data = await _collect_statement_data(db, rec["vendor_id"], rec["month"])
    pdf = build_monthly_statement_pdf(vendor, rec["month"], data)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=releve-rcr-{rec['month']}-{rec['vendor_id'][:8]}.pdf"})


# ============== STATISTIQUES RCR (DASHBOARD) ==============

@rcr_reports_router.get("/admin/rcr-stats")
async def rcr_stats(months: int = 6, current_user: dict = Depends(get_current_user)):
    """Évolution mensuelle des fractions RCR constituées et remboursées."""
    await check_admin(current_user)
    db = get_database()
    months = max(1, min(months, 24))
    now = datetime.now(timezone.utc)
    keys = []
    y, m = now.year, now.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    constitue = {k: 0 for k in keys}
    rembourse = {k: 0 for k in keys}
    async for att in db.attestations_nominatives.find({}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        for f in ledger["fractions"]:
            k = (f.get("date") or "")[:7]
            if k in constitue:
                constitue[k] += f["fraction_cents"]
    async for r in db.rcr_reimbursements.find({}, {"_id": 0, "amount_cents": 1, "created_at": 1}):
        k = (r.get("created_at") or "")[:7]
        if k in rembourse:
            rembourse[k] += r.get("amount_cents", 0)
    return {"months": [{"month": k, "constitue_cents": constitue[k], "rembourse_cents": rembourse[k]}
                       for k in keys],
            "total_constitue_cents": sum(constitue.values()),
            "total_rembourse_cents": sum(rembourse.values())}


# ============== ALERTES PLAFOND RCR (80 % DU CAP GLOBAL) ==============

async def check_rcr_cap_alerts(db) -> int:
    """Alerte les admins quand un fournisseur atteint 80 % (puis 100 %) du cap global RCR."""
    reg = await build_rcr_registry(db)
    cap_cents = int(reg["totaux"]["rcr_global_cap_eur"] * 100)
    if cap_cents <= 0:
        return 0
    sent = 0
    for v in reg["registre_rcr"]:
        pct = v["plafond_cible_cents"] / cap_cents * 100
        level = "100" if pct >= 100 else "80" if pct >= 80 else None
        if not level:
            continue
        if await db.rcr_cap_alerts.find_one({"vendor_id": v["vendor_id"], "level": level}):
            continue
        record = {"id": str(uuid.uuid4()), "vendor_id": v["vendor_id"],
                  "vendor_name": v.get("vendor_name"), "level": level, "pct": round(pct, 1),
                  "plafond_cible_cents": v["plafond_cible_cents"], "cap_cents": cap_cents,
                  "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            from brevo_service import is_brevo_configured, send_email, _wrap_html
            admins = await db.users.find({"is_admin": True, "email": {"$ne": None}},
                                         {"_id": 0, "email": 1}).to_list(10)
            if is_brevo_configured() and admins:
                title = ("🔴 Cap global RCR ATTEINT" if level == "100"
                         else "⚠️ Cap global RCR bientôt atteint (≥ 80 %)")
                body = (
                    f"<p>Le fournisseur <strong>{v.get('vendor_name')}</strong> "
                    f"{'a atteint' if level == '100' else 'approche'} le cap global RCR :</p>"
                    f"<ul><li>Plafond-cible consolidé : <strong>{_eur(v['plafond_cible_cents'])}</strong></li>"
                    f"<li>Cap global : <strong>{_eur(cap_cents)}</strong> ({record['pct']} %)</li></ul>"
                    "<p>Les prochaines attestations de ce fournisseur seront plafonnées. "
                    "Consultez le registre FOGEDOM-RCR dans le Super Admin (onglet Contrats).</p>")
                for a in admins:
                    await send_email(to_email=a["email"], to_name=None,
                                     subject=f"{title} — {v.get('vendor_name')}",
                                     html_content=_wrap_html("Alerte plafond RCR", body),
                                     tags=["rcr-cap-alerte"])
                sent += 1
        except Exception as exc:
            logger.warning("Alerte cap RCR %s impossible : %s", v["vendor_id"], exc)
        await db.rcr_cap_alerts.insert_one({**record})
    if sent:
        logger.info("Alertes cap RCR envoyées : %s", sent)
    return sent
