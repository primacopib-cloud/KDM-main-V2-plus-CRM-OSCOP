"""Extrait d'immatriculation automatique (API Recherche d'entreprises data.gouv) + PDF + GED."""
import asyncio
import io
import logging
import os
from datetime import datetime, timezone

import httpx
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

EXTRACT_DIR = "/app/backend/uploads/extracts"
API_URL = "https://recherche-entreprises.api.gouv.fr/search"

VIOLET = colors.HexColor("#451F6B")
VIOLET_DARK = colors.HexColor("#2A1045")

_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, textColor=VIOLET_DARK, spaceAfter=3)
_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#6b5a7a"), spaceAfter=10)
_H2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, textColor=VIOLET, spaceBefore=12, spaceAfter=5)
_BODY = ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#2a2233"))


async def fetch_company_info(siret: str) -> dict | None:
    """Interroge l'API officielle Recherche d'entreprises (aucune clé requise)."""
    q = "".join(c for c in siret if c.isdigit())
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(API_URL, params={"q": q, "page": 1, "per_page": 1})
        r.raise_for_status()
        results = r.json().get("results") or []
        return results[0] if results else None


def _rows_table(rows):
    t = Table(rows, colWidths=[55 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), VIOLET),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4eefa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_extract_pdf(siret: str, info: dict) -> bytes:
    siege = info.get("siege") or {}
    adresse = siege.get("adresse") or info.get("adresse") or ""
    dirigeants = info.get("dirigeants") or []
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    el = [
        Paragraph("Extrait d'immatriculation — Fiche entreprise", _TITLE),
        Paragraph("Communityplace — KDMARCHÉ × O'SCOP · Registre des membres · "
                  f"Généré automatiquement le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", _SUB),
        Paragraph("1. Identification", _H2),
        _rows_table([
            ["Dénomination", (info.get("nom_complet") or info.get("nom_raison_sociale") or "").upper()],
            ["SIREN", info.get("siren") or ""],
            ["SIRET (siège)", siege.get("siret") or siret],
            ["Forme juridique", str(info.get("nature_juridique") or "")],
            ["Activité principale (NAF)", info.get("activite_principale") or siege.get("activite_principale") or ""],
            ["Date de création", info.get("date_creation") or ""],
            ["État administratif", "Actif" if (info.get("etat_administratif") == "A") else (info.get("etat_administratif") or "")],
            ["Tranche d'effectif", str(info.get("tranche_effectif_salarie") or "N.C.")],
        ]),
        Paragraph("2. Siège social", _H2),
        _rows_table([
            ["Adresse", adresse],
            ["Commune", f"{siege.get('code_postal') or ''} {siege.get('libelle_commune') or ''}".strip()],
        ]),
    ]
    if dirigeants:
        rows = [[
            (d.get("nom") and f"{(d.get('prenoms') or '').split(',')[0]} {d.get('nom')}".strip())
            or d.get("denomination") or "—",
            d.get("qualite") or d.get("role") or "",
        ] for d in dirigeants[:8]]
        el += [Paragraph("3. Dirigeants", _H2), _rows_table(rows)]
    el += [
        Spacer(1, 12),
        Paragraph("Document généré automatiquement à partir des données publiques de l'API officielle "
                  "« Recherche d'entreprises » (data.gouv.fr) lors de l'adhésion du membre. "
                  "Il est classé dans la GED de la coopérative et annexé au registre des membres.", _SUB),
    ]
    doc.build(el)
    return buf.getvalue()


async def generate_company_extract(database, siret: str, org_id: str | None = None,
                                   legal_name: str | None = None, force: bool = False) -> dict:
    """Récupère les données, génère le PDF, stocke localement + pousse en GED. Idempotent par SIRET."""
    siret = "".join(c for c in (siret or "") if c.isdigit())
    if len(siret) < 9:
        return {"status": "INVALID_SIRET", "siret": siret}
    existing = await database.company_extracts.find_one({"siret": siret}, {"_id": 0})
    if existing and existing.get("status") == "SUCCESS" and not force:
        if org_id and not existing.get("org_id"):
            await database.company_extracts.update_one({"siret": siret}, {"$set": {"org_id": org_id}})
        return existing
    doc_out = {"siret": siret, "org_id": org_id, "legal_name": legal_name,
               "fetched_at": datetime.now(timezone.utc).isoformat()}
    try:
        info = await fetch_company_info(siret)
    except Exception as exc:
        doc_out.update({"status": "ERROR", "error": str(exc)[:300]})
        await database.company_extracts.update_one({"siret": siret}, {"$set": doc_out}, upsert=True)
        return doc_out
    if not info:
        doc_out.update({"status": "NOT_FOUND"})
        await database.company_extracts.update_one({"siret": siret}, {"$set": doc_out}, upsert=True)
        return doc_out
    pdf = build_extract_pdf(siret, info)
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    path = os.path.join(EXTRACT_DIR, f"extrait-{siret}.pdf")
    with open(path, "wb") as f:
        f.write(pdf)
    doc_out.update({
        "status": "SUCCESS",
        "legal_name": info.get("nom_complet") or legal_name,
        "pdf_path": path,
        "data": {
            "nom_complet": info.get("nom_complet"),
            "siren": info.get("siren"),
            "nature_juridique": info.get("nature_juridique"),
            "activite_principale": info.get("activite_principale"),
            "date_creation": info.get("date_creation"),
            "etat_administratif": info.get("etat_administratif"),
        },
    })
    try:
        from gedess_client import is_gedess_configured, gedess_upload_file
        if is_gedess_configured():
            ged_doc = await gedess_upload_file(
                filename=f"extrait-immatriculation-{siret}.pdf",
                content=pdf,
                categorie="rapport",
                description=f"Extrait d'immatriculation automatique — {doc_out.get('legal_name') or siret} (SIRET {siret}).",
                tags="communityplace,immatriculation,registre-membres,extrait",
                mime_type="application/pdf",
            )
            doc_out["ged_document_id"] = ged_doc.get("id")
    except Exception as exc:
        logger.warning("Extrait %s : push GED échoué (%s)", siret, exc)
    await database.company_extracts.update_one({"siret": siret}, {"$set": doc_out}, upsert=True)
    logger.info("Extrait d'immatriculation généré pour %s (%s)", siret, doc_out.get("legal_name"))
    return doc_out


async def get_or_generate_extract(database, siret: str) -> tuple[bytes | None, str, dict]:
    """Retourne (pdf_bytes, filename, meta) — génération à la demande si absent."""
    siret = "".join(c for c in (siret or "") if c.isdigit())
    doc = await database.company_extracts.find_one({"siret": siret}, {"_id": 0})
    if not doc or doc.get("status") != "SUCCESS" or not os.path.exists(doc.get("pdf_path") or ""):
        doc = await generate_company_extract(database, siret, force=True)
    if doc.get("status") != "SUCCESS":
        return None, "", doc
    with open(doc["pdf_path"], "rb") as f:
        return f.read(), f"extrait-immatriculation-{siret}.pdf", doc


def schedule_extract(database, siret: str, org_id: str | None = None, legal_name: str | None = None) -> None:
    """Lance la génération en tâche de fond (non bloquant)."""
    if siret:
        asyncio.create_task(generate_company_extract(database, siret, org_id=org_id, legal_name=legal_name))
