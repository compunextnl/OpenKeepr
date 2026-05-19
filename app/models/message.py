"""Message storage.

Design notes — what the server stores and (importantly) what it does NOT.

Stored:
  - `public_id`            short URL-safe random ID used in the URL path
  - `ciphertext`           opaque blob produced by browser-side AES-256-GCM
  - `iv` / `salt`          random bytes the browser uses to derive/encrypt
                           (these are NOT secret; the key in the URL fragment is)
  - `is_markdown`          render hint for the recipient's browser
  - `expires_at`           hard upper bound on retention
  - `max_opens`            optional max read count
  - `opens`                read counter
  - `security_code_hash`   optional argon2 hash of a 6-digit code (when no
                           recipient e-mail allow-list is used)
  - `created_at`           timestamp (for cleanup)

Never stored:
  - decryption key (lives only in URL fragment, never sent to server)
  - plaintext content
  - plaintext recipient e-mail addresses (only HMAC-SHA256, in RecipientHash)
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_public_id(length: int = 22) -> str:
    """Random URL-safe ID; 22 chars ≈ 132 bits of entropy."""
    return secrets.token_urlsafe(length)[:length]


class Message(db.Model):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    # --- Encrypted payload (opaque to server) ---
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # 12 bytes for GCM
    salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # for PBKDF2 (when used)
    kdf_iterations: Mapped[int] = mapped_column(Integer, default=600_000, nullable=False)

    # --- Display hints ---
    is_markdown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Lifecycle ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    max_opens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    burned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Auth ---
    # Only one of these will be populated:
    #   - security_code_hash: argon2 of the 6-digit code (anonymous-recipient mode)
    #   - recipients (table): HMAC-hashed e-mail allow-list
    security_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Audit metadata (no identifying info) ---
    creator_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ciphertext_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recipients: Mapped[list["RecipientHash"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    verification_codes: Mapped[list["VerificationCode"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_expired(self) -> bool:
        if self.burned:
            return True
        if self.max_opens is not None and self.opens >= self.max_opens:
            return True
        # SQLite returns tz-naive datetimes; treat them as UTC.
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return _utcnow() >= exp

    @property
    def requires_recipient_email(self) -> bool:
        return len(self.recipients) > 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message public_id={self.public_id} expires_at={self.expires_at}>"


class RecipientHash(db.Model):
    """HMAC-SHA256 of an allowed recipient e-mail address.

    Two different operators (different RECIPIENT_HASH_SECRET) will produce
    different hashes for the same e-mail, so leaking a DB doesn't even let an
    attacker do offline dictionary attacks across instances.
    """

    __tablename__ = "recipient_hashes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # hex HMAC
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    message: Mapped["Message"] = relationship(back_populates="recipients")

    __table_args__ = (Index("ix_recipient_hashes_msg_hash", "message_id", "email_hash"),)


class VerificationCode(db.Model):
    """Short-lived 6-digit codes used to gate access to a message.

    The code is hashed (argon2). Only the hash is stored. After a small number
    of failed attempts, the row is invalidated.
    """

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Hashed e-mail (matches RecipientHash.email_hash); null in anonymous mode.
    email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    message: Mapped["Message"] = relationship(back_populates="verification_codes")
