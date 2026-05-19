"""API keys.

We store only a SHA-256 hash of the key (with a per-key prefix shown in the
UI for identification). The plaintext key is shown to the user exactly once,
at creation time, and never recoverable from the database.

Format: `okp_<24-char-rand>` — the `okp_` prefix lets log scanners detect
leaked keys (similar to how GitHub uses `ghp_*`).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Scopes available on API keys. Keep the list small and explicit.
SCOPES = {
    "messages:write": "Create new messages",
    "messages:read": "Retrieve metadata for messages you created",
    "attachments:write": "Upload encrypted attachments to your messages",
    "attachments:read": "List attachment metadata for your messages",
    "feedback:write": "Submit feedback",
    "admin:read": "Read admin-only data (audit log, settings) — admin only",
    "admin:write": "Mutate admin-only data — admin only",
}


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (plain_key, prefix, sha256_hex)."""
    rand = secrets.token_urlsafe(24)
    plain = f"okp_{rand}"
    prefix = plain[:12]  # shown in UI: okp_xxxxxxxx
    digest = hashlib.sha256(plain.encode()).hexdigest()
    return plain, prefix, digest


class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Space-separated scopes (e.g. "messages:write messages:read")
    scopes: Mapped[str] = mapped_column(String(255), default="messages:write", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User")

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and self.expires_at <= _utcnow():
            return False
        return True

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes.split()
