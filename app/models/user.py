"""Accounts.

OpenKeepr supports user accounts for:
  - admin (always required — has full backstage access except message content)
  - regular users (optional — needed for API keys, feedback ownership)

Passwords are hashed with argon2id (memory-hard, side-channel resistant).
TOTP secrets are encrypted at rest with SERVER_ENCRYPTION_KEY (see crypto.py).
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active_flag: Mapped[bool] = mapped_column("is_active", Boolean, default=True, nullable=False)

    # 2FA
    totp_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_codes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # i18n preference (overrides browser detection if set)
    preferred_language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        # Flask-Login looks at this attribute.
        if not self.is_active_flag:
            return False
        if self.locked_until and self.locked_until > _utcnow():
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email!r} admin={self.is_admin}>"
