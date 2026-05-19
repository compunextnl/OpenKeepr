"""Bearer-token auth + scope decorator for the API."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps

from flask import g, jsonify, request
from sqlalchemy import select

from app.extensions import db
from app.models.api_key import ApiKey
from app.services.crypto import hash_api_key


def _extract_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_api_key(*scopes: str):
    """Decorator: enforces a valid API key with all requested scopes."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            if not token:
                return jsonify(error="missing_api_key"), 401
            key = db.session.scalar(
                select(ApiKey).where(ApiKey.key_hash == hash_api_key(token))
            )
            if key is None or not key.is_valid:
                return jsonify(error="invalid_or_revoked_api_key"), 401
            for s in scopes:
                if not key.has_scope(s):
                    return jsonify(error="insufficient_scope", required=s), 403
            # Touch last_used_at sparingly (only if older than 1 min)
            now = datetime.now(timezone.utc)
            if (key.last_used_at is None) or (now - key.last_used_at.replace(tzinfo=timezone.utc)).total_seconds() > 60:
                key.last_used_at = now
                db.session.commit()
            g.api_key = key
            g.api_user = key.user
            return fn(*args, **kwargs)

        return wrapper

    return decorator
