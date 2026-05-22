"""
Routes pour le renouvellement PASS (opt-in/opt-out) et le parrainage coopérateur.

Modèle :
- `lolodrive_passes.is_auto_renew: bool` (déjà présent dans le seed) → opt-in renouvellement.
- Endpoint utilisateur pour activer/désactiver son auto-renew.
- Système de parrainage (referral) :
  * `lolodrive_referrals` : code unique par titulaire actif.
  * Endpoint pour récupérer/générer son code (idempotent).
  * Endpoint pour appliquer un code à l'inscription PASS (bonus +50 UC parrain & filleul, plafonné).
  * Endpoint admin : stats parrainage (top parrains).

Note : la mécanique de bonus est appliquée à la "claim" d'un code valide, pas automatique.
"""
from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lolodrive/pass", tags=["PASS Lifecycle"])

db = None

REFERRAL_BONUS_UC = 50  # UC offerts au parrain ET au filleul
REFERRAL_MAX_PER_SPONSOR = 10  # plafond par parrain


def set_pass_lifecycle_database(database):
    global db
    db = database


async def _resolve_user(user_id: str) -> dict:
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    user.pop("_id", None)
    return user


# =======================
# Auto-renew opt-in
# =======================

class AutoRenewIn(BaseModel):
    enabled: bool


@router.post("/auto-renew")
async def set_auto_renew(payload: AutoRenewIn, user_id: str = Depends(get_current_user_id)):
    user = await _resolve_user(user_id)
    pass_doc = await db.lolodrive_passes.find_one({"user_id": user["id"]}, {"_id": 0})
    if not pass_doc:
        raise HTTPException(status_code=404, detail="Aucun PASS trouvé pour cet utilisateur")
    now = datetime.now(timezone.utc)
    await db.lolodrive_passes.update_one(
        {"id": pass_doc["id"]},
        {"$set": {"is_auto_renew": payload.enabled, "updated_at": now}},
    )
    return {"ok": True, "is_auto_renew": payload.enabled}


# =======================
# Parrainage (referrals)
# =======================

def _generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    code = "KDM-" + "".join(secrets.choice(alphabet) for _ in range(6))
    return code


@router.get("/referral/me")
async def get_my_referral_code(user_id: str = Depends(get_current_user_id)):
    user = await _resolve_user(user_id)
    existing = await db.lolodrive_referrals.find_one({"sponsor_user_id": user["id"]}, {"_id": 0})
    if existing:
        used_count = await db.lolodrive_referral_claims.count_documents({"sponsor_user_id": user["id"]})
        return {
            "code": existing["code"],
            "uses": used_count,
            "max_uses": REFERRAL_MAX_PER_SPONSOR,
            "bonus_uc_per_use": REFERRAL_BONUS_UC,
            "active": existing.get("active", True),
        }
    code = _generate_referral_code()
    while await db.lolodrive_referrals.find_one({"code": code}):
        code = _generate_referral_code()
    now = datetime.now(timezone.utc)
    await db.lolodrive_referrals.insert_one({
        "id": secrets.token_hex(8),
        "code": code,
        "sponsor_user_id": user["id"],
        "sponsor_email": user.get("email"),
        "active": True,
        "created_at": now,
    })
    return {
        "code": code,
        "uses": 0,
        "max_uses": REFERRAL_MAX_PER_SPONSOR,
        "bonus_uc_per_use": REFERRAL_BONUS_UC,
        "active": True,
    }


class ReferralClaimIn(BaseModel):
    code: str = Field(..., min_length=4, max_length=24)


@router.post("/referral/claim")
async def claim_referral_code(payload: ReferralClaimIn, user_id: str = Depends(get_current_user_id)):
    user = await _resolve_user(user_id)
    code = payload.code.strip().upper()
    referral = await db.lolodrive_referrals.find_one({"code": code, "active": True}, {"_id": 0})
    if not referral:
        raise HTTPException(status_code=404, detail="Code de parrainage invalide ou expiré")
    if referral["sponsor_user_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas utiliser votre propre code")

    existing = await db.lolodrive_referral_claims.find_one({"referee_user_id": user["id"]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="Vous avez déjà utilisé un code de parrainage")

    uses = await db.lolodrive_referral_claims.count_documents({"sponsor_user_id": referral["sponsor_user_id"]})
    if uses >= REFERRAL_MAX_PER_SPONSOR:
        raise HTTPException(status_code=409, detail="Ce code a atteint son plafond d'utilisations")

    now = datetime.now(timezone.utc)
    claim_id = secrets.token_hex(8)
    await db.lolodrive_referral_claims.insert_one({
        "id": claim_id,
        "code": code,
        "sponsor_user_id": referral["sponsor_user_id"],
        "referee_user_id": user["id"],
        "referee_email": user.get("email"),
        "bonus_uc_each": REFERRAL_BONUS_UC,
        "created_at": now,
    })

    for uid, role in ((referral["sponsor_user_id"], "sponsor"), (user["id"], "referee")):
        wallet = await db.lolodrive_wallets.find_one({"user_id": uid}, {"_id": 0})
        if not wallet:
            continue
        # Idempotent ledger insert: unique on (wallet_id, ref_id) — only credits the wallet
        # if the ledger entry was actually NEW. Replays of this loop after a crash will see
        # the existing ledger row and skip the $inc.
        ledger_ref = f"REF-{claim_id}-{role.upper()}"
        result = await db.lolodrive_wallet_ledger.update_one(
            {"wallet_id": wallet["id"], "ref_id": ledger_ref},
            {"$setOnInsert": {
                "id": secrets.token_hex(8),
                "wallet_id": wallet["id"],
                "ref_id": ledger_ref,
                "type": "CREDIT",
                "amount_uc": REFERRAL_BONUS_UC,
                "reason": f"REFERRAL_BONUS_{role.upper()}",
                "created_at": now,
            }},
            upsert=True,
        )
        # Only credit balance if ledger entry was newly inserted
        if result.upserted_id is not None:
            await db.lolodrive_wallets.update_one(
                {"id": wallet["id"]},
                {"$inc": {"balance_uc": REFERRAL_BONUS_UC}, "$set": {"updated_at": now}},
            )
    return {
        "ok": True,
        "code": code,
        "bonus_uc_each": REFERRAL_BONUS_UC,
        "sponsor_credited": True,
        "referee_credited": True,
    }


# =======================
# Admin stats
# =======================

@router.get("/referral/stats")
async def referral_stats(user_id: str = Depends(get_current_user_id)):
    user = await _resolve_user(user_id)
    role = (user.get("role") or "").lower()
    is_admin = user.get("is_admin") or role in {
        "super_admin", "admin", "oscop_super_admin", "kdm_b2b_admin"
    }
    if not is_admin:
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    total_codes = await db.lolodrive_referrals.count_documents({})
    total_claims = await db.lolodrive_referral_claims.count_documents({})
    pipeline = [
        {"$group": {"_id": "$sponsor_user_id", "uses": {"$sum": 1}}},
        {"$sort": {"uses": -1}},
        {"$limit": 10},
    ]
    top = await db.lolodrive_referral_claims.aggregate(pipeline).to_list(10)
    enriched = []
    for t in top:
        u = await db.users.find_one({"id": t["_id"]}, {"_id": 0, "email": 1, "contact_name": 1})
        ref = await db.lolodrive_referrals.find_one({"sponsor_user_id": t["_id"]}, {"_id": 0, "code": 1})
        enriched.append({
            "sponsor_user_id": t["_id"],
            "sponsor_email": (u or {}).get("email"),
            "sponsor_name": (u or {}).get("contact_name"),
            "code": (ref or {}).get("code"),
            "uses": t["uses"],
        })
    return {
        "total_codes": total_codes,
        "total_claims": total_claims,
        "total_bonus_uc_distributed": total_claims * REFERRAL_BONUS_UC * 2,
        "top_sponsors": enriched,
    }


async def setup_pass_lifecycle_indexes(database):
    await database.lolodrive_referrals.create_index("code", unique=True)
    await database.lolodrive_referrals.create_index("sponsor_user_id")
    await database.lolodrive_referral_claims.create_index("referee_user_id", unique=True)
    await database.lolodrive_referral_claims.create_index("sponsor_user_id")
    # Strict idempotency on wallet ledger : (wallet_id, ref_id) must be unique.
    # Allows safe retry of the credit loop after partial failures.
    try:
        await database.lolodrive_wallet_ledger.create_index(
            [("wallet_id", 1), ("ref_id", 1)],
            unique=True,
            partialFilterExpression={"ref_id": {"$exists": True, "$type": "string"}},
        )
    except Exception:
        # Index may already exist with a different spec; safe to ignore.
        pass
