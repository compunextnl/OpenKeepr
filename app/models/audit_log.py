"""Append-only audit log.

We record metadata about security-relevant events ONLY. We never log message
content, decryption keys, plaintext recipient e-mails, passwords, TOTP codes,
or API keys.

Indexed for fast filtering by event type & actor.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Canonical event types — keep this list tight.
EVENT_TYPES = {
    "auth.login.success",
    "auth.login.failed",
    "auth.logout",
    "auth.2fa.enabled",
    "auth.2fa.disabled",
    "auth.password.changed",
    "auth.register",
    "user.locked",
    "user.unlocked",
    "message.created",
    "message.viewed",
    "message.expired",
    "message.burned",
    "message.purged",
    "verification.sent",
    "verification.verified",
    "verification.failed",
    "apikey.created",
    "apikey.revoked",
    "admin.setting.changed",
    "admin.maintenance.enabled",
    "admin.maintenance.disabled",
    "admin.email.test.sent",
    "admin.email.test.failed",
    "feedback.submitted",
}


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Actor — either a user id (if logged in) or null. We deliberately do
    # NOT store IP addresses by default; flip the constant below if you have
    # a legitimate need and have updated your privacy policy.
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Subject — what was acted upon. Stored as opaque short identifiers.
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Free-form structured detail. JSON-serialized but stored as TEXT for
    # SQLite portability. Must NOT contain PII.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
