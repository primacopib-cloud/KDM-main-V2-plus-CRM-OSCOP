"""Attestations Nominatives d'agrégation de volumes — IA + QR code de vérification."""
import logging
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core_deps import get_current_user
from convention_settings import get_convention_settings
from db import get_database

logger = logging.getLogger(__name__)
attestation_router = APIRouter(prefix="/api/attestations", tags=["attestations"])
GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")


async def _ai_attestation_text(product: dict, vendor: dict) -> str:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"attestation-{uuid.uuid4()}",
            system_message=("Tu es un assistant juridique. Rédige en français, style juridique sobre, "
                            "un seul paragraphe, sans markdown."),
        ).with_model("openai", "gpt-5.4")
        prompt = (
            "Rédige le paragraphe déclaratif (3 à 4 phrases) d'une Attestation Nominative d'agrégation "
            "de volumes par catégorie (Annexe 2 d'une convention cadre tripartite O'SCOP / KDMARCHÉ PRO / Fournisseur) :\n"
            f"- Fournisseur : {vendor.get('company_name')}\n"
            f"- Produit : {product.get('name')} (catégorie {product.get('category')})\n"
            f"- Volume agrégé accepté : {product.get('stock_quantity')} {product.get('unit_type', 'unité')}(s)\n"
            f"- Prix plafond HT : {product.get('price_ht')} €\n"
            "Précise que l'attestation matérialise une capacité de disponibilité sans engagement ferme "
            "d'achat (absence de take-or-pay) et que la RCR est constituée par fractions sur factures éligibles.")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = str(resp).strip()
        if len(text) > 80:
            return text
    except Exception as exc:
        logger.warning("IA attestation indisponible : %s", exc)
    return (f"Le Fournisseur {vendor.get('company_name')} atteste accepter l'agrégation d'un volume de "
            f"{product.get('stock_quantity')} {product.get('unit_type', 'unité')}(s) du produit "
            f"« {product.get('name')} » (catégorie {product.get('category')}), au prix plafond HT de "
            f"{product.get('price_ht')} €. La présente attestation matérialise une capacité de disponibilité "
            "sans engagement ferme d'achat (absence de take-or-pay). La Retenue Contributive Remboursable "
            "est constituée par fractions sur les factures éligibles et conservée par le FOGEDOM-SCIC.")


async def create_attestation_for_product(db, product: dict, vendor: dict) -> dict:
    """Créée à la soumission du produit ; le vendeur signe automatiquement."""
    settings = await get_convention_settings(db)
    rate = settings["rcr_default_rate"]
    montant_cents = int(round(float(product.get("price_ht") or 0) * 100)) * int(product.get("stock_quantity") or 0)
    plafond_cents = int(montant_cents * rate / 100)
    cap_cents = int(settings["rcr_global_cap_eur"] * 100)
    seq = await db.attestations_nominatives.count_documents({}) + 1
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "ref": f"ATT-{datetime.utcnow().strftime('%Y%m%d')}-{seq:04d}",
        "vendor_id": vendor["id"], "vendor_name": vendor.get("company_name"),
        "product_id": product["id"], "product_name": product.get("name"),
        "category": product.get("category"),
        "zones": product.get("available_zones") or [],
        "volume": product.get("stock_quantity"), "unit": product.get("unit_type", "unité"),
        "price_ht": product.get("price_ht"),
        "montant_agrege_cents": montant_cents,
        "rcr_rate": rate,
        "plafond_cible_cents": min(plafond_cents, cap_cents),
        "ai_text": await _ai_attestation_text(product, vendor),
        "status": "pending_countersign",
        "signatures": {"fournisseur": {"name": vendor.get("contact_name") or vendor.get("company_name"),
                                       "at": now_iso}},
        "created_at": now_iso,
    }
    await db.attestations_nominatives.insert_one({**doc})
    logger.info("Attestation %s créée (produit %s, plafond RCR %s c)", doc["ref"], product["id"], doc["plafond_cible_cents"])
    return doc


async def countersign_attestation(db, product_id: str, admin_email: str = "") -> None:
    """O'SCOP et KDMARCHÉ signent lors de la validation admin du produit."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.attestations_nominatives.update_one(
        {"product_id": product_id, "status": "pending_countersign"},
        {"$set": {"status": "signed",
                  "signatures.oscop": {"name": f"O'SCOP{f' ({admin_email})' if admin_email else ''}", "at": now_iso},
                  "signatures.kdmarche": {"name": "KDMARCHÉ PRO", "at": now_iso}}})


def _qr_png(url: str) -> bytes:
    import qrcode
    img = qrcode.make(url, box_size=6, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_attestation_pdf(att: dict) -> bytes:
    base = (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
    verify_url = f"{base}/verifier-attestation/{att['id']}"
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=14)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=11, spaceBefore=6)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, textColor=colors.grey)
    sigs = att.get("signatures") or {}
    rows = [
        ["Référence", att["ref"]],
        ["Fournisseur", att.get("vendor_name", "")],
        ["Produit / Catégorie", f"{att.get('product_name')} — {att.get('category')}"],
        ["Territoire(s)", ", ".join(att.get("zones") or []) or "[À COMPLÉTER]"],
        ["Volume agrégé accepté", f"{att.get('volume')} {att.get('unit')}(s)"],
        ["Prix plafond HT", f"{att.get('price_ht')} €"],
        ["Montant agrégé HT", f"{att.get('montant_agrege_cents', 0) / 100:,.2f} €".replace(",", " ")],
        ["Taux de Retenue Contributive", f"{att.get('rcr_rate', 5.0):.2f} %"],
        ["Plafond-cible RCR (Montant × Taux)", f"{att.get('plafond_cible_cents', 0) / 100:,.2f} €".replace(",", " ")],
        ["Statut", "Signée par les trois parties" if att.get("status") == "signed" else "En attente de contre-signature O'SCOP / KDMARCHÉ"],
    ]
    t = Table(rows, colWidths=[70 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    sig_rows = [["Partie", "Signataire", "Date"]]
    for key, label in (("fournisseur", "Fournisseur"), ("oscop", "O'SCOP"), ("kdmarche", "KDMARCHÉ PRO")):
        s = sigs.get(key)
        sig_rows.append([label, (s or {}).get("name", "—"),
                         (s or {}).get("at", "")[:10] if s else "En attente"])
    st = Table(sig_rows, colWidths=[45 * mm, 80 * mm, 45 * mm])
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5DCC8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FBF6EE")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    doc.build([
        Paragraph("ATTESTATION NOMINATIVE D'AGRÉGATION DE VOLUMES", h1),
        Paragraph("Annexe 2 — Convention cadre tripartite O'SCOP × KDMARCHÉ PRO × Fournisseur", small),
        Spacer(1, 4 * mm), t, Spacer(1, 4 * mm),
        Paragraph("DÉCLARATION", h2), Paragraph(att.get("ai_text", ""), n),
        Spacer(1, 4 * mm), Paragraph("SIGNATURES", h2), st,
        Spacer(1, 5 * mm), Paragraph("VÉRIFICATION D'AUTHENTICITÉ", h2),
        RLImage(BytesIO(_qr_png(verify_url)), width=32 * mm, height=32 * mm, hAlign="LEFT"),
        Paragraph(f"Scannez ce QR code ou visitez : {verify_url}", small),
        Paragraph("Ce QR code permet à toute partie de vérifier en ligne le statut et les signatures de la présente attestation.", small),
    ])
    return buf.getvalue()


@attestation_router.get("/verify/{att_id}")
async def verify_attestation(att_id: str):
    """Vérification publique (QR code) — aucune authentification requise."""
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0, "ai_text": 0})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    return {"ref": att["ref"], "vendor_name": att.get("vendor_name"),
            "product_name": att.get("product_name"), "category": att.get("category"),
            "zones": att.get("zones"), "volume": att.get("volume"), "unit": att.get("unit"),
            "montant_agrege_cents": att.get("montant_agrege_cents"),
            "rcr_rate": att.get("rcr_rate"), "plafond_cible_cents": att.get("plafond_cible_cents"),
            "status": att.get("status"), "signatures": att.get("signatures"),
            "created_at": att.get("created_at")}


@attestation_router.get("/vendor/{vendor_id}")
async def list_vendor_attestations(vendor_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    if not current_user.get("is_admin") and current_user.get("vendor_id") != vendor_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return await db.attestations_nominatives.find(
        {"vendor_id": vendor_id}, {"_id": 0, "ai_text": 0}).sort("created_at", -1).to_list(100)


@attestation_router.get("/{att_id}/pdf")
async def download_attestation_pdf(att_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    if not current_user.get("is_admin") and current_user.get("vendor_id") != att["vendor_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    pdf = build_attestation_pdf(att)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={att['ref']}.pdf"})
