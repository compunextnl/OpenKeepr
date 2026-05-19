"""First-boot helpers."""

from __future__ import annotations

import logging
import secrets

from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models.user import User
from app.services.crypto import hash_password


def ensure_initial_admin(logger: logging.Logger) -> None:
    """If no admin exists, create one — printing the password once.

    Only runs after migrations have created the users table. If the table
    doesn't exist yet (fresh checkout, migrations not run), we silently bail
    so `flask db upgrade` can succeed.
    """
    try:
        existing = db.session.scalar(select(User).where(User.is_admin.is_(True)))
    except Exception:
        # Likely "no such table" — migrations haven't run yet. Caller will
        # run them; we'll re-try on next boot.
        return

    if existing is not None:
        return

    email = current_app.config["ADMIN_EMAIL"]
    plain = current_app.config["ADMIN_INITIAL_PASSWORD"] or secrets.token_urlsafe(18)
    user = User(
        email=email.lower(),
        password_hash=hash_password(plain),
        is_admin=True,
    )
    db.session.add(user)
    db.session.commit()
    logger.warning(
        "==========================================================\n"
        "First-time setup: created admin account.\n"
        "  email:    %s\n"
        "  password: %s\n"
        "Log in at /auth/login and enable 2FA immediately.\n"
        "This password will NOT be printed again.\n"
        "==========================================================",
        email,
        plain,
    )
