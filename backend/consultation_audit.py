"""Journal d'audit des consultations — append-only, chaîné par hachage SHA-256 (toute altération casse la chaîne)."""
import hashlib
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

db = None


def set_audit_database(database):
    global db
    db = database


async def audit(event_type: str, actor: str, consultation_id: str = None, payload: dict = None):
    for _ in range(3):
        last = await db.audit_journal.find_one({}, {"_id": 0, "seq": 1, "sha256_self": 1}, sort=[("seq", -1)])
        seq = (last or {}).get("seq", 0) + 1
        prev = (last or {}).get("sha256_self", "genesis")
        entry = {
            "seq": seq, "event_type": event_type, "actor": actor,
            "consultation_id": consultation_id, "payload": payload or {},
            "ts": datetime.now(timezone.utc).isoformat(), "sha256_prev": prev,
        }
        body = json.dumps(entry, sort_keys=True, default=str)
        entry["sha256_self"] = hashlib.sha256((prev + body).encode()).hexdigest()
        try:
            await db.audit_journal.insert_one({**entry})
            return entry["sha256_self"]
        except Exception:
            continue
    return None


async def verify_chain(limit: int = 5000) -> dict:
    """Revérifie l'intégrité de la chaîne complète."""
    prev = "genesis"
    count = 0
    async for e in db.audit_journal.find({}, {"_id": 0}).sort("seq", 1).limit(limit):
        stored_self = e.pop("sha256_self")
        if e.get("sha256_prev") != prev:
            return {"valid": False, "broken_at_seq": e["seq"], "reason": "prev hash mismatch"}
        body = json.dumps(e, sort_keys=True, default=str)
        if hashlib.sha256((prev + body).encode()).hexdigest() != stored_self:
            return {"valid": False, "broken_at_seq": e["seq"], "reason": "self hash mismatch"}
        prev = stored_self
        count += 1
    return {"valid": True, "entries_verified": count}
