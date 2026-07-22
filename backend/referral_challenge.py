"""Défi parrainage mensuel — récompense CREDI'SCOP pour le meilleur parrain du mois."""
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
challenge_router = APIRouter(prefix="/api/admin/referral/challenge", tags=["referral-challenge"])
challenge_public_router = APIRouter(prefix="/api/public/referral-challenge", tags=["referral-challenge-public"])
db = None

DEFAULTS = {"id": "default", "enabled": False, "reward_credits": 50}


def set_challenge_database(database):
    global db
    db = database


class ChallengeBody(BaseModel):
    enabled: bool = None
    reward_credits: int = None


async def _get_settings(database) -> dict:
    doc = await database.referral_challenge_settings.find_one({"id": "default"}, {"_id": 0})
    return {**DEFAULTS, **(doc or {})}


async def _leaderboard(database, month: str, limit: int = 5) -> list:
    counts = {}
    async for l in database.referral_links.find({"created_at": {"$gte": f"{month}-01", "$lt": f"{month}-99"}}):
        counts[l["sponsor_id"]] = counts.get(l["sponsor_id"], 0) + 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])[:limit]
    ids = [r[0] for r in ranked]
    emails = {u["id"]: u.get("email") for u in
              await database.users.find({"id": {"$in": ids}}, {"id": 1, "email": 1}).to_list(limit)}
    return [{"sponsor_id": sid, "sponsor": emails.get(sid, sid), "referred": n} for sid, n in ranked]


@challenge_router.get("")
async def get_challenge(admin: dict = Depends(require_admin)):
    settings = await _get_settings(db)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    leaderboard = await _leaderboard(db, month)
    winners = await db.referral_challenges.find({}, {"_id": 0}).sort("month", -1).to_list(6)
    return {**settings, "month": month, "leaderboard": leaderboard, "past_winners": winners}


@challenge_router.put("")
async def update_challenge(body: ChallengeBody, admin: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "reward_credits" in updates:
        updates["reward_credits"] = max(1, min(updates["reward_credits"], 1000))
    if updates:
        await db.referral_challenge_settings.update_one({"id": "default"}, {"$set": updates}, upsert=True)
        from consultation_audit import audit
        await audit("REFERRAL_CHALLENGE_UPDATED", admin.get("email"), None, updates)
    return await _get_settings(db)


def _mask(email: str) -> str:
    if not email or "@" not in email:
        return email or "Un membre"
    local = email.split("@")[0]
    return (local[:2] + "•••") if len(local) > 2 else local + "•••"


@challenge_public_router.get("/standing")
async def my_challenge_standing(request: Request):
    from auth import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Connexion requise")
    settings = await _get_settings(db)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    board = await _leaderboard(db, month, limit=100)
    my_rank, my_count = None, 0
    for i, row in enumerate(board):
        if row["sponsor_id"] == user_id:
            my_rank, my_count = i + 1, row["referred"]
            break
    return {
        "enabled": bool(settings.get("enabled")), "reward_credits": settings.get("reward_credits", 50),
        "month": month, "my_rank": my_rank, "my_count": my_count,
        "participants": len(board),
        "top": [{"name": _mask(r["sponsor"]), "referred": r["referred"], "me": r["sponsor_id"] == user_id}
                for r in board[:3]],
    }


@challenge_public_router.get("")
async def public_challenge():
    settings = await _get_settings(db)
    last = await db.referral_challenges.find_one(
        {"winner": {"$ne": None}}, {"_id": 0, "month": 1, "winner": 1, "referred": 1, "reward": 1},
        sort=[("month", -1)])
    if not settings.get("enabled") and not last:
        return {"active": False}
    return {
        "active": bool(settings.get("enabled")),
        "reward_credits": settings.get("reward_credits", 50),
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "last_winner": ({"month": last["month"], "name": _mask(last["winner"]),
                         "referred": last["referred"], "reward": last["reward"]} if last else None),
    }


async def process_referral_challenge(database) -> None:
    """Au début de chaque mois : récompense le meilleur parrain du mois précédent (une fois)."""
    settings = await _get_settings(database)
    if not settings.get("enabled"):
        return
    now = datetime.now(timezone.utc)
    prev_month = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    if await database.referral_challenges.find_one({"month": prev_month}):
        return
    board = await _leaderboard(database, prev_month, limit=1)
    if not board:
        await database.referral_challenges.insert_one({
            "id": str(uuid.uuid4()), "month": prev_month, "winner": None, "referred": 0,
            "reward": 0, "awarded_at": now.isoformat()})
        return
    winner = board[0]
    reward = settings["reward_credits"]
    from cpc_ledger import add_cpc_movement
    entry = await add_cpc_movement(
        winner["sponsor_id"], "PROMO_GRANT", reward,
        idempotency_key=f"referral-challenge:{prev_month}",
        reason=f"🏆 Défi parrainage {prev_month} — meilleur parrain du mois ({winner['referred']} filleul(s))")
    await database.referral_challenges.insert_one({
        "id": str(uuid.uuid4()), "month": prev_month, "winner_id": winner["sponsor_id"],
        "winner": winner["sponsor"], "referred": winner["referred"], "reward": reward,
        "awarded_at": now.isoformat()})
    if entry and winner["sponsor"]:
        try:
            from brevo_service import send_email
            base = os.environ.get("FRONTEND_URL", "").rstrip("/")
            await send_email(
                to_email=winner["sponsor"], to_name=None,
                subject=f"🏆 Félicitations — meilleur parrain du mois {prev_month} !",
                html_content=(f"<div style='font-family:Arial,sans-serif;max-width:560px'><p>Bravo !</p>"
                              f"<p>Avec <b>{winner['referred']} filleul(s)</b> en {prev_month}, vous remportez le défi parrainage : "
                              f"<b>+{reward} CREDI'SCOP</b> viennent d'être crédités sur votre compte.</p>"
                              f"<p><a href='{base}/vendor?tab=cpc' style='background:#5B2E8C;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none'>Voir mon solde</a></p>"
                              "<p style='color:#999;font-size:10px;margin-top:18px'>KDMARCHÉ × O'SCOP</p></div>"),
                tags=["referral-challenge"])
        except Exception as exc:
            logger.warning("Email gagnant défi parrainage échoué : %s", exc)
    from consultation_audit import audit
    await audit("REFERRAL_CHALLENGE_AWARDED", "system", None,
                {"month": prev_month, "winner": winner["sponsor"], "reward": reward})
    logger.info("Défi parrainage %s : %s récompensé (+%s crédits)", prev_month, winner["sponsor"], reward)
