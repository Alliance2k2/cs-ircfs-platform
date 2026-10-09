"""In-process weekly advice scheduler (WP2), controlled by settings.

Disabled unless ``ADVICE_SCHEDULE_ENABLED=true``. A single background task sleeps
until the next configured slot (``ADVICE_SCHEDULE_WEEKDAY`` + ``ADVICE_SCHEDULE_TIME``,
Africa/Kigali), runs the same idempotent send as ``scripts/send_weekly_advice.py``,
then sleeps until the following week. Because ``send_weekly_advice`` records each
sector's send in ``advice_runs``, an overlap with the cron script never sends twice.
"""
import asyncio
import logging
from datetime import datetime

from app.core.config import Settings
from app.db.session import SessionLocal
from app.services.advisory import KIGALI, next_advice_run, send_weekly_advice

logger = logging.getLogger(__name__)
CHECK_EVERY_SECONDS = 30  # tolerate clock skew and slow starts without missing the slot


async def run_once() -> None:
    """Send this week's advice on a worker thread; log but never crash the API."""
    def _send() -> None:
        db = SessionLocal()
        try:
            summary = send_weekly_advice(db)
        finally:
            db.close()
        if summary["sectors"]:
            logger.info(
                "Weekly advice sent: %d sectors, %d recipients (week %s, dry_run=%s)",
                len(summary["sectors"]), summary["total_recipients"], summary["week_key"], summary["dry_run"],
            )
        elif summary["skipped_already_sent"]:
            logger.info("Weekly advice already sent for week %s; skipped", summary["week_key"])
        else:
            logger.info("Weekly advice skipped: no sectors with rain-gauge readings")
    try:
        await asyncio.to_thread(_send)
    except Exception:  # noqa: BLE001 - a failed send must never take down the API
        logger.exception("Weekly advice send failed")


async def _loop(settings: Settings) -> None:
    while True:
        target = next_advice_run(settings)
        if target is None:
            return  # disabled while running (settings reloaded on restart)
        seconds = max(1.0, (target - datetime.now(KIGALI)).total_seconds())
        await asyncio.sleep(seconds)
        await run_once()
        await asyncio.sleep(CHECK_EVERY_SECONDS)  # let the slot pass before planning the next week


def start(settings: Settings):
    """Return the scheduler task, or None when the scheduler is disabled."""
    if not settings.advice_schedule_enabled:
        return None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    return loop.create_task(_loop(settings))
