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
_iabois_task: asyncio.Task | None = None
_health_task: asyncio.Task | None = None
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
        try:
            if datetime.utcnow().day == 1:
                from vendor_monthly_report import send_vendor_monthly_reports
                await send_vendor_monthly_reports()
        except Exception as exc:
            logger.exception("Scheduler monthly report iteration crashed: %s", exc)
        try:
            if datetime.utcnow().day == 1:
                from routes_vendor_contracts import send_monthly_guarantees_report
                await send_monthly_guarantees_report()
        except Exception as exc:
            logger.exception("Scheduler guarantees report iteration crashed: %s", exc)
        try:
            prev_month = (datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            from ged_archive_watch import run_monthly_archives_with_alerts
            await run_monthly_archives_with_alerts(_db, prev_month)
        except Exception as exc:
            logger.exception("Scheduler GED archives crashed: %s", exc)
        try:
            from routes_vendor_onboarding import check_vendor_subscriptions
            await check_vendor_subscriptions(_db)
        except Exception as exc:
            logger.exception("Scheduler vendor subscriptions crashed: %s", exc)
        try:
            from vendor_suspension import check_vendor_suspensions
            await check_vendor_suspensions(_db)
        except Exception as exc:
            logger.exception("Scheduler vendor suspensions crashed: %s", exc)
        try:
            from vendor_emails import check_abandoned_onboardings
            await check_abandoned_onboardings(_db)
        except Exception as exc:
            logger.exception("Scheduler abandoned onboardings crashed: %s", exc)
        try:
            from vendor_weekly_report import send_weekly_unpaid_report
            await send_weekly_unpaid_report(_db)
        except Exception as exc:
            logger.exception("Scheduler weekly unpaid report crashed: %s", exc)
        try:
            from routes_accounting import snapshot_fiscal_register
            await snapshot_fiscal_register(_db)
        except Exception as exc:
            logger.exception("Scheduler fiscal register snapshot crashed: %s", exc)
        try:
            from cpc_ledger import expire_cpc_purchases
            await expire_cpc_purchases(_db)
        except Exception as exc:
            logger.exception("Scheduler CPC expiry crashed: %s", exc)
        try:
            from consultation_notify import close_due_consultations
            await close_due_consultations(_db)
        except Exception as exc:
            logger.exception("Scheduler due closures crashed: %s", exc)
        try:
            from routes_consultation_templates import run_recurring_templates
            await run_recurring_templates(_db)
        except Exception as exc:
            logger.exception("Scheduler recurring templates crashed: %s", exc)
        try:
            from routes_benchmark import send_monthly_benchmarks
            await send_monthly_benchmarks(_db)
        except Exception as exc:
            logger.exception("Scheduler monthly benchmarks crashed: %s", exc)
        try:
            from routes_liquidity import snapshot_liquidity
            await snapshot_liquidity(_db)
        except Exception as exc:
            logger.exception("Scheduler liquidity snapshot crashed: %s", exc)
        try:
            from vendor_weekly_recap import send_weekly_recaps
            await send_weekly_recaps(_db)
        except Exception as exc:
            logger.exception("Scheduler weekly recap crashed: %s", exc)
        try:
            from routes_bids import send_closure_reminders
            await send_closure_reminders(_db)
        except Exception as exc:
            logger.exception("Scheduler closure reminders crashed: %s", exc)
        try:
            from campaign_alerts import check_campaign_closure_alerts
            await check_campaign_closure_alerts(_db)
        except Exception as exc:
            logger.exception("Scheduler campaign alerts crashed: %s", exc)
        await asyncio.sleep(PASS_J3_INTERVAL_SECONDS)


def start_scheduler():
    global _task, _iabois_task, _health_task
    if _task is None or _task.done():
        loop = asyncio.get_event_loop()
        _task = loop.create_task(_scheduler_loop())
        logger.info("Scheduler started (PASS J-3 + auto-renew every %.1fh)", PASS_J3_INTERVAL_SECONDS / 3600)
    if _iabois_task is None or _iabois_task.done():
        from connectors.iabois_sync import iabois_sync_loop
        _iabois_task = asyncio.get_event_loop().create_task(iabois_sync_loop())
        logger.info("IA Bois sync loop started (every 15 min)")
    if _health_task is None or _health_task.done():
        from connectors.health_watch import health_watch_loop
        _health_task = asyncio.get_event_loop().create_task(health_watch_loop())
        logger.info("Ecosystem health watch started (every 10 min)")


def stop_scheduler():
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
