"""Account-bound API-key management (also reachable via the web UI)."""

from __future__ import annotations

from flask import g, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import select

from app.blueprints.api.v1 import bp
from app.blueprints.api.v1.auth import require_api_key
from app.extensions import csrf, db
from app.models.api_key import SCOPES, ApiKey, generate_api_key
from app.services.audit import audit
from app.services.crypto import hash_api_key


@bp.get("/keys/scopes")
def list_scopes():
    """Discoverable list of available scopes — public to ease integration."""
    return jsonify(scopes=SCOPES)


@bp.get("/keys")
@require_api_key("messages:read")
def list_keys():
    rows = db.session.scalars(select(ApiKey).where(ApiKey.user_id == g.api_user.id)).all()
    return jsonify(keys=[{
        "id": k.id,
        "label": k.label,
        "prefix": k.prefix,
        "scopes": k.scopes.split(),
        "revoked": k.revoked,
        "created_at": k.created_at.isoformat(),
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
    } for k in rows])
