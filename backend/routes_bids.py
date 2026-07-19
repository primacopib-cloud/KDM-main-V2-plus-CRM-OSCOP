"""Participation vendeur — inscription (débit CPC), offres scellées chiffrées, enchère inversée 3 tours à rang anonyme."""
import base64
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from consultation_audit import audit

logger = logging.getLogger(__name__)

bids_router = APIRouter(prefix="/api/consultations", tags=["consultation-bids"])

db = None


def set_bids_database(database):
    global db
    db = database


def _fernet() -> Fernet:
    key = hashlib.sha256(os.environ["JWT_SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


async def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _auto_close(c: dict) -> dict:
    """Clôture automatique à l'heure serveur + ouverture simultanée des offres scellées."""
    if c["status"] in ("INSCRIPTIONS_OUVERTES", "EN_COURS") and c.get("closes_at") and c["closes_at"] <= datetime.now(timezone.utc).isoformat():
        await db.consultations.update_one({"id": c["id"]}, {"$set": {"status": "CLOTUREE", "closed_at": await _now()}})
        await audit("CLOSED", "system", c["id"], {"auto": True, "closes_at": c["closes_at"]})
        if c["procedure"] == "SCELLEE":
            await open_sealed_bids(c["id"])
        c["status"] = "CLOTUREE"
    return c


async def open_sealed_bids(cid: str):
    """Ouverture simultanée : déchiffre toutes les offres scellées valides et journalise."""
    f = _fernet()
    opened = 0
    async for b in db.bids.find({"consultation_id": cid, "sealed_payload": {"$ne": None}, "amount_ht_cents": None}):
        try:
            payload = json.loads(f.decrypt(b["sealed_payload"].encode()).decode())
            await db.bids.update_one({"id": b["id"]}, {"$set": {
                "amount_ht_cents": payload["amount_ht_cents"], "details": payload.get("details", {}),
                "opened_at": await _now()}})
            opened += 1
        except Exception as exc:
            logger.warning("Ouverture offre scellée %s : %s", b["id"], exc)
    await audit("SEALED_OPENED", "system", cid, {"opened": opened})
    return opened


async def send_closure_reminders(database):
    """Cron : rappel email aux inscrits sans offre valide, 24h avant la clôture (une seule fois)."""
    global db
    if db is None:
        db = database
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    horizon = (now + timedelta(hours=24)).isoformat()
    async for c in db.consultations.find({"status": "EN_COURS", "closes_at": {"$gt": now.isoformat(), "$lte": horizon}}, {"_id": 0}):
        async for e in db.consultation_entries.find({"consultation_id": c["id"], "status": "INSCRIT",
                                                     "closure_reminder_sent": {"$ne": True}}, {"_id": 0}):
            has_bid = await db.bids.find_one({"consultation_id": c["id"], "entry_id": e["id"], "status": "VALIDE"}, {"_id": 0, "id": 1})
            if has_bid:
                continue
            u = await db.users.find_one({"id": e["vendor_user_id"]}, {"_id": 0, "email": 1, "full_name": 1, "name": 1})
            if u and u.get("email"):
                try:
                    from brevo_service import send_email
                    base = os.environ.get("FRONTEND_PUBLIC_URL", "")
                    await send_email(
                        to_email=u["email"], to_name=u.get("full_name") or u.get("name"),
                        subject=f"Dernières heures — consultation {c['ref']} : vous n'avez pas encore déposé d'offre",
                        html_content=f"""<h2 style="color:#451F6B;">Clôture imminente — {c['ref']}</h2>
                        <p>Bonjour,</p>
                        <p>Vous êtes inscrit à <strong>{c['title']}</strong> mais aucune offre n'a encore été déposée.
                        La clôture est fixée au <strong>{str(c['closes_at'])[:16].replace('T', ' ')}</strong> (heure serveur, ferme et sans prolongation).</p>
                        <p style="margin:24px 0;"><a href="{base}/vendor?tab=consultations"
                        style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Déposer mon offre</a></p>""",
                        tags=["consultation-closure-reminder"])
                    await audit("REMINDER_SENT", "system", c["id"], {"entry_id": e["id"]})
                except Exception as exc:
                    logger.warning("Relance clôture %s → %s : %s", c["ref"], u["email"], exc)
            await db.consultation_entries.update_one({"id": e["id"]}, {"$set": {"closure_reminder_sent": True}})


async def _vendor_user(user_id: str) -> dict:
    from routes_cpc import _require_vendor
    return await _require_vendor(user_id)


async def _my_entry(cid: str, user_id: str) -> Optional[dict]:
    return await db.consultation_entries.find_one(
        {"consultation_id": cid, "vendor_user_id": user_id, "status": "INSCRIT"}, {"_id": 0})


async def _latest_valid_bids(cid: str) -> list:
    """Dernière offre valide par participant (enchère : la plus récente ; scellée : non remplacée)."""
    bids = await db.bids.find({"consultation_id": cid, "status": "VALIDE"}, {"_id": 0}).sort("server_ts", 1).to_list(500)
    latest = {}
    for b in bids:
        latest[b["entry_id"]] = b
    return list(latest.values())


@bids_router.get("")
async def open_consultations(user_id: str = Depends(get_current_user_id)):
    items = await db.consultations.find(
        {"status": {"$in": ["INSCRIPTIONS_OUVERTES", "EN_COURS", "CLOTUREE", "EN_EVALUATION", "ATTRIBUEE"]}},
        {"_id": 0, "published_snapshot": 0}).sort("closes_at", 1).limit(50).to_list(50)
    out = []
    for c in items:
        c = await _auto_close(c)
        entry = await _my_entry(c["id"], user_id)
        out.append({k: c.get(k) for k in ("id", "ref", "title", "type", "procedure", "legal_status", "products",
                                          "territories", "specs", "cpc_cost", "max_rounds", "criteria",
                                          "opens_at", "closes_at", "status")} | {"registered": bool(entry)})
    return {"items": out}


@bids_router.get("/tracking")
async def organizer_tracking(user_id: str = Depends(get_current_user_id)):
    """Suivi organisateur (espace acheteur) : statuts + participation, sans montants avant clôture."""
    out = []
    async for c in db.consultations.find({}, {"_id": 0, "published_snapshot": 0}).sort("created_at", -1).limit(50):
        c = await _auto_close(c)
        entries = await db.consultation_entries.count_documents({"consultation_id": c["id"], "status": "INSCRIT"})
        bids_n = len(await _latest_valid_bids(c["id"]))
        closed = c["status"] in ("CLOTUREE", "EN_EVALUATION", "ATTRIBUEE", "SANS_SUITE", "ARCHIVEE")
        best = None
        if closed:
            priced = [b["amount_ht_cents"] for b in await _latest_valid_bids(c["id"]) if b.get("amount_ht_cents")]
            best = min(priced) if priced else None
        award = await db.consultation_awards.find_one({"consultation_id": c["id"], "awarded_entry_id": {"$ne": None}}, {"_id": 0, "ranking": 1, "awarded_entry_id": 1})
        winner = None
        if award:
            winner = next((r["company"] for r in award["ranking"] if r["entry_id"] == award["awarded_entry_id"]), None)
        out.append({k: c.get(k) for k in ("id", "ref", "title", "type", "procedure", "legal_status", "category",
                                          "cpc_cost", "opens_at", "closes_at", "status")} |
                   {"participants": entries, "valid_bids": bids_n, "best_offer_ht_cents": best, "winner": winner})
    return {"items": out}


class RegisterBody(BaseModel):
    accept_rules: bool = False


@bids_router.post("/{cid}/register")
async def register(cid: str, body: RegisterBody, user_id: str = Depends(get_current_user_id)):
    await _vendor_user(user_id)
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    c = await _auto_close(c)
    if c["status"] not in ("INSCRIPTIONS_OUVERTES", "EN_COURS"):
        raise HTTPException(status_code=409, detail=f"Inscriptions fermées (statut {c['status']})")
    if not body.accept_rules:
        raise HTTPException(status_code=400, detail="Vous devez accepter le règlement de la consultation et le coût CPC affiché")
    if await _my_entry(cid, user_id):
        raise HTTPException(status_code=409, detail="Vous êtes déjà inscrit")
    from cpc_ledger import add_cpc_movement
    mv = await add_cpc_movement(
        user_id, "CONSULTATION_ENTRY", -c["cpc_cost"], idempotency_key=f"entry:{cid}:{user_id}",
        reason=f"Inscription consultation {c['ref']} ({c['cpc_cost']} CPC — accès complet, {c['max_rounds']} tours inclus)",
        consultation_id=cid)
    if mv is None:
        raise HTTPException(status_code=409, detail="Inscription déjà traitée")
    entry = {"id": str(uuid.uuid4()), "consultation_id": cid, "vendor_user_id": user_id,
             "participant_type": "vendor_pro", "accepted_rules_at": await _now(),
             "cpc_ledger_id": mv["id"], "status": "INSCRIT", "created_at": await _now()}
    await db.consultation_entries.insert_one({**entry})
    await audit("ENTRY_REGISTERED", user_id, cid, {"entry_id": entry["id"], "cpc": c["cpc_cost"]})
    return {"ok": True, "entry_id": entry["id"], "balance": mv["balance_after"]}


class BidBody(BaseModel):
    amount_ht_cents: int
    details: dict = {}


@bids_router.post("/{cid}/bid")
async def submit_bid(cid: str, body: BidBody, user_id: str = Depends(get_current_user_id)):
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    c = await _auto_close(c)
    if c["status"] != "EN_COURS":
        raise HTTPException(status_code=410 if c["status"] == "CLOTUREE" else 409,
                            detail="La consultation n'accepte pas d'offres (statut " + c["status"] + ")")
    entry = await _my_entry(cid, user_id)
    if not entry:
        raise HTTPException(status_code=403, detail="Inscrivez-vous d'abord à la consultation")
    if body.amount_ht_cents <= 0:
        raise HTTPException(status_code=400, detail="Le prix doit être exprimé en euros HT positif")
    now = await _now()
    my_bids = await db.bids.find({"consultation_id": cid, "entry_id": entry["id"], "status": "VALIDE"},
                                 {"_id": 0}).sort("round", 1).to_list(10)
    if c["procedure"] == "ENCHERE_INVERSEE":
        rnd = len(my_bids) + 1
        if rnd > c.get("max_rounds", 3):
            raise HTTPException(status_code=409, detail=f"Nombre maximal de tours atteint ({c.get('max_rounds', 3)})")
        if my_bids and body.amount_ht_cents >= my_bids[-1]["amount_ht_cents"]:
            raise HTTPException(status_code=400, detail="Enchère inversée : votre nouvelle offre doit être inférieure à la précédente")
        doc = {"id": str(uuid.uuid4()), "consultation_id": cid, "entry_id": entry["id"], "round": rnd,
               "amount_ht_cents": body.amount_ht_cents, "currency": "EUR", "details": body.details,
               "sealed_payload": None, "payload_sha256": hashlib.sha256(str(body.amount_ht_cents).encode()).hexdigest(),
               "server_ts": now, "status": "VALIDE"}
        await db.bids.insert_one({**doc})
        await audit("BID_SUBMITTED", user_id, cid, {"entry_id": entry["id"], "round": rnd})
        return {"ok": True, "round": rnd, **await _rank_info(c, entry)}
    # SCELLEE : remplacement versionné, contenu chiffré jusqu'à la clôture
    payload = json.dumps({"amount_ht_cents": body.amount_ht_cents, "details": body.details})
    enc = _fernet().encrypt(payload.encode()).decode()
    if my_bids:
        await db.bids.update_many({"consultation_id": cid, "entry_id": entry["id"], "status": "VALIDE"},
                                  {"$set": {"status": "REMPLACEE"}})
        await audit("BID_REPLACED", user_id, cid, {"entry_id": entry["id"]})
    doc = {"id": str(uuid.uuid4()), "consultation_id": cid, "entry_id": entry["id"], "round": len(my_bids) + 1,
           "amount_ht_cents": None, "currency": "EUR", "details": {},
           "sealed_payload": enc, "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
           "server_ts": now, "status": "VALIDE"}
    await db.bids.insert_one({**doc})
    await audit("BID_SUBMITTED", user_id, cid, {"entry_id": entry["id"], "sealed": True, "sha256": doc["payload_sha256"][:16]})
    return {"ok": True, "sealed": True, "fingerprint": doc["payload_sha256"]}


async def _rank_info(c: dict, entry: dict) -> dict:
    """Rang anonyme + écart avec la meilleure offre (enchère inversée uniquement)."""
    if c["procedure"] != "ENCHERE_INVERSEE":
        return {}
    latest = await _latest_valid_bids(c["id"])
    priced = sorted([b for b in latest if b.get("amount_ht_cents")], key=lambda b: (b["amount_ht_cents"], b["server_ts"]))
    mine = next((i for i, b in enumerate(priced) if b["entry_id"] == entry["id"]), None)
    if mine is None:
        return {"rank": None, "participants": len(priced)}
    best = priced[0]["amount_ht_cents"]
    return {"rank": mine + 1, "participants": len(priced),
            "gap_to_best_cents": priced[mine]["amount_ht_cents"] - best}


@bids_router.get("/{cid}/my-status")
async def my_status(cid: str, user_id: str = Depends(get_current_user_id)):
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    c = await _auto_close(c)
    entry = await _my_entry(cid, user_id)
    if not entry:
        return {"registered": False, "status": c["status"]}
    my_bids = await db.bids.find({"consultation_id": cid, "entry_id": entry["id"]},
                                 {"_id": 0, "sealed_payload": 0}).sort("round", 1).to_list(10)
    return {"registered": True, "status": c["status"], "procedure": c["procedure"],
            "max_rounds": c.get("max_rounds", 3), "my_bids": my_bids, **await _rank_info(c, entry)}


@bids_router.post("/{cid}/report")
async def buy_report(cid: str, user_id: str = Depends(get_current_user_id)):
    """Rapport d'analyse détaillé (service facultatif, coût report_cost CPC — débit unique idempotent)."""
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c or c["status"] not in ("CLOTUREE", "EN_EVALUATION", "ATTRIBUEE", "SANS_SUITE", "ARCHIVEE"):
        raise HTTPException(status_code=409, detail="Rapport disponible après la clôture")
    entry = await _my_entry(cid, user_id)
    if not entry:
        raise HTTPException(status_code=403, detail="Réservé aux participants")
    key = f"report:{cid}:{user_id}"
    already = await db.cpc_ledger.find_one({"idempotency_key": key}, {"_id": 0, "id": 1})
    if not already:
        from routes_cpc_admin import get_cpc_settings
        from cpc_ledger import add_cpc_movement
        cost = (await get_cpc_settings())["report_cost"]
        await add_cpc_movement(user_id, "REPORT_PURCHASE", -cost, idempotency_key=key,
                               reason=f"Rapport d'analyse — consultation {c['ref']}", consultation_id=cid)
        await audit("REPORT_PURCHASED", user_id, cid, {"entry_id": entry["id"], "cost": cost})
    # Contenu du rapport
    latest = await _latest_valid_bids(cid)
    priced = sorted([b["amount_ht_cents"] for b in latest if b.get("amount_ht_cents")])
    my_bids = await db.bids.find({"consultation_id": cid, "entry_id": entry["id"]},
                                 {"_id": 0, "sealed_payload": 0}).sort("round", 1).to_list(10)
    my_last = next((b["amount_ht_cents"] for b in reversed(my_bids) if b.get("amount_ht_cents")), None)
    award = await db.consultation_awards.find_one({"consultation_id": cid}, {"_id": 0})
    my_rank = my_score = None
    if award and award.get("ranking"):
        for i, r in enumerate(award["ranking"]):
            if r["entry_id"] == entry["id"]:
                my_rank, my_score = i + 1, r["total"]
    median = priced[len(priced) // 2] if priced else None
    return {"ref": c["ref"], "title": c["title"], "participants": len(latest),
            "best_offer_ht_cents": priced[0] if priced else None, "median_offer_ht_cents": median,
            "my_last_offer_ht_cents": my_last,
            "my_gap_to_best_cents": (my_last - priced[0]) if (my_last and priced) else None,
            "my_final_rank": my_rank, "my_score": my_score, "my_bids": my_bids,
            "criteria_weights": {cr["key"]: cr["weight"] for cr in c.get("criteria", [])}}


@bids_router.post("/{cid}/winner-identity")
async def winner_identity(cid: str, user_id: str = Depends(get_current_user_id)):
    """Obligation L.442-8 : un participant peut demander l'identité du candidat retenu (demande tracée)."""
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c or c["status"] != "ATTRIBUEE":
        raise HTTPException(status_code=409, detail="Consultation non attribuée")
    entry = await _my_entry(cid, user_id)
    if not entry:
        raise HTTPException(status_code=403, detail="Réservé aux participants")
    award = await db.consultation_awards.find_one({"consultation_id": cid}, {"_id": 0})
    winner_entry = await db.consultation_entries.find_one({"id": award["awarded_entry_id"]}, {"_id": 0})
    winner = await db.users.find_one({"id": winner_entry["vendor_user_id"]}, {"_id": 0, "email": 1, "full_name": 1, "company": 1})
    vendor = await db.vendors.find_one({"email": (winner or {}).get("email")}, {"_id": 0, "company_name": 1})
    response = (vendor or {}).get("company_name") or (winner or {}).get("company") or (winner or {}).get("full_name") or "Candidat retenu"
    await db.winner_identity_requests.insert_one({
        "consultation_id": cid, "requester_entry_id": entry["id"], "requested_at": await _now(),
        "answered_at": await _now(), "response": response})
    await audit("WINNER_IDENTITY_REQUESTED", user_id, cid, {"entry_id": entry["id"]})
    return {"winner": response}
