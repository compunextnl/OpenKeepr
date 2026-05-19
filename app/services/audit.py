"""Audit logging helper.

Use `audit("event.name", subject="...", detail={...})` from anywhere.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models.audit_log import EVENT_TYPES, AuditLog
from app.services.crypto import hash_ip

log = logging.getLogger(__name__)


def audit(
    event_type: str,
    *,
    subject: str | None = None,
    detail: dict[str, Any] | None = None,
    actor_user_id: int | None = None,
) -> None:
    """Record an audit event. Never raises — best-effort."""
    if event_type not in EVENT_TYPES:
        log.warning("Unknown audit event type: %s", event_type)

    try:
        actor_id = actor_user_id
        if actor_id is None and has_request_context() and current_user.is_authenticated:
            actor_id = int(getattr(current_user, "id", 0)) or None

        ip_hash = None
        if has_request_context():
            ip_hash = hash_ip(request.headers.get("X-Forwarded-For", request.remote_addr))

        entry = AuditLog(
            event_type=event_type,
            actor_user_id=actor_id,
            actor_ip_hash=ip_hash,
            subject=subject,
            detail=json.dumps(detail, separators=(",", ":")) if detail else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        log.exception("Audit logging failed for %s", event_type)
        db.session.rollback()
