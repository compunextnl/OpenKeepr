"""Runtime-mutable settings (admin-tweakable, persisted in DB).

These are deliberately separate from environment-based config: they're the
things an operator wants to change without restarting the app, like enabling
maintenance mode or changing the banner text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Settings(db.Model):
    """Single-row table holding mutable runtime settings."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    maintenance_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Admin-tweakable defaults
    default_expiry_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    # Public banner (optional notice shown at top of every page)
    banner_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_level: Mapped[str | None] = mapped_column(String(16), nullable=True)  # info|warning|danger

    # Feature toggles editable at runtime (combined AND-style with env-level
    # flags; either side being False disables the feature).
    public_login_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_registration_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


def get_settings() -> Optional[Settings]:
    """Fetch (or lazily create) the singleton Settings row."""
    obj = db.session.get(Settings, 1)
    if obj is None:
        obj = Settings(id=1)
        db.session.add(obj)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            obj = db.session.get(Settings, 1)
    return obj
