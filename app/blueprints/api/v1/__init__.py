"""REST API v1 — `/api/v1/*`.

Authentication: `Authorization: Bearer <api-key>` header.
Scopes:         see app/models/api_key.py.

The API is intentionally narrow and mirrors what the browser does. It is
documented in docs/api.md (rendered at /docs/api).
"""

from flask import Blueprint, abort

bp = Blueprint("api_v1", __name__)


@bp.before_request
def _gate_api():  # type: ignore[no-untyped-def]
    """Block all API traffic when the admin has switched the API off."""
    from app.models.settings import get_settings

    s = get_settings()
    if s is not None and not s.api_enabled:
        abort(404)


from app.blueprints.api.v1 import (  # noqa: E402, F401
    attachments,
    auth,
    feedback,
    keys,
    messages,
)
