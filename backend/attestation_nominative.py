"""Attestations Nominatives V2.0 — Achat de volumes de produits prédéfinis, RCR FOGEDOM-SCIC. IA + QR code."""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from attestation_pdf import build_attestation_pdf
from core_deps import get_current_user
from convention_settings import get_convention_settings
from db import get_database

logger = logging.getLogger(__name__)
attestation_router = APIRouter(prefix="/api/attestations", tags=["attestations"])


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
            "Rédige le paragraphe déclaratif (3 à 4 phrases) d'une Attestation Nominative d'ACHAT DE VOLUMES "
            "de produits prédéfinis et de rattachement à la RCR FOGEDOM-SCIC (contrat d'application de la "
            "Convention-cadre V2.0 tripartite O'SCOP / KDMARCHE PRO / Fournisseur) :\n"
            f"- Fournisseur : {vendor.get('company_name')}\n"
            f"- Produit : {product.get('name')} (catégorie {product.get('category')})\n"
            f"- Volume d'Achat Ferme : {product.get('stock_quantity')} {product.get('unit_type', 'unité')}(s)\n"
            f"- Prix plafond HT : {product.get('price_ht')} €\n"
            "Précise que le Volume d'Achat Ferme engage KDMARCHE à acheter et le Fournisseur à fournir "
            "(sans mécanisme take-or-pay, non sélectionné), que le règlement est scindé (net Fournisseur + "
            "fraction RCR) et que la RCR, individualisée par facture et ligne produit, demeure remboursable "
            "au Fournisseur via le FOGEDOM-SCIC.")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = str(resp).strip()
        if len(text) > 80:
            return text
    except Exception as exc:
        logger.warning("IA attestation indisponible : %s", exc)
    return (f"Le Fournisseur {vendor.get('company_name')} accepte l'achat d'un Volume d'Achat Ferme de "
            f"{product.get('stock_quantity')} {product.get('unit_type', 'unité')}(s) du produit "
            f"« {product.get('name')} » (catégorie {product.get('category')}), au prix plafond HT de "
            f"{product.get('price_ht')} €. Le Volume d'Achat Ferme engage KDMARCHE PRO à acheter et le "
            "Fournisseur à fournir, sans mécanisme take-or-pay (non sélectionné). Le règlement est scindé : "
            "net Fournisseur + fraction RCR individualisée par facture et ligne produit, conservée par le "
            "FOGEDOM-SCIC, le Fournisseur demeurant bénéficiaire économique du solde jusqu'à remboursement.")


async def create_attestation_for_product(db, product: dict, vendor: dict) -> dict:
    """Créée à la soumission du produit ; le vendeur signe automatiquement (modèle V2.0)."""
    settings = await get_convention_settings(db)
    rate = settings["rcr_default_rate"]
    montant_cents = int(round(float(product.get("price_ht") or 0) * 100)) * int(product.get("stock_quantity") or 0)
    plafond_cents = int(montant_cents * rate / 100)
    cap_cents = int(settings["rcr_global_cap_eur"] * 100)
    seq = await db.attestations_nominatives.count_documents({}) + 1
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    year = now.strftime("%Y")
    cat = (product.get("category") or "CAT").upper().replace(" ", "-")[:14]
    conv = await db.conventions_cadres.find_one({"vendor_id": vendor["id"]}, {"_id": 0, "ref": 1})
    doc = {
        "id": str(uuid.uuid4()),
        "ref": f"OSC-KDM-FOUR-ACHAT-{cat}-{year}-{seq:03d}",
        "version": "V2.0",
        "fogedom_ref": f"FOGEDOM-RCR/FOUR/{cat}/{year}/{seq:03d}",
        "convention_ref": (conv or {}).get("ref") or "OSC/KDM/FOUR/CADRE-ACHAT-VOL-RCR-FOGEDOM/[À COMPLÉTER] / V2.0",
        "vendor_id": vendor["id"], "vendor_name": vendor.get("company_name"),
        "vendor_siret": vendor.get("siret"),
        "product_id": product["id"], "product_name": product.get("name"),
        "product_sku": product.get("sku"),
        "category": product.get("category"),
        "zones": product.get("available_zones") or [],
        "volume": product.get("stock_quantity"), "unit": product.get("unit_type", "unité"),
        "price_ht": product.get("price_ht"),
        "montant_agrege_cents": montant_cents,
        "rcr_rate": rate,
        "plafond_cible_cents": min(plafond_cents, cap_cents),
        "tolerance_rate": settings.get("tolerance_rate", 5.0),
        "devise": "EUR",
        "nature_achat": "VOLUME FERME",
        "mode_execution": "O'SCOP AGENT DE PSP",
        "cycle_remboursement": "À L'EXPIRATION",
        "incoterm": "EXW — site du Fournisseur",
        "storage_conditions": product.get("storage_conditions"),
        "date_entree": now_iso,
        "date_expiration": (now + timedelta(days=365)).isoformat(),
        "ai_text": await _ai_attestation_text(product, vendor),
        "status": "pending_countersign",
        "signatures": {"fournisseur": {"name": vendor.get("contact_name") or vendor.get("company_name"),
                                       "at": now_iso}},
        "created_at": now_iso,
    }
    await db.attestations_nominatives.insert_one({**doc})
    logger.info("Attestation V2.0 %s créée (produit %s, plafond RCR %s c)", doc["ref"], product["id"], doc["plafond_cible_cents"])
    return doc


async def countersign_attestation(db, product_id: str, admin_email: str = "") -> None:
    """O'SCOP et KDMARCHÉ signent lors de la validation admin du produit."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.attestations_nominatives.update_one(
        {"product_id": product_id, "status": "pending_countersign"},
        {"$set": {"status": "signed",
                  "signatures.oscop": {"name": f"O'SCOP{f' ({admin_email})' if admin_email else ''}", "at": now_iso},
                  "signatures.kdmarche": {"name": "KDMARCHÉ PRO", "at": now_iso}}})


@attestation_router.get("/verify/{att_id}")
async def verify_attestation(att_id: str):
    """Vérification publique (QR code) — aucune authentification requise."""
    db = get_database()
    att = await db.attestations_nominatives.find_one({"id": att_id}, {"_id": 0, "ai_text": 0})
    if not att:
        raise HTTPException(status_code=404, detail="Attestation introuvable")
    return {"ref": att["ref"], "version": att.get("version", "V2.0"),
            "fogedom_ref": att.get("fogedom_ref"), "convention_ref": att.get("convention_ref"),
            "vendor_name": att.get("vendor_name"),
            "product_name": att.get("product_name"), "category": att.get("category"),
            "zones": att.get("zones"), "volume": att.get("volume"), "unit": att.get("unit"),
            "montant_agrege_cents": att.get("montant_agrege_cents"),
            "rcr_rate": att.get("rcr_rate"), "plafond_cible_cents": att.get("plafond_cible_cents"),
            "nature_achat": att.get("nature_achat"), "mode_execution": att.get("mode_execution"),
            "date_entree": att.get("date_entree"), "date_expiration": att.get("date_expiration"),
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
