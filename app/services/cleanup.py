"""Periodic cleanup of expired data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_

from app.extensions import db
from app.models.message import Message, VerificationCode
from app.services.audit import audit

log = logging.getLogger(__name__)


def purge_expired_messages(*, max_retention_days: int) -> int:
    """Delete messages that are expired, burned, opened-out, or beyond hard cap.

    Returns the number of rows deleted.
    """
    now = datetime.now(timezone.utc)
    hard_cap = now - timedelta(days=max_retention_days)

    # SQLAlchemy can't easily express "opens >= max_opens" portably in a bulk
    # DELETE on SQLite < 3.33; do a select-then-delete loop.
    candidates = db.session.scalars(
        db.select(Message).where(
            or_(
                Message.expires_at <= now,
                Message.burned.is_(True),
                Message.created_at <= hard_cap,
            )
        )
    ).all()

    from app.services.attachments import delete_message_dir

    count = 0
    purged_ids: list[str] = []
    for m in candidates:
        purged_ids.append(m.public_id)
        db.session.delete(m)
        count += 1

    extra = db.session.scalars(
        db.select(Message).where(Message.max_opens.isnot(None))
    ).all()
    for m in extra:
        if m.max_opens is not None and m.opens >= m.max_opens:
            purged_ids.append(m.public_id)
            db.session.delete(m)
            count += 1

    db.session.commit()

    # After DB rows are gone, remove the on-disk attachment blobs too.
    for pid in purged_ids:
        try:
            delete_message_dir(pid)
        except Exception:  # noqa: BLE001
            log.exception("Failed to purge attachment directory for %s", pid)

    if count:
        log.info("Purged %d expired message(s)", count)
        audit("message.purged", detail={"count": count})
    return count


def purge_old_verification_codes() -> int:
    now = datetime.now(timezone.utc)
    result = db.session.execute(
        delete(VerificationCode).where(VerificationCode.expires_at <= now)
    )
    db.session.commit()
    return result.rowcount or 0
