from __future__ import annotations

from flask import current_app, jsonify, request

from app.blueprints.api.v1 import bp
from app.blueprints.api.v1.auth import require_api_key
from app.extensions import db, limiter
from app.models.feedback import FEEDBACK_TYPES, Feedback
from app.services.audit import audit
from app.version import __version__


@bp.post("/feedback")
@limiter.limit("20 per hour")
@require_api_key("feedback:write")
def post_feedback():
    data = request.get_json(silent=True) or {}
    ftype = data.get("type") or "other"
    if ftype not in FEEDBACK_TYPES:
        return jsonify(error="invalid_type", allowed=list(FEEDBACK_TYPES)), 400
    message = (data.get("message") or "").strip()
    if not (1 <= len(message) <= 5000):
        return jsonify(error="message must be 1..5000 chars"), 400
    fb = Feedback(
        type=ftype,
        message=message,
        contact=(data.get("contact") or "").strip() or None,
        page=(data.get("page") or "").strip() or None,
        user_agent=request.headers.get("User-Agent", "")[:255] or None,
        app_version=__version__,
        language=(data.get("language") or "").strip() or None,
    )
    db.session.add(fb)
    db.session.commit()
    audit("feedback.submitted", subject=str(fb.id), detail={"type": fb.type, "via": "api"})
    return jsonify(id=fb.id, status=fb.status), 201
