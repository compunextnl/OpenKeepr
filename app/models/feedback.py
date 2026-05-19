"""User-submitted feedback (in-app form)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


FEEDBACK_TYPES = ("bug", "feature", "praise", "other")
FEEDBACK_STATUS = ("new", "in_progress", "resolved", "spam")


class Feedback(db.Model):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)  # optional e-mail
    page: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new", index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
