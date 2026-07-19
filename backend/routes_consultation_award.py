"""Lot 1.5/1.6 — Scoring multicritère, départage déterministe, attribution, Attestation nominative, PV PDF, exports."""
import csv
import hashlib
import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

award_router = APIRouter(prefix="/api/admin/consultations", tags=["consultation-award"])

db = None


def set_award_database(database):
    global db
    db = database


async def _get(cid: str) -> dict:
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    return c


async def _entries_with_bids(cid: str) -> list:
    from routes_bids import _latest_valid_bids
    latest = {b["entry_id"]: b for b in await _latest_valid_bids(cid)}
    out = []
    async for e in db.consultation_entries.find({"consultation_id": cid, "status": "INSCRIT"}, {"_id": 0}):
        u = await db.users.find_one({"id": e["vendor_user_id"]}, {"_id": 0, "email": 1, "full_name": 1, "company": 1})
        v = await db.vendors.find_one({"email": (u or {}).get("email")}, {"_id": 0, "company_name": 1})
        out.append({**e, "company": (v or {}).get("company_name") or (u or {}).get("company") or (u or {}).get("full_name") or (u or {}).get("email"),
                    "bid": latest.get(e["id"])})
    return out


@award_router.get("/{cid}/bids")
async def admin_bids(cid: str, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    closed = c["status"] in ("CLOTUREE", "EN_EVALUATION", "ATTRIBUEE", "SANS_SUITE", "ARCHIVEE")
    if c["procedure"] == "SCELLEE" and not closed:
        await audit("ADMIN_SENSITIVE_ACCESS", admin.get("email"), cid, {"action": "bids_before_close", "denied": True})
        raise HTTPException(status_code=403, detail="Offres scellées : aucun accès avant la clôture (tentative journalisée)")
    return {"entries": await _entries_with_bids(cid)}


class ScoreItem(BaseModel):
    entry_id: str
    criteria: dict  # {qualite: 0-100, disponibilite: .., logistique: .., impact: .., tracabilite: ..}


class ScoresBody(BaseModel):
    scores: List[ScoreItem]


@award_router.post("/{cid}/scores")
async def compute_scores(cid: str, body: ScoresBody, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    if c["status"] != "EN_EVALUATION":
        raise HTTPException(status_code=409, detail=f"Scoring impossible au statut {c['status']}")
    entries = await _entries_with_bids(cid)
    priced = [e for e in entries if e.get("bid") and e["bid"].get("amount_ht_cents")]
    if not priced:
        raise HTTPException(status_code=409, detail="Aucune offre valide à évaluer")
    best_price = min(e["bid"]["amount_ht_cents"] for e in priced)
    manual = {s.entry_id: s.criteria for s in body.scores}
    weights = {cr["key"]: cr["weight"] for cr in c["criteria"]}
    ranking = []
    for e in priced:
        sc = {"prix": round(best_price / e["bid"]["amount_ht_cents"] * 100, 2)}
        for k in weights:
            if k != "prix":
                sc[k] = float(manual.get(e["id"], {}).get(k, 0))
        total = round(sum(sc.get(k, 0) * w / 100 for k, w in weights.items()), 2)
        ranking.append({"entry_id": e["id"], "company": e["company"],
                        "amount_ht_cents": e["bid"]["amount_ht_cents"],
                        "bid_ts": e["bid"]["server_ts"], "scores": sc, "total": total})
    tie_order = c.get("tie_break_order", ["qualite", "logistique", "disponibilite", "tracabilite", "first_timestamp"])
    def sort_key(r):
        keys = [-r["total"]]
        for t in tie_order:
            keys.append(r["bid_ts"] if t == "first_timestamp" else -r["scores"].get(t, 0))
        return tuple(keys)
    ranking.sort(key=sort_key)
    await db.consultation_awards.update_one(
        {"consultation_id": cid},
        {"$set": {"consultation_id": cid, "ranking": ranking, "scored_by": admin.get("email"),
                  "scored_at": datetime.now(timezone.utc).isoformat(), "awarded_entry_id": None}}, upsert=True)
    await audit("RANKING_COMPUTED", admin.get("email"), cid, {"participants": len(ranking), "weights": weights})
    return {"ranking": ranking}


class AwardBody(BaseModel):
    entry_id: Optional[str] = None
    derogation_reason: Optional[str] = None


@award_router.post("/{cid}/award")
async def award_consultation(cid: str, body: AwardBody, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    if c["status"] != "EN_EVALUATION":
        raise HTTPException(status_code=409, detail=f"Attribution impossible au statut {c['status']}")
    aw = await db.consultation_awards.find_one({"consultation_id": cid}, {"_id": 0})
    if not aw or not aw.get("ranking"):
        raise HTTPException(status_code=409, detail="Calculez d'abord le classement (scores)")
    first = aw["ranking"][0]
    target = body.entry_id or first["entry_id"]
    derogation = None
    if target != first["entry_id"]:
        if not (body.derogation_reason or "").strip():
            raise HTTPException(status_code=400, detail="Attribution dérogatoire : motivation écrite obligatoire")
        derogation = {"reason": body.derogation_reason.strip(), "validated_by": [admin.get("email")],
                      "at": datetime.now(timezone.utc).isoformat()}
        await audit("DEROGATION", admin.get("email"), cid, derogation)
    winner = next((r for r in aw["ranking"] if r["entry_id"] == target), None)
    if not winner:
        raise HTTPException(status_code=404, detail="Participant introuvable dans le classement")
    now = datetime.now(timezone.utc).isoformat()
    await db.consultation_awards.update_one({"consultation_id": cid}, {"$set": {
        "awarded_entry_id": target, "derogation": derogation,
        "validated_by": admin.get("email"), "validated_at": now}})
    await db.consultations.update_one({"id": cid}, {"$set": {"status": "ATTRIBUEE", "updated_at": now}})
    att = {
        "id": str(uuid.uuid4()), "consultation_id": cid, "consultation_ref": c["ref"],
        "supplier": winner["company"], "supplier_entry_id": target,
        "products": c.get("products"), "territories": c.get("territories"),
        "amount_ht_cents": winner["amount_ht_cents"],
        "valid_from": None, "valid_until": None, "fogedom_rcr_ref": None,
        "status": "PROJET", "note": "Projet d'attestation — ne vaut ni paiement, ni facture, ni RCR, ni bon de commande définitif.",
        "created_at": now,
    }
    await db.nominative_attestations.insert_one({**att})
    await audit("AWARD_VALIDATED", admin.get("email"), cid,
                {"entry_id": target, "company": winner["company"], "attestation_id": att["id"]})
    return {"ok": True, "status": "ATTRIBUEE", "winner": winner["company"], "attestation_id": att["id"]}


# ---------- Lot 1.6 : PV PDF + exports ----------

@award_router.get("/{cid}/pv.pdf")
async def pv_pdf(cid: str, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    if c["status"] not in ("ATTRIBUEE", "SANS_SUITE", "ANNULEE", "ARCHIVEE"):
        raise HTTPException(status_code=409, detail="PV disponible après attribution, classement sans suite ou annulation")
    aw = await db.consultation_awards.find_one({"consultation_id": cid}, {"_id": 0})
    entries = await _entries_with_bids(cid)
    events = await db.audit_journal.find({"consultation_id": cid}, {"_id": 0}).sort("seq", 1).to_list(500)
    from consultation_pv_pdf import build_pv_pdf
    pdf = build_pv_pdf(c, entries, aw, events)
    sha = hashlib.sha256(pdf).hexdigest()
    await db.consultation_pv.update_one({"consultation_id": cid}, {"$set": {
        "consultation_id": cid, "sha256": sha, "generated_by": admin.get("email"),
        "generated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    await audit("EXPORTED", admin.get("email"), cid, {"kind": "pv_pdf", "sha256": sha[:16]})
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="PV-{c["ref"]}.pdf"',
                             "X-PV-SHA256": sha})


@award_router.get("/{cid}/export.json")
async def export_json(cid: str, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    events = await db.audit_journal.find({"consultation_id": cid}, {"_id": 0}).sort("seq", 1).to_list(1000)
    await audit("EXPORTED", admin.get("email"), cid, {"kind": "json"})
    return Response(content=json.dumps({"consultation": c, "audit": events}, default=str, indent=2),
                    media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{c["ref"]}-audit.json"'})


@award_router.get("/{cid}/export.csv")
async def export_csv(cid: str, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    events = await db.audit_journal.find({"consultation_id": cid}, {"_id": 0}).sort("seq", 1).to_list(1000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["seq", "date", "événement", "acteur", "détails", "sha256"])
    for e in events:
        w.writerow([e["seq"], e["ts"], e["event_type"], e["actor"], json.dumps(e.get("payload"), default=str), e["sha256_self"][:16]])
    await audit("EXPORTED", admin.get("email"), cid, {"kind": "csv"})
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{c["ref"]}-audit.csv"'})
