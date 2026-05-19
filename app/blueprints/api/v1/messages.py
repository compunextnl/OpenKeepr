"""/api/v1/messages — programmatic message creation & metadata.

NOTE: This API does NOT decrypt messages for you. By design — your server-side
code holds the key, and we keep zero-knowledge guarantees intact. To create a
message via the API, encrypt client-side first; we accept the ciphertext only.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from flask import current_app, g, jsonify, request
from sqlalchemy import select

from app.blueprints.api.v1 import bp
from app.blueprints.api.v1.auth import require_api_key
from app.extensions import db, limiter
from app.models.message import (
    Message,
    RecipientHash,
    generate_public_id,
)
from app.services.audit import audit
from app.services.crypto import (
    hash_email,
    hash_password,
    random_6digit_code,
)


def _b64(s: str) -> bytes:
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@bp.post("/messages")
@limiter.limit("60 per hour")
@require_api_key("messages:write")
def create_message():
    data = request.get_json(silent=True) or {}
    try:
        ct = _b64(data["ciphertext_b64"])
        iv = _b64(data["iv_b64"])
        salt = _b64(data["salt_b64"])
    except (KeyError, ValueError):
        return jsonify(error="missing or invalid ciphertext/iv/salt"), 400

    max_kb = current_app.config["MAX_MESSAGE_SIZE_KB"]
    if len(ct) > max_kb * 1024:
        return jsonify(error=f"ciphertext exceeds {max_kb} KB"), 413
    if len(iv) != 12 or len(salt) not in (16, 32):
        return jsonify(error="iv must be 12 bytes; salt 16 or 32 bytes"), 400

    hard_cap_days = current_app.config["MAX_RETENTION_DAYS"]
    hours = max(1, min(int(data.get("expires_in_hours") or 24), hard_cap_days * 24))
    expires_at = _utcnow() + timedelta(hours=hours)

    max_opens = data.get("max_opens")
    if max_opens in (None, 0, "0"):
        max_opens = None
    else:
        try:
            max_opens = max(1, min(int(max_opens), current_app.config["MAX_OPENS_LIMIT"]))
        except (TypeError, ValueError):
            return jsonify(error="invalid max_opens"), 400

    from email_validator import EmailNotValidError, validate_email

    raw_input = [r for r in (data.get("recipients") or []) if r and r.strip()]
    valid: list[str] = []
    invalid: list[str] = []
    for r in raw_input:
        try:
            info = validate_email(r.strip(), check_deliverability=False)
            valid.append(info.normalized.lower())
        except EmailNotValidError:
            invalid.append(r.strip())
    if invalid:
        return jsonify(error="invalid_recipients", invalid=invalid), 400
    _seen: set[str] = set()
    recipients_raw = [r for r in valid if not (r in _seen or _seen.add(r))]
    use_code = bool(data.get("use_security_code")) or not recipients_raw

    security_code_plain = None
    security_code_hash = None
    if not recipients_raw and use_code:
        security_code_plain = random_6digit_code()
        security_code_hash = hash_password(security_code_plain)

    msg = Message(
        public_id=generate_public_id(),
        ciphertext=ct,
        iv=iv,
        salt=salt,
        is_markdown=bool(data.get("is_markdown")),
        expires_at=expires_at,
        max_opens=max_opens,
        security_code_hash=security_code_hash,
        creator_user_id=g.api_user.id,
        ciphertext_size=len(ct),
    )
    db.session.add(msg)
    db.session.flush()
    for email in recipients_raw:
        db.session.add(RecipientHash(message_id=msg.id, email_hash=hash_email(email)))
    db.session.commit()
    audit("message.created", subject=msg.public_id, detail={"via": "api", "size": len(ct)})

    base = current_app.config["BASE_URL"].rstrip("/")
    return (
        jsonify(
            id=msg.public_id,
            url=f"{base}/m/{msg.public_id}",
            expires_at=msg.expires_at.replace(tzinfo=timezone.utc).isoformat(),
            max_opens=msg.max_opens,
            security_code=security_code_plain,
            requires_email=bool(recipients_raw),
        ),
        201,
    )


@bp.get("/messages/<public_id>")
@require_api_key("messages:read")
def get_message_meta(public_id: str):
    """Return metadata for a message you created. Never returns content."""
    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.creator_user_id != g.api_user.id:
        return jsonify(error="not_found"), 404
    return jsonify(
        id=msg.public_id,
        created_at=msg.created_at.replace(tzinfo=timezone.utc).isoformat(),
        expires_at=msg.expires_at.replace(tzinfo=timezone.utc).isoformat(),
        max_opens=msg.max_opens,
        opens=msg.opens,
        burned=msg.burned,
        is_markdown=msg.is_markdown,
        recipients_count=len(msg.recipients),
        size_bytes=msg.ciphertext_size,
    )


@bp.delete("/messages/<public_id>")
@require_api_key("messages:write")
def burn_message(public_id: str):
    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.creator_user_id != g.api_user.id:
        return jsonify(error="not_found"), 404
    msg.burned = True
    db.session.commit()
    audit("message.burned", subject=public_id, detail={"via": "api"})
    return jsonify(ok=True)
