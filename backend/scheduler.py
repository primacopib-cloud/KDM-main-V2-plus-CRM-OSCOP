"""
Lightweight scheduler for KDMARCHE × O'SCOP background jobs.

Runs as an asyncio task started during FastAPI lifespan.
Currently scheduled jobs:
  - PASS J-3 expiry reminder batch  → every 6h
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Run interval (seconds) — every 6 hours
PASS_J3_INTERVAL_SECONDS = 6 * 60 * 60
AUTO_RENEW_INTERVAL_SECONDS = 6 * 60 * 60

_task: asyncio.Task | None = None
_db = None


def set_scheduler_database(database):
    global _db
    _db = database


async def _send_pass_j3_batch():
    """One iteration of the J-3 reminder. Mirrors the admin endpoint, idempotent via `j3_notified_at`."""
    if _db is None:
        return 0
    from brevo_service import notify_pass_expiry_j3, is_brevo_configured
    if not is_brevo_configured():
        logger.info("Scheduler: Brevo not configured — skipping PASS J-3 batch")
        return 0
    now = datetime.utcnow()
    window_start = now + timedelta(days=2, hours=12)
    window_end = now + timedelta(days=3, hours=12)
    cursor = _db.lolodrive_passes.find({
        "status": "ACTIVE",
        "ends_at": {"$gte": window_start, "$lte": window_end},
        "$or": [{"j3_notified_at": {"$exists": False}}, {"j3_notified_at": None}],
    }, {"_id": 0})
    sent = 0
    async for p in cursor:
        user = await _db.users.find_one({"id": p["user_id"]}, {"_id": 0, "email": 1, "contact_name": 1, "phone": 1})
        if not user or not user.get("email"):
            continue
        try:
            await notify_pass_expiry_j3(
                to_email=user["email"],
                to_name=user.get("contact_name"),
                to_phone=user.get("phone"),
                pass_id=p.get("id", "PASS"),
                ends_at=p["ends_at"],
            )
            await _db.lolodrive_passes.update_one(
                {"id": p["id"]}, {"$set": {"j3_notified_at": now, "updated_at": now}}
            )
            sent += 1
        except Exception as exc:
            logger.warning("Scheduler PASS J-3 failure for %s: %s", user.get("email"), exc)
    if sent:
        logger.info("Scheduler PASS J-3: %d notifications sent", sent)
    return sent


async def _scheduler_loop():
    """Main background loop. Sleeps then runs jobs forever, with crash protection."""
    # Slight delay on startup so the API is ready before the first run.
    await asyncio.sleep(60)
    while True:
        try:
            await _send_pass_j3_batch()
        except Exception as exc:
            logger.exception("Scheduler J3 iteration crashed: %s", exc)
        try:
            from pass_auto_renew import run_auto_renew_batch
            await run_auto_renew_batch(_db)
        except Exception as exc:
            logger.exception("Scheduler auto-renew iteration crashed: %s", exc)
        await asyncio.sleep(PASS_J3_INTERVAL_SECONDS)


def start_scheduler():
    global _task
    if _task is None or _task.done():
        loop = asyncio.get_event_loop()
        _task = loop.create_task(_scheduler_loop())
        logger.info("Scheduler started (PASS J-3 + auto-renew every %.1fh)", PASS_J3_INTERVAL_SECONDS / 3600)


def stop_scheduler():
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
