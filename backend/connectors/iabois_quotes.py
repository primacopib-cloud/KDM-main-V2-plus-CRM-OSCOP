"""Génération de devis matériaux pré-remplis depuis un projet IA Bois importé."""
from __future__ import annotations

import ast
import uuid
from datetime import datetime, timezone

TVA_RATE = 8.5

db = None


def set_iabois_quotes_database(database) -> None:
    global db
    db = database


def _parse_params(raw: dict) -> dict:
    try:
        params = ast.literal_eval(raw.get("params") or "{}")
        return params if isinstance(params, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def build_material_lines(params: dict) -> list[dict]:
    """Estime les lignes matériaux à partir des paramètres du projet (surface, chambres, toit...)."""
    surface = float(params.get("surface") or 100)
    chambres = int(params.get("chambres") or 2)
    floors = int(params.get("floors") or 1)
    roof_flat = (params.get("roofType") or "plat") == "plat"

    lines = [
        ("Ossature bois structurelle", surface, "m²", 185.0),
        ("Isolation biosourcée (murs + toiture)", surface, "m²", 45.0),
        ("Bardage bois extérieur", round(surface * 0.8, 1), "m²", 78.0),
        ("Membrane EPDM toit plat", surface, "m²", 95.0) if roof_flat
        else ("Couverture bac acier", surface, "m²", 65.0),
        ("Menuiseries bois (fenêtres + portes)", chambres + 2, "unité", 650.0),
    ]
    if floors > 1:
        lines.append(("Plancher bois intermédiaire", surface, "m²", 120.0))
    if params.get("terrasse"):
        lines.append(("Terrasse bois (lames + lambourdes)", 20, "m²", 140.0))
    if params.get("garage"):
        lines.append(("Extension garage ossature bois", 1, "forfait", 8500.0))

    return [
        {"label": label, "qty": qty, "unit": unit, "unit_price_ht": pu,
         "total_ht": round(qty * pu, 2)}
        for label, qty, unit, pu in lines
    ]


async def create_quote_from_project(project_id: str) -> dict | None:
    """Crée (idempotent) un devis matériaux pré-rempli. Retourne {quote, created} ou None si projet inconnu."""
    project = await db.iabois_quote_requests.find_one({"id": project_id}, {"_id": 0})
    if not project:
        return None

    existing = await db.iabois_quotes.find_one({"project_id": project_id}, {"_id": 0})
    if existing:
        return {"quote": existing, "created": False}

    params = _parse_params(project.get("raw") or {})
    lines = build_material_lines(params)
    total_ht = round(sum(line["total_ht"] for line in lines), 2)
    total_tva = round(total_ht * TVA_RATE / 100, 2)

    quote = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "title": project.get("title"),
        "client": project.get("client"),
        "params": params,
        "lines": lines,
        "total_ht": total_ht,
        "tva_rate": TVA_RATE,
        "total_tva": total_tva,
        "total_ttc": round(total_ht + total_tva, 2),
        "status": "DRAFT",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.iabois_quotes.insert_one({**quote})
    await db.iabois_quote_requests.update_one(
        {"id": project_id},
        {"$set": {"status": "QUOTED", "quote_id": quote["id"]}},
    )
    return {"quote": quote, "created": True}
