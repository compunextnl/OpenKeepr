"""/api/v1/messages/<id>/attachments — programmatic encrypted-file uploads.

Mirrors the browser flow: encrypt client-side, send ciphertext + IV here.
The server only stores opaque bytes — never the plaintext filename, MIME
or content.
"""

from __future__ import annotations

import base64

from flask import current_app, g, jsonify, request
from sqlalchemy import select

from app.blueprints.api.v1 import bp
from app.blueprints.api.v1.auth import require_api_key
from app.extensions import db, limiter
from app.models.attachment import Attachment, generate_attachment_id
from app.models.message import Message
from app.services.attachments import save_blob
from app.services.audit import audit


def _b64(s: str) -> bytes:
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


@bp.post("/messages/<public_id>/attachments")
@limiter.limit("60 per hour")
@require_api_key("attachments:write")
def upload_attachment(public_id: str):
    if not current_app.config["ATTACHMENTS_ENABLED"]:
        return jsonify(error="attachments_disabled"), 404

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.creator_user_id != g.api_user.id:
        return jsonify(error="not_found"), 404
    if msg.is_expired:
        return jsonify(error="expired"), 410
    if msg.opens > 0:
        return jsonify(error="message_sealed"), 403

    data = request.get_json(silent=True) or {}
    try:
        iv = _b64(data["iv_b64"])
        ciphertext = _b64(data["ciphertext_b64"])
    except (KeyError, ValueError):
        return jsonify(error="missing or invalid iv_b64/ciphertext_b64"), 400
    if len(iv) != 12:
        return jsonify(error="iv must be 12 bytes"), 400

    max_file = current_app.config["ATTACHMENTS_MAX_FILE_SIZE_MB"] * 1024 * 1024
    max_total = current_app.config["ATTACHMENTS_MAX_TOTAL_MB"] * 1024 * 1024
    max_count = current_app.config["ATTACHMENTS_MAX_PER_MESSAGE"]
    if len(ciphertext) > max_file:
        return jsonify(error="file_too_large", limit_bytes=max_file), 413
    if len(msg.attachments) >= max_count:
        return jsonify(error="too_many_attachments", limit=max_count), 413
    total_so_far = sum(a.size_bytes for a in msg.attachments)
    if total_so_far + len(ciphertext) > max_total:
        return jsonify(error="total_size_exceeded", limit_bytes=max_total), 413

    att_pid = generate_attachment_id()
    size = save_blob(public_id, att_pid, ciphertext)
    att = Attachment(public_id=att_pid, message_id=msg.id, iv=iv, size_bytes=size)
    db.session.add(att)
    db.session.commit()
    audit("attachment.uploaded", subject=public_id, detail={"via": "api", "att_id": att_pid, "size": size})
    return jsonify(id=att.public_id, size_bytes=size), 201


@bp.get("/messages/<public_id>/attachments")
@require_api_key("attachments:read")
def list_attachments(public_id: str):
    if not current_app.config["ATTACHMENTS_ENABLED"]:
        return jsonify(error="attachments_disabled"), 404

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.creator_user_id != g.api_user.id:
        return jsonify(error="not_found"), 404
    return jsonify(attachments=[
        {"id": a.public_id, "size_bytes": a.size_bytes,
         "created_at": a.created_at.isoformat()}
        for a in msg.attachments
    ])
