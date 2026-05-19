"""Attachments — encrypted file blobs linked to a Message.

Storage strategy: ciphertext lives on the filesystem (under
`instance/attachments/<message_public_id>/<public_id>.bin`), the DB only
holds the metadata needed to find it back and serve it.

Important: the **original filename, MIME-type and contents** are all part of
the encrypted blob and are NEVER stored or seen by the server.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_attachment_id(length: int = 22) -> str:
    return secrets.token_urlsafe(length)[:length]


class Attachment(db.Model):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # 12-byte AES-GCM nonce used for this attachment (each attachment has its
    # own IV so the same key can encrypt multiple things safely).
    iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Cleartext metadata stored ONLY for cleanup/quota tracking — derived from
    # the ciphertext file. Plaintext name/MIME are inside the encrypted blob.
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    # `passive_deletes=True` + cascade tells SQLAlchemy NOT to null out the FK
    # before deleting (which would violate the NOT NULL constraint) — children
    # are deleted alongside the parent in one transaction.
    message = relationship(
        "Message",
        backref=db.backref(
            "attachments",
            cascade="all, delete-orphan",
            passive_deletes=True,
            lazy="selectin",
        ),
    )
