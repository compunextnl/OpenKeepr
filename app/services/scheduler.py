"""Background scheduler — runs cleanup on a regular interval.

We use APScheduler's BackgroundScheduler so it lives in-process. For multi-
worker production setups, run the cleanup as a separate cron / systemd timer
to avoid duplicate work (see deploy/openkeepr-cleanup.timer).
"""

from __future__ import annotations

import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from app.services.cleanup import purge_expired_messages, purge_old_verification_codes

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_background_jobs(app: Flask) -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")

    def _cleanup_tick() -> None:
        with app.app_context():
            try:
                purge_expired_messages(max_retention_days=app.config["MAX_RETENTION_DAYS"])
                purge_old_verification_codes()
            except Exception:  # noqa: BLE001
                log.exception("Scheduled cleanup failed")

    # Run every 10 minutes — cheap, and bounds latency on expiry
    _scheduler.add_job(_cleanup_tick, "interval", minutes=10, id="cleanup", coalesce=True)
    _scheduler.start()
    atexit.register(lambda: _scheduler and _scheduler.shutdown(wait=False))
    log.info("Background scheduler started")
